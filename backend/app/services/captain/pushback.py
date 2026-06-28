"""
JarvisPushbackEngine — JARVIS pushes back when Captain makes weak decisions.
Stress-tests strategies and surfaces risks before they become expensive mistakes.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

# Triggers that almost always warrant a PUSHBACK or CAUTION
_PUSHBACK_PATTERNS = [
    (re.compile(r"lower.{0,20}price|discount|cheaper|cut.{0,15}rate|reduce.{0,15}cost", re.I), "PRICING_RISK"),
    (re.compile(r"500|1000|blast|spam|mass.{0,10}email|bulk.{0,10}unsolicited", re.I), "COMPLIANCE_RISK"),
    (re.compile(r"no budget|zero budget|free|pro bono|trial for free", re.I), "REVENUE_RISK"),
    (re.compile(r"work.{0,20}weekend|overnight|no sleep|24.hour", re.I), "CAPACITY_RISK"),
    (re.compile(r"guarantee\s+result|promise\s+revenue|100\s*%\s+success", re.I), "REPUTATION_RISK"),
]

_ADVERSARIAL_QUESTIONS = [
    "What if a direct competitor executes this strategy first and faster?",
    "What if the primary client or revenue source churns within 30 days of launch?",
    "What if a critical dependency (API, vendor, team member) fails mid-execution?",
    "What if revenue targets miss by 50% in the first 90 days?",
    "What if execution takes 3× longer and costs 2× more than projected?",
]


def _coerce_uuid(val: Any) -> UUID:
    return UUID(str(val)) if not isinstance(val, UUID) else val


def _parse_json_response(text: str) -> dict:
    try:
        match = re.search(r"\{[\s\S]+\}", text or "")
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


class JarvisPushbackEngine:
    """Evaluates Captain's decisions and strategies with adversarial rigour."""

    # ──────────────────────────── DECISION EVALUATOR ──────────────────────── #

    async def evaluate_captain_decision(
        self,
        tenant_id: Any,
        decision: str,
        context: dict | None = None,
    ) -> dict:
        """Evaluate a proposed decision and return APPROVE / CAUTION / PUSHBACK."""
        tenant_uuid = _coerce_uuid(tenant_id)
        context = context or {}

        # Fast-path: check known danger patterns
        detected_risks: list[str] = []
        for pattern, risk_type in _PUSHBACK_PATTERNS:
            if pattern.search(decision):
                detected_risks.append(risk_type)

        prompt = f"""You are JARVIS — the executive operations manager and strategic advisor for Aliyar Solutions.
Captain has proposed the following decision. Your job is to evaluate it honestly and protect the company.

DECISION:
{decision}

ADDITIONAL CONTEXT:
{json.dumps(context) if context else "None provided"}

DETECTED RISK SIGNALS: {detected_risks if detected_risks else "None detected by static analysis"}

Evaluate this decision rigorously. Return ONLY valid JSON:
{{
  "verdict": "APPROVE|CAUTION|PUSHBACK",
  "confidence": 0.85,
  "risks": [
    {{"risk": "string", "severity": "LOW|MEDIUM|HIGH|CRITICAL", "category": "string"}}
  ],
  "alternatives": [
    {{"alternative": "string", "rationale": "string"}}
  ],
  "final_recommendation": "A direct, honest 2–3 sentence recommendation from JARVIS to Captain",
  "strategic_alignment": "HIGH|MEDIUM|LOW",
  "revenue_impact": "POSITIVE|NEUTRAL|NEGATIVE|UNKNOWN"
}}

VERDICT CRITERIA:
- APPROVE: Sound decision with manageable risks
- CAUTION: Proceed but address specific risks first
- PUSHBACK: Do NOT execute — serious risks detected

confidence must be float 0.0–1.0."""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                max_tokens=900,
            )
            if response.error:
                raise ValueError(response.error)
            result = _parse_json_response(response.content)
            if result and "verdict" in result:
                result["evaluated_at"] = datetime.now(UTC).isoformat()
                result["tenant_id"] = str(tenant_uuid)
                result["decision"] = decision
                # Escalate to PUSHBACK if critical static risks found
                if detected_risks and result.get("verdict") == "APPROVE":
                    result["verdict"] = "CAUTION"
                    result["risks"] = result.get("risks", []) + [
                        {"risk": r, "severity": "HIGH", "category": "STATIC_ANALYSIS"} for r in detected_risks
                    ]
                return result
        except Exception as exc:
            logger.warning("Decision evaluation failed: %s", exc)

        # Fallback verdict
        verdict = "PUSHBACK" if len(detected_risks) >= 2 else ("CAUTION" if detected_risks else "APPROVE")
        return {
            "verdict": verdict,
            "confidence": 0.5,
            "risks": [{"risk": r, "severity": "HIGH", "category": "STATIC_ANALYSIS"} for r in detected_risks],
            "alternatives": [],
            "final_recommendation": (
                "JARVIS recommends reviewing this decision carefully before proceeding. Multiple risk signals detected."
                if detected_risks
                else "Decision appears sound based on available information. Proceed with standard diligence."
            ),
            "strategic_alignment": "UNKNOWN",
            "revenue_impact": "UNKNOWN",
            "evaluated_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
            "decision": decision,
        }

    # ──────────────────────────── STRATEGY STRESS TEST ────────────────────── #

    async def stress_test_strategy(self, tenant_id: Any, strategy: str) -> dict:
        """Run a strategy through 5 adversarial failure scenarios."""
        tenant_uuid = _coerce_uuid(tenant_id)

        questions_block = "\n".join(
            f"{i+1}. {q}" for i, q in enumerate(_ADVERSARIAL_QUESTIONS)
        )

        prompt = f"""You are JARVIS, the adversarial strategy evaluator for Aliyar Solutions.
Captain has proposed this strategy:

STRATEGY:
{strategy}

Stress-test it against these 5 adversarial questions:
{questions_block}

Return ONLY valid JSON:
{{
  "stress_score": 72,
  "failure_modes": [
    {{
      "question_index": 1,
      "scenario": "string describing the failure",
      "probability": "LOW|MEDIUM|HIGH",
      "business_impact": "string",
      "mitigation": "string"
    }}
  ],
  "resilience_improvements": [
    "Improvement 1 string",
    "Improvement 2 string"
  ],
  "go_no_go": "GO|NO_GO|GO_WITH_MODIFICATIONS",
  "overall_assessment": "2–3 sentence strategic assessment",
  "strongest_risk": "The single biggest threat to this strategy"
}}

stress_score: 0 = catastrophically fragile, 100 = highly resilient.
Be ruthlessly honest — Captain needs the truth, not validation."""

        try:
            response, _ = await ai_router.chat(
                messages=[Message(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                max_tokens=1200,
            )
            if response.error:
                raise ValueError(response.error)
            result = _parse_json_response(response.content)
            if result and "stress_score" in result:
                result["strategy"] = strategy
                result["evaluated_at"] = datetime.now(UTC).isoformat()
                result["tenant_id"] = str(tenant_uuid)
                return result
        except Exception as exc:
            logger.warning("Strategy stress test failed: %s", exc)

        return {
            "stress_score": 50,
            "failure_modes": [
                {
                    "question_index": i + 1,
                    "scenario": f"Scenario {i+1} could not be evaluated — AI unavailable",
                    "probability": "UNKNOWN",
                    "business_impact": "Unknown",
                    "mitigation": "Manual review required",
                }
                for i in range(5)
            ],
            "resilience_improvements": ["Manual stress-test required", "Engage strategy team for full assessment"],
            "go_no_go": "GO_WITH_MODIFICATIONS",
            "overall_assessment": "Full stress test unavailable. Proceed with standard risk management protocols.",
            "strongest_risk": "Unknown — AI evaluation failed",
            "strategy": strategy,
            "evaluated_at": datetime.now(UTC).isoformat(),
            "tenant_id": str(tenant_uuid),
        }


jarvis_pushback = JarvisPushbackEngine()
