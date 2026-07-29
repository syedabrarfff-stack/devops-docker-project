"""AIONX HIA Certification Engine — performance-based skill certification for AI agents.

Every AI agent (HIA) has a certification tier based on accuracy, speed, and reliability.
Tiers unlock autonomy levels: higher tier = more autonomous decisions without escalation.
"""
from __future__ import annotations

import logging
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

# Certification tiers
CERTIFICATION_TIERS = {
    "TIER_0": {
        "name": "Unproven",
        "min_accuracy": 0.0,
        "min_decisions": 0,
        "autonomous_threshold": 0.0,  # No autonomous decisions
        "escalation_required": True,
    },
    "TIER_1": {
        "name": "Junior",
        "min_accuracy": 0.60,
        "min_decisions": 5,
        "autonomous_threshold": 0.5,  # ≤50% autonomy for tier 1 decisions
        "escalation_required": True,
    },
    "TIER_2": {
        "name": "Proficient",
        "min_accuracy": 0.75,
        "min_decisions": 15,
        "autonomous_threshold": 0.7,  # ≤70% autonomy for tier 2 decisions
        "escalation_required": True,
    },
    "TIER_3": {
        "name": "Expert",
        "min_accuracy": 0.85,
        "min_decisions": 30,
        "autonomous_threshold": 0.95,  # ≤95% autonomy for tier 3 decisions
        "escalation_required": False,  # Can make tier 2+ decisions autonomously
    },
    "TIER_4": {
        "name": "Master",
        "min_accuracy": 0.92,
        "min_decisions": 50,
        "autonomous_threshold": 1.0,  # Full autonomy (with logging)
        "escalation_required": False,
    },
}


async def compute_hia_certification(
    db: AsyncSession,
    hia_agent_id: str,
) -> dict[str, Any]:
    """Compute HIA certification tier based on decision performance."""

    # Get all decisions by this HIA
    decisions_result = await db.execute(
        select(DecisionObject).where(
            DecisionObject.executor_role == hia_agent_id
        ).order_by(DecisionObject.created_at.desc()).limit(100)
    )
    decisions = decisions_result.scalars().all()

    if not decisions:
        return {
            "hia_agent_id": hia_agent_id,
            "tier": "TIER_0",
            "tier_name": "Unproven",
            "decisions_evaluated": 0,
            "accuracy": 0.0,
            "recommendation": "Insufficient decision history",
        }

    # Calculate accuracy from outcomes
    accuracy_scores = []
    for decision in decisions:
        accuracy_scores.extend(await _actuality_scores_for_decision(db, decision.id))

    accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0

    # Determine tier
    current_tier = "TIER_0"
    for tier_key in reversed(["TIER_4", "TIER_3", "TIER_2", "TIER_1"]):
        tier = CERTIFICATION_TIERS[tier_key]
        if accuracy >= tier["min_accuracy"] and len(decisions) >= tier["min_decisions"]:
            current_tier = tier_key
            break

    tier_info = CERTIFICATION_TIERS[current_tier]

    logger.info(
        "HIA Certification: %s → %s (%s, %.0f%% accuracy, %d decisions)",
        hia_agent_id, current_tier, tier_info["name"], accuracy * 100, len(decisions)
    )

    return {
        "hia_agent_id": hia_agent_id,
        "tier": current_tier,
        "tier_name": tier_info["name"],
        "accuracy": accuracy,
        "decisions_evaluated": len(decisions),
        "min_accuracy_for_next": next(
            (CERTIFICATION_TIERS[t]["min_accuracy"] for t in ["TIER_4", "TIER_3", "TIER_2", "TIER_1"]
             if CERTIFICATION_TIERS[t]["min_accuracy"] > accuracy),
            1.0
        ),
        "escalation_required": tier_info["escalation_required"],
        "autonomous_limit": tier_info["autonomous_threshold"],
    }


async def check_certification_renewal(
    db: AsyncSession,
    hia_agent_id: str,
    last_certified_at: datetime | None = None,
    renewal_interval_days: int = 30,
) -> dict[str, Any]:
    """Check if HIA certification needs renewal (accuracy decline over time)."""

    if not last_certified_at:
        last_certified_at = datetime.now(timezone.utc) - timedelta(days=renewal_interval_days)

    # Get recent decisions
    recent_result = await db.execute(
        select(DecisionObject).where(
            DecisionObject.executor_role == hia_agent_id,
            DecisionObject.created_at >= last_certified_at,
        ).limit(200)
    )
    recent_decisions = recent_result.scalars().all()

    if len(recent_decisions) < 3:
        return {
            "hia_agent_id": hia_agent_id,
            "renewal_due": False,
            "reason": "Insufficient recent decisions",
        }

    # Check accuracy on recent decisions
    recent_accuracy_scores = []
    for decision in recent_decisions:
        recent_accuracy_scores.extend(await _actuality_scores_for_decision(db, decision.id))

    recent_accuracy = sum(recent_accuracy_scores) / len(recent_accuracy_scores) if recent_accuracy_scores else 0.5

    # Get historical accuracy
    certification = await compute_hia_certification(db, hia_agent_id)
    historical_accuracy = certification["accuracy"]

    # Renewal triggered if recent accuracy >10% below historical
    decline = historical_accuracy - recent_accuracy
    renewal_due = decline > 0.10

    logger.info(
        "HIA Certification Renewal: %s (recent=%.0f%%, historical=%.0f%%, decline=%.0f%%) → %s",
        hia_agent_id,
        recent_accuracy * 100,
        historical_accuracy * 100,
        decline * 100,
        "RENEWAL_DUE" if renewal_due else "VALID"
    )

    return {
        "hia_agent_id": hia_agent_id,
        "renewal_due": renewal_due,
        "recent_accuracy": recent_accuracy,
        "historical_accuracy": historical_accuracy,
        "accuracy_decline": decline,
        "recommendation": (
            f"CRITICAL: {hia_agent_id} accuracy declined {decline:.0%}. "
            f"Recommend retraining or escalation policy change."
            if renewal_due
            else f"{hia_agent_id} performing nominally."
        ),
    }


async def grant_hia_certification(
    db: AsyncSession,
    hia_agent_id: str,
    tier: str,
    certified_by: str = "AIONX_AUTO",
) -> dict[str, Any]:
    """Record HIA certification grant with tier assignment."""

    if tier not in CERTIFICATION_TIERS:
        return {"error": f"Invalid tier: {tier}"}

    tier_info = CERTIFICATION_TIERS[tier]

    logger.info(
        "HIA Certification Granted: %s → %s (%s)",
        hia_agent_id, tier, tier_info["name"]
    )

    return {
        "hia_agent_id": hia_agent_id,
        "tier": tier,
        "tier_name": tier_info["name"],
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "certified_by": certified_by,
        "escalation_required": tier_info["escalation_required"],
        "autonomy_level": tier_info["autonomous_threshold"],
    }


async def revoke_hia_certification(
    db: AsyncSession,
    hia_agent_id: str,
    reason: str = "Performance decline",
    revoked_by: str = "AIONX_AUTO",
) -> dict[str, Any]:
    """Revoke HIA certification and downgrade to TIER_0 (supervised)."""

    logger.warning(
        "HIA Certification Revoked: %s (reason: %s)",
        hia_agent_id, reason
    )

    return {
        "hia_agent_id": hia_agent_id,
        "tier": "TIER_0",
        "tier_name": "Unproven",
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "revoked_by": revoked_by,
        "reason": reason,
        "escalation_required": True,
        "autonomy_level": 0.0,
        "action": "All decisions require Captain approval pending retraining",
    }


async def _actuality_scores_for_decision(db: AsyncSession, decision_id) -> list[float]:
    """Map a decision to counterfactual actualizations through simulations."""
    simulation_ids = (await db.execute(
        select(CounterfactualSimulation.id).where(CounterfactualSimulation.decision_id == decision_id).limit(100)
    )).scalars().all()
    if not simulation_ids:
        return []

    actualities = (await db.execute(
        select(CounterfactualActualization).where(
            CounterfactualActualization.simulation_id.in_(simulation_ids)
        ).limit(100)
    )).scalars().all()

    scores: list[float] = []
    for actuality in actualities:
        if actuality.overall_calibration is not None:
            scores.append(float(actuality.overall_calibration))
        elif actuality.day_30_accuracy_score is not None:
            scores.append(float(actuality.day_30_accuracy_score))
        elif actuality.day_30_actual:
            scores.append(1.0 if "positive" in actuality.day_30_actual.lower() else 0.0)
    return scores
