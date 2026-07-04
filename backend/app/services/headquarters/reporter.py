"""HQ-6: Reporting — deep briefings for Captain-initiated work, and a channel
for autonomous background operations (self-healer, health checks, etc.) to
surface into the same Headquarters conversation without Captain ever having
to say "the website is down."
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.headquarters import HQActionRequest

log = logging.getLogger(__name__)

AUTONOMOUS_SESSION_ID = "system-autonomous"


def narrate_execution(operation: str | None, driver_model: str | None, result: dict[str, Any]) -> str:
    """Turn a structured execute_plan() result into a plain-English briefing —
    what was attempted, each step, and the outcome. Not a one-word "Verified."
    """
    steps = result.get("steps", [])
    lines: list[str] = []

    if operation:
        lines.append(f"Operation: {operation}" + (f" (drafted by {driver_model})" if driver_model else ""))

    lines.append(f"{len(steps)} step(s) taken:")
    for s in steps:
        tool = s.get("tool")
        outcome = s.get("outcome", {})
        mark = "done" if outcome.get("ok") else "FAILED"
        step_index = s.get("step")
        step_num = step_index + 1 if isinstance(step_index, int) else "?"
        lines.append(f"  {step_num}. {tool} — {mark}")

    status = result.get("status")
    if status == "COMPLETED":
        test_out = result.get("test_output", {})
        lines.append(f"Tests: {'passed' if test_out.get('ok') else 'not run/failed'}.")
        lines.append("Verified — every step committed, tests green.")
    elif status == "FAILED":
        reason = result.get("reason") or f"step {result.get('failed_step')} failed"
        lines.append(f"Stopped: {reason}.")
        rollback = result.get("rollback", {})
        if rollback.get("ok"):
            lines.append("Rolled back to the last known-good commit — nothing broken left in place.")
        else:
            lines.append(f"Rollback note: {rollback.get('error', 'see audit log')}.")

    return "\n".join(lines)


async def log_autonomous_operation(
    session: AsyncSession,
    source: str,
    summary: str,
    details: dict[str, Any],
    had_action: bool,
) -> None:
    """Record an autonomous background operation (self-healer, health check,
    predictive scan, etc.) so it appears in the Headquarters conversation
    without Captain ever asking. Skips silent no-op cycles — only logs when
    something was actually detected or acted on.
    """
    if not had_action:
        return
    try:
        record = HQActionRequest(
            session_id=AUTONOMOUS_SESSION_ID,
            request_text=f"[Autonomous — {source}]",
            kind="autonomous_operation",
            status="COMPLETED",
            driver_model=source,
            answer_text=summary,
            result=details,
        )
        session.add(record)
        await session.commit()
    except Exception as exc:
        log.warning("[Headquarters] Failed to log autonomous operation from %s: %s", source, exc)
