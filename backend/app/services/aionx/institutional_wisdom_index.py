"""Institutional Wisdom Index — master fitness signal of the AIONX organism.

Measures organizational intelligence growth. The organism optimizes itself
against this score every week. Captain's briefing begins with Wisdom Index.
Score: 0–1000. Starts at 500.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    DecisionObject,
    DecisionOutcome,
    InstitutionalDebtIndex,
    WisdomIndexSnapshot,
)


WEIGHTS = {
    "decision_accuracy": 100,
    "calibration_quality": 80,
    "counterfactual_precision": 40,
    "provider_authority": 80,
    "pattern_reuse": 60,
    "client_retention": 75,
    "debt_burden": -150,  # penalty, capped
    "knowledge_freshness": 50,
    "convergence_efficiency": 40,
    "self_mod_success": 50,
}

BASE_SCORE = 500.0
MAX_SCORE = 1000.0


async def compute_weekly_wisdom(
    db: AsyncSession,
    week_of: date | None = None,
) -> WisdomIndexSnapshot:
    if not week_of:
        week_of = datetime.utcnow().date()

    week_start = datetime.combine(week_of - timedelta(days=7), datetime.min.time())
    week_end = datetime.combine(week_of, datetime.max.time())

    # Decision accuracy
    decisions_result = await db.execute(
        select(DecisionObject).where(
            DecisionObject.created_at.between(week_start, week_end),
            DecisionObject.outcome_summary.is_not(None),
        )
    )
    decisions = decisions_result.scalars().all()
    total = len(decisions)
    correct = sum(1 for d in decisions if d.outcome_summary and "success" in d.outcome_summary.lower())
    accuracy_ratio = correct / total if total > 0 else 0.5
    decision_accuracy_score = accuracy_ratio * WEIGHTS["decision_accuracy"]

    # Decision debt burden
    debt_result = await db.execute(
        select(InstitutionalDebtIndex).order_by(InstitutionalDebtIndex.created_at.desc()).limit(1)
    )
    debt = debt_result.scalar_one_or_none()
    debt_burden_penalty = min(
        abs(WEIGHTS["debt_burden"]),
        (debt.total_debt_score / 10.0) if debt else 0.0,
    )

    # Previous score
    prev_result = await db.execute(
        select(WisdomIndexSnapshot).order_by(WisdomIndexSnapshot.created_at.desc()).limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    previous_score = prev.wisdom_score if prev else BASE_SCORE

    wisdom_score = min(
        MAX_SCORE,
        BASE_SCORE
        + decision_accuracy_score
        + WEIGHTS["calibration_quality"] * 0.5
        + WEIGHTS["pattern_reuse"] * 0.4
        + WEIGHTS["client_retention"] * 0.6
        - debt_burden_penalty
        + WEIGHTS["knowledge_freshness"] * 0.3,
    )

    snapshot = WisdomIndexSnapshot(
        week_of=week_of,
        wisdom_score=round(wisdom_score, 1),
        previous_score=round(previous_score, 1),
        delta=round(wisdom_score - previous_score, 1),
        decision_accuracy_score=round(decision_accuracy_score, 1),
        calibration_quality_score=round(WEIGHTS["calibration_quality"] * 0.5, 1),
        counterfactual_precision_score=0.0,
        provider_authority_score=round(WEIGHTS["provider_authority"] * 0.5, 1),
        pattern_reuse_score=round(WEIGHTS["pattern_reuse"] * 0.4, 1),
        client_retention_score=round(WEIGHTS["client_retention"] * 0.6, 1),
        debt_burden_penalty=round(debt_burden_penalty, 1),
        knowledge_freshness_score=round(WEIGHTS["knowledge_freshness"] * 0.3, 1),
        convergence_efficiency_score=0.0,
        self_mod_success_score=0.0,
        narrative=_generate_narrative(wisdom_score, previous_score, correct, total, debt),
        recommendations=_generate_recommendations(wisdom_score, debt_burden_penalty),
    )
    db.add(snapshot)
    await db.commit()
    return snapshot


def _generate_narrative(
    score: float,
    previous: float,
    correct: int,
    total: int,
    debt: Any,
) -> str:
    delta = score - previous
    direction = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
    accuracy_pct = f"{(correct / total * 100):.0f}%" if total > 0 else "N/A"
    debt_score = f"{debt.total_debt_score:.0f}" if debt else "0"
    return (
        f"AIONX Wisdom Index: {score:.0f} ({direction} this week). "
        f"Decision accuracy: {accuracy_pct} ({correct}/{total}). "
        f"Institutional debt: {debt_score}. "
        f"{'Wisdom growing — organism becoming wiser.' if delta >= 0 else 'Wisdom declining — investigate root causes.'}"
    )


def _generate_recommendations(score: float, debt_penalty: float) -> list[str]:
    recs = []
    if debt_penalty > 100:
        recs.append("CRITICAL: Begin debt refactoring initiative — debt burden exceeding threshold.")
    if score < 600:
        recs.append("Wisdom below optimal — review recent incorrect decisions for pattern causes.")
    if score > 800:
        recs.append("High wisdom achieved — consider promoting top patterns to Tier 1 automation.")
    return recs


async def get_current_wisdom(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(WisdomIndexSnapshot).order_by(WisdomIndexSnapshot.created_at.desc()).limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return {"wisdom_score": BASE_SCORE, "narrative": "No data yet — wisdom starts at 500."}
    return {
        "wisdom_score": snapshot.wisdom_score,
        "delta": snapshot.delta,
        "narrative": snapshot.narrative,
        "week_of": snapshot.week_of.isoformat(),
        "recommendations": snapshot.recommendations,
    }
