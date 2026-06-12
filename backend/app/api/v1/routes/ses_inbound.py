"""SES Inbound Email Webhook + Operational Status Report.

Routes:
  POST /webhooks/email/inbound    — SNS endpoint for SES receipt rules
  GET  /ops/status                — Real-time operational status report for Captain
"""
from __future__ import annotations

import asyncio
import uuid
import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.lead import Lead, LeadStatus
from app.models.outreach import FollowUpQueue, FollowUpStatus, OutreachLog, OutreachStatus
from app.services.outreach.ses_inbound import process_ses_sns_notification
from app.services.outreach.email_transport import get_outbound_email_status
from app.services.communication.whatsapp_transport import evolution_status

router = APIRouter()
webhook_router = APIRouter(prefix="/webhooks", tags=["Inbound Webhooks"])
ops_router = APIRouter(prefix="/ops", tags=["Operations"])
logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _default_tenant() -> uuid.UUID:
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
    return SYSTEM_TENANT_ID


@webhook_router.post("/email/inbound")
async def ses_inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AWS SNS → SES receipt rule inbound email endpoint.

    Must be subscribed in AWS SNS as the HTTP/HTTPS endpoint for the SES
    receipt rule topic. Handles SubscriptionConfirmation + Notification types.
    """
    raw_body = await request.body()
    background_tasks.add_task(_process_inbound_background, raw_body)
    return {"accepted": True, "queued": True}


async def _process_inbound_background(raw_body: bytes) -> None:
    try:
        result = await process_ses_sns_notification(raw_body)
        logger.info("SES inbound processed: %s", result.get("processing", {}).get("action", "ok"))
    except Exception:
        logger.exception("SES inbound background processing failed")


@ops_router.get("/status")
async def operational_status(
    tenant_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Captain-facing operational report.

    Returns real-time status of all key systems and pipeline metrics.
    This is the single source of truth for: are we ready to acquire clients?
    """
    resolved = tenant_id or _default_tenant()

    ses_task = asyncio.create_task(
        asyncio.wait_for(get_outbound_email_status(validate_provider=True), timeout=4.0)
    )
    wa_task = asyncio.create_task(
        asyncio.wait_for(evolution_status(), timeout=4.0)
    )

    async with AsyncSessionLocal() as db:
        lead_counts = await _lead_counts(db, resolved)
        outreach_counts = await _outreach_counts(db, resolved)
        queue_counts = await _queue_counts(db, resolved)

    ses_status: dict[str, Any] = {}
    wa_status: dict[str, Any] = {}

    try:
        ses_status = await ses_task
    except asyncio.TimeoutError:
        ses_status = {"connected": False, "blocker_code": "ses_status_timeout", "send_mode": "blocked"}
    except Exception as exc:
        ses_status = {"connected": False, "blocker_code": "ses_error", "validation_error": str(exc)}

    try:
        wa_status = await wa_task
    except asyncio.TimeoutError:
        wa_status = {"connected": False, "blocker_code": "wa_status_timeout", "status": "blocked"}
    except Exception as exc:
        wa_status = {"connected": False, "blocker_code": "wa_error", "status": "blocked"}

    ses_live = bool(ses_status.get("connected") or ses_status.get("send_mode") == "live")
    wa_live = bool(wa_status.get("connected"))
    outreach_ready = ses_live and not settings.OUTREACH_PAUSED

    blockers: list[str] = []
    if not ses_live:
        blockers.append(ses_status.get("required_action") or ses_status.get("blocker_code") or "SES not live")
    if not wa_live:
        blockers.append(wa_status.get("required_action") or wa_status.get("blocker_code") or "WhatsApp not connected")
    if settings.OUTREACH_PAUSED:
        blockers.append("Outreach is paused (OUTREACH_PAUSED=true) — enable in config to start sending")

    return {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "tenant_id": str(resolved),
        "operational_summary": {
            "ses_status": "LIVE" if ses_live else "BLOCKED",
            "whatsapp_status": "CONNECTED" if wa_live else "DISCONNECTED",
            "outreach_engine_status": "READY" if outreach_ready else "BLOCKED",
            "revenue_engine_status": "ACTIVE" if lead_counts["total"] > 0 else "NO_LEADS",
            "first_outreach_ready": outreach_ready and lead_counts["with_email"] > 0,
        },
        "lead_pipeline": {
            "total_leads": lead_counts["total"],
            "active_leads": lead_counts["active"],
            "hot_leads": lead_counts["hot"],
            "with_email": lead_counts["with_email"],
            "with_whatsapp": lead_counts["with_phone"],
            "contacted": lead_counts["contacted"],
            "replied": lead_counts["replied"],
            "interested": lead_counts["interested"],
        },
        "outreach_pipeline": {
            "emails_sent_total": outreach_counts["sent"],
            "emails_failed": outreach_counts["failed"],
            "emails_skipped": outreach_counts["skipped"],
            "pending_in_queue": queue_counts["pending"],
            "due_now": queue_counts["due_now"],
            "daily_cap": int(settings.OUTREACH_DAILY_SEND_CAP or 48),
        },
        "transport": {
            "ses": {
                "status": "live" if ses_live else "blocked",
                "blocker_code": ses_status.get("blocker_code"),
                "from_email": ses_status.get("from_email"),
                "production_access": ses_status.get("production_access_enabled"),
                "identity_verified": ses_status.get("identity_verified"),
                "required_action": ses_status.get("required_action") if not ses_live else None,
            },
            "whatsapp": {
                "status": "connected" if wa_live else "disconnected",
                "instance": wa_status.get("instance"),
                "blocker_code": wa_status.get("blocker_code"),
                "required_action": wa_status.get("required_action") if not wa_live else None,
                "auto_reply_enabled": wa_status.get("auto_reply_enabled", False),
            },
        },
        "blockers": blockers,
        "estimated_time_to_first_outreach": _estimate_activation_time(ses_live, wa_live, lead_counts),
        "next_actions": _next_actions(ses_live, wa_live, lead_counts),
    }


async def _lead_counts(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    try:
        total = await db.scalar(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)
        ) or 0
        active = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.status.notin_([LeadStatus.CLOSED_LOST, LeadStatus.DO_NOT_CONTACT])
                if hasattr(LeadStatus, 'CLOSED_LOST') else text("1=1"),
            )
        ) or 0
        hot = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.icp_score >= 80,
            )
        ) or 0
        with_email = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.email.isnot(None),
                Lead.email != "",
            )
        ) or 0
        with_phone = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.phone.isnot(None),
                Lead.phone != "",
            )
        ) or 0
        contacted = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.outreach_sent == True,
            )
        ) or 0
        replied = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.status == LeadStatus.REPLIED,
            )
        ) or 0
        interested = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.tenant_id == tenant_id,
                Lead.status.in_([LeadStatus.DEMO_SCHEDULED, LeadStatus.PROPOSAL_SENT])
                if hasattr(LeadStatus, 'DEMO_SCHEDULED') else text("1=2"),
            )
        ) or 0
        return {
            "total": int(total),
            "active": int(active),
            "hot": int(hot),
            "with_email": int(with_email),
            "with_phone": int(with_phone),
            "contacted": int(contacted),
            "replied": int(replied),
            "interested": int(interested),
        }
    except Exception as exc:
        logger.warning("Lead count query failed: %s", exc)
        return {k: 0 for k in ("total", "active", "hot", "with_email", "with_phone", "contacted", "replied", "interested")}


async def _outreach_counts(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    try:
        sent = await db.scalar(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.status == OutreachStatus.SENT,
            )
        ) or 0
        failed = await db.scalar(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.status == OutreachStatus.FAILED,
            )
        ) or 0
        skipped = await db.scalar(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.status == OutreachStatus.SKIPPED,
            )
        ) or 0
        return {"sent": int(sent), "failed": int(failed), "skipped": int(skipped)}
    except Exception as exc:
        logger.warning("Outreach count query failed: %s", exc)
        return {"sent": 0, "failed": 0, "skipped": 0}


async def _queue_counts(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    try:
        from datetime import datetime
        now = datetime.utcnow()
        pending = await db.scalar(
            select(func.count(FollowUpQueue.id)).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.status == FollowUpStatus.PENDING,
            )
        ) or 0
        due_now = await db.scalar(
            select(func.count(FollowUpQueue.id)).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.status == FollowUpStatus.PENDING,
                FollowUpQueue.scheduled_at <= now,
            )
        ) or 0
        return {"pending": int(pending), "due_now": int(due_now)}
    except Exception as exc:
        logger.warning("Queue count query failed: %s", exc)
        return {"pending": 0, "due_now": 0}


def _estimate_activation_time(ses_live: bool, wa_live: bool, leads: dict) -> str:
    if ses_live and leads["with_email"] > 0:
        return "READY — first outreach can fire immediately"
    steps = []
    if not ses_live:
        steps.append("SES domain verification: ~15 min (DNS propagation)")
    if leads["with_email"] == 0:
        steps.append("Lead import/discovery: ~30 min")
    if not steps:
        return "READY"
    return " + ".join(steps)


def _next_actions(ses_live: bool, wa_live: bool, leads: dict) -> list[str]:
    actions = []
    if not ses_live:
        actions.append("1. Add 3 DKIM CNAME records + SPF TXT to GoDaddy DNS for aliyarsolutions.com")
        actions.append("2. In AWS SES Console (ap-south-2): verify domain identity")
        actions.append("3. Request SES production access if still in sandbox")
    else:
        actions.append("✅ SES is live — email outreach can fire")
    if not wa_live:
        actions.append("4. Start Evolution API container and pair WhatsApp to +973 34360246")
    else:
        actions.append("✅ WhatsApp connected")
    if leads["with_email"] == 0:
        actions.append("5. Import leads via POST /api/v1/leads/ or run discovery at POST /api/v1/discovery/google-maps")
    if leads["with_email"] > 0 and ses_live:
        actions.append(f"6. Queue outreach for {leads['with_email']} email leads: POST /api/v1/outreach/queue")
        actions.append("7. Execute due outreach: POST /api/v1/outreach/execute")
    return actions


router.include_router(webhook_router)
router.include_router(ops_router)
