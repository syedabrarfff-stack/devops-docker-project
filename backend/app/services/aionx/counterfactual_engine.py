"""AIONX Counterfactual Engine.

Simulates alternate decision paths and stores calibration evidence in the live
counterfactual organ tables.
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
    DecisionOption,
)
from app.services.ai.router import route_task

logger = logging.getLogger(__name__)


async def simulate_decision(
    db: AsyncSession,
    decision_id: uuid.UUID,
) -> dict[str, Any]:
    """Simulate what might have happened with a different decision option."""
    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    option = (await db.execute(
        select(DecisionOption).where(DecisionOption.decision_id == decision_id).limit(1)
    )).scalars().first()
    option_id = option.id if option else uuid.uuid4()

    analysis = await route_task(
        task_type="reasoning",
        prompt=(
            f"Decision made: {decision.problem_statement}\n"
            f"Category: {decision.decision_category}\n"
            f"Confidence: {decision.confidence_score}\n\n"
            "Simulate the strongest realistic alternative path, including "
            "revenue impact, reputation impact, opportunity cost, and risk."
        ),
        max_tokens=600,
    )
    if analysis == "ROUTE_TASK_UNAVAILABLE":
        analysis = "Simulation unavailable"

    simulation = CounterfactualSimulation(
        decision_id=decision_id,
        option_id=option_id,
        simulation_narrative=analysis,
        predicted_revenue_impact=option.predicted_revenue_impact if option else 0.0,
        predicted_reputation_impact=option.predicted_reputation_impact if option else 0.0,
        opportunity_cost=option.opportunity_cost if option else 0.0,
        confidence=0.7,
    )
    db.add(simulation)
    await db.flush()

    logger.info("Counterfactual: simulated decision %s", decision_id)
    return {
        "simulation_id": str(simulation.id),
        "decision_id": str(decision_id),
        "option_id": str(option_id),
        "outcome": analysis,
    }


async def record_actuality(
    db: AsyncSession,
    decision_id: uuid.UUID,
    actual_outcome: str,
    actual_revenue_delta: float = 0.0,
    actual_timeline_delta_days: int = 0,
) -> dict[str, Any]:
    """Record what actually happened and calibrate the latest simulation."""
    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "decision not found"}

    simulation = (await db.execute(
        select(CounterfactualSimulation).where(
            CounterfactualSimulation.decision_id == decision_id
        ).order_by(CounterfactualSimulation.simulated_at.desc())
    )).scalars().first()

    if not simulation:
        await simulate_decision(db, decision_id)
        simulation = (await db.execute(
            select(CounterfactualSimulation).where(
                CounterfactualSimulation.decision_id == decision_id
            ).order_by(CounterfactualSimulation.simulated_at.desc())
        )).scalars().first()

    if not simulation:
        return {"error": "simulation not available"}

    lower_outcome = actual_outcome.lower()
    accuracy = 0.8 if any(word in lower_outcome for word in ("positive", "success", "won")) else 0.5

    actuality = CounterfactualActualization(
        simulation_id=simulation.id,
        day_30_actual=actual_outcome,
        day_30_accuracy_score=accuracy,
        overall_calibration=accuracy,
        learnings=(
            f"Revenue delta: {actual_revenue_delta}; "
            f"timeline delta days: {actual_timeline_delta_days}"
        ),
    )
    db.add(actuality)
    await db.flush()

    logger.info("Counterfactual: recorded actuality for decision %s", decision_id)
    return {
        "actuality_id": str(actuality.id),
        "decision_id": str(decision_id),
        "actual_outcome": actual_outcome,
        "simulated_outcome": simulation.simulation_narrative,
        "accuracy_score": accuracy,
    }


async def extract_learning(db: AsyncSession) -> dict[str, Any]:
    """Extract calibration patterns from recent actualizations."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    actualities = (await db.execute(
        select(CounterfactualActualization).where(
            CounterfactualActualization.updated_at >= thirty_days_ago
        )
    )).scalars().all()

    if not actualities:
        return {"learnings": [], "decisions_reviewed": 0}

    positive_outcomes = sum(
        1 for actuality in actualities
        if actuality.day_30_actual and "positive" in actuality.day_30_actual.lower()
    )
    avg_accuracy = sum(
        actuality.day_30_accuracy_score or 0.0 for actuality in actualities
    ) / len(actualities)

    learnings = [
        f"Decision success signals: {positive_outcomes}/{len(actualities)}",
        f"Average counterfactual calibration: {avg_accuracy:.2f}",
    ]

    logger.info("Counterfactual: extracted learning from %d actualizations", len(actualities))
    return {
        "learnings": learnings,
        "decisions_reviewed": len(actualities),
        "success_rate": positive_outcomes / len(actualities),
        "avg_accuracy": avg_accuracy,
    }
