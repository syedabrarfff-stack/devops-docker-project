"""AIONX Decision Debt Engine — quantify the cost of bad decisions.

Every wrong decision carries debt: lost revenue, remediation cost, opportunity cost.
Aggregates into institutional debt penalty on Wisdom Index.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import DecisionDebtAssessment, InstitutionalDebtIndex, DecisionObject

logger = logging.getLogger(__name__)


async def compute_decision_debt(
    db: AsyncSession,
    decision_id: uuid.UUID,
    lost_revenue_usd: float = 0.0,
    remediation_effort_hours: float = 0.0,
    opportunity_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Compute total debt for a single bad decision.

    Formula: debt = (lost_revenue * 0.4) + (remediation_hours * 150 * 0.3) + (opportunity * 0.3)
    """

    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    # Compute weighted debt
    revenue_component = lost_revenue_usd * 0.4
    remediation_component = (remediation_effort_hours * 150) * 0.3  # $150/hour engineering rate
    opportunity_component = opportunity_cost_usd * 0.3

    total_debt = revenue_component + remediation_component + opportunity_component

    # Store debt assessment
    assessment = DecisionDebtAssessment(
        decision_id=decision_id,
        lost_revenue_usd=lost_revenue_usd,
        remediation_effort_hours=remediation_effort_hours,
        opportunity_cost_usd=opportunity_cost_usd,
        total_debt_usd=total_debt,
        debt_status="ACTIVE",
    )
    db.add(assessment)
    await db.flush()

    logger.info(
        "Decision Debt: decision %s debt=$%.2f (revenue=$%.2f + remediation=$%.2f + opportunity=$%.2f)",
        decision_id, total_debt, revenue_component, remediation_component, opportunity_component
    )

    return {
        "assessment_id": str(assessment.id),
        "decision_id": str(decision_id),
        "total_debt_usd": total_debt,
        "components": {
            "revenue": revenue_component,
            "remediation": remediation_component,
            "opportunity": opportunity_component,
        },
    }


async def assess_institutional_debt(db: AsyncSession) -> dict[str, Any]:
    """Aggregate all active debt across all decisions."""

    # Sum all active debt
    total_debt = (await db.execute(
        select(func.sum(DecisionDebtAssessment.total_debt_usd)).where(
            DecisionDebtAssessment.debt_status == "ACTIVE"
        )
    )).scalar_one()

    total_debt = total_debt or 0.0

    # Count high-debt decisions
    high_debt_decisions = (await db.execute(
        select(func.count()).select_from(DecisionDebtAssessment).where(
            DecisionDebtAssessment.debt_status == "ACTIVE",
            DecisionDebtAssessment.total_debt_usd > 50000,
        )
    )).scalar_one()

    # Average debt per decision
    avg_debt = (await db.execute(
        select(func.avg(DecisionDebtAssessment.total_debt_usd)).where(
            DecisionDebtAssessment.debt_status == "ACTIVE"
        )
    )).scalar_one()

    avg_debt = avg_debt or 0.0

    # Store institutional index
    index = InstitutionalDebtIndex(
        total_debt_usd=total_debt,
        high_debt_decision_count=high_debt_decisions,
        average_decision_debt_usd=avg_debt,
        debt_trajectory="STABLE",  # or RISING, FALLING
    )
    db.add(index)
    await db.flush()

    # Compute debt penalty for Wisdom Index (0-20 points)
    # $100k debt = -5 points, $500k = -20 points
    debt_penalty = min(20.0, (total_debt / 100000) * 5)

    logger.info(
        "Institutional Debt: total=$%.2f, high-debt decisions=%d, penalty=%.1f pts",
        total_debt, high_debt_decisions, debt_penalty
    )

    return {
        "index_id": str(index.id),
        "total_institutional_debt_usd": total_debt,
        "high_debt_decision_count": high_debt_decisions,
        "average_decision_debt_usd": avg_debt,
        "wisdom_index_penalty_points": debt_penalty,
    }


async def recommend_debt_reduction(db: AsyncSession) -> list[str]:
    """Recommend actions to reduce institutional debt."""

    # Get highest-debt decisions
    high_debts = (await db.execute(
        select(DecisionDebtAssessment).where(
            DecisionDebtAssessment.debt_status == "ACTIVE"
        ).order_by(DecisionDebtAssessment.total_debt_usd.desc()).limit(5)
    )).scalars().all()

    recommendations = []

    for debt in high_debts:
        if debt.lost_revenue_usd > 50000:
            recommendations.append(
                f"Decision {debt.decision_id}: Reverse or pivot this decision (${debt.lost_revenue_usd:,.0f} revenue loss)"
            )
        if debt.remediation_effort_hours > 100:
            recommendations.append(
                f"Decision {debt.decision_id}: Allocate engineering team to remediation (${debt.remediation_effort_hours * 150:,.0f} cost)"
            )
        if debt.opportunity_cost_usd > 50000:
            recommendations.append(
                f"Decision {debt.decision_id}: Consider strategic pivot ({debt.opportunity_cost_usd:,.0f} missed opportunity)"
            )

    logger.info("Decision Debt: %d recommendations generated", len(recommendations))

    return recommendations
