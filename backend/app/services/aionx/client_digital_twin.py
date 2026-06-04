"""Client Digital Twin Engine — persistent executive profile per client.

Every client receives a living psychological/operational/political memory profile.
Updated after every interaction. HIA agents load it before every call.
Churn detection and upsell prediction run continuously.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ClientDigitalTwin,
    ClientTwinInteraction,
    ClientTwinPrediction,
)


async def get_or_create_twin(
    db: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> ClientDigitalTwin:
    result = await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )
    twin = result.scalar_one_or_none()
    if not twin:
        twin = ClientDigitalTwin(client_id=client_id, tenant_id=tenant_id)
        db.add(twin)
        await db.commit()
    return twin


async def update_twin_profile(
    db: AsyncSession,
    client_id: uuid.UUID,
    updates: dict[str, Any],
) -> ClientDigitalTwin:
    result = await db.execute(
        select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
    )
    twin = result.scalar_one_or_none()
    if not twin:
        twin = ClientDigitalTwin(client_id=client_id)
        db.add(twin)

    allowed_fields = {
        "communication_preferences", "decision_speed", "risk_tolerance",
        "budget_authority", "internal_politics", "buying_psychology",
        "technical_maturity", "support_expectation", "preferred_hia_agent",
        "historical_objections", "successful_strategies", "trust_score",
        "stakeholder_map", "churn_risk_score", "upsell_opportunity_score",
        "renewal_probability",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(twin, field, value)

    twin.updated_at = datetime.utcnow()
    await db.commit()
    return twin


async def record_interaction(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    interaction_type: str,
    hia_agent: str | None = None,
    sentiment: str = "neutral",
    trust_delta: float = 0.0,
    summary: str | None = None,
    profile_updates: dict[str, Any] | None = None,
    raw_notes: str | None = None,
) -> ClientTwinInteraction:
    twin = await get_or_create_twin(db, client_id)

    interaction = ClientTwinInteraction(
        twin_id=twin.id,
        interaction_type=interaction_type,
        hia_agent=hia_agent,
        sentiment=sentiment,
        trust_delta=trust_delta,
        summary=summary,
        profile_updates=profile_updates or {},
        raw_notes=raw_notes,
    )
    db.add(interaction)

    # Update trust score
    twin.trust_score = max(0.0, min(100.0, twin.trust_score + trust_delta))
    twin.last_interaction_at = datetime.utcnow()
    twin.updated_at = datetime.utcnow()

    if profile_updates:
        await update_twin_profile(db, client_id, profile_updates)

    await db.commit()
    return interaction


async def update_predictions(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> list[ClientTwinPrediction]:
    twin = await get_or_create_twin(db, client_id)

    # Churn risk: higher if low trust, no recent interaction
    days_since_interaction = 0
    if twin.last_interaction_at:
        days_since_interaction = (datetime.utcnow() - twin.last_interaction_at).days

    churn_risk = min(1.0, (
        (1.0 - twin.trust_score / 100.0) * 0.6
        + (min(days_since_interaction, 90) / 90.0) * 0.4
    ))

    upsell_opportunity = max(0.0, (
        (twin.trust_score / 100.0) * 0.5
        + twin.upsell_opportunity_score * 0.5
    ))

    predictions_data = [
        ("CHURN_RISK", churn_risk, "churn_risk"),
        ("UPSELL_OPPORTUNITY", upsell_opportunity, "upsell_opportunity"),
        ("RENEWAL_PROBABILITY", twin.renewal_probability, "renewal"),
    ]

    predictions = []
    for model_type, value, label in predictions_data:
        result = await db.execute(
            select(ClientTwinPrediction).where(
                ClientTwinPrediction.twin_id == twin.id,
                ClientTwinPrediction.model_type == model_type,
            )
        )
        pred = result.scalar_one_or_none()
        if not pred:
            pred = ClientTwinPrediction(twin_id=twin.id, model_type=model_type)
            db.add(pred)

        pred.confidence = min(1.0, abs(value))
        pred.prediction_value = value
        pred.prediction_label = label
        pred.updated_at = datetime.utcnow()
        predictions.append(pred)

    # Alert on high churn risk
    if churn_risk > 0.7:
        twin.churn_risk_score = churn_risk

    await db.commit()
    return predictions


async def get_twin_for_hia(
    db: AsyncSession,
    client_id: uuid.UUID,
) -> dict[str, Any]:
    twin = await get_or_create_twin(db, client_id)
    await update_predictions(db, client_id)

    result = await db.execute(
        select(ClientTwinPrediction).where(ClientTwinPrediction.twin_id == twin.id)
    )
    predictions = result.scalars().all()

    return {
        "client_id": str(client_id),
        "communication_preferences": twin.communication_preferences,
        "decision_speed": twin.decision_speed,
        "risk_tolerance": twin.risk_tolerance,
        "budget_authority": twin.budget_authority,
        "buying_psychology": twin.buying_psychology,
        "technical_maturity": twin.technical_maturity,
        "support_expectation": twin.support_expectation,
        "preferred_hia_agent": twin.preferred_hia_agent,
        "historical_objections": twin.historical_objections,
        "successful_strategies": twin.successful_strategies,
        "trust_score": twin.trust_score,
        "stakeholder_map": twin.stakeholder_map,
        "churn_risk": twin.churn_risk_score,
        "upsell_opportunity": twin.upsell_opportunity_score,
        "renewal_probability": twin.renewal_probability,
        "internal_politics": twin.internal_politics,
        "predictions": [
            {
                "type": p.model_type,
                "value": p.prediction_value,
                "confidence": p.confidence,
            }
            for p in predictions
        ],
        "hia_briefing": _generate_hia_briefing(twin),
    }


def _generate_hia_briefing(twin: ClientDigitalTwin) -> str:
    risk_level = "HIGH" if twin.churn_risk_score > 0.7 else "MEDIUM" if twin.churn_risk_score > 0.4 else "LOW"
    return (
        f"CLIENT BRIEFING — Trust: {twin.trust_score:.0f}/100 | Churn Risk: {risk_level}\n"
        f"Communication: {twin.decision_speed} decisions, {twin.risk_tolerance} risk tolerance\n"
        f"Approach: {twin.support_expectation} support expected\n"
        f"Key objections: {', '.join(twin.historical_objections[:3]) if twin.historical_objections else 'None recorded'}\n"
        f"Preferred agent: {twin.preferred_hia_agent or 'Not assigned'}"
    )
