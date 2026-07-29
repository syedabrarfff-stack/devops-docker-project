"""
JARVIS NEXUS — Master Orchestrator.

Connects Constitution → Brain → Heartbeat → Healer → SIGNAL → GHOST → AUTOPILOT.
The end-to-end autonomous intelligence cycle:

  PULSE: Read pipeline state
  THINK: Brain generates decision manifesto
  VALIDATE: Constitution evaluates action
  ACT: Dispatch to appropriate subsystem (GHOST → AUTOPILOT)
  HEAL: Check subsystem health, self-recover
  LOG: Persist decision + outcomes
  NOTIFY: Alert Captain on critical events
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Any

from app.services.nexus.constitution import evaluate_action
from app.services.nexus.brain import think
from app.services.nexus.heartbeat import run_pulse, log_decision, get_decisions, get_latest_pulse
from app.services.nexus.healer import diagnose_all, auto_heal_all

logger = logging.getLogger(__name__)

# ── NEXUS version ─────────────────────────────────────────────────────────────
NEXUS_VERSION = "1.0.0"
NEXUS_CODENAME = "CONSTITUTION"


async def nexus_status(db) -> dict:
    """Return full NEXUS operational status for the dashboard."""
    pulse = await get_latest_pulse()
    decisions = await get_decisions(5)
    health = await diagnose_all(db)

    healthy_count = sum(1 for s in health.values() if s.get("status") == "healthy")
    total_subsystems = len(health)

    return {
        "version": NEXUS_VERSION,
        "codename": NEXUS_CODENAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operational": healthy_count >= (total_subsystems // 2),
        "subsystem_health": health,
        "healthy_subsystems": healthy_count,
        "total_subsystems": total_subsystems,
        "latest_pulse": pulse,
        "recent_decisions": decisions,
    }


async def nexus_cycle_stream(db) -> AsyncIterator[str]:
    """
    Full autonomous cycle as SSE stream.
    Protocol:
      data: {"type":"phase","phase":"PULSE","message":"..."}
      data: {"type":"pulse","data":{...}}
      data: {"type":"phase","phase":"THINK","message":"..."}
      data: {"type":"thinking","text":"..."}  (streaming tokens)
      data: {"type":"decision","decision":{...}}
      data: {"type":"phase","phase":"HEAL","message":"..."}
      data: {"type":"heal","results":[...]}
      data: {"type":"phase","phase":"COMPLETE","message":"..."}
      data: {"type":"done"}
    """

    def _emit(obj: dict) -> str:
        return "data: " + json.dumps(obj, default=str) + "\n\n"

    # ── PHASE 1: PULSE ────────────────────────────────────────────────────────
    yield _emit({"type": "phase", "phase": "PULSE", "message": "Reading pipeline state..."})
    try:
        pulse = await run_pulse(db)
        yield _emit({"type": "pulse", "data": pulse})
    except Exception as exc:
        yield _emit({"type": "error", "phase": "PULSE", "message": str(exc)})
        pulse = {}

    # ── PHASE 2: THINK ────────────────────────────────────────────────────────
    yield _emit({"type": "phase", "phase": "THINK", "message": "NEXUS BRAIN reasoning..."})

    pipeline_state = {
        **pulse.get("pipeline", {}),
        "pending_drafts": pulse.get("autopilot_pending", 0),
        "subsystem_health": pulse.get("subsystems", {}),
        "top_signals": [],
    }

    import anthropic
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    from app.services.nexus.brain import _fallback_decision
    decision: dict = _fallback_decision(pipeline_state)

    if api_key:
        from app.services.nexus.brain import _BRAIN_SYSTEM_PROMPT, _fallback_decision
        state_summary = json.dumps(pipeline_state, indent=2)
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
                    yield _emit({"type": "thinking", "text": token})

            raw = full_text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:]).rsplit("```", 1)[0].strip()
            decision = json.loads(raw)

            # Constitution check
            primary = decision.get("primary_decision", {})
            verdict = evaluate_action(primary.get("action", ""), {"estimated_cost_usd": 0.5})
            decision["constitution_verdict"] = {
                "allowed": verdict.allowed,
                "violations": verdict.violations,
                "warnings": verdict.warnings,
            }
            if not verdict.allowed:
                decision["primary_decision"]["action"] = "standby"
                decision["primary_decision"]["rationale"] = f"Blocked by Constitution: {'; '.join(verdict.violations)}"

        except Exception as exc:
            logger.error("NEXUS THINK failed: %s", exc)
            from app.services.nexus.brain import _fallback_decision
            decision = {**_fallback_decision(pipeline_state), "error": str(exc)}
    else:
        from app.services.nexus.brain import _fallback_decision
        decision = _fallback_decision(pipeline_state)

    yield _emit({"type": "decision", "decision": decision})

    # Log the decision
    await log_decision({
        "cycle_type": "autonomous",
        "action": decision.get("primary_decision", {}).get("action", "unknown"),
        "confidence": decision.get("confidence", 0),
        "constitution_allowed": decision.get("constitution_verdict", {}).get("allowed", True),
        "situational_summary": decision.get("situational_summary", ""),
    })

    # ── PHASE 3: ACT ─────────────────────────────────────────────────────────
    primary_action = decision.get("primary_decision", {}).get("action", "standby")
    constitution_ok = decision.get("constitution_verdict", {}).get("allowed", True)

    if primary_action == "send_outreach" and constitution_ok:
        yield _emit({"type": "phase", "phase": "ACT", "message": "Triggering AUTOPILOT outreach cycle..."})
        try:
            from app.services.autopilot.pipeline import run_autopilot_cycle
            from app.core.config import settings as _cfg
            import uuid as _uuid_mod
            _nexus_tid = None
            if _cfg.JARVIS_DEFAULT_TENANT_ID:
                try:
                    _nexus_tid = _uuid_mod.UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
                except (ValueError, AttributeError):
                    pass
            cycle_result = await run_autopilot_cycle(
                tenant_id=_nexus_tid,
                max_leads=10,
                min_score=70.0,
                tone=decision.get("primary_decision", {}).get("tone", "professional"),
            )
            yield _emit({"type": "act_result", "subsystem": "autopilot", "result": cycle_result})
        except Exception as exc:
            yield _emit({"type": "act_error", "subsystem": "autopilot", "message": str(exc)})
    else:
        yield _emit({"type": "phase", "phase": "ACT", "message": f"Action: {primary_action} (no dispatch needed)"})

    # ── PHASE 4: HEAL ────────────────────────────────────────────────────────
    yield _emit({"type": "phase", "phase": "HEAL", "message": "Running self-heal diagnostics..."})
    try:
        heal_results = await auto_heal_all(db)
        yield _emit({"type": "heal", "results": heal_results})
    except Exception as exc:
        yield _emit({"type": "heal_error", "message": str(exc)})

    # ── COMPLETE ─────────────────────────────────────────────────────────────
    yield _emit({
        "type": "phase",
        "phase": "COMPLETE",
        "message": "NEXUS cycle complete.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    yield _emit({"type": "done"})
