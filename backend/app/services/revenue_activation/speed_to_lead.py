from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.lead import Lead
from app.models.outreach import FollowUpQueue, FollowUpStatus, OutreachEmail, OutreachLog, OutreachStatus
from app.models.revenue_activation import SpeedToLeadEvent
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.outreach.engine import PERSONAS
from app.services.revenue_activation.teaching_engine import teaching_engine

logger = logging.getLogger(__name__)

SPEED_TO_LEAD_STEP = 90


class SpeedToLeadEngine:
    async def trigger(self, tenant_id=None, lookback_minutes: int = 5) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        cutoff = datetime.now(UTC) - timedelta(minutes=max(1, min(lookback_minutes, 60)))
        captain_online = await self._captain_online()
        results: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                candidates = await self._engagement_candidates(session, tenant_uuid, cutoff)

                for candidate in candidates:
                    if await self._already_processed(session, tenant_uuid, candidate):
                        continue
                    lead = await self._lead_for_candidate(session, tenant_uuid, candidate)
                    if not lead:
                        await self._audit(
                            session,
                            tenant_uuid,
                            "speed_to_lead_skipped_no_lead",
                            None,
                            {"candidate": candidate},
                        )
                        continue

                    draft = await self._draft_followup(lead, candidate)
                    if captain_online:
                        action = await self._queue_for_captain(session, tenant_uuid, lead, candidate, draft)
                    else:
                        action = await self._schedule_send(session, tenant_uuid, lead, candidate, draft)
                    scheduled_send_at = action.get("_scheduled_send_at_dt")
                    public_action = {key: value for key, value in action.items() if not key.startswith("_")}

                    event = SpeedToLeadEvent(
                        tenant_id=tenant_uuid,
                        lead_id=lead.id,
                        source_type=candidate["source_type"],
                        source_id=candidate["source_id"],
                        trigger_type=candidate["trigger_type"],
                        captain_online=captain_online,
                        action_taken=action["action_taken"],
                        draft_subject=draft["subject"],
                        draft_body=draft["body"],
                        scheduled_send_at=scheduled_send_at,
                        payload={
                            "candidate": candidate,
                            "draft": draft,
                            "action": public_action,
                        },
                    )
                    session.add(event)
                    await self._audit(
                        session,
                        tenant_uuid,
                        "speed_to_lead_processed",
                        lead.id,
                        {
                            "source_type": candidate["source_type"],
                            "source_id": candidate["source_id"],
                            "trigger_type": candidate["trigger_type"],
                            "captain_online": captain_online,
                            **public_action,
                        },
                    )
                    results.append(
                        {
                            "lead_id": str(lead.id),
                            "company": lead.company_name or lead.company,
                            "trigger_type": candidate["trigger_type"],
                            "captain_online": captain_online,
                            **public_action,
                        }
                    )

        try:
            await teaching_engine.analyze_recent_outreach(tenant_uuid, days=30)
        except Exception as exc:
            logger.warning("Speed-to-lead teaching analysis skipped: %s", exc)

        return {
            "tenant_id": str(tenant_uuid),
            "lookback_minutes": lookback_minutes,
            "captain_online": captain_online,
            "processed": len(results),
            "results": results,
        }

    async def _engagement_candidates(self, session, tenant_uuid: uuid.UUID, cutoff: datetime) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        outreach_rows = (
            await session.execute(
                select(OutreachLog)
                .where(
                    OutreachLog.tenant_id == tenant_uuid,
                    OutreachLog.updated_at >= cutoff,
                    OutreachLog.status.in_([OutreachStatus.OPENED, OutreachStatus.REPLIED]),
                )
                .order_by(OutreachLog.updated_at.desc())
                .limit(100)
            )
        ).scalars().all()
        for row in outreach_rows:
            candidates.append(
                {
                    "source_type": "outreach_log",
                    "source_id": str(row.id),
                    "lead_id": str(row.lead_id) if row.lead_id else None,
                    "trigger_type": row.status.value.lower(),
                    "subject": row.subject,
                    "body_preview": (row.body_text or "")[:400],
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
            )

        email_rows = (
            await session.execute(
                select(OutreachEmail)
                .where(
                    OutreachEmail.tenant_id == tenant_uuid,
                    OutreachEmail.updated_at >= cutoff,
                    OutreachEmail.status.in_(["opened", "replied"]),
                )
                .order_by(OutreachEmail.updated_at.desc())
                .limit(100)
            )
        ).scalars().all()
        for row in email_rows:
            candidates.append(
                {
                    "source_type": "outreach_email",
                    "source_id": str(row.id),
                    "lead_id": None,
                    "to_email": row.to_email,
                    "to_name": row.to_name,
                    "trigger_type": str(row.status).lower(),
                    "subject": row.subject,
                    "body_preview": (row.body or "")[:400],
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
            )
        return candidates

    async def _already_processed(self, session, tenant_uuid: uuid.UUID, candidate: dict[str, Any]) -> bool:
        existing = await session.scalar(
            select(SpeedToLeadEvent.id)
            .where(
                SpeedToLeadEvent.tenant_id == tenant_uuid,
                SpeedToLeadEvent.source_type == candidate["source_type"],
                SpeedToLeadEvent.source_id == candidate["source_id"],
            )
            .limit(1)
        )
        return bool(existing)

    async def _lead_for_candidate(self, session, tenant_uuid: uuid.UUID, candidate: dict[str, Any]) -> Lead | None:
        if candidate.get("lead_id"):
            return await session.scalar(
                select(Lead).where(Lead.tenant_id == tenant_uuid, Lead.id == uuid.UUID(str(candidate["lead_id"])))
            )
        email = (candidate.get("to_email") or "").strip().lower()
        if not email:
            return None
        return await session.scalar(
            select(Lead)
            .where(
                Lead.tenant_id == tenant_uuid,
                or_(Lead.email == email, Lead.contact_email == email),
            )
            .limit(1)
        )

    async def _draft_followup(self, lead: Lead, candidate: dict[str, Any]) -> dict[str, str]:
        company = lead.company_name or lead.company or "your team"
        contact = (lead.contact_name or candidate.get("to_name") or "there").split()[0]
        trigger = candidate.get("trigger_type") or "engaged"
        pain = ", ".join(lead.pain_points or []) or "manual follow-up and operational visibility"
        prompt = f"""
Write one speed-to-lead follow-up email from Darren Mitchell at Aliyar Solutions.
Context:
- Prospect: {contact}
- Company: {company}
- Trigger: prospect {trigger} the previous email within the last five minutes
- Industry: {lead.industry or "unknown"}
- Pain points: {pain}

Rules:
- Return JSON only: {{"subject":"...","body":"..."}}
- Subject max 6 words.
- Body max 90 words.
- Warm, human, specific.
- No pricing.
- No attachments.
- Never mention AI, bots, Claude, prompts, or internal systems.
- Ask one soft question about whether the demo path is relevant.
""".strip()
        try:
            response, _ = await ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.SALES,
                max_tokens=500,
            )
            if not response.error:
                parsed = _parse_json_object(response.content)
                subject = str(parsed.get("subject") or "").strip()
                body = str(parsed.get("body") or "").strip()
                if subject and body and len(subject.split()) <= 6:
                    return {"subject": subject, "body": body}
        except Exception as exc:
            logger.warning("Speed-to-lead AI draft failed: %s", exc)

        return {
            "subject": "Saw your interest",
            "body": (
                f"Hi {contact} - it looks like {company} may be reviewing the note about {pain}. "
                "Our team can turn the likely bottleneck into a short demo path before any scope discussion. "
                "Would this be relevant enough for Aliyar Solutions to share the next step? "
                "Darren Mitchell, Client Acquisition Specialist, Aliyar Solutions."
            ),
        }

    async def _queue_for_captain(self, session, tenant_uuid, lead: Lead, candidate: dict, draft: dict) -> dict:
        approval = ApprovalRequest(
            tenant_id=tenant_uuid,
            action_type="speed_to_lead_followup",
            title=f"Speed-to-lead follow-up: {lead.company_name or lead.company or lead.email}",
            summary="Prospect engaged within the last 5 minutes. Captain is online, so JARVIS prepared a rapid follow-up for approval.",
            priority=1,
            risk_level="LOW",
            status=ApprovalStatus.PENDING,
            raised_by="SpeedToLeadEngine",
            payload={
                "lead_id": str(lead.id),
                "candidate": candidate,
                "subject": draft["subject"],
                "body": draft["body"],
                "persona": PERSONAS["darren_mitchell"],
            },
        )
        session.add(approval)
        await session.flush()
        return {"action_taken": "queued_for_captain", "approval_id": str(approval.id)}

    async def _schedule_send(self, session, tenant_uuid, lead: Lead, candidate: dict, draft: dict) -> dict:
        send_at = datetime.now(UTC) + timedelta(hours=4)
        sequence = list((lead.enrichment_data or {}).get("outreach_sequence") or [])
        sequence = [item for item in sequence if int(item.get("step") or 0) != SPEED_TO_LEAD_STEP]
        sequence.append(
            {
                "step": SPEED_TO_LEAD_STEP,
                "subject": draft["subject"],
                "body": draft["body"],
                "persona": PERSONAS["darren_mitchell"]["name"],
                "source": "speed_to_lead",
            }
        )
        lead.enrichment_data = {
            **(lead.enrichment_data or {}),
            "outreach_sequence": sequence,
            "speed_to_lead_last_trigger": candidate,
            "speed_to_lead_scheduled_at": send_at.isoformat(),
        }
        existing = await session.scalar(
            select(FollowUpQueue.id)
            .where(
                FollowUpQueue.tenant_id == tenant_uuid,
                FollowUpQueue.lead_id == lead.id,
                FollowUpQueue.sequence_step == SPEED_TO_LEAD_STEP,
                FollowUpQueue.status == FollowUpStatus.PENDING,
            )
            .limit(1)
        )
        if not existing:
            session.add(
                FollowUpQueue(
                    tenant_id=tenant_uuid,
                    lead_id=lead.id,
                    sequence_step=SPEED_TO_LEAD_STEP,
                    scheduled_at=send_at,
                    status=FollowUpStatus.PENDING,
                )
            )
        return {
            "action_taken": "scheduled_send",
            "scheduled_send_at": send_at.isoformat(),
            "_scheduled_send_at_dt": send_at,
        }

    async def _captain_online(self) -> bool:
        if not settings.REDIS_URL:
            return False
        try:
            import redis.asyncio as aioredis

            redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            raw = await redis.get("captain_presence") or await redis.get("jarvis:captain_presence")
            await redis.aclose()
            if not raw:
                return False
            timestamp = _presence_timestamp(raw)
            if not timestamp:
                return False
            return (datetime.now(UTC) - timestamp).total_seconds() < 120
        except Exception:
            return False

    async def _audit(self, session, tenant_uuid, action: str, lead_id, details: dict) -> None:
        session.add(
            AuditLog(
                tenant_id=tenant_uuid,
                action=action,
                entity_type="lead",
                entity_id=lead_id,
                actor="SpeedToLeadEngine",
                details=details,
                after_json=details,
            )
        )


def _parse_json_object(text: str) -> dict[str, Any]:
    clean = (text or "").strip()
    if "```" in clean:
        parts = clean.split("```")
        clean = next((part for part in parts if "{" in part and "}" in part), clean)
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _presence_timestamp(raw: str) -> datetime | None:
    try:
        payload = json.loads(raw)
        raw = payload.get("heartbeat_at") or payload.get("last_seen") or payload.get("timestamp") or raw
    except json.JSONDecodeError:
        pass
    try:
        if str(raw).isdigit():
            return datetime.fromtimestamp(float(raw), tz=UTC)
        value = str(raw).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except Exception:
        return None


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


speed_to_lead_engine = SpeedToLeadEngine()
