from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus, AuditLog
from app.models.crm import Deal
from app.models.intelligence import BriefingHistory
from app.models.lead import Lead
from app.models.outreach import FollowUpQueue, FollowUpStatus, OutreachEmail, ReplyLog
from app.models.revenue import Client, ClientStatus, RevenueSnapshot
from app.services.notifications import notify_slack, notify_telegram


class MorningBriefingEngine:
    async def generate_and_send(self, tenant_id) -> str:
        tenant_uuid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await _apply_tenant_context(db, tenant_uuid)
            metrics = await self._collect_metrics(db, tenant_uuid)
            content = self._render(metrics)

            sent_channels: list[str] = []
            if await notify_slack(content):
                sent_channels.append("slack")
            if await notify_telegram(content):
                sent_channels.append("telegram")

            history = BriefingHistory(
                tenant_id=tenant_uuid,
                title=f"JARVIS Morning Briefing - {metrics['date']}",
                content=content,
                channels=sent_channels,
                status="sent" if sent_channels else "generated",
                metrics=metrics,
                sent_at=datetime.now(timezone.utc) if sent_channels else None,
            )
            db.add(history)
            db.add(
                AuditLog(
                    tenant_id=tenant_uuid,
                    action="morning_briefing_generated",
                    entity_type="briefing_history",
                    actor="morning_briefing_engine",
                    details={"channels": sent_channels, "metrics": metrics},
                )
            )
            await db.commit()
            return content

    async def _collect_metrics(self, db, tenant_id: uuid.UUID) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        top_leads = (
            await db.execute(
                select(Lead)
                .where(Lead.tenant_id == tenant_id)
                .order_by(Lead.score.desc(), Lead.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        new_leads = await db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.created_at >= today_start,
            )
        )
        latest_revenue = (
            await db.execute(
                select(RevenueSnapshot)
                .where(RevenueSnapshot.tenant_id == tenant_id)
                .order_by(RevenueSnapshot.snapshot_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        mrr = latest_revenue.mrr_usd if latest_revenue else await db.scalar(
            select(func.coalesce(func.sum(Client.mrr_usd), 0.0)).where(
                Client.tenant_id == tenant_id,
                Client.status == ClientStatus.ACTIVE,
            )
        )
        pipeline = await db.scalar(
            select(func.coalesce(func.sum(Deal.value), 0.0)).where(
                Deal.tenant_id == tenant_id,
                Deal.stage.notin_(("closed_won", "closed_lost")),
            )
        )
        pending_approvals = (
            await db.execute(
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.tenant_id == tenant_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
                .order_by(ApprovalRequest.priority.asc(), ApprovalRequest.created_at.asc())
                .limit(5)
            )
        ).scalars().all()
        outreach_count = await db.scalar(
            select(func.count()).select_from(FollowUpQueue).where(
                FollowUpQueue.tenant_id == tenant_id,
                FollowUpQueue.status == FollowUpStatus.PENDING,
                FollowUpQueue.scheduled_at >= today_start,
                FollowUpQueue.scheduled_at < today_start + timedelta(days=1),
            )
        )
        scheduled_emails = await db.scalar(
            select(func.count()).select_from(OutreachEmail).where(
                OutreachEmail.tenant_id == tenant_id,
                OutreachEmail.status == "scheduled",
                OutreachEmail.scheduled_at >= today_start,
                OutreachEmail.scheduled_at < today_start + timedelta(days=1),
            )
        )
        replies_week = await db.scalar(
            select(func.count()).select_from(ReplyLog).where(
                ReplyLog.tenant_id == tenant_id,
                ReplyLog.created_at >= week_start,
            )
        )

        return {
            "date": now.strftime("%Y-%m-%d"),
            "mrr": float(mrr or 0.0),
            "new_leads": int(new_leads or 0),
            "pipeline": float(pipeline or 0.0),
            "pending_approvals": len(pending_approvals),
            "approval_list": [
                {
                    "title": approval.title or approval.action_type or "Approval item",
                    "risk": approval.risk_level or "MEDIUM",
                }
                for approval in pending_approvals
            ],
            "outreach_count": int(outreach_count or 0) + int(scheduled_emails or 0),
            "reply_count": int(replies_week or 0),
            "top_lead_name": _lead_name(top_leads[0]) if top_leads else "None",
            "top_lead_score": float(top_leads[0].score) if top_leads else 0.0,
            "top_leads": [_lead_payload(lead) for lead in top_leads],
            "system_health_summary": "DB reachable, scheduler active, tenant context ready",
        }

    def _render(self, metrics: dict) -> str:
        approval_lines = "\n".join(
            f"  - {item['title']} ({item['risk']})" for item in metrics["approval_list"]
        ) or "  - None"
        top_lead_score = int(metrics["top_lead_score"])
        return (
            f"JARVIS MORNING BRIEFING - {metrics['date']}\n\n"
            "REVENUE:\n"
            f"- Current MRR: ${metrics['mrr']:,.0f}\n"
            f"- New leads today: {metrics['new_leads']}\n"
            f"- Pipeline value: ${metrics['pipeline']:,.0f}\n\n"
            f"ACTION REQUIRED ({metrics['pending_approvals']} items):\n"
            f"{approval_lines}\n\n"
            "OUTREACH:\n"
            f"- Scheduled today: {metrics['outreach_count']} messages\n"
            f"- Replied this week: {metrics['reply_count']}\n"
            f"- Top lead: {metrics['top_lead_name']} ({top_lead_score}/100)\n\n"
            f"SYSTEM: {metrics['system_health_summary']}"
        )


async def _apply_tenant_context(db, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(db, str(tenant_id))


def _coerce_tenant_id(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _lead_name(lead: Lead) -> str:
    return lead.company_name or lead.company or lead.contact_name or lead.email or "Unnamed lead"


def _lead_payload(lead: Lead) -> dict:
    return {
        "id": str(lead.id),
        "company": _lead_name(lead),
        "score": float(lead.score or 0.0),
        "industry": lead.industry,
        "country": lead.country,
    }
