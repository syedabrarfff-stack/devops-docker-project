"""
JARVIS Expert Council Engine — 5 parallel AI agents with distinct perspectives
convene to analyze strategic questions and produce synthesized recommendations.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

logger = logging.getLogger(__name__)

# ── Agent definitions ─────────────────────────────────────────────────────────

AGENTS = {
    "Strategist": {
        "system": (
            "You are the Chief Strategist agent in JARVIS's Expert Council. "
            "Your role is to evaluate decisions through the lens of long-term competitive positioning, "
            "market differentiation, and sustainable growth. Focus on: market share, competitive moats, "
            "strategic timing, and how this decision compounds value over 12-24 months. "
            "Be direct and confident. Output a structured analysis as JSON with keys: "
            "perspective, recommendation, key_points (list of 3), confidence (0-1), risk_level (LOW/MEDIUM/HIGH)."
        ),
        "task_type": TaskType.REASONING,
    },
    "Contrarian": {
        "system": (
            "You are the Contrarian agent in JARVIS's Expert Council. "
            "Your job is to challenge assumptions, find flaws in plans, expose hidden risks, "
            "and ask the uncomfortable questions others avoid. Look for: confirmation bias, "
            "overconfidence, unintended consequences, and failure modes. "
            "Be intellectually rigorous and provocative. Output as JSON with keys: "
            "perspective, recommendation, key_points (list of 3), confidence (0-1), risk_level (LOW/MEDIUM/HIGH)."
        ),
        "task_type": TaskType.REASONING,
    },
    "Technologist": {
        "system": (
            "You are the Technologist agent in JARVIS's Expert Council. "
            "Evaluate decisions through the lens of technical feasibility, implementation risk, "
            "infrastructure complexity, scalability, and technology debt. Consider: build vs buy, "
            "integration challenges, maintenance burden, and technical obsolescence risk. "
            "Output as JSON with keys: "
            "perspective, recommendation, key_points (list of 3), confidence (0-1), risk_level (LOW/MEDIUM/HIGH)."
        ),
        "task_type": TaskType.REASONING,
    },
    "Financier": {
        "system": (
            "You are the Financier agent in JARVIS's Expert Council. "
            "Evaluate decisions through ROI, unit economics, cash flow impact, payback period, "
            "revenue potential, cost structure, and financial risk. Think like a CFO + growth investor. "
            "Quantify where possible. Focus on: revenue impact, cost to execute, break-even timeline, "
            "and capital efficiency. Output as JSON with keys: "
            "perspective, recommendation, key_points (list of 3), confidence (0-1), risk_level (LOW/MEDIUM/HIGH)."
        ),
        "task_type": TaskType.REASONING,
    },
    "Ethicist": {
        "system": (
            "You are the Ethics & Brand agent in JARVIS's Expert Council. "
            "Evaluate decisions through brand risk, client trust, ethical implications, "
            "reputational exposure, and long-term relationship integrity. Consider: "
            "is this honest, is this sustainable, does this build or erode trust, "
            "what would clients/partners think if they knew. Output as JSON with keys: "
            "perspective, recommendation, key_points (list of 3), confidence (0-1), risk_level (LOW/MEDIUM/HIGH)."
        ),
        "task_type": TaskType.REASONING,
    },
}


def _parse_agent_response(content: str, agent_name: str) -> dict[str, Any]:
    """Parse JSON from AI response, fall back gracefully."""
    try:
        # Try to extract JSON block
        match = re.search(r"\{.*\}", content or "", re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    # Fallback
    return {
        "perspective": content[:500] if content else f"{agent_name} analysis unavailable.",
        "recommendation": "See perspective for details.",
        "key_points": [],
        "confidence": 0.5,
        "risk_level": "MEDIUM",
    }


async def _run_agent(
    agent_name: str,
    agent_config: dict,
    question: str,
    context: Optional[dict],
) -> dict[str, Any]:
    """Run a single agent and return its structured response."""
    context_str = ""
    if context:
        context_str = f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"

    prompt = (
        f"Question for council deliberation:\n{question}"
        f"{context_str}\n\n"
        f"Provide your expert perspective as the {agent_name}. "
        f"Return your analysis as a JSON object."
    )

    try:
        response, _ = await asyncio.wait_for(
            ai_router.chat(
                [Message(role="user", content=prompt)],
                task_type=agent_config["task_type"],
                system_prompt=agent_config["system"],
                max_tokens=800,
            ),
            timeout=60.0,
        )
        if response.error:
            raise ValueError(response.error)
        parsed = _parse_agent_response(response.content, agent_name)
        parsed["agent"] = agent_name
        return parsed
    except Exception as exc:
        logger.warning("Agent %s failed: %s", agent_name, exc)
        return {
            "agent": agent_name,
            "perspective": f"{agent_name} encountered an error during analysis.",
            "recommendation": "Unable to provide recommendation at this time.",
            "key_points": [],
            "confidence": 0.0,
            "risk_level": "MEDIUM",
        }


def _synthesize_council(agent_responses: list[dict]) -> dict[str, Any]:
    """Aggregate agent responses into council consensus."""
    recommendations = [r.get("recommendation", "") for r in agent_responses if r.get("recommendation")]
    confidences = [r.get("confidence", 0.5) for r in agent_responses]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    # Find agreements (common themes across key_points)
    all_key_points = []
    for r in agent_responses:
        all_key_points.extend(r.get("key_points", []))

    # Determine majority recommendation by analyzing content
    proceed_votes = sum(
        1 for r in agent_responses
        if any(word in r.get("recommendation", "").lower() for word in ["proceed", "yes", "approve", "go ahead", "recommend"])
    )
    caution_votes = sum(
        1 for r in agent_responses
        if any(word in r.get("recommendation", "").lower() for word in ["caution", "careful", "risk", "avoid", "concern"])
    )

    if proceed_votes > len(agent_responses) / 2:
        majority = "PROCEED — council majority recommends moving forward with appropriate safeguards."
    elif caution_votes > len(agent_responses) / 2:
        majority = "CAUTION — council majority flags significant risks requiring mitigation before proceeding."
    else:
        majority = "MIXED — council is divided; requires Captain judgment on which perspective to prioritize."

    # Final synthesis
    synthesis_parts = []
    for r in agent_responses:
        agent = r.get("agent", "Agent")
        rec = r.get("recommendation", "")
        if rec:
            synthesis_parts.append(f"{agent}: {rec}")

    final_synthesis = (
        f"Council of {len(agent_responses)} agents completed deliberation. "
        + " | ".join(synthesis_parts[:3])
        + (f" [+{len(synthesis_parts)-3} more]" if len(synthesis_parts) > 3 else "")
    )

    # Key agreements vs disagreements
    risk_levels = [r.get("risk_level", "MEDIUM") for r in agent_responses]
    high_risk_count = risk_levels.count("HIGH")
    low_risk_count = risk_levels.count("LOW")

    key_agreements = [p for p in all_key_points[:6] if p]
    key_disagreements = []
    if high_risk_count > 0 and low_risk_count > 0:
        key_disagreements.append(f"Risk assessment split: {high_risk_count} agents rate HIGH, {low_risk_count} rate LOW")
    if proceed_votes > 0 and caution_votes > 0:
        key_disagreements.append(f"Direction split: {proceed_votes} agents say proceed, {caution_votes} urge caution")

    return {
        "majority_recommendation": majority,
        "key_agreements": key_agreements[:5],
        "key_disagreements": key_disagreements,
        "confidence_score": round(avg_confidence, 3),
        "final_synthesis": final_synthesis,
        "agents_used": len(agent_responses),
        "vote_breakdown": {"proceed": proceed_votes, "caution": caution_votes},
    }


class ExpertCouncilEngine:
    """Runs parallel AI agent council sessions for strategic decision support."""

    async def convene_council(
        self,
        tenant_id: UUID,
        question: str,
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Full 5-agent council session."""
        agent_names = list(AGENTS.keys())
        tasks = [
            _run_agent(name, AGENTS[name], question, context)
            for name in agent_names
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for _v in raw:
            if isinstance(_v, BaseException):
                logger.warning("Expert council agent raised: %s", _v)
        agent_responses = [v for v in raw if isinstance(v, dict)]

        consensus = _synthesize_council(list(agent_responses))

        result = {
            "question": question,
            "session_type": "full_council",
            "tenant_id": str(tenant_id),
            "agent_responses": list(agent_responses),
            "consensus": consensus,
            "convened_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist session
        await self._persist_session(tenant_id, question, context, consensus, agent_responses)
        return result

    async def quick_council(
        self,
        tenant_id: UUID,
        question: str,
    ) -> dict[str, Any]:
        """Fast 3-agent council (Strategist, Contrarian, Financier)."""
        quick_agents = ["Strategist", "Contrarian", "Financier"]
        tasks = [
            _run_agent(name, AGENTS[name], question, None)
            for name in quick_agents
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for _v in raw:
            if isinstance(_v, BaseException):
                logger.warning("Expert council quick agent raised: %s", _v)
        agent_responses = [v for v in raw if isinstance(v, dict)]

        consensus = _synthesize_council(list(agent_responses))

        result = {
            "question": question,
            "session_type": "quick_council",
            "tenant_id": str(tenant_id),
            "agent_responses": list(agent_responses),
            "consensus": consensus,
            "convened_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._persist_session(tenant_id, question, None, consensus, agent_responses)
        return result

    async def _persist_session(
        self,
        tenant_id: UUID,
        question: str,
        context: Optional[dict],
        consensus: dict,
        agent_responses: list,
    ) -> None:
        """Store council session in database."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            import uuid
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)
                await session.execute(
                    text(
                        """
                        INSERT INTO expert_council_sessions
                          (id, tenant_id, question, context, majority_recommendation,
                           key_agreements, key_disagreements, confidence_score,
                           final_synthesis, agents_used, created_at)
                        VALUES
                          (:id, :tenant_id, :question, :context, :majority_recommendation,
                           :key_agreements::jsonb, :key_disagreements::jsonb, :confidence_score,
                           :final_synthesis, :agents_used, now())
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "question": question,
                        "context": json.dumps(context or {}),
                        "majority_recommendation": consensus.get("majority_recommendation", ""),
                        "key_agreements": json.dumps(consensus.get("key_agreements", [])),
                        "key_disagreements": json.dumps(consensus.get("key_disagreements", [])),
                        "confidence_score": consensus.get("confidence_score", 0.5),
                        "final_synthesis": consensus.get("final_synthesis", ""),
                        "agents_used": consensus.get("agents_used", 0),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist council session: %s", exc)

    async def get_recent_sessions(self, tenant_id: UUID, limit: int = 10) -> list[dict]:
        """Retrieve recent council sessions."""
        try:
            from app.core.database import AsyncSessionLocal, set_tenant_context
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                await set_tenant_context(session, tenant_id)
                rows = await session.execute(
                    text(
                        """
                        SELECT id, question, majority_recommendation, confidence_score,
                               final_synthesis, agents_used, created_at
                        FROM expert_council_sessions
                        WHERE tenant_id = :tenant_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"tenant_id": str(tenant_id), "limit": limit},
                )
                return [
                    {
                        "id": str(r.id),
                        "question": r.question,
                        "majority_recommendation": r.majority_recommendation,
                        "confidence_score": float(r.confidence_score or 0),
                        "final_synthesis": r.final_synthesis,
                        "agents_used": r.agents_used,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning("Failed to fetch council sessions: %s", exc)
            return []


expert_council_engine = ExpertCouncilEngine()
