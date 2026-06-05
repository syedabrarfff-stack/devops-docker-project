"""AIONX Executive Accountability Engine.

Tracks decision quality by accountable executor role and identifies when Captain
review should be required.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    CounterfactualActualization,
    CounterfactualSimulation,
    DecisionObject,
)

logger = logging.getLogger(__name__)


async def score_decision_quality(
    db: AsyncSession,
    decision_id: uuid.UUID,
    actual_outcome_quality: float,
) -> dict[str, Any]:
    """Score the quality of a single decision from 0-100."""
    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    outcome_score = actual_outcome_quality * 100
    confidence_penalty = (1.0 - decision.confidence_score) * 20
    quality_score = max(0, min(100, outcome_score - confidence_penalty))

    logger.info("Accountability: decision %s quality score %.1f", decision_id, quality_score)
    return {
        "decision_id": str(decision_id),
        "quality_score": quality_score,
        "outcome_score": outcome_score,
        "confidence_penalty": confidence_penalty,
    }


async def track_maker_accuracy(
    db: AsyncSession,
    maker_id: str,
) -> dict[str, Any]:
    """Compute decision accuracy for an executor role or human authority label."""
    decisions = (await db.execute(
        select(DecisionObject).where(
            DecisionObject.executor_role == maker_id
        ).order_by(DecisionObject.created_at.desc()).limit(20)
    )).scalars().all()

    if not decisions:
        return {
            "maker_id": maker_id,
            "accuracy": 0.5,
            "decisions_tracked": 0,
            "authority_score": 50,
        }

    accuracy_scores = []
    for decision in decisions:
        accuracy_scores.extend(await _actuality_scores_for_decision(db, decision.id))

    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.5
    authority_score = avg_accuracy * 100

    logger.info("Accountability: maker %s authority %.1f", maker_id, authority_score)
    return {
        "maker_id": maker_id,
        "accuracy": avg_accuracy,
        "decisions_tracked": len(decisions),
        "decisions_with_outcomes": len(accuracy_scores),
        "authority_score": authority_score,
    }


async def compute_authority_decay(
    db: AsyncSession,
    maker_id: str,
) -> dict[str, Any]:
    """Reduce authority if recent accuracy is declining."""
    recent = await track_maker_accuracy(db, maker_id)
    sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    old_decisions = (await db.execute(
        select(DecisionObject).where(
            DecisionObject.executor_role == maker_id,
            DecisionObject.created_at >= sixty_days_ago,
            DecisionObject.created_at < thirty_days_ago,
        )
    )).scalars().all()

    old_scores = []
    for decision in old_decisions:
        old_scores.extend(await _actuality_scores_for_decision(db, decision.id))

    previous_authority = (sum(old_scores) / len(old_scores) * 100) if old_scores else 50.0
    current_authority = recent["authority_score"]
    authority_decay = previous_authority - current_authority

    recommendations = []
    if authority_decay > 10:
        recommendations.append(f"Authority declining: {authority_decay:.1f}pt drop. Increase oversight.")
    if current_authority < 40:
        recommendations.append("Low authority. Require Captain approval for all decisions.")
    if current_authority > 85:
        recommendations.append("High authority. Grant expanded decision autonomy.")

    return {
        "maker_id": maker_id,
        "previous_authority": previous_authority,
        "current_authority": current_authority,
        "authority_decay": authority_decay,
        "recommendations": recommendations,
    }


async def escalate_for_captain_review(
    db: AsyncSession,
    decision_id: uuid.UUID,
) -> dict[str, Any]:
    """Flag a decision for Captain review when authority or confidence is weak."""
    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    escalation_reasons = []
    maker_accuracy = await track_maker_accuracy(db, decision.executor_role)
    if maker_accuracy["authority_score"] < 50:
        escalation_reasons.append(f"Low maker authority: {maker_accuracy['authority_score']:.0f}")
    if decision.tier <= 1:
        escalation_reasons.append(f"High-stakes decision (tier {decision.tier})")
    if decision.confidence_score < 0.6:
        escalation_reasons.append(f"Low confidence: {decision.confidence_score:.0%}")

    escalated = len(escalation_reasons) > 0
    logger.info("Accountability: decision %s escalated=%s", decision_id, escalated)
    return {
        "decision_id": str(decision_id),
        "escalated": escalated,
        "escalation_reasons": escalation_reasons,
    }


async def _actuality_scores_for_decision(db: AsyncSession, decision_id: uuid.UUID) -> list[float]:
    simulations = (await db.execute(
        select(CounterfactualSimulation.id).where(CounterfactualSimulation.decision_id == decision_id)
    )).scalars().all()
    if not simulations:
        return []

    actualities = (await db.execute(
        select(CounterfactualActualization).where(
            CounterfactualActualization.simulation_id.in_(simulations)
        )
    )).scalars().all()

    scores = []
    for actuality in actualities:
        if actuality.overall_calibration is not None:
            scores.append(float(actuality.overall_calibration))
        elif actuality.day_30_actual:
            scores.append(1.0 if "positive" in actuality.day_30_actual.lower() else 0.0)
    return scores
