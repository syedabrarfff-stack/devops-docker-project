"""AIONX Executive Accountability Engine — track decision quality by decision maker.

Every AI agent and human has an authority score based on decision accuracy.
Low-accuracy makers get escalations and oversight. High-accuracy makers get autonomy.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import DecisionObject, CounterfactualActualization

logger = logging.getLogger(__name__)


async def score_decision_quality(
    db: AsyncSession,
    decision_id: uuid.UUID,
    actual_outcome_quality: float,  # 0.0-1.0 (1.0 = perfect)
) -> dict[str, Any]:
    """Score the quality of a single decision (0-100)."""

    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    # Quality score: weighted combination of outcome + confidence
    outcome_score = actual_outcome_quality * 100
    confidence_penalty = (1.0 - decision.confidence_score) * 20  # Over-confidence penalty

    quality_score = max(0, min(100, outcome_score - confidence_penalty))

    logger.info(
        "Accountability: decision %s quality score %.1f (outcome=%.2f, confidence=%.2f)",
        decision_id, quality_score, actual_outcome_quality, decision.confidence_score
    )

    return {
        "decision_id": str(decision_id),
        "quality_score": quality_score,
        "outcome_score": outcome_score,
        "confidence_penalty": confidence_penalty,
    }


async def track_maker_accuracy(
    db: AsyncSession,
    maker_id: str,  # AI agent name or human identifier
) -> dict[str, Any]:
    """Compute decision accuracy for a specific decision maker."""

    # Get all decisions by this maker
    decisions = (await db.execute(
        select(DecisionObject).where(
            DecisionObject.created_by == maker_id
        ).order_by(DecisionObject.created_at.desc()).limit(20)
    )).scalars().all()

    if not decisions:
        return {
            "maker_id": maker_id,
            "accuracy": 0.5,  # Default for new makers
            "decisions_tracked": 0,
            "authority_score": 50,  # Neutral authority
        }

    # For each decision, check if there's an actuality
    accuracy_scores = []

    for decision in decisions:
        actuality = (await db.execute(
            select(CounterfactualActualization).where(
                CounterfactualActualization.decision_id == decision.id
            )
        )).scalars().first()

        if actuality:
            # Simple accuracy: was outcome positive?
            is_accurate = 1.0 if "positive" in actuality.actual_outcome.lower() else 0.0
            accuracy_scores.append(is_accurate)

    # Compute average accuracy
    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.5

    # Authority score: 0-100 based on accuracy
    authority_score = avg_accuracy * 100

    logger.info(
        "Accountability: maker %s accuracy %.2f%% (%d decisions)",
        maker_id, avg_accuracy * 100, len(decisions)
    )

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
    """Reduce authority if accuracy is declining."""

    # Track maker accuracy over time
    last_30_days_accuracy = await track_maker_accuracy(db, maker_id)

    # Get decisions from 30-60 days ago for comparison
    sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    old_decisions = (await db.execute(
        select(DecisionObject).where(
            DecisionObject.created_by == maker_id,
            DecisionObject.created_at >= sixty_days_ago,
            DecisionObject.created_at < thirty_days_ago,
        )
    )).scalars().all()

    old_accuracy = 0.5  # Default
    if old_decisions:
        old_accuracies = []
        for decision in old_decisions:
            actuality = (await db.execute(
                select(CounterfactualActualization).where(
                    CounterfactualActualization.decision_id == decision.id
                )
            )).scalars().first()
            if actuality:
                is_accurate = 1.0 if "positive" in actuality.actual_outcome.lower() else 0.0
                old_accuracies.append(is_accurate)
        if old_accuracies:
            old_accuracy = sum(old_accuracies) / len(old_accuracies)

    # Compute decay
    current_authority = last_30_days_accuracy["authority_score"]
    previous_authority = old_accuracy * 100

    authority_decay = previous_authority - current_authority

    # Recommendations
    recommendations = []
    if authority_decay > 10:
        recommendations.append(f"Authority declining: {authority_decay:.1f}pt drop. Increase oversight.")
    if current_authority < 40:
        recommendations.append("Low authority. Require Captain approval for all decisions.")
    if current_authority > 85:
        recommendations.append("High authority. Grant expanded decision autonomy.")

    logger.info(
        "Accountability: maker %s decay %.1f pts (prev=%.1f now=%.1f)",
        maker_id, authority_decay, previous_authority, current_authority
    )

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
    """Flag decision for Captain review (low authority maker, high stakes, etc.)."""

    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    escalation_reasons = []

    # Check maker authority
    maker_accuracy = await track_maker_accuracy(db, decision.created_by)
    if maker_accuracy["authority_score"] < 50:
        escalation_reasons.append(f"Low maker authority: {maker_accuracy['authority_score']:.0f}")

    # Check decision tier
    if decision.tier <= 1:  # Tier 1 = strategic/high-stakes
        escalation_reasons.append(f"High-stakes decision (tier {decision.tier})")

    # Check confidence
    if decision.confidence_score < 0.6:
        escalation_reasons.append(f"Low confidence: {decision.confidence_score:.0%}")

    escalated = len(escalation_reasons) > 0

    logger.info(
        "Accountability: decision %s %s for Captain review (%s)",
        decision_id, "escalated" if escalated else "approved", "; ".join(escalation_reasons)
    )

    return {
        "decision_id": str(decision_id),
        "escalated": escalated,
        "escalation_reasons": escalation_reasons,
    }
