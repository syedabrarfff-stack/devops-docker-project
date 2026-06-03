"""
JARVIS Revenue Forecaster — Monte Carlo simulation engine for pipeline-to-revenue projection.
Uses pure stdlib (random + statistics) — no numpy dependency.
"""
from __future__ import annotations

import logging
import random
import statistics
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_LEAD_TO_PROPOSAL_MIN = 0.20
_LEAD_TO_PROPOSAL_MAX = 0.40
_PROPOSAL_TO_CLOSE_MIN = 0.15
_PROPOSAL_TO_CLOSE_MAX = 0.35
_RETAINER_MIN = 3_000.0
_RETAINER_MAX = 8_000.0
_PROJECT_MIN = 5_000.0
_PROJECT_MAX = 25_000.0
_HORIZONS = [30, 60, 90]


def _percentile(data: list[float], pct: float) -> float:
    """Return the p-th percentile of a sorted list (linear interpolation)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    index = (pct / 100) * (n - 1)
    lower = int(index)
    upper = min(lower + 1, n - 1)
    frac = index - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])


def _simulate_single_run(pipeline_leads: int, proposals_sent: int, current_mrr: float) -> dict[str, float]:
    """One Monte Carlo iteration — returns revenue outcome per horizon."""
    l2p = random.uniform(_LEAD_TO_PROPOSAL_MIN, _LEAD_TO_PROPOSAL_MAX)
    p2c = random.uniform(_PROPOSAL_TO_CLOSE_MIN, _PROPOSAL_TO_CLOSE_MAX)

    new_proposals_from_pipeline = int(pipeline_leads * l2p)
    total_proposals = proposals_sent + new_proposals_from_pipeline
    new_clients = int(total_proposals * p2c)

    # Each new client is either retainer (70%) or project (30%)
    new_mrr = 0.0
    project_revenue = 0.0
    for _ in range(new_clients):
        if random.random() < 0.70:
            new_mrr += random.uniform(_RETAINER_MIN, _RETAINER_MAX)
        else:
            project_revenue += random.uniform(_PROJECT_MIN, _PROJECT_MAX)

    results: dict[str, float] = {}
    for days in _HORIZONS:
        months = days / 30.0
        recurring = (current_mrr + new_mrr) * months
        results[f"horizon_{days}"] = round(recurring + project_revenue, 2)
    return results


class RevenueForecaster:
    """Monte Carlo revenue forecasting engine."""

    async def _fetch_pipeline_metrics(self, tenant_id: UUID) -> dict[str, Any]:
        """Query database for pipeline metrics under the given tenant."""
        from app.models.lead import Lead, LeadStatus

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            try:
                pipeline_result = await session.execute(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tenant_id,
                        Lead.score >= 60,
                        Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST]),
                    )
                )
                pipeline_leads = pipeline_result.scalar() or 0

                proposals_result = await session.execute(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tenant_id,
                        Lead.status == LeadStatus.PROPOSAL,
                    )
                )
                proposals_sent = proposals_result.scalar() or 0

                # Rough MRR estimate from WON leads count * average retainer midpoint
                won_result = await session.execute(
                    select(func.count()).select_from(Lead).where(
                        Lead.tenant_id == tenant_id,
                        Lead.status == LeadStatus.WON,
                    )
                )
                won_count = won_result.scalar() or 0
                current_mrr = won_count * 4_500.0  # proxy until revenue model is wired

            except Exception as exc:
                logger.warning("Pipeline metrics query failed, using defaults: %s", exc)
                pipeline_leads, proposals_sent, current_mrr = 5, 2, 0.0

        return {
            "pipeline_leads": pipeline_leads,
            "proposals_sent": proposals_sent,
            "current_mrr": current_mrr,
        }

    async def run_monte_carlo(
        self,
        tenant_id: UUID,
        iterations: int = 1_000,
        horizon_days: int = 90,
    ) -> dict[str, Any]:
        """Run Monte Carlo simulation and return P10/P50/P90 outcomes."""
        metrics = await self._fetch_pipeline_metrics(tenant_id)
        pipeline_leads: int = metrics["pipeline_leads"]
        proposals_sent: int = metrics["proposals_sent"]
        current_mrr: float = metrics["current_mrr"]

        iterations = max(100, min(iterations, 10_000))
        outcomes: dict[str, list[float]] = {f"horizon_{d}": [] for d in _HORIZONS}

        for _ in range(iterations):
            run = _simulate_single_run(pipeline_leads, proposals_sent, current_mrr)
            for key in outcomes:
                outcomes[key].append(run[key])

        results_by_horizon: dict[str, Any] = {}
        for days in _HORIZONS:
            key = f"horizon_{days}"
            series = outcomes[key]
            results_by_horizon[key] = {
                "p10": round(_percentile(series, 10), 2),
                "p50": round(_percentile(series, 50), 2),
                "p90": round(_percentile(series, 90), 2),
                "mean": round(statistics.mean(series), 2),
                "horizon_days": days,
            }

        primary = results_by_horizon[f"horizon_{horizon_days}"]
        recommendations = _build_recommendations(
            pipeline_leads, proposals_sent, current_mrr, primary["p50"]
        )

        return {
            "p10": primary["p10"],
            "p50": primary["p50"],
            "p90": primary["p90"],
            "horizon_days": horizon_days,
            "pipeline_size": pipeline_leads,
            "proposals_active": proposals_sent,
            "current_mrr": current_mrr,
            "simulation_runs": iterations,
            "forecast_date": date.today().isoformat(),
            "all_horizons": results_by_horizon,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def quick_forecast(self, tenant_id: UUID) -> dict[str, Any]:
        """Simplified deterministic forecast — no simulation."""
        metrics = await self._fetch_pipeline_metrics(tenant_id)
        pipeline = metrics["pipeline_leads"]
        proposals = metrics["proposals_sent"]
        mrr = metrics["current_mrr"]

        mid_l2p = (_LEAD_TO_PROPOSAL_MIN + _LEAD_TO_PROPOSAL_MAX) / 2
        mid_p2c = (_PROPOSAL_TO_CLOSE_MIN + _PROPOSAL_TO_CLOSE_MAX) / 2
        avg_deal = (_RETAINER_MIN + _RETAINER_MAX) / 2

        new_clients_30 = (proposals + int(pipeline * mid_l2p * 0.33)) * mid_p2c
        new_clients_90 = (proposals + int(pipeline * mid_l2p)) * mid_p2c
        rev_30 = round(mrr + new_clients_30 * avg_deal, 2)
        rev_90 = round(mrr * 3 + new_clients_90 * avg_deal, 2)

        return {
            "quick_estimate_30d": rev_30,
            "quick_estimate_90d": rev_90,
            "current_mrr": mrr,
            "pipeline_size": pipeline,
            "forecast_date": date.today().isoformat(),
        }


def _build_recommendations(
    pipeline: int, proposals: int, mrr: float, p50: float
) -> list[str]:
    recs: list[str] = []
    if pipeline < 10:
        recs.append("Pipeline is thin — activate lead generation campaigns to reach 20+ qualified leads.")
    if proposals == 0:
        recs.append("No active proposals — convert pipeline leads to proposal stage immediately.")
    if mrr == 0:
        recs.append("Zero recurring revenue — prioritise retainer positioning over one-off projects.")
    if p50 < 5_000:
        recs.append("Projected revenue is low — focus on upselling existing clients and higher-value service tiers.")
    if not recs:
        recs.append("Pipeline health is solid — maintain outreach cadence and proposal conversion focus.")
    return recs


revenue_forecaster = RevenueForecaster()
