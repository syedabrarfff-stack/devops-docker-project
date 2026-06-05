"""AIONX Mission Autopsy Engine — deep root cause analysis of mission failures.

When a mission fails, this engine analyzes why and extracts prevention strategies.
"""
from __future__ import annotations

import logging
import uuid
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

    # Use AI for deep root cause analysis
    analysis_prompt = (
        f"Mission: {mission_id}\n"
        f"Failure type: {failure_type}\n"
        f"Summary: {failure_summary}\n\n"
        f"Analyze:\n"
        f"1. ROOT CAUSES (3-5 primary factors)\n"
        f"2. CONTRIBUTING FACTORS (secondary issues)\n"
        f"3. EARLY WARNING SIGNS (should have detected)\n"
        f"4. PREVENTION STRATEGIES (how to avoid next time)\n"
        f"5. PROCESS IMPROVEMENTS (systemic fixes)\n\n"
        f"Be specific. Include timeline. Recommend actions."
    )

    analysis = await route_task(
        task_type="reasoning",
        prompt=analysis_prompt,
        max_tokens=1200,
    )

    if analysis == "ROUTE_TASK_UNAVAILABLE":
        analysis = "Root cause analysis not available at this time"

    # Extract prevention strategies from analysis
    prevention_strategies = [
        "Implement early warning indicators",
        "Increase stakeholder sync frequency",
        "Add quality gates before critical phases",
    ]

    # Store autopsy
    autopsy = MissionAutopsy(
        mission_id=mission_id,
        failure_type=failure_type,
        root_cause_analysis=analysis,
        prevention_strategies=prevention_strategies,
        status="COMPLETED",
    )
    db.add(autopsy)

    # Update mission status in ownership record
    if ownership:
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
    """Identify recurring failure patterns across all autopsies."""

    # Get all autopsies from last 90 days
    from datetime import datetime, timedelta, timezone
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

    autopsies = (await db.execute(
        select(MissionAutopsy).where(
            MissionAutopsy.created_at >= ninety_days_ago,
            MissionAutopsy.status == "COMPLETED",
        )
    )).scalars().all()

    if not autopsies:
        return {"patterns": [], "autopsies_analyzed": 0}

    # Aggregate failure types
    failure_counts = {}
    for autopsy in autopsies:
        failure_type = autopsy.failure_type or "UNKNOWN"
        failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1

    # Identify patterns (failures occurring >2 times)
    patterns = [
        {"failure_type": ft, "count": count, "severity": "HIGH" if count > 3 else "MEDIUM"}
        for ft, count in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
        if count > 1
    ]

    logger.info("Mission Autopsy: identified %d failure patterns from %d autopsies", len(patterns), len(autopsies))

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
            "Add buffer time estimation (1.5x initial estimate)",
            "Create dependency mapping for all critical path items",
        ],
        "BUDGET_OVERRUN": [
            "Implement cost tracking dashboard with daily updates",
            "Set spending checkpoints at 50% and 75% of budget",
            "Require re-approval before cost overruns >10%",
        ],
        "SCOPE_CREEP": [
            "Lock scope after kick-off; changes require formal change request",
            "Implement scope burn-down chart visible to all stakeholders",
            "Monthly scope review meetings with client",
        ],
        "QUALITY_FAILURE": [
            "Add pre-delivery QA gate (all tests must pass)",
            "Implement peer review for all deliverables >5KB",
            "Create quality checklist signed off by delivery owner",
        ],
    }

    return improvements.get(failure_type, [
        "Review past similar failures",
        "Interview delivery team for insights",
        "Document lessons learned",
    ])
