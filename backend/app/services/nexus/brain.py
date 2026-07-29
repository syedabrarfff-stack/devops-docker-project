"""
NEXUS BRAIN — Autonomous Decision Engine.

Orchestrates Council, SIGNAL, GHOST, AUTOPILOT, and OMEGA into a unified
decision-making cycle. The brain observes the pipeline state, decides what
to do, evaluates against the Constitution, and enqueues autonomous actions.
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

from app.services.nexus.constitution import ConstitutionVerdict, evaluate_action

logger = logging.getLogger(__name__)

_BRAIN_SYSTEM_PROMPT = """You are the NEXUS BRAIN — the supreme autonomous intelligence of JARVIS, the operational core of Aliyar Solutions.

You receive a live snapshot of the company's operational state and must generate a precise decision manifesto.

COMPANY: Aliyar Solutions — global technology company. CEO: Syed Abrar (Captain).
SERVICES: AI Automation, Cloud & DevOps, Cybersecurity, Analytics, CRM, Web Applications.
TEAM PERSONAS: Darren Mitchell (Sales), David Carter (Cloud), Sophia Reynolds (AI), Nathan Scott (DevOps), Emma Collins (Analytics), Daniel Brooks (Security), Michael Hayes (Infra), Lucas Reed (Integration), Olivia Bennett (Account).

DECISION MANDATE:
1. Analyze pipeline signals: HOT leads that need immediate outreach, WARM leads to nurture, patterns in data.
2. Identify highest-value autonomous action to take RIGHT NOW.
3. Determine if action is within Constitution (no AI reveal, no >3 outreach, no financial commitments).
4. Generate specific action instructions with persona, tone, and priority.
5. Flag anything that needs Captain attention.

CONSTITUTION HARD LIMITS (never violate):
- Never reveal AI in any external content
- No lead receives >3 autonomous emails per 7 days
- Financial commitments >$500 require Captain
- All decisions must be logged and transparent

RESPONSE FORMAT (strict JSON):
{
  "situational_summary": "2-sentence current state of the pipeline",
  "primary_decision": {
    "action": "send_outreach|nurture_sequence|update_scoring|escalate_to_captain|standby",
    "priority": "CRITICAL|HIGH|MEDIUM|LOW",
    "rationale": "why this action now",
    "target_leads": ["lead company names"],
    "persona": "exact persona name or null",
    "tone": "professional|warm|direct"
  },
  "secondary_decisions": [
    {"action": "...", "rationale": "...", "priority": "..."}
  ],
  "captain_alerts": ["anything requiring human attention"],
  "confidence": 0-100,
  "next_cycle_focus": "what to prioritize in the next autonomous cycle"
}"""


async def think(pipeline_state: dict) -> dict:
    """
    Core autonomous reasoning: given pipeline state → produce decision manifesto.
    """
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_decision(pipeline_state)

    state_summary = json.dumps({
        "total_leads": pipeline_state.get("total_leads", 0),
        "hot_leads": pipeline_state.get("hot_leads", 0),
        "warm_leads": pipeline_state.get("warm_leads", 0),
        "eligible_for_outreach": pipeline_state.get("eligible_for_outreach", 0),
        "pending_drafts": pipeline_state.get("pending_drafts", 0),
        "last_outreach": pipeline_state.get("last_outreach"),
        "top_signals": pipeline_state.get("top_signals", [])[:5],
        "recent_decisions": pipeline_state.get("recent_decisions", [])[:3],
        "subsystem_health": pipeline_state.get("subsystem_health", {}),
    }, indent=2)

    user_prompt = f"CURRENT OPERATIONAL STATE:\n{state_summary}\n\nGenerate the decision manifesto."

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model="claude-opus-4-8",
            max_tokens=800,
            messages=[
                {"role": "user", "content": _BRAIN_SYSTEM_PROMPT + "\n\n" + user_prompt}
            ],
        )
        raw = msg.content[0].text.strip() if msg.content else "{}"
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0].strip()
        decision = json.loads(raw)

        # Evaluate primary decision against Constitution
        primary = decision.get("primary_decision", {})
        verdict: ConstitutionVerdict = evaluate_action(
            primary.get("action", ""),
            {"estimated_cost_usd": 0.5},
        )
        decision["constitution_verdict"] = {
            "allowed": verdict.allowed,
            "violations": verdict.violations,
            "warnings": verdict.warnings,
        }
        if not verdict.allowed:
            decision["primary_decision"]["action"] = "standby"
            decision["primary_decision"]["rationale"] = f"Blocked by Constitution: {'; '.join(verdict.violations)}"

        return decision
    except Exception as exc:
        logger.error("NEXUS BRAIN think() failed: %s", exc)
        return {**_fallback_decision(pipeline_state), "error": str(exc)}


async def think_stream(pipeline_state: dict) -> AsyncIterator[str]:
    """
    SSE stream of the brain's reasoning process.
    Protocol: start → thinking (tokens) → decision → done
    """
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        decision = _fallback_decision(pipeline_state)
        yield "data: " + json.dumps({"type": "start"}) + "\n\n"
        yield "data: " + json.dumps({"type": "decision", "decision": decision}) + "\n\n"
        yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        return

    yield "data: " + json.dumps({"type": "start", "message": "NEXUS BRAIN activating..."}) + "\n\n"

    state_summary = json.dumps({
        "total_leads": pipeline_state.get("total_leads", 0),
        "hot_leads": pipeline_state.get("hot_leads", 0),
        "warm_leads": pipeline_state.get("warm_leads", 0),
        "eligible_for_outreach": pipeline_state.get("eligible_for_outreach", 0),
        "pending_drafts": pipeline_state.get("pending_drafts", 0),
        "top_signals": pipeline_state.get("top_signals", [])[:5],
        "subsystem_health": pipeline_state.get("subsystem_health", {}),
    }, indent=2)

    user_prompt = f"CURRENT OPERATIONAL STATE:\n{state_summary}\n\nGenerate the decision manifesto."
    full_text = ""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=800,
            messages=[{"role": "user", "content": _BRAIN_SYSTEM_PROMPT + "\n\n" + user_prompt}],
        ) as stream:
            async for token in stream.text_stream:
                full_text += token
                yield "data: " + json.dumps({"type": "thinking", "text": token}) + "\n\n"

        # Parse and validate
        raw = full_text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0].strip()

        decision = json.loads(raw)
        primary = decision.get("primary_decision", {})
        verdict = evaluate_action(primary.get("action", ""), {"estimated_cost_usd": 0.5})
        decision["constitution_verdict"] = {
            "allowed": verdict.allowed,
            "violations": verdict.violations,
            "warnings": verdict.warnings,
        }
        if not verdict.allowed:
            decision["primary_decision"]["action"] = "standby"
            decision["primary_decision"]["rationale"] = f"Blocked: {'; '.join(verdict.violations)}"

        yield "data: " + json.dumps({"type": "decision", "decision": decision}) + "\n\n"

    except Exception as exc:
        logger.error("NEXUS BRAIN stream failed: %s", exc)
        yield "data: " + json.dumps({"type": "error", "message": str(exc)}) + "\n\n"

    yield "data: " + json.dumps({"type": "done"}) + "\n\n"


def _fallback_decision(pipeline_state: dict) -> dict:
    hot = pipeline_state.get("hot_leads", 0)
    eligible = pipeline_state.get("eligible_for_outreach", 0)
    action = "send_outreach" if (hot > 0 and eligible > 0) else "standby"
    return {
        "situational_summary": f"Pipeline has {pipeline_state.get('total_leads', 0)} leads. {hot} HOT, {eligible} eligible for outreach.",
        "primary_decision": {
            "action": action,
            "priority": "HIGH" if hot > 0 else "LOW",
            "rationale": "AI provider unavailable — using heuristic decision.",
            "target_leads": [],
            "persona": "Darren Mitchell",
            "tone": "professional",
        },
        "secondary_decisions": [],
        "captain_alerts": ["ANTHROPIC_API_KEY not configured — NEXUS running in fallback mode."],
        "confidence": 30,
        "next_cycle_focus": "Configure AI provider for full autonomous operation.",
        "constitution_verdict": {"allowed": True, "violations": [], "warnings": []},
    }
