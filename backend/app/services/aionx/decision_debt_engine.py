"""AIONX Decision Debt Engine.

Quantifies operational debt from decisions using the canonical debt assessment
and institutional debt index tables.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import DecisionDebtAssessment, DecisionObject, InstitutionalDebtIndex

logger = logging.getLogger(__name__)


def _resolve_tenant(tenant_id=None) -> uuid.UUID | None:
    if tenant_id:
        return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    from app.core.config import settings as _cfg
    raw = getattr(_cfg, "JARVIS_DEFAULT_TENANT_ID", None)
    if raw:
        try:
            return uuid.UUID(str(raw))
        except (ValueError, AttributeError):
            pass
    return None


async def compute_decision_debt(
    db: AsyncSession,
    decision_id: uuid.UUID,
    lost_revenue_usd: float = 0.0,
    remediation_effort_hours: float = 0.0,
    opportunity_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Compute debt for a single decision and persist a schema-valid assessment."""
    _tid = _resolve_tenant()
    _dq = select(DecisionObject).where(DecisionObject.id == decision_id)
    if _tid:
        _dq = _dq.where(DecisionObject.tenant_id == _tid)
    decision = (await db.execute(_dq)).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    revenue_component = lost_revenue_usd * 0.4
    remediation_component = remediation_effort_hours * 150 * 0.3
    opportunity_component = opportunity_cost_usd * 0.3
    total_debt = revenue_component + remediation_component + opportunity_component
    debt_score = min(100.0, total_debt / 1000.0)
    priority = "CRITICAL" if debt_score >= 90 else "HIGH" if debt_score >= 70 else "MEDIUM"

    assessment = DecisionDebtAssessment(
        decision_id=decision_id,
        debt_category=decision.decision_category or "OPERATIONAL",
        debt_score=debt_score,
        description=(
            f"Estimated debt from lost revenue={lost_revenue_usd}, "
            f"remediation_hours={remediation_effort_hours}, "
            f"opportunity_cost={opportunity_cost_usd}"
        ),
        repayment_cost_estimate=total_debt,
        repayment_priority=priority,
        is_paid_off=False,
    )
    db.add(assessment)
    await db.flush()
    await db.commit()

    logger.info("Decision Debt: decision %s debt=$%.2f", decision_id, total_debt)
    return {
        "assessment_id": str(assessment.id),
        "decision_id": str(decision_id),
        "total_debt_usd": total_debt,
        "debt_score": debt_score,
        "components": {
            "revenue": revenue_component,
            "remediation": remediation_component,
            "opportunity": opportunity_component,
        },
    }


async def assess_institutional_debt(db: AsyncSession) -> dict[str, Any]:
    """Aggregate open decision debt into the weekly institutional index."""
    total_debt = (await db.execute(
        select(func.sum(DecisionDebtAssessment.repayment_cost_estimate)).where(
            DecisionDebtAssessment.is_paid_off.is_(False)
        )
    )).scalar_one() or 0.0

    high_count = (await db.execute(
        select(func.count()).select_from(DecisionDebtAssessment).where(
            DecisionDebtAssessment.is_paid_off.is_(False),
            DecisionDebtAssessment.debt_score >= 70,
        )
    )).scalar_one()

    critical_count = (await db.execute(
        select(func.count()).select_from(DecisionDebtAssessment).where(
            DecisionDebtAssessment.is_paid_off.is_(False),
            DecisionDebtAssessment.debt_score >= 90,
        )
    )).scalar_one()

    avg_debt = (await db.execute(
        select(func.avg(DecisionDebtAssessment.repayment_cost_estimate)).where(
            DecisionDebtAssessment.is_paid_off.is_(False)
        )
    )).scalar_one() or 0.0

    week_of = date.today()
    index = (await db.execute(
        select(InstitutionalDebtIndex).where(InstitutionalDebtIndex.week_of == week_of)
    )).scalars().first()
    if not index:
        index = InstitutionalDebtIndex(week_of=week_of)
        db.add(index)

    index.total_debt_score = min(100.0, total_debt / 1000.0)
    index.operational_debt = total_debt
    index.critical_count = critical_count
    index.high_count = high_count
    index.estimated_repayment_weeks = round(total_debt / 10000.0, 1) if total_debt else 0.0
    index.trend = "RISING" if total_debt > 0 else "STABLE"
    await db.flush()

    debt_penalty = min(20.0, (total_debt / 100000) * 5)
    logger.info("Institutional Debt: total=$%.2f high=%d critical=%d", total_debt, high_count, critical_count)
    return {
        "index_id": str(index.id),
        "total_institutional_debt_usd": total_debt,
        "high_debt_decision_count": high_count,
        "critical_debt_decision_count": critical_count,
        "average_decision_debt_usd": avg_debt,
        "wisdom_index_penalty_points": debt_penalty,
    }


async def recommend_debt_reduction(db: AsyncSession) -> list[str]:
    """Recommend actions for the highest open debt assessments."""
    high_debts = (await db.execute(
        select(DecisionDebtAssessment).where(
            DecisionDebtAssessment.is_paid_off.is_(False)
        ).order_by(DecisionDebtAssessment.debt_score.desc()).limit(5)
    )).scalars().all()

    recommendations = []
    for debt in high_debts:
        recommendations.append(
            f"Decision {debt.decision_id}: repay {debt.repayment_priority.lower()} "
            f"{debt.debt_category.lower()} debt (${debt.repayment_cost_estimate:,.0f}) - "
            f"{debt.description or 'no description'}"
        )

    logger.info("Decision Debt: %d recommendations generated", len(recommendations))
    return recommendations
