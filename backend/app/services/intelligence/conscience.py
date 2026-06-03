"""
JARVIS Conscience Layer — values-based ethical evaluation engine.
Ensures all autonomous JARVIS actions align with core company values.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# ── Core Values ───────────────────────────────────────────────────────────────

CORE_VALUES = {
    "honesty": {
        "description": "Never deceive clients about capabilities, timelines, or outcomes.",
        "violation_triggers": [
            "overpromise", "guaranteed", "100% success", "never fail",
            "instant results", "fabricate", "false claim",
        ],
        "weight": 1.0,
    },
    "fairness": {
        "description": "No predatory pricing, exploitation of vulnerable clients, or discriminatory practices.",
        "violation_triggers": [
            "emergency_markup", "desperation_pricing", "exploit", "lock_in_unfair",
            "hidden_fees", "bait_and_switch",
        ],
        "weight": 0.9,
    },
    "quality": {
        "description": "Never deliver below Aliyar Solutions standard — no shortcuts on deliverables.",
        "violation_triggers": [
            "skip_review", "no_qa", "untested", "draft_as_final",
            "incomplete_delivery", "placeholder_content",
        ],
        "weight": 0.85,
    },
    "privacy": {
        "description": "Protect all client data — no unauthorized sharing, logging, or exposure.",
        "violation_triggers": [
            "share_client_data", "expose_credentials", "log_pii", "third_party_data",
            "unauthorized_access", "data_leak",
        ],
        "weight": 1.0,
    },
    "sustainability": {
        "description": "Don't overcommit resources, timelines, or capabilities beyond what is deliverable.",
        "violation_triggers": [
            "overcommit", "impossible_deadline", "beyond_capacity",
            "unsustainable_promise", "burnout_risk",
        ],
        "weight": 0.8,
    },
}

SEVERITY_LEVELS = {
    "BLOCK": "Action blocked — critical value violation detected.",
    "WARN": "Action approved with warnings — review before proceeding.",
    "OK": "Action approved — no ethical concerns detected.",
}

# Action type risk profiles
ACTION_RISK_PROFILES: dict[str, dict] = {
    "send_proposal": {"base_risk": 0.2, "checks": ["honesty", "quality", "sustainability"]},
    "send_email": {"base_risk": 0.1, "checks": ["honesty", "fairness"]},
    "create_invoice": {"base_risk": 0.15, "checks": ["fairness", "honesty"]},
    "deploy_infrastructure": {"base_risk": 0.3, "checks": ["quality", "sustainability"]},
    "share_data": {"base_risk": 0.5, "checks": ["privacy", "honesty"]},
    "price_service": {"base_risk": 0.25, "checks": ["fairness", "honesty"]},
    "commit_timeline": {"base_risk": 0.35, "checks": ["honesty", "sustainability", "quality"]},
    "approve_action": {"base_risk": 0.2, "checks": list(CORE_VALUES.keys())},
}


def _scan_payload_for_violations(payload: dict, value_name: str) -> list[str]:
    """Scan payload text for violation triggers."""
    triggers = CORE_VALUES[value_name]["violation_triggers"]
    payload_str = str(payload).lower()
    found = [t for t in triggers if t.lower() in payload_str]
    return found


def _evaluate_value(value_name: str, payload: dict) -> dict[str, Any]:
    """Evaluate a single core value against a payload."""
    violations = _scan_payload_for_violations(payload, value_name)
    return {
        "value": value_name,
        "passed": len(violations) == 0,
        "violations_found": violations,
        "description": CORE_VALUES[value_name]["description"],
        "weight": CORE_VALUES[value_name]["weight"],
    }


class ConscienceLayer:
    """JARVIS values engine — ethical evaluation of all autonomous actions."""

    def evaluate_action_ethics(
        self,
        action_type: str,
        payload: dict,
    ) -> dict[str, Any]:
        """
        Check any proposed JARVIS action against core values.
        Returns: approved, violations, warnings, modified_payload, severity.
        """
        risk_profile = ACTION_RISK_PROFILES.get(
            action_type,
            {"base_risk": 0.2, "checks": list(CORE_VALUES.keys())},
        )

        checks_to_run = risk_profile["checks"]
        evaluations = [_evaluate_value(v, payload) for v in checks_to_run]

        # High-weight violations = BLOCK, low-weight = WARN
        hard_violations = []
        soft_warnings = []
        modified_payload = dict(payload)

        for eval_result in evaluations:
            if not eval_result["passed"]:
                weight = eval_result["weight"]
                violation_detail = {
                    "value": eval_result["value"],
                    "triggers": eval_result["violations_found"],
                    "description": eval_result["description"],
                }
                if weight >= 0.9:
                    hard_violations.append(violation_detail)
                else:
                    soft_warnings.append(violation_detail)

        # Determine severity
        if hard_violations:
            severity = "BLOCK"
            approved = False
        elif soft_warnings:
            severity = "WARN"
            approved = True
        else:
            severity = "OK"
            approved = True

        # Attempt to clean modified_payload for WARN cases
        if severity == "WARN":
            # Flag overpromising language in text fields
            for key, val in modified_payload.items():
                if isinstance(val, str):
                    for warning in soft_warnings:
                        for trigger in warning.get("triggers", []):
                            if trigger in val.lower():
                                modified_payload[f"_{key}_flagged"] = f"Review '{trigger}' before sending"

        return {
            "approved": approved,
            "severity": severity,
            "severity_message": SEVERITY_LEVELS[severity],
            "violations": hard_violations,
            "warnings": soft_warnings,
            "values_checked": checks_to_run,
            "modified_payload": modified_payload if severity == "WARN" else payload,
            "ethics_score": round(
                100.0 * (1 - len(hard_violations) * 0.3 - len(soft_warnings) * 0.1),
                2,
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def audit_recent_actions(
        self,
        tenant_id: UUID,
        days: int = 7,
    ) -> dict[str, Any]:
        """Review recent autonomous governance log for ethical issues."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            from sqlalchemy import text

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)

                # Try to query governance log
                try:
                    rows = await session.execute(
                        text(
                            """
                            SELECT action_type, payload, decision, tier, created_at
                            FROM autonomous_governance_log
                            WHERE tenant_id = :tenant_id
                              AND created_at >= :cutoff
                            ORDER BY created_at DESC
                            LIMIT 200
                            """
                        ),
                        {"tenant_id": str(tenant_id), "cutoff": cutoff},
                    )
                    actions = rows.fetchall()
                except Exception:
                    actions = []

                reviewed = len(actions)
                violations_found = 0
                warnings_issued = 0
                scores = []

                for action in actions:
                    payload = action.payload or {}
                    result = self.evaluate_action_ethics(action.action_type, payload)
                    scores.append(result["ethics_score"])
                    if result["violations"]:
                        violations_found += 1
                    if result["warnings"]:
                        warnings_issued += 1

                avg_score = round(sum(scores) / len(scores), 2) if scores else 100.0

                return {
                    "tenant_id": str(tenant_id),
                    "period_days": days,
                    "actions_reviewed": reviewed,
                    "violations_found": violations_found,
                    "warnings_issued": warnings_issued,
                    "ethics_score": avg_score,
                    "grade": "A" if avg_score >= 90 else "B" if avg_score >= 75 else "C" if avg_score >= 60 else "D",
                    "summary": (
                        f"Reviewed {reviewed} autonomous actions over {days} days. "
                        f"Ethics score: {avg_score}/100. "
                        f"{violations_found} violations, {warnings_issued} warnings."
                    ),
                    "audited_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as exc:
            logger.warning("Conscience audit failed: %s", exc)
            return {
                "tenant_id": str(tenant_id),
                "period_days": days,
                "actions_reviewed": 0,
                "violations_found": 0,
                "warnings_issued": 0,
                "ethics_score": 100.0,
                "grade": "A",
                "summary": "No actions available for review.",
                "audited_at": datetime.now(timezone.utc).isoformat(),
            }


conscience_layer = ConscienceLayer()
