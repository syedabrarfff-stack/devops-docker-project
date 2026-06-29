"""
JARVIS Financial Intelligence Engine — Virtual CFO system.
Tracks MRR, ARR, gross margin, CAC, LTV, runway, concentration risk.
Weekly CFO briefing. Revenue risk alerts. Expansion opportunity detection.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

MONTHLY_INFRASTRUCTURE_COST = 180.0
MONTHLY_AI_COST_ESTIMATE = 150.0
MONTHLY_TOOLS_COST = 100.0
TOTAL_MONTHLY_OPEX = MONTHLY_INFRASTRUCTURE_COST + MONTHLY_AI_COST_ESTIMATE + MONTHLY_TOOLS_COST  # 430.0

BOOTSTRAP_RUNWAY_MONTHS = 6.0


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


def _compute_financial_health_score(
    mrr: float,
    gross_margin_pct: float,
    concentration_risk: float,
    runway_months: float,
    active_clients: int,
) -> float:
    score = 0.0
    # MRR component (0-30 pts): $10K = full 30 pts
    score += min(30.0, mrr / 10000 * 30)
    # Gross margin (0-25 pts): 70%+ = full
    score += min(25.0, gross_margin_pct / 70 * 25) if gross_margin_pct > 0 else 0
    # Concentration risk (0-20 pts): lower risk = higher score
    score += max(0.0, 20.0 - concentration_risk / 5)
    # Runway (0-15 pts): 12+ months = full
    score += min(15.0, runway_months / 12 * 15)
    # Client diversification (0-10 pts): 5+ clients = full
    score += min(10.0, active_clients * 2.0)
    return round(min(100.0, score), 2)


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


class FinancialIntelligenceEngine:
    """Virtual CFO — computes financial health, forecasts cashflow, generates briefings."""

    async def compute_financial_snapshot(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import FinancialHealth
        tid = _coerce_tenant_id(tenant_id)

        mrr = 0.0
        active_clients = 0
        new_clients_30d = 0
        churned_clients_30d = 0
        service_breakdown: dict[str, float] = {}
        max_single_client_mrr = 0.0

        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            try:
                from app.models.revenue import Client, ClientStatus
                result = await db.execute(
                    select(Client).where(
                        Client.tenant_id == tid,
                        Client.status == ClientStatus.ACTIVE,
                    ).limit(500)
                )
                clients = result.scalars().all()
                active_clients = len(clients)
                for c in clients:
                    client_mrr = getattr(c, "mrr_usd", 0.0) or 0.0
                    mrr += client_mrr
                    if client_mrr > max_single_client_mrr:
                        max_single_client_mrr = client_mrr
                    pkg = getattr(c, "package_tier", "general") or "general"
                    service_breakdown[pkg] = service_breakdown.get(pkg, 0.0) + client_mrr

                new_result = await db.execute(
                    select(func.count()).select_from(Client).where(
                        Client.tenant_id == tid,
                        Client.created_at >= cutoff_30d,
                    )
                )
                new_clients_30d = new_result.scalar() or 0

                churned_result = await db.execute(
                    select(func.count()).select_from(Client).where(
                        Client.tenant_id == tid,
                        Client.status == ClientStatus.CHURNED,
                        Client.updated_at >= cutoff_30d,
                    )
                )
                churned_clients_30d = churned_result.scalar() or 0

            except Exception as exc:
                logger.warning("Client query failed in financial snapshot: %s", exc)

            arr = mrr * 12
            gross_margin_pct = max(0.0, (mrr - TOTAL_MONTHLY_OPEX) / mrr * 100) if mrr > 0 else 0.0
            cac = (TOTAL_MONTHLY_OPEX * 3) / max(new_clients_30d, 1)
            concentration_risk = (max_single_client_mrr / mrr * 100) if mrr > 0 else 0.0
            runway_months = BOOTSTRAP_RUNWAY_MONTHS if mrr == 0 else min(mrr / TOTAL_MONTHLY_OPEX, 24.0)
            health_score = _compute_financial_health_score(mrr, gross_margin_pct, concentration_risk, runway_months, active_clients)

            risk_alerts = []
            if concentration_risk > 50:
                risk_alerts.append(f"Revenue concentration risk: {concentration_risk:.1f}% from single client. Diversify immediately.")
            if runway_months < 3 and mrr == 0:
                risk_alerts.append("Pre-revenue: Bootstrap runway estimated at 6 months. First client acquisition is critical.")
            if gross_margin_pct < 40 and mrr > 0:
                risk_alerts.append(f"Gross margin at {gross_margin_pct:.1f}% — below 40% threshold. Review pricing.")
            if active_clients == 1:
                risk_alerts.append("Single client dependency. One churn event eliminates 100% of revenue.")

            expansion_alerts = []
            if active_clients >= 3 and concentration_risk < 40:
                expansion_alerts.append("Revenue diversification achieved. Ready to target enterprise contracts ($8K+/mo).")
            if mrr >= 5000:
                expansion_alerts.append("MRR threshold reached. Begin white-label licensing pipeline (Phase 3).")
            if active_clients >= 5:
                expansion_alerts.append("Client base sufficient for case study portfolio. Activate social proof campaign.")

            cfo_briefing = self._render_cfo_briefing(
                mrr=mrr, arr=arr, gross_margin_pct=gross_margin_pct,
                cac=cac, concentration_risk=concentration_risk,
                runway_months=runway_months, health_score=health_score,
                active_clients=active_clients, new_clients_30d=new_clients_30d,
                churned_clients_30d=churned_clients_30d, risk_alerts=risk_alerts,
                expansion_alerts=expansion_alerts,
            )

            snapshot = FinancialHealth(
                tenant_id=tid,
                snapshot_date=datetime.now(timezone.utc),
                mrr=mrr,
                arr=arr,
                gross_margin_pct=gross_margin_pct,
                client_acquisition_cost=cac,
                revenue_concentration_risk=concentration_risk,
                runway_months=runway_months,
                financial_health_score=health_score,
                active_clients=active_clients,
                churned_clients_30d=churned_clients_30d,
                new_clients_30d=new_clients_30d,
                service_line_breakdown=service_breakdown,
                risk_alerts=risk_alerts,
                expansion_alerts=expansion_alerts,
                cfo_briefing=cfo_briefing,
            )
            db.add(snapshot)
            await db.commit()

        return {
            "mrr": mrr,
            "arr": arr,
            "gross_margin_pct": round(gross_margin_pct, 2),
            "client_acquisition_cost": round(cac, 2),
            "revenue_concentration_risk": round(concentration_risk, 2),
            "runway_months": round(runway_months, 2),
            "financial_health_score": health_score,
            "grade": _grade(health_score),
            "active_clients": active_clients,
            "new_clients_30d": new_clients_30d,
            "churned_clients_30d": churned_clients_30d,
            "service_line_breakdown": service_breakdown,
            "risk_alerts": risk_alerts,
            "expansion_alerts": expansion_alerts,
            "cfo_briefing": cfo_briefing,
            "total_monthly_opex": TOTAL_MONTHLY_OPEX,
        }

    def _render_cfo_briefing(self, **kw) -> str:
        lines = [
            f"ALIYAR SOLUTIONS — CFO BRIEFING | {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "",
            f"MRR: ${kw['mrr']:,.0f} | ARR: ${kw['arr']:,.0f} | Health Score: {kw['health_score']:.0f}/100 ({_grade(kw['health_score'])})",
            f"Active Clients: {kw['active_clients']} | New (30d): {kw['new_clients_30d']} | Churned (30d): {kw['churned_clients_30d']}",
            f"Gross Margin: {kw['gross_margin_pct']:.1f}% | Monthly OPEX: ${TOTAL_MONTHLY_OPEX:,.0f}",
            f"Revenue Concentration Risk: {kw['concentration_risk']:.1f}% | Runway: {kw['runway_months']:.1f} months",
            f"CAC (estimated): ${kw['cac']:,.0f}",
            "",
        ]
        if kw["risk_alerts"]:
            lines.append("⚠️ RISK ALERTS:")
            for a in kw["risk_alerts"]:
                lines.append(f"  • {a}")
            lines.append("")
        if kw["expansion_alerts"]:
            lines.append("🚀 EXPANSION OPPORTUNITIES:")
            for a in kw["expansion_alerts"]:
                lines.append(f"  • {a}")
            lines.append("")
        if kw["mrr"] == 0:
            lines.append("STATUS: Pre-revenue. All systems built. First client acquisition is the sole priority.")
        else:
            lines.append("STATUS: Revenue generating. Focus on retention and pipeline growth.")
        return "\n".join(lines)

    async def generate_cashflow_forecast(self, tenant_id: Any, horizon_days: int = 90) -> list:
        from app.models.truth_resilience import CashflowForecast
        tid = _coerce_tenant_id(tenant_id)
        snapshot = await self.compute_financial_snapshot(tid)
        mrr = snapshot["mrr"]
        results = []

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            for days in [30, 60, 90]:
                if days > horizon_days:
                    continue
                months = days / 30.0
                projected_revenue = mrr * months
                projected_expenses = TOTAL_MONTHLY_OPEX * months
                projected_net = projected_revenue - projected_expenses
                confidence_low = projected_net * 0.75
                confidence_high = projected_net * 1.35

                fc = CashflowForecast(
                    tenant_id=tid,
                    forecast_date=datetime.now(timezone.utc),
                    horizon_days=days,
                    projected_revenue=round(projected_revenue, 2),
                    projected_expenses=round(projected_expenses, 2),
                    projected_net=round(projected_net, 2),
                    confidence_low=round(confidence_low, 2),
                    confidence_high=round(confidence_high, 2),
                    assumptions={"mrr": mrr, "opex_monthly": TOTAL_MONTHLY_OPEX, "growth_rate": 0.0},
                    risk_factors=snapshot["risk_alerts"],
                )
                db.add(fc)
                results.append({
                    "horizon_days": days,
                    "projected_revenue": fc.projected_revenue,
                    "projected_expenses": fc.projected_expenses,
                    "projected_net": fc.projected_net,
                    "confidence_low": fc.confidence_low,
                    "confidence_high": fc.confidence_high,
                })
            await db.commit()
        return results

    async def get_cfo_briefing(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import FinancialHealth, CashflowForecast
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            fh_result = await db.execute(
                select(FinancialHealth).where(FinancialHealth.tenant_id == tid).order_by(FinancialHealth.snapshot_date.desc()).limit(1)
            )
            latest = fh_result.scalar_one_or_none()

            fc_result = await db.execute(
                select(CashflowForecast).where(CashflowForecast.tenant_id == tid).order_by(CashflowForecast.forecast_date.desc()).limit(3)
            )
            forecasts = fc_result.scalars().all()

        if not latest:
            return {"status": "no_snapshot", "message": "Run /financial/snapshot first"}

        return {
            "snapshot": {
                "mrr": latest.mrr,
                "arr": latest.arr,
                "gross_margin_pct": latest.gross_margin_pct,
                "financial_health_score": latest.financial_health_score,
                "grade": _grade(latest.financial_health_score or 0),
                "active_clients": latest.active_clients,
                "runway_months": latest.runway_months,
                "revenue_concentration_risk": latest.revenue_concentration_risk,
                "risk_alerts": latest.risk_alerts,
                "expansion_alerts": latest.expansion_alerts,
                "cfo_briefing": latest.cfo_briefing,
                "snapshot_date": latest.snapshot_date.isoformat() if latest.snapshot_date else None,
            },
            "cashflow_forecasts": [
                {
                    "horizon_days": f.horizon_days,
                    "projected_revenue": f.projected_revenue,
                    "projected_net": f.projected_net,
                    "confidence_low": f.confidence_low,
                    "confidence_high": f.confidence_high,
                }
                for f in forecasts
            ],
        }

    async def compute_weekly_health(self, tenant_id: Any) -> dict:
        tid = _coerce_tenant_id(tenant_id)
        snapshot = await self.compute_financial_snapshot(tid)
        forecasts = await self.generate_cashflow_forecast(tid, horizon_days=90)
        msg = f"📊 Weekly CFO Report | Health: {snapshot['financial_health_score']:.0f}/100 ({snapshot['grade']}) | MRR: ${snapshot['mrr']:,.0f}"
        try:
            from app.services.notifications import notify_telegram, notify_slack
            await notify_telegram(msg)
            await notify_slack(msg)
        except Exception as exc:
            logger.warning("Failed to send weekly CFO report: %s", exc)
        return {"snapshot": snapshot, "forecasts": forecasts}


financial_intelligence = FinancialIntelligenceEngine()
