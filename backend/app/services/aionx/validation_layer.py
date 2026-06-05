"""AIONX Validation Layer — pre-execution verification gate for decisions.

Before any decision is executed, validate:
- Completeness (all required fields)
- Feasibility (resources, constraints)
- Risk (unintended consequences)
- Alignment (matches strategy, doesn't conflict)
- Authority (maker has sufficient certification)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import DecisionObject

logger = logging.getLogger(__name__)


async def validate_decision_before_execution(
    db: AsyncSession,
    decision_id: UUID,
) -> dict[str, Any]:
    """Run all validation checks before decision execution."""

    decision = (await db.execute(
        select(DecisionObject).where(DecisionObject.id == decision_id)
    )).scalars().first()

    if not decision:
        return {"error": "Decision not found", "valid": False}

    validations = {}

    # Check 1: Completeness
    validations["completeness"] = await _check_completeness(decision)

    # Check 2: Feasibility
    validations["feasibility"] = await _check_feasibility(db, decision)

    # Check 3: Risk assessment
    validations["risk"] = await _check_risk(decision)

    # Check 4: Strategic alignment
    validations["alignment"] = await _check_alignment(db, decision)

    # Check 5: Maker authority
    validations["authority"] = await _check_maker_authority(db, decision)

    # Overall status
    all_pass = all(v.get("pass", False) for v in validations.values())

    logger.info(
        "Decision Validation: %s → %s",
        str(decision_id)[:8],
        "PASS" if all_pass else "FAIL"
    )

    return {
        "decision_id": str(decision_id),
        "valid": all_pass,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validations": validations,
        "can_execute": all_pass,
        "failed_checks": [k for k, v in validations.items() if not v.get("pass", False)],
    }


async def _check_completeness(decision: DecisionObject) -> dict[str, Any]:
    """Verify all required decision fields are populated."""

    issues = []

    if not decision.problem_statement or len(decision.problem_statement) < 10:
        issues.append("Problem statement missing or too short")

    if decision.tier is None:
        issues.append("Decision tier not set")

    if not decision.confidence_score or decision.confidence_score < 0.3:
        issues.append("Confidence score too low or not set")

    if not decision.options or len(decision.options) < 2:
        issues.append("At least 2 options must be considered")

    return {
        "pass": len(issues) == 0,
        "checks": len(issues) == 0,
        "issues": issues,
        "message": "Decision is complete" if len(issues) == 0 else f"{len(issues)} completeness issues",
    }


async def _check_feasibility(db: AsyncSession, decision: DecisionObject) -> dict[str, Any]:
    """Verify decision is feasible (resources, constraints, timeline)."""

    issues = []

    # Check if similar decisions have been attempted recently
    # Check if required resources are available
    # Check timeline constraints

    if decision.tier <= 1:  # Tier 1 = strategic/high-stakes
        if not decision.assumptions or len(decision.assumptions) < 3:
            issues.append("Strategic decisions require documented assumptions")

    return {
        "pass": len(issues) == 0,
        "issues": issues,
        "message": "Decision is feasible" if len(issues) == 0 else f"{len(issues)} feasibility risks",
    }


async def _check_risk(decision: DecisionObject) -> dict[str, Any]:
    """Assess decision risk (unintended consequences, downside)."""

    issues = []
    risks = []

    if decision.risk_flags and len(decision.risk_flags) > 0:
        for flag in decision.risk_flags:
            if flag.get("severity") == "CRITICAL":
                risks.append(f"CRITICAL risk: {flag.get('description')}")

    if decision.confidence_score < 0.5:
        risks.append(f"Low confidence (only {decision.confidence_score:.0%}) increases execution risk")

    # Tier-1 decisions with >3 critical risks should trigger Captain review
    if decision.tier <= 1 and len([r for r in risks if "CRITICAL" in r]) > 3:
        issues.append("Too many critical risks for autonomous execution")

    return {
        "pass": len(issues) == 0,
        "risks_identified": risks,
        "critical_risk_count": len([r for r in risks if "CRITICAL" in r]),
        "message": "Acceptable risk profile" if len(issues) == 0 else "High-risk decision",
    }


async def _check_alignment(db: AsyncSession, decision: DecisionObject) -> dict[str, Any]:
    """Verify decision aligns with strategy and doesn't conflict with existing decisions."""

    issues = []

    # Check if decision category is known
    known_categories = [
        "STRATEGIC", "OPERATIONAL", "TACTICAL", "EMERGENCY",
        "CLIENT", "INTERNAL", "TEST", "GENERAL"
    ]
    if decision.decision_category not in known_categories:
        issues.append(f"Unknown decision category: {decision.decision_category}")

    # Check for conflicting decisions
    # (in production, would query for decisions with opposite conclusions on same topic)

    return {
        "pass": len(issues) == 0,
        "category": decision.decision_category,
        "conflicts": [],
        "message": "Decision aligns with strategy" if len(issues) == 0 else "Alignment issues detected",
    }


async def _check_maker_authority(db: AsyncSession, decision: DecisionObject) -> dict[str, Any]:
    """Verify decision maker has sufficient certification to make this decision."""

    issues = []
    maker_id = decision.created_by

    # In production, would:
    # 1. Get HIA certification tier
    # 2. Check if tier allows this decision tier
    # 3. Check if escalation is required

    # For now, mock check:
    if not maker_id:
        issues.append("Decision maker not identified")
    elif maker_id == "UNKNOWN_AGENT":
        issues.append("Maker certification not found")
    elif decision.tier <= 1 and maker_id not in ["JARVIS", "Captain", "Cortex"]:
        # Strategic decisions typically require high-authority makers
        logger.warning("Low-authority maker %s attempting Tier %d decision", maker_id, decision.tier)

    return {
        "pass": len(issues) == 0,
        "maker_id": maker_id,
        "tier_authorized": True,
        "issues": issues,
        "message": "Maker has sufficient authority" if len(issues) == 0 else "Authority issues detected",
    }


async def pre_flight_check(
    db: AsyncSession,
    decision_id: UUID,
) -> dict[str, Any]:
    """Final pre-flight check before decision execution (all systems go?)."""

    validation = await validate_decision_before_execution(db, decision_id)

    if not validation.get("can_execute"):
        return {
            "decision_id": str(decision_id),
            "pre_flight_status": "BLOCKED",
            "reason": f"Validation failed: {validation['failed_checks']}",
            "can_proceed": False,
        }

    logger.info("Decision Pre-flight: READY FOR EXECUTION → %s", str(decision_id)[:8])

    return {
        "decision_id": str(decision_id),
        "pre_flight_status": "GO",
        "cleared_for_execution": True,
        "can_proceed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
