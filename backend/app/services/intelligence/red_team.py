"""
JARVIS Red Team Engine — adversarial stress-testing of business strategy.
Simulates hostile competitor analysis and identifies strategic vulnerabilities.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

logger = logging.getLogger(__name__)

ATTACK_VECTORS = [
    {
        "id": "pricing_vulnerability",
        "name": "Pricing Vulnerability",
        "description": "Can a competitor undercut our pricing and capture our market?",
    },
    {
        "id": "service_gap_exploitation",
        "name": "Service Gap Exploitation",
        "description": "What service gaps could competitors fill to differentiate against us?",
    },
    {
        "id": "competitor_replication",
        "name": "Competitor Replication",
        "description": "How easily can a well-funded competitor replicate our entire offering?",
    },
    {
        "id": "client_concentration_risk",
        "name": "Client Concentration Risk",
        "description": "What happens if our top 3 clients leave simultaneously?",
    },
    {
        "id": "single_point_failure",
        "name": "Single Point of Failure Analysis",
        "description": "What single dependency or person, if removed, would collapse operations?",
    },
]

RED_TEAM_SYSTEM = """You are a hostile red team analyst — a senior strategist at a well-funded competitor
to Aliyar Solutions. Your job is to find every weakness, vulnerability, and attack vector
in Aliyar Solutions' business strategy and market position.

Aliyar Solutions is a global AI-powered technology operations company offering:
cloud/DevOps, AI automation, sales automation, content, and intelligence services
at premium retainer rates ($2k-$8k/month) and project rates ($3k-$25k).

Be ruthlessly analytical. Think like a competitor who wants to win.
Output structured JSON only."""


def _parse_json_response(content: str) -> dict:
    """Extract JSON from AI response."""
    try:
        match = re.search(r"\{.*\}", content or "", re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


async def _analyze_attack_vector(vector: dict) -> dict[str, Any]:
    """Run AI analysis for a single attack vector."""
    prompt = (
        f"Attack Vector: {vector['name']}\n"
        f"Question: {vector['description']}\n\n"
        f"As a hostile competitor analyst, analyze this attack vector against Aliyar Solutions. "
        f"Return JSON with keys: threat_description (string), severity (1-10 integer), "
        f"specific_tactics (list of 3 strings), defensive_response (string), "
        f"time_to_exploit_months (integer)."
    )
    try:
        response, _ = await asyncio.wait_for(
            ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=TaskType.REASONING,
                system_prompt=RED_TEAM_SYSTEM,
                max_tokens=600,
            ),
            timeout=60.0,
        )
        if response.error:
            raise ValueError(response.error)
        parsed = _parse_json_response(response.content or "")
        return {
            "vector_id": vector["id"],
            "vector_name": vector["name"],
            "threat_description": parsed.get("threat_description", "Analysis pending."),
            "severity": int(parsed.get("severity", 5)),
            "specific_tactics": parsed.get("specific_tactics", []),
            "defensive_response": parsed.get("defensive_response", "Develop mitigation strategy."),
            "time_to_exploit_months": int(parsed.get("time_to_exploit_months", 6)),
        }
    except Exception as exc:
        logger.warning("Red team vector analysis failed for %s: %s", vector["id"], exc)
        return {
            "vector_id": vector["id"],
            "vector_name": vector["name"],
            "threat_description": f"Unable to analyze {vector['name']} at this time.",
            "severity": 5,
            "specific_tactics": [],
            "defensive_response": "Manual review required.",
            "time_to_exploit_months": 6,
        }


class RedTeamEngine:
    """Adversarial business strategy stress-testing engine."""

    async def run_weekly_analysis(self, tenant_id: UUID) -> dict[str, Any]:
        """Full adversarial stress-test across all attack vectors."""
        import asyncio

        tasks = [_analyze_attack_vector(v) for v in ATTACK_VECTORS]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for _v in raw:
            if isinstance(_v, BaseException):
                logger.warning("Red team vector task raised: %s", _v)
        attack_results = [v for v in raw if isinstance(v, dict)]

        # Calculate overall risk score
        severities = [r["severity"] for r in attack_results]
        avg_severity = sum(severities) / len(severities) if severities else 5
        max_severity = max(severities) if severities else 5
        overall_risk_score = round((avg_severity * 0.6 + max_severity * 0.4) * 10, 2)

        # Identify critical vulnerabilities (severity >= 7)
        critical_vulnerabilities = [
            {
                "name": r["vector_name"],
                "severity": r["severity"],
                "threat": r["threat_description"][:200],
                "time_to_exploit_months": r["time_to_exploit_months"],
            }
            for r in attack_results
            if r["severity"] >= 7
        ]

        # Compile defensive actions
        defensive_actions = [
            {
                "for_vector": r["vector_name"],
                "action": r["defensive_response"],
                "priority": "CRITICAL" if r["severity"] >= 8 else "HIGH" if r["severity"] >= 6 else "MEDIUM",
            }
            for r in attack_results
        ]

        next_assessment_date = (date.today() + timedelta(days=7)).isoformat()

        result = {
            "tenant_id": str(tenant_id),
            "attack_vectors": attack_results,
            "overall_risk_score": overall_risk_score,
            "critical_vulnerabilities": critical_vulnerabilities,
            "defensive_actions": defensive_actions,
            "next_assessment_date": next_assessment_date,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "verdict": (
                "CRITICAL — immediate defensive action required"
                if overall_risk_score >= 70
                else "HIGH RISK — strategic hardening recommended"
                if overall_risk_score >= 50
                else "MODERATE — maintain defensive posture"
                if overall_risk_score >= 30
                else "LOW — strategy appears resilient"
            ),
        }

        # Persist to database
        await self._persist_analysis(tenant_id, result)
        return result

    async def analyze_competitor_positioning(
        self,
        tenant_id: UUID,
        competitor_name: str = "generic AI agency",
    ) -> dict[str, Any]:
        """Analyze how a specific competitor might position against Aliyar Solutions."""
        prompt = (
            f"Competitor: {competitor_name}\n\n"
            f"You are a senior strategist at {competitor_name}. "
            f"Develop a competitive strategy to win against Aliyar Solutions in the market. "
            f"Return JSON with keys: "
            f"their_likely_pitch (how they'd pitch against us, string), "
            f"our_vulnerabilities (list of 3-4 specific weaknesses they'd exploit), "
            f"our_counter_strategy (how Aliyar Solutions should respond, string), "
            f"win_probability (their probability of winning a head-to-head deal, 0.0-1.0 float), "
            f"key_battlegrounds (list of 3 areas where this competition is decided)."
        )

        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.REASONING,
                    system_prompt=RED_TEAM_SYSTEM,
                    max_tokens=900,
                ),
                timeout=60.0,
            )
            if response.error:
                raise ValueError(response.error)
            parsed = _parse_json_response(response.content or "")
            return {
                "tenant_id": str(tenant_id),
                "competitor": competitor_name,
                "their_likely_pitch": parsed.get("their_likely_pitch", "Analysis unavailable."),
                "our_vulnerabilities": parsed.get("our_vulnerabilities", []),
                "our_counter_strategy": parsed.get("our_counter_strategy", "Maintain quality and relationships."),
                "win_probability": float(parsed.get("win_probability", 0.4)),
                "key_battlegrounds": parsed.get("key_battlegrounds", []),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("Competitor positioning analysis failed: %s", exc)
            return {
                "tenant_id": str(tenant_id),
                "competitor": competitor_name,
                "their_likely_pitch": "Analysis unavailable.",
                "our_vulnerabilities": [],
                "our_counter_strategy": "Manual competitive analysis required.",
                "win_probability": 0.5,
                "key_battlegrounds": [],
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _persist_analysis(self, tenant_id: UUID, result: dict) -> None:
        """Store red team analysis in database."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            import uuid
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)
                await session.execute(
                    text(
                        """
                        INSERT INTO red_team_analyses
                          (id, tenant_id, attack_vectors, overall_risk_score,
                           critical_vulnerabilities, defensive_actions,
                           next_assessment_date, created_at)
                        VALUES
                          (:id, :tenant_id, :attack_vectors::jsonb, :overall_risk_score,
                           :critical_vulnerabilities::jsonb, :defensive_actions::jsonb,
                           :next_assessment_date, now())
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "attack_vectors": json.dumps(result["attack_vectors"]),
                        "overall_risk_score": result["overall_risk_score"],
                        "critical_vulnerabilities": json.dumps(result["critical_vulnerabilities"]),
                        "defensive_actions": json.dumps(result["defensive_actions"]),
                        "next_assessment_date": result["next_assessment_date"],
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist red team analysis: %s", exc)

    async def get_latest_analysis(self, tenant_id: UUID) -> dict | None:
        """Get the most recent red team analysis."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)
                row = await session.execute(
                    text(
                        """
                        SELECT id, attack_vectors, overall_risk_score,
                               critical_vulnerabilities, defensive_actions,
                               next_assessment_date, created_at
                        FROM red_team_analyses
                        WHERE tenant_id = :tenant_id
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {"tenant_id": str(tenant_id)},
                )
                r = row.fetchone()
                if not r:
                    return None
                return {
                    "id": str(r.id),
                    "attack_vectors": r.attack_vectors,
                    "overall_risk_score": float(r.overall_risk_score or 0),
                    "critical_vulnerabilities": r.critical_vulnerabilities,
                    "defensive_actions": r.defensive_actions,
                    "next_assessment_date": str(r.next_assessment_date),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
        except Exception as exc:
            logger.warning("Failed to fetch red team analysis: %s", exc)
            return None


red_team_engine = RedTeamEngine()
