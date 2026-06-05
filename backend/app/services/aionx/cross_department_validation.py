"""AIONX cross-department validation gates.

These gates prevent one department's optimistic claim from reaching clients
without engineering, operations, sales, and fit checks.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.aionx.operational_persistence import record_event


VALIDATION_GATES: list[dict[str, Any]] = [
    {
        "code": "DELIVERY_READINESS",
        "name": "Delivery Readiness",
        "owners": ["Engineering", "Operations", "QA", "HIA"],
        "blocks_on": ["missing_success_criteria", "open_critical_risk", "qa_failed"],
    },
    {
        "code": "SALES_ACCURACY",
        "name": "Sales Accuracy",
        "owners": ["Sales", "Engineering", "Finance"],
        "blocks_on": ["unsupported_claim", "capacity_mismatch", "pricing_risk"],
    },
    {
        "code": "CLIENT_FIT",
        "name": "Client Fit",
        "owners": ["Market", "Client Success", "Council"],
        "blocks_on": ["bad_culture_fit", "unsupported_need", "trust_risk"],
    },
    {
        "code": "STAGE_TRANSITION",
        "name": "Major Stage Transition",
        "owners": ["Mission Control", "Council", "JARVIS"],
        "blocks_on": ["captain_gate_missing", "dependency_unresolved", "validation_failed"],
    },
]


async def validation_status(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(text("SELECT COUNT(*) FROM aionx_cross_validation_records"))
    count = int(result.scalar_one())
    recent = await db.execute(
        text(
            """
            SELECT validation_type, subject_id, severity, verdict, created_at
            FROM aionx_cross_validation_records
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
    )
    return {
        "status": "cross_department_validation_live",
        "gate_count": len(VALIDATION_GATES),
        "gates": VALIDATION_GATES,
        "records": count,
        "recent": [dict(row._mapping) for row in recent.fetchall()],
        "governance": "Blockers prevent stage advancement; warnings create Captain/Council visibility.",
    }


async def validate_delivery_readiness(db: AsyncSession, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("success_criteria", bool(payload.get("success_criteria")), "Success criteria must be explicit."),
        _check("qa_status", payload.get("qa_status", "PENDING") in {"PASS", "CONDITIONAL_PASS"}, "QA must pass or conditionally pass."),
        _check("critical_risks", not payload.get("critical_risks"), "Critical risks must be resolved before delivery."),
    ]
    return await _record_validation(db, "DELIVERY_READINESS", mission_id, checks, payload)


async def validate_sales_accuracy(db: AsyncSession, proposal_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("claim_evidence", bool(payload.get("claim_evidence")), "Sales claims require evidence."),
        _check("engineering_capacity", payload.get("engineering_capacity", "UNKNOWN") != "INSUFFICIENT", "Engineering capacity is insufficient."),
        _check("pricing_margin", float(payload.get("gross_margin_pct", 40)) >= 25, "Gross margin below 25%."),
    ]
    return await _record_validation(db, "SALES_ACCURACY", proposal_id, checks, payload)


async def validate_client_fit(db: AsyncSession, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("capability_match", float(payload.get("capability_match", 0.75)) >= 0.6, "Capability match below 60%."),
        _check("culture_fit", float(payload.get("culture_fit", 0.75)) >= 0.5, "Culture fit below 50%."),
        _check("trust_risk", float(payload.get("trust_risk", 0.2)) < 0.7, "Trust risk is too high."),
    ]
    return await _record_validation(db, "CLIENT_FIT", client_id, checks, payload)


async def validate_stage_transition(db: AsyncSession, subject_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    target_stage = int(payload.get("target_stage", 1))
    checks = [
        _check("target_stage", 1 <= target_stage <= 33, "Target stage must be within 1-33."),
        _check("dependencies", not payload.get("unresolved_dependencies"), "Unresolved dependencies exist."),
        _check("captain_gate", not (target_stage in {25, 30, 33} and not payload.get("captain_approved")), "Captain approval required for this stage."),
    ]
    return await _record_validation(db, "STAGE_TRANSITION", subject_id, checks, payload)


async def _record_validation(
    db: AsyncSession,
    validation_type: str,
    subject_id: str,
    checks: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    blockers = [check for check in checks if not check["pass"] and check["severity"] == "BLOCK"]
    warnings = [check for check in checks if not check["pass"] and check["severity"] == "WARN"]
    verdict = "BLOCK" if blockers else "WARN" if warnings else "PASS"
    severity = "CRITICAL" if blockers else "WARNING" if warnings else "INFO"
    recommendations = [
        check["message"] for check in checks if not check["pass"]
    ] or ["Validation passed. Continue through governed workflow."]
    result = await db.execute(
        text(
            """
            INSERT INTO aionx_cross_validation_records (
                validation_type, subject_id, severity, verdict, checks,
                blockers, recommendations, payload
            )
            VALUES (
                :validation_type, :subject_id, :severity, :verdict,
                CAST(:checks AS jsonb), CAST(:blockers AS jsonb),
                CAST(:recommendations AS jsonb), CAST(:payload AS jsonb)
            )
            RETURNING id
            """
        ),
        {
            "validation_type": validation_type,
            "subject_id": subject_id,
            "severity": severity,
            "verdict": verdict,
            "checks": json.dumps(checks, default=str),
            "blockers": json.dumps(blockers, default=str),
            "recommendations": json.dumps(recommendations, default=str),
            "payload": json.dumps(payload, default=str),
        },
    )
    validation_id = str(result.scalar_one())
    response = {
        "validation_id": validation_id,
        "validation_type": validation_type,
        "subject_id": subject_id,
        "verdict": verdict,
        "severity": severity,
        "checks": checks,
        "blockers": blockers,
        "recommendations": recommendations,
        "can_proceed": verdict != "BLOCK",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await record_event(
        db,
        f"CROSS_VALIDATION_{verdict}",
        "CROSS_DEPARTMENT_VALIDATION",
        response,
        severity=severity,
        captain_approval_required=verdict == "BLOCK",
    )
    await db.commit()
    return response


def _check(name: str, passed: bool, message: str, severity: str = "BLOCK") -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "message": message, "severity": severity}
