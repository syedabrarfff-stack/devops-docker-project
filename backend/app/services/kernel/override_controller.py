"""K1-9: JARVIS Override Controller — Telegram PAUSE/STOP/ROLLBACK/SHUTDOWN.

This is Captain's 24/7 emergency lever. Any of these commands, received via
Telegram (or the REST API), immediately halts the corresponding autonomous
operation without requiring a laptop, VPN, or code change.

Supported override commands:
  PAUSE <scope>     — halt autonomous task execution (scope: ALL or engine name)
  STOP <job>        — stop a specific scheduler job
  ROLLBACK <sha>    — trigger git rollback to the named commit SHA
  SHUTDOWN          — full system shutdown of autonomous operations
  RESUME            — lift a prior PAUSE
  STATUS            — return current kernel + health summary to Captain

Architecture:
  - Receives commands from the Telegram webhook (which calls handle_override)
  - Updates State Machine (so all other engines know the system is paused)
  - Publishes override events to the Event Bus
  - Writes every command + outcome to the Audit Logger
  - SHUTDOWN: marks state + kills scheduler jobs via APScheduler

This controller never executes directly — it coordinates via the Kernel
(State Machine + Event Bus + Task Queue). No direct DB/infra mutations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kernel.state_machine import StateMachine
from app.services.kernel.task_queue import TaskQueue, TaskPriority
from app.services.kernel.audit_logger import AuditLogger
from app.services.kernel.event_bus import get_event_bus

log = logging.getLogger(__name__)

ACTOR = "override_controller"


class OverrideResult:
    def __init__(self, success: bool, message: str, command: str) -> None:
        self.success = success
        self.message = message
        self.command = command
        self.executed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "command": self.command,
            "message": self.message,
            "executed_at": self.executed_at,
        }


class OverrideController:
    """Execute Captain override commands with full audit trail.

    Inject a DB session; the controller is stateless beyond that.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sm = StateMachine(session)
        self._queue = TaskQueue(session)
        self._audit = AuditLogger(session)
        self._bus = get_event_bus()

    async def handle_override(
        self,
        command: str,
        args: Optional[str] = None,
        captain_id: Optional[str] = None,
    ) -> OverrideResult:
        """Dispatch a Captain override command.

        command: one of PAUSE / STOP / ROLLBACK / SHUTDOWN / RESUME / STATUS
        args:    optional argument (scope, job name, SHA, etc.)
        captain_id: Telegram user ID for audit trail
        """
        cmd = command.strip().upper()
        actor = f"captain:{captain_id}" if captain_id else "captain"

        audit_details = {
            "command": cmd,
            "args": args,
            "captain_id": captain_id,
        }

        log.warning(
            "OverrideController: received %s from %s (args=%s)",
            cmd, actor, args,
        )

        try:
            if cmd == "PAUSE":
                result = await self._pause(scope=args or "ALL", actor=actor)
            elif cmd == "STOP":
                result = await self._stop_job(job_name=args or "", actor=actor)
            elif cmd == "ROLLBACK":
                result = await self._rollback(sha=args or "", actor=actor)
            elif cmd == "SHUTDOWN":
                result = await self._shutdown(actor=actor)
            elif cmd == "RESUME":
                result = await self._resume(actor=actor)
            elif cmd == "STATUS":
                result = await self._status()
            else:
                result = OverrideResult(
                    success=False,
                    message=f"Unknown command '{cmd}'. Valid: PAUSE / STOP / ROLLBACK / SHUTDOWN / RESUME / STATUS",
                    command=cmd,
                )
        except Exception as exc:
            log.error("OverrideController: command %s failed: %s", cmd, exc)
            result = OverrideResult(
                success=False,
                message=f"Command failed: {exc}",
                command=cmd,
            )

        await self._audit.write(
            action_type=f"override.{cmd.lower()}",
            actor=actor,
            details={**audit_details, "result": result.to_dict()},
            outcome="COMPLETED" if result.success else "FAILED",
        )

        return result

    # ── Command implementations ───────────────────────────────────────────────

    async def _pause(self, scope: str, actor: str) -> OverrideResult:
        await self._sm.mark_paused(reason=f"Captain override: PAUSE {scope}")
        await self._bus.emit(
            "override.pause",
            payload={"scope": scope, "issued_by": actor},
            source_engine=ACTOR,
        )
        msg = f"✅ PAUSED: autonomous operations halted (scope={scope}). Send RESUME to lift."
        log.warning("OverrideController: PAUSE executed (scope=%s)", scope)
        return OverrideResult(success=True, message=msg, command="PAUSE")

    async def _stop_job(self, job_name: str, actor: str) -> OverrideResult:
        if not job_name:
            return OverrideResult(
                success=False,
                message="STOP requires a job name. Usage: STOP <job_name>",
                command="STOP",
            )
        await self._bus.emit(
            "override.stop_job",
            payload={"job_name": job_name, "issued_by": actor},
            source_engine=ACTOR,
        )
        # Enqueue a high-priority task for the scheduler to pick up and act on.
        await self._queue.enqueue(
            payload={"type": "scheduler.stop_job", "job_name": job_name},
            priority=TaskPriority.CRITICAL,
        )
        msg = f"✅ STOP enqueued for job '{job_name}'. Scheduler will halt it within seconds."
        log.warning("OverrideController: STOP enqueued for job=%s", job_name)
        return OverrideResult(success=True, message=msg, command="STOP")

    async def _rollback(self, sha: str, actor: str) -> OverrideResult:
        if not sha or len(sha) < 7:
            return OverrideResult(
                success=False,
                message="ROLLBACK requires a valid git commit SHA (min 7 chars). Usage: ROLLBACK <sha>",
                command="ROLLBACK",
            )
        await self._bus.emit(
            "override.rollback",
            payload={"sha": sha, "issued_by": actor},
            source_engine=ACTOR,
        )
        await self._queue.enqueue(
            payload={"type": "deploy.rollback", "target_sha": sha},
            priority=TaskPriority.CRITICAL,
        )
        msg = (
            f"✅ ROLLBACK to `{sha}` enqueued as CRITICAL task. "
            f"The deploy engine will trigger a GitHub Actions run to roll back. "
            f"Health checks will follow automatically."
        )
        log.warning("OverrideController: ROLLBACK enqueued (sha=%s)", sha)
        return OverrideResult(success=True, message=msg, command="ROLLBACK")

    async def _shutdown(self, actor: str) -> OverrideResult:
        await self._sm.mark_shutdown(reason=f"Captain override: SHUTDOWN by {actor}")
        await self._bus.emit(
            "override.shutdown",
            payload={"issued_by": actor},
            source_engine=ACTOR,
        )
        msg = (
            "⛔ SHUTDOWN: autonomous operations HALTED. "
            "All pending tasks are paused. Infrastructure (Docker, DB, Redis) remains up. "
            "Send RESUME to restart autonomous operations."
        )
        log.critical("OverrideController: SHUTDOWN executed by %s", actor)
        return OverrideResult(success=True, message=msg, command="SHUTDOWN")

    async def _resume(self, actor: str) -> OverrideResult:
        current = await self._sm.get(stage="paused")
        is_shutdown = await self._sm.is_shutdown()
        if current is None and not is_shutdown:
            return OverrideResult(
                success=False,
                message="System is not currently PAUSED or SHUTDOWN — nothing to resume.",
                command="RESUME",
            )
        await self._sm.set_idle()
        await self._bus.emit(
            "override.resume",
            payload={"issued_by": actor},
            source_engine=ACTOR,
        )
        msg = "✅ RESUMED: autonomous operations restarted."
        log.warning("OverrideController: RESUME executed by %s", actor)
        return OverrideResult(success=True, message=msg, command="RESUME")

    async def _status(self) -> OverrideResult:
        from app.services.kernel.health_aggregator import get_health_aggregator
        summary = get_health_aggregator().get_summary()
        state = await self._sm.get()
        state_info = (
            f"stage={state.stage}, status={state.status}, v{state.version}"
            if state else "no state record"
        )
        msg = (
            f"📊 JARVIS STATUS\n"
            f"System state: {state_info}\n"
            f"Overall health: {summary.get('overall', 'UNKNOWN')}\n"
            f"Engines: {list(summary.get('engines', {}).keys())}"
        )
        return OverrideResult(success=True, message=msg, command="STATUS")
