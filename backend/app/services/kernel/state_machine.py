"""K1-2: JARVIS Kernel State Machine — transactional, versioned system state.

Single source of truth for JARVIS runtime state. Every state transition is:
  - Atomic (DB transaction)
  - Versioned (optimistic concurrency control)
  - Audited (publishes event to Event Bus)
  - Observable (external callers can read current state)

Defined stages (non-exhaustive — new stages can be added without code change):
  idle, decision_pending, verification_running, task_executing,
  budget_alert, health_degraded, dr_failover, paused, shutdown

Valid status values per stage are enforced by callers; the state machine itself
is intentionally permissive to avoid blocking valid operational flows.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kernel import SystemState
from app.services.kernel.event_bus import KernelEvent, get_event_bus

log = logging.getLogger(__name__)


class StateConflictError(Exception):
    """Raised when an optimistic concurrency version conflict is detected."""


class StateMachine:
    """Manage JARVIS system state with OCC and Event Bus integration.

    Usage:
        sm = StateMachine(db_session)
        state = await sm.get()
        await sm.transition(
            new_stage="decision_pending",
            new_status="running",
            data={"decision_id": str(decision_id)},
            expected_version=state.version,
        )
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get(self, stage: Optional[str] = None) -> Optional[SystemState]:
        """Return the most recently updated state record, optionally filtered by stage."""
        q = select(SystemState).order_by(SystemState.updated_at.desc()).limit(1)
        if stage is not None:
            q = q.where(SystemState.stage == stage)
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[SystemState]:
        """Return all current state records (one per stage in practice)."""
        result = await self._session.execute(
            select(SystemState).order_by(SystemState.updated_at.desc())
        )
        return list(result.scalars().all())

    # ── Write ─────────────────────────────────────────────────────────────────

    async def transition(
        self,
        new_stage: str,
        new_status: str,
        data: dict | None = None,
        autonomous_action_id: uuid.UUID | None = None,
        expected_version: int | None = None,
    ) -> SystemState:
        """Transition to a new stage+status atomically.

        If expected_version is provided, raises StateConflictError if the
        current version differs (optimistic concurrency control).

        Publishes a 'state.transitioned' event to the Event Bus after commit.
        """
        async with self._session.begin_nested():
            current = await self.get(stage=new_stage)

            if current is not None and expected_version is not None:
                if current.version != expected_version:
                    raise StateConflictError(
                        f"State version conflict: expected {expected_version}, "
                        f"found {current.version}"
                    )

            if current is None:
                state = SystemState(
                    stage=new_stage,
                    status=new_status,
                    data=data or {},
                    autonomous_action_id=autonomous_action_id,
                    version=1,
                )
                self._session.add(state)
            else:
                prev_version = current.version
                result = await self._session.execute(
                    update(SystemState)
                    .where(
                        SystemState.id == current.id,
                        SystemState.version == prev_version,
                    )
                    .values(
                        status=new_status,
                        data=data or current.data,
                        autonomous_action_id=autonomous_action_id or current.autonomous_action_id,
                        version=prev_version + 1,
                        updated_at=datetime.now(timezone.utc),
                    )
                    .returning(SystemState)
                )
                state = result.scalar_one_or_none()
                if state is None:
                    raise StateConflictError(
                        f"Concurrent modification detected for stage '{new_stage}'"
                    )

        log.info(
            "StateMachine: %s → %s (v%d)",
            new_stage,
            new_status,
            state.version,
        )

        # Publish event asynchronously — do not fail the transition if bus unavailable.
        try:
            bus = get_event_bus()
            await bus.publish(KernelEvent(
                event_type="state.transitioned",
                source_engine="state_machine",
                payload={
                    "stage": new_stage,
                    "status": new_status,
                    "version": state.version,
                    "state_id": str(state.id),
                },
            ))
        except Exception as exc:
            log.warning("StateMachine: event bus publish failed (non-fatal): %s", exc)

        return state

    async def set_idle(self) -> SystemState:
        """Convenience: transition the global state to idle."""
        return await self.transition(
            new_stage="idle",
            new_status="ready",
            data={"source": "state_machine.set_idle"},
        )

    async def mark_paused(self, reason: str = "override") -> SystemState:
        """Convenience: pause all autonomous operations."""
        return await self.transition(
            new_stage="paused",
            new_status="paused",
            data={"reason": reason, "paused_at": datetime.now(timezone.utc).isoformat()},
        )

    async def mark_shutdown(self, reason: str = "override") -> SystemState:
        """Convenience: mark the system as shutdown."""
        return await self.transition(
            new_stage="shutdown",
            new_status="shutdown",
            data={"reason": reason, "shutdown_at": datetime.now(timezone.utc).isoformat()},
        )

    # ── Inspection ────────────────────────────────────────────────────────────

    async def is_paused(self) -> bool:
        state = await self.get(stage="paused")
        return state is not None and state.status == "paused"

    async def is_shutdown(self) -> bool:
        state = await self.get(stage="shutdown")
        return state is not None and state.status == "shutdown"
