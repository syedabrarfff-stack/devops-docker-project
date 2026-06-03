from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.economics import AICostLedger, InfrastructureCostConfig
from app.models.governance import Proposal
from app.models.lead import Lead
from app.models.outreach import OutreachLog
from app.models.revenue import Client, ClientStatus
from app.services.notifications.telegram import notify_telegram

DEFAULT_INFRASTRUCTURE_COSTS = {
    "ec2_monthly": 45.0,
    "postgres_monthly": 0.0,
    "redis_monthly": 0.0,
    "total_monthly": 45.0,
}
DAILY_AI_ALERT_THRESHOLD_USD = 5.0
TARGET_CLIENT_GROSS_MARGIN_USD = 1000.0


class EconomicsService:
    async def log_ai_call(
        self,
        *,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        tokens_total: int,
        cost_usd: float,
        department: str,
        task_type: str,
        latency_ms: int,
        success: bool = True,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        tenant_id: uuid.UUID | str | None = None,
    ) -> None:
        tenant_uuid = _tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                session.add(
                    AICostLedger(
                        tenant_id=tenant_uuid,
                        provider=provider,
                        model=model,
                        tokens_in=max(0, int(tokens_in or 0)),
                        tokens_out=max(0, int(tokens_out or 0)),
                        tokens_total=max(0, int(tokens_total or 0)),
                        cost_usd=round(float(cost_usd or 0.0), 6),
                        department=department or "general",
                        task_type=task_type or "general",
                        latency_ms=max(0, int(latency_ms or 0)),
                        success=success,
                        error_message=(error_message or "")[:500] or None,
                        metadata_json=metadata or {},
                    )
                )

        await self._alert_if_needed(tenant_uuid)

    async def dashboard(self, tenant_id) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        yesterday_start = today_start - timedelta(days=1)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                infra = await self._infrastructure_config(session, tenant_uuid)
                ai_today = await _ai_spend(session, tenant_uuid, today_start, now)
                ai_yesterday = await _ai_spend(session, tenant_uuid, yesterday_start, today_start)
                ai_week = await _ai_spend(session, tenant_uuid, week_start, now)
                ai_month = await _ai_spend(session, tenant_uuid, month_start, now)

                leads_month = await _count_since(session, Lead, tenant_uuid, month_start)
                proposals_month = await _count_since(session, Proposal, tenant_uuid, month_start)
                outreach_sent_month = await session.scalar(
                    select(func.count())
                    .select_from(OutreachLog)
                    .where(
                        OutreachLog.tenant_id == tenant_uuid,
                        OutreachLog.created_at >= month_start,
                        OutreachLog.sent_at.is_not(None),
                    )
                )
                active_clients = await session.scalar(
                    select(func.count())
                    .select_from(Client)
                    .where(Client.tenant_id == tenant_uuid, Client.status == ClientStatus.ACTIVE)
                )

        monthly_burn = float(infra["total_monthly"]) + ai_month
        clients_needed = max(1, int((monthly_burn / TARGET_CLIENT_GROSS_MARGIN_USD) + 0.9999))
        cost_to_close = ai_month / max(1, int(active_clients or 0))

        return {
            "ai_spend": {
                "today": round(ai_today, 4),
                "yesterday": round(ai_yesterday, 4),
                "this_week": round(ai_week, 4),
                "this_month": round(ai_month, 4),
                "daily_alert_threshold": DAILY_AI_ALERT_THRESHOLD_USD,
                "status": "over_budget" if ai_today > DAILY_AI_ALERT_THRESHOLD_USD else "on_track",
            },
            "infrastructure_costs": infra,
            "unit_economics": {
                "cost_per_lead_discovered": _safe_unit(ai_month, leads_month),
                "cost_per_proposal_generated": _safe_unit(ai_month, proposals_month),
                "cost_per_outreach_email_sent": _safe_unit(ai_month, outreach_sent_month),
                "estimated_cost_to_close_one_client": round(cost_to_close, 4),
            },
            "break_even": {
                "monthly_burn_usd": round(monthly_burn, 2),
                "target_client_margin_usd": TARGET_CLIENT_GROSS_MARGIN_USD,
                "clients_needed_to_be_profitable": clients_needed,
                "active_clients": int(active_clients or 0),
            },
            "counts": {
                "leads_this_month": int(leads_month or 0),
                "proposals_this_month": int(proposals_month or 0),
                "outreach_emails_sent_this_month": int(outreach_sent_month or 0),
            },
        }

    async def yesterday_report_line(self, tenant_id) -> str:
        tenant_uuid = _tenant_uuid(tenant_id)
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                spend = await _ai_spend(session, tenant_uuid, yesterday_start, today_start)
        status = "over budget" if spend > DAILY_AI_ALERT_THRESHOLD_USD else "on track"
        return f"AI spend yesterday: ${spend:.2f} - {status}"

    async def _infrastructure_config(self, session, tenant_uuid: uuid.UUID) -> dict[str, float]:
        config = await session.scalar(
            select(InfrastructureCostConfig)
            .where(InfrastructureCostConfig.tenant_id == tenant_uuid, InfrastructureCostConfig.name == "production")
            .order_by(InfrastructureCostConfig.created_at.desc())
            .limit(1)
        )
        if not config:
            config = InfrastructureCostConfig(
                tenant_id=tenant_uuid,
                name="production",
                **DEFAULT_INFRASTRUCTURE_COSTS,
                metadata_json={"source": "default_layer_30_config"},
            )
            session.add(config)
            await session.flush()
        total = config.total_monthly or (config.ec2_monthly + config.postgres_monthly + config.redis_monthly)
        return {
            "ec2_monthly": float(config.ec2_monthly or 0.0),
            "postgres_monthly": float(config.postgres_monthly or 0.0),
            "redis_monthly": float(config.redis_monthly or 0.0),
            "total_monthly": float(total or 0.0),
        }

    async def _alert_if_needed(self, tenant_uuid: uuid.UUID) -> None:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                spend = await _ai_spend(session, tenant_uuid, today_start, now)
                already_alerted = await session.scalar(
                    select(func.count())
                    .select_from(AuditLog)
                    .where(
                        AuditLog.tenant_id == tenant_uuid,
                        AuditLog.action == "daily_ai_spend_alert_sent",
                        AuditLog.created_at >= today_start,
                    )
                )
                if spend <= DAILY_AI_ALERT_THRESHOLD_USD or already_alerted:
                    return
                sent = await notify_telegram(
                    f"Captain - daily AI spend is ${spend:.2f}, above the ${DAILY_AI_ALERT_THRESHOLD_USD:.2f} limit."
                )
                session.add(
                    AuditLog(
                        tenant_id=tenant_uuid,
                        action="daily_ai_spend_alert_sent",
                        entity_type="ai_cost_ledger",
                        actor="EconomicsService",
                        details={"spend": spend, "telegram_sent": sent},
                    )
                )


economics_service = EconomicsService()


async def _ai_spend(session, tenant_uuid: uuid.UUID, start: datetime, end: datetime) -> float:
    value = await session.scalar(
        select(func.coalesce(func.sum(AICostLedger.cost_usd), 0.0)).where(
            AICostLedger.tenant_id == tenant_uuid,
            AICostLedger.created_at >= start,
            AICostLedger.created_at < end,
        )
    )
    return float(value or 0.0)


async def _count_since(session, model, tenant_uuid: uuid.UUID, start: datetime) -> int:
    value = await session.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_uuid, model.created_at >= start)
    )
    return int(value or 0)


def _safe_unit(total_cost: float, count: int | None) -> float:
    return round(float(total_cost or 0.0) / max(1, int(count or 0)), 4)


def _tenant_uuid(value: uuid.UUID | str | None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID or "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
