from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.approval import ApprovalRequest
from app.models.crm import Contact, Deal
from app.models.governance import Proposal
from app.models.lead import Lead
from app.models.notifications import NotificationLog
from app.models.outreach import OutreachEmail
from app.services.storage.secure import get_credential

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/revenue")
async def revenue_dashboard(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    day_start = now - timedelta(hours=24)

    async def count(model, *filters) -> int:
        query = select(func.count()).select_from(model)
        for condition in filters:
            query = query.where(condition)
        return int(await db.scalar(query) or 0)

    total_leads = await count(Lead)
    leads_week = await count(Lead, Lead.created_at >= week_start)
    qualified = await count(Lead, Lead.status == "qualified")
    contacts = await count(Contact)

    sent_emails = await count(OutreachEmail, OutreachEmail.status == "sent")
    replies = await count(OutreachEmail, OutreachEmail.status == "replied")
    drafted = await count(OutreachEmail, OutreachEmail.status.in_(["draft", "scheduled", "queued"]))
    failed = await count(OutreachEmail, OutreachEmail.status == "failed")

    proposals_total = await count(Proposal)
    proposals_sent = await count(Proposal, Proposal.status == "sent")
    proposals_draft = await count(Proposal, Proposal.status == "draft")
    proposals_week = await count(Proposal, Proposal.created_at >= week_start)

    pending_approvals = await count(ApprovalRequest, ApprovalRequest.status == "pending")
    approval_packets = await count(
        ApprovalRequest,
        ApprovalRequest.action_type == "revenue_outreach_batch",
        ApprovalRequest.created_at >= week_start,
    )

    pipeline_value = float(await db.scalar(
        select(func.coalesce(func.sum(Deal.value), 0)).where(Deal.stage != "closed_lost")
    ) or 0)
    weighted_forecast = float(await db.scalar(
        select(func.coalesce(func.sum(Deal.value * Deal.probability / 100), 0)).where(Deal.stage != "closed_lost")
    ) or 0)

    recent_activity_rows = (await db.execute(
        select(NotificationLog)
        .where(NotificationLog.category.in_(["outreach", "lead", "approval", "system"]))
        .order_by(desc(NotificationLog.created_at))
        .limit(8)
    )).scalars().all()

    overnight_rows = (await db.execute(
        select(NotificationLog)
        .where(NotificationLog.created_at >= day_start)
        .where(NotificationLog.title.ilike("%revenue engine%"))
        .order_by(desc(NotificationLog.created_at))
        .limit(5)
    )).scalars().all()

    latest_approval = (await db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.action_type == "revenue_outreach_batch")
        .order_by(desc(ApprovalRequest.created_at))
        .limit(1)
    )).scalar_one_or_none()

    apollo_key = await get_credential(db, "APOLLO_API_KEY")
    gmail_address = await get_credential(db, "GMAIL_ADDRESS")
    gmail_password = await get_credential(db, "GMAIL_APP_PASSWORD")
    clean_gmail_password = (gmail_password or "").replace(" ", "").strip()
    gmail_password_valid = clean_gmail_password.isascii() and len(clean_gmail_password) == 16
    gmail_ready = bool(gmail_address and gmail_password_valid)

    blockers = []
    if not apollo_key:
        blockers.append("APOLLO_API_KEY missing: live lead discovery is paused.")
    if not gmail_ready:
        blockers.append("Gmail app password/OAuth invalid or missing: approved outreach cannot send yet.")

    reply_rate = round((replies / sent_emails) * 100, 1) if sent_emails else 0.0
    conversion_signal = round((qualified / total_leads) * 100, 1) if total_leads else 0.0

    return {
        "generated_at": now.isoformat(),
        "revenue_forecast": {
            "pipeline_value": round(pipeline_value, 2),
            "weighted_forecast": round(weighted_forecast, 2),
            "currency": "USD",
        },
        "leads": {
            "total": total_leads,
            "this_week": leads_week,
            "qualified": qualified,
            "contacts": contacts,
            "qualification_rate": conversion_signal,
        },
        "outreach": {
            "drafted": drafted,
            "sent": sent_emails,
            "replies": replies,
            "failed": failed,
            "reply_rate": reply_rate,
        },
        "proposals": {
            "total": proposals_total,
            "sent": proposals_sent,
            "draft": proposals_draft,
            "this_week": proposals_week,
        },
        "approvals": {
            "pending": pending_approvals,
            "revenue_packets_this_week": approval_packets,
            "latest_revenue_packet": _approval_summary(latest_approval),
        },
        "gmail": {
            "address_configured": bool(gmail_address),
            "send_ready": gmail_ready,
            "drafts_waiting": drafted,
            "last_send_status": "ready" if gmail_ready else "blocked",
        },
        "engine": {
            "apollo_ready": bool(apollo_key),
            "gmail_ready": gmail_ready,
            "blockers": blockers,
            "overnight_activity": [_notification_summary(n) for n in overnight_rows],
            "activity_log": [_notification_summary(n) for n in recent_activity_rows],
        },
    }


def _notification_summary(n: NotificationLog) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "level": n.level,
        "category": n.category,
        "reference": n.reference,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _approval_summary(a: ApprovalRequest | None) -> dict | None:
    if not a:
        return None
    return {
        "id": a.id,
        "title": a.title,
        "status": a.status,
        "summary": a.summary,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
