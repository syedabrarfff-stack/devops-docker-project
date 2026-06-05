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

from app.models.aionx_organs import ClientDigitalTwin, MissionOwnershipRecord

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
        )
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
    threshold: float = 20.0,  # Alert if drop >20%
) -> dict[str, Any]:
    """Alert if client trust is eroding."""

    twin = (await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )).scalars().first()

    if not twin:
        return {"error": "client twin not found"}

    current_score = twin.trust_score or 70
    previous_score = twin.previous_trust_score or current_score  # Default to current

    score_change = previous_score - current_score
    pct_change = (score_change / previous_score * 100) if previous_score > 0 else 0

    escalated = pct_change > threshold

    if escalated:
        logger.warning(
            "Client Trust: EROSION ALERT for client %s (%.1f%% drop from %.1f to %.1f)",
            client_id, pct_change, previous_score, current_score
        )

    return {
        "client_id": str(client_id),
        "current_score": current_score,
        "previous_score": previous_score,
        "pct_change": pct_change,
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
