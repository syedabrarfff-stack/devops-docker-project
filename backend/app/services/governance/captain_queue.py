from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.services.notifications.slack import notify_slack
from app.services.notifications.telegram import notify_telegram

logger = logging.getLogger(__name__)

HIGH_PRIORITY_ACTIONS = {
    "pricing_decision",
    "contract_signing",
    "production_deployment",
    "payment_collection",
}
MEDIUM_PRIORITY_ACTIONS = {
    "proposal",
    "proposal_review",
    "proposal_sending",
    "outreach_emails",
    "client_communication",
}


class CaptainQueue:
    async def add_item(
        self,
        action_type: str,
        title: str,
        summary: str,
        payload: dict,
        risk_level: str,
        tenant_id,
    ) -> ApprovalRequest:
        tenant_uuid = _tenant_uuid(tenant_id)
        priority = _priority(action_type, risk_level)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                approval = ApprovalRequest(
                    tenant_id=tenant_uuid,
                    action_type=action_type,
                    title=title,
                    summary=summary,
                    payload=payload or {},
                    risk_level=(risk_level or "MEDIUM").upper(),
                    priority=priority,
                    status=ApprovalStatus.PENDING,
                    raised_by=(payload or {}).get("raised_by", "JARVIS"),
                )
                session.add(approval)
                await session.flush()
                await self._audit(
                    session,
                    tenant_uuid,
                    "captain_queue_item_created",
                    approval,
                    {"priority": priority, "action_type": action_type},
                )
                await session.refresh(approval)
                data = _serialize(approval)

        await _notify_new_item(data)
        return approval

    async def get_pending(self, tenant_id) -> list[ApprovalRequest]:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                rows = (
                    await session.execute(
                        select(ApprovalRequest)
                        .where(
                            ApprovalRequest.tenant_id == tenant_uuid,
                            ApprovalRequest.status == ApprovalStatus.PENDING,
                        )
                        .order_by(ApprovalRequest.priority.desc(), ApprovalRequest.created_at.asc())
                        .limit(100)
                    )
                ).scalars().all()
                return list(rows)

    async def approve(self, approval_id, captain_note: str | None, tenant_id) -> dict:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                approval = await _load_approval(session, tenant_uuid, approval_id)
                if not approval:
                    raise ValueError("Approval not found")

                approval.status = ApprovalStatus.APPROVED
                approval.captain_note = captain_note
                approval.decided_by = "Captain"
                approval.decided_at = datetime.now(UTC)
                approval.approved_at = approval.decided_at
                action_result = await _execute_queued_action(session, tenant_uuid, approval)
                await self._audit(
                    session,
                    tenant_uuid,
                    "captain_queue_item_approved",
                    approval,
                    {"captain_note": captain_note, "action_result": action_result},
                )
                data = _serialize(approval)

        if action_result.get("type") == "outreach_enrollment_review_approved":
            action_result = await _queue_outreach_after_approval(tenant_uuid, action_result)

        await _notify_decision(data, "approved", action_result)
        return {"status": "approved", "approval": data, "action_result": action_result}

    async def reject(self, approval_id, reason: str | None, tenant_id) -> dict:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                approval = await _load_approval(session, tenant_uuid, approval_id)
                if not approval:
                    raise ValueError("Approval not found")

                approval.status = ApprovalStatus.REJECTED
                approval.captain_note = reason
                approval.decided_by = "Captain"
                approval.decided_at = datetime.now(UTC)
                await self._audit(
                    session,
                    tenant_uuid,
                    "captain_queue_item_rejected",
                    approval,
                    {"reason": reason},
                )
                data = _serialize(approval)

        await _notify_decision(data, "rejected", {"executed": False, "reason": reason})
        return {"status": "rejected", "approval": data}

    async def pending_count(self, tenant_id) -> int:
        return len(await self.get_pending(tenant_id))

    async def _audit(
        self,
        session,
        tenant_id: uuid.UUID,
        action: str,
        approval: ApprovalRequest,
        payload: dict[str, Any],
    ) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type="approval_request",
                entity_id=approval.id,
                actor="CaptainQueue",
                after_json={"approval_id": str(approval.id), **payload},
                details={"approval_id": str(approval.id), **payload},
            )
        )


async def _load_approval(session, tenant_id: uuid.UUID, approval_id) -> ApprovalRequest | None:
    return await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.id == uuid.UUID(str(approval_id)),
        )
    )


async def _execute_queued_action(session, tenant_id: uuid.UUID, approval: ApprovalRequest) -> dict:
    payload = approval.payload or {}

    if payload.get("proposal_id"):
        from app.models.governance import Proposal

        proposal = await session.scalar(
            select(Proposal).where(
                Proposal.tenant_id == tenant_id,
                Proposal.id == int(payload["proposal_id"]),
            )
        )
        if proposal:
            proposal.status = "approved"
            proposal.approved_at = datetime.now(UTC)
            return {"executed": True, "type": "proposal_approved", "proposal_id": proposal.id}
        return {"executed": False, "type": "proposal_approved", "reason": "proposal_not_found"}

    if payload.get("follow_up_queue_id"):
        from app.models.outreach import FollowUpQueue, FollowUpStatus

        follow_up = await session.scalar(
            select(FollowUpQueue).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.id == uuid.UUID(str(payload["follow_up_queue_id"])),
            )
        )
        if follow_up:
            follow_up.status = FollowUpStatus.PENDING
            follow_up.scheduled_at = datetime.now(UTC)
            return {"executed": True, "type": "outreach_requeued", "follow_up_queue_id": str(follow_up.id)}
        return {"executed": False, "type": "outreach_requeued", "reason": "follow_up_not_found"}

    if approval.action_type == "outreach_enrollment_review" and payload.get("lead_id"):
        return {
            "executed": False,
            "type": "outreach_enrollment_review_approved",
            "lead_id": str(payload["lead_id"]),
            "reason": "queue_after_approval_commit",
        }

    return {"executed": True, "type": "logged_approval"}


async def _queue_outreach_after_approval(tenant_id: uuid.UUID, action_result: dict[str, Any]) -> dict[str, Any]:
    from app.models.outreach import FollowUpQueue, FollowUpStatus
    from app.services.outreach.engine import outreach_engine

    lead_id = action_result.get("lead_id")
    if not lead_id:
        return {**action_result, "executed": False, "reason": "missing_lead_id"}

    await outreach_engine.queue_sequence(lead_id, tenant_id)

    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, str(tenant_id))
        queued_count = await session.scalar(
            select(func.count()).select_from(FollowUpQueue).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.lead_id == uuid.UUID(str(lead_id)),
                FollowUpQueue.status == FollowUpStatus.PENDING,
            )
        )

    return {
        **action_result,
        "executed": bool(queued_count),
        "queued_followups": int(queued_count or 0),
        "reason": "captain_approved_and_queued" if queued_count else "captain_approved_but_not_queued",
    }


async def _notify_new_item(data: dict) -> None:
    await notify_slack(
        f"*JARVIS Approval Required*\n\n*{data['title']}*\nRisk: {data['risk_level']}\n{data['summary'][:300]}"
    )
    await notify_telegram(
        f"*JARVIS Approval Required*\n\n*{data['title']}*\nRisk: {data['risk_level']}\n{data['summary'][:500]}"
    )
    await _broadcast("approval_created", data)


async def _notify_decision(data: dict, decision: str, action_result: dict) -> None:
    await notify_slack(f"*Captain {decision.upper()}*: {data['title']}")
    await notify_telegram(f"*Captain {decision.upper()}*: {data['title']}")
    await _broadcast("approval_decided", {**data, "decision": decision, "action_result": action_result})


async def _broadcast(event_type: str, data: dict) -> None:
    try:
        from app.api.v1.routes.ws import broadcast, captain_broadcast

        await broadcast(event_type, data, persist=True)
        await captain_broadcast(event_type, data)
    except Exception as exc:
        logger.debug("Approval websocket broadcast skipped: %s", exc)


def _priority(action_type: str, risk_level: str) -> int:
    action = (action_type or "").lower()
    risk = (risk_level or "").lower()
    if risk == "critical" or action in HIGH_PRIORITY_ACTIONS:
        return 100
    if risk == "high":
        return 80
    if action in MEDIUM_PRIORITY_ACTIONS or "proposal" in action:
        return 50
    if risk == "medium":
        return 40
    return 10


def _tenant_uuid(tenant_id) -> uuid.UUID:
    resolved = tenant_id or settings.JARVIS_DEFAULT_TENANT_ID
    if not resolved:
        raise ValueError("tenant_id is required")
    return uuid.UUID(str(resolved))


def _serialize(approval: ApprovalRequest) -> dict:
    return {
        "id": str(approval.id),
        "title": approval.title,
        "action_type": approval.action_type,
        "summary": approval.summary,
        "risk_level": (approval.risk_level or "medium").lower(),
        "priority": approval.priority,
        "estimated_cost": approval.estimated_cost,
        "benefits": approval.benefits,
        "risks": approval.risks,
        "rollback_plan": approval.rollback_plan,
        "payload": approval.payload or {},
        "status": _status_value(approval.status).lower(),
        "captain_note": approval.captain_note,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status or "PENDING")


captain_queue = CaptainQueue()
