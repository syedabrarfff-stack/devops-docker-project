"""AIONX Client Trust Index — track and predict client satisfaction.

Trust score (0-100) reflects: delivery quality, communication, problem resolution,
result accuracy, culture fit.

Feeds into Digital Twin predictions and churn detection.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import ClientDigitalTwin, ClientTwinInteraction, MissionOwnershipRecord

logger = logging.getLogger(__name__)

# Trust score factors (0-100, all weight equally)
TRUST_FACTORS = {
    "on_time_delivery": 20,      # 20% of score
    "communication_quality": 20,  # 20%
    "problem_resolution": 20,     # 20%
    "result_accuracy": 20,        # 20%
    "culture_fit": 20,            # 20%
}


async def compute_trust_score(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> dict[str, Any]:
    """Compute 0-100 trust score for a client."""

    twin = (await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )).scalars().first()

    if not twin:
        return {"error": "client twin not found"}

    # Get all missions for this client
    missions = (await db.execute(
        select(MissionOwnershipRecord).where(
            MissionOwnershipRecord.client_id == client_id
        ).limit(100)
    )).scalars().all()

    # Compute score factors
    factors = {
        "on_time_delivery": 85,  # Default
        "communication_quality": 80,
        "problem_resolution": 75,
        "result_accuracy": 80,
        "culture_fit": 70,
    }

    if missions:
        # On-time delivery: percentage of missions completed on time
        on_time_count = sum(1 for m in missions if m.delivery_on_time)
        factors["on_time_delivery"] = (on_time_count / len(missions)) * 100 if missions else 50

        # Problem resolution: correlation with repair loops (fewer = better)
        avg_repairs = sum(m.repair_loops_count for m in missions) / len(missions)
        factors["problem_resolution"] = max(20, 100 - (avg_repairs * 10))

        # Result accuracy: satisfaction scores from completed missions
        satisfied = sum(1 for m in missions if (m.client_satisfaction_score or 0) > 80)
        factors["result_accuracy"] = (satisfied / len(missions)) * 100 if missions else 50

    # Weighted trust score
    trust_score = sum(
        factors.get(factor, 50) * (weight / 100)
        for factor, weight in TRUST_FACTORS.items()
    )

    # Update twin
    twin.trust_score = trust_score
    await db.flush()

    logger.info(
        "Client Trust: computed score %.1f for client %s (factors: %s)",
        trust_score, client_id, factors
    )

    return {
        "client_id": str(client_id),
        "trust_score": trust_score,
        "factors": factors,
    }


async def escalate_trust_erosion(
    db: AsyncSession,
    client_id: uuid.UUID,
    threshold: float = 20.0,  # Alert if drop >20 points over last 30 days
) -> dict[str, Any]:
    """Alert if client trust is eroding based on recent interaction deltas."""

    twin = (await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )).scalars().first()

    if not twin:
        return {"error": "client twin not found"}

    current_score = twin.trust_score or 70

    # Sum trust_deltas from interactions in the last 30 days to compute actual erosion.
    # Negative net delta = trust is falling; if the drop exceeds threshold, alert.
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_delta = (await db.execute(
        select(func.coalesce(func.sum(ClientTwinInteraction.trust_delta), 0.0)).where(
            ClientTwinInteraction.twin_id == twin.id,
            ClientTwinInteraction.occurred_at >= thirty_days_ago,
        )
    )).scalar_one()
    recent_delta = float(recent_delta)

    # previous_score is reconstructed from the current score minus recent adjustments
    previous_score = max(0.0, current_score - recent_delta)
    score_change = previous_score - current_score  # positive = erosion (score fell)
    pct_change = (score_change / previous_score * 100) if previous_score > 0 else 0.0

    escalated = score_change > threshold

    if escalated:
        logger.warning(
            "Client Trust: EROSION ALERT for client %s (%.1f pt drop, %.1f%% — from %.1f to %.1f over 30d)",
            client_id, score_change, pct_change, previous_score, current_score
        )

    return {
        "client_id": str(client_id),
        "current_score": current_score,
        "previous_score": round(previous_score, 1),
        "score_change_30d": round(score_change, 1),
        "pct_change": round(pct_change, 1),
        "escalated": escalated,
        "escalation_reason": "Trust erosion detected" if escalated else None,
    }


async def recovery_protocol(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> list[str]:
    """Auto-recommend trust-building actions."""

    twin = (await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )).scalars().first()

    if not twin:
        return []

    trust_score = twin.trust_score or 70
    actions = []

    # Base actions for all clients
    actions.append("Schedule monthly executive check-in call")

    if trust_score < 50:
        actions.extend([
            "URGENT: Assign dedicated success manager",
            "Conduct discovery call to identify concerns",
            "Offer service credit or pro-bono improvement work",
        ])
    elif trust_score < 70:
        actions.extend([
            "Increase communication frequency (weekly standup)",
            "Provide transparent progress dashboards",
            "Celebrate quick wins publicly",
        ])
    elif trust_score > 85:
        actions.extend([
            "Offer upsell opportunity (expand services)",
            "Request testimonial/case study",
            "Invite to advisory board or beta program",
        ])

    logger.info("Client Trust: %d recovery actions recommended for client %s", len(actions), client_id)

    return actions
