"""AIONX Mission Autopsy Engine.

Analyzes failed missions and converts failures into durable doctrine using the
canonical mission autopsy schema.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import MissionAutopsy, MissionOwnershipRecord
from app.services.ai.router import route_task

logger = logging.getLogger(__name__)


async def analyze_mission_failure(
    db: AsyncSession,
    mission_id: uuid.UUID,
    failure_type: str = "UNKNOWN",
    failure_summary: str = "",
) -> dict[str, Any]:
    """Deep AI-powered root cause analysis of mission failure."""
    ownership = (await db.execute(
        select(MissionOwnershipRecord).where(MissionOwnershipRecord.mission_id == mission_id)
    )).scalars().first()

    if not ownership:
        return {"error": "mission not found"}

    analysis = await route_task(
        task_type="reasoning",
        prompt=(
            f"Mission: {mission_id}\n"
            f"Failure type: {failure_type}\n"
            f"Summary: {failure_summary}\n\n"
            "Analyze root causes, contributing factors, early warning signs, "
            "prevention strategies, and systemic process improvements."
        ),
        max_tokens=1200,
    )
    if analysis == "ROUTE_TASK_UNAVAILABLE":
        analysis = "Root cause analysis not available at this time"

    prevention_strategies = [
        "Implement early warning indicators",
        "Increase stakeholder sync frequency",
        "Add quality gates before critical phases",
    ]

    autopsy = MissionAutopsy(
        mission_id=mission_id,
        client_id=ownership.client_id,
        failure_type=failure_type,
        failure_summary=failure_summary or "Mission failure detected",
        causal_chain=[
            {"step": "failure_detected", "summary": failure_summary or failure_type},
            {"step": "analysis", "summary": analysis},
        ],
        what_failed=failure_summary or failure_type,
        why_it_failed=analysis,
        who_detected="MissionAutopsyEngine",
        alternative_path_that_would_succeed="Run earlier convergence review and enforce quality gates.",
        institutional_doctrine="Every failed mission must generate doctrine and prevention controls.",
    )
    db.add(autopsy)

    ownership.mission_status = "FAILED"
    ownership.mission_outcome = failure_type
    ownership.root_causes = prevention_strategies

    await db.flush()
    logger.info("Mission Autopsy: analyzed failure for mission %s", mission_id)
    return {
        "autopsy_id": str(autopsy.id),
        "mission_id": str(mission_id),
        "analysis": analysis,
        "prevention_strategies": prevention_strategies,
    }


async def extract_failure_patterns(db: AsyncSession) -> dict[str, Any]:
    """Identify recurring failure patterns across recent autopsies."""
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

    autopsies = (await db.execute(
        select(MissionAutopsy).where(MissionAutopsy.created_at >= ninety_days_ago)
    )).scalars().all()

    if not autopsies:
        return {"patterns": [], "autopsies_analyzed": 0}

    failure_counts: dict[str, int] = {}
    for autopsy in autopsies:
        failure_type = autopsy.failure_type or "UNKNOWN"
        failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1

    patterns = [
        {"failure_type": failure_type, "count": count, "severity": "HIGH" if count > 3 else "MEDIUM"}
        for failure_type, count in sorted(failure_counts.items(), key=lambda item: item[1], reverse=True)
        if count > 1
    ]

    logger.info("Mission Autopsy: identified %d patterns from %d autopsies", len(patterns), len(autopsies))
    return {
        "patterns": patterns,
        "autopsies_analyzed": len(autopsies),
        "top_failure_type": patterns[0]["failure_type"] if patterns else None,
    }


async def recommend_process_improvement(db: AsyncSession, failure_type: str) -> list[str]:
    """Recommend systemic process improvements for a specific failure type."""
    improvements = {
        "SCHEDULE_OVERRUN": [
            "Implement weekly milestone reviews instead of biweekly",
            "Add buffer time estimation at 1.5x initial estimate",
            "Create dependency mapping for all critical path items",
        ],
        "BUDGET_OVERRUN": [
            "Implement cost tracking dashboard with daily updates",
            "Set spending checkpoints at 50% and 75% of budget",
            "Require re-approval before cost overruns above 10%",
        ],
        "SCOPE_CREEP": [
            "Lock scope after kick-off; changes require formal change request",
            "Implement scope burn-down chart visible to all stakeholders",
            "Run monthly scope review meetings with client",
        ],
        "QUALITY_FAILURE": [
            "Add pre-delivery QA gate with all checks passing",
            "Implement peer review for major deliverables",
            "Create quality checklist signed off by delivery owner",
        ],
    }
    return improvements.get(failure_type, [
        "Review past similar failures",
        "Interview delivery team for insights",
        "Document lessons learned",
    ])
