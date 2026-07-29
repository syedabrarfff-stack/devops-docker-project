"""K1-7: JARVIS Health Aggregator — poll engines every 30s, aggregate, publish.

The Health Aggregator is the system's nervous system — it continuously polls
every registered engine and aggregates their health into:
  1. A `health_snapshots` DB record (queryable history)
  2. An Event Bus event ('health.degraded' or 'health.critical')
  3. A cached in-memory summary (for the Ops Dashboard)

Health status levels:
  HEALTHY   — all checks passing
  DEGRADED  — one or more checks failing, system still operational
  CRITICAL  — core subsystem down, autonomous operation at risk
  UNKNOWN   — engine not reachable for polling

Engine registration:
    aggregator = get_health_aggregator()
    aggregator.register("ai_router", check_ai_router_health)
    await aggregator.start()   # begin 30s polling loop

Usage in Ops Dashboard:
    summary = aggregator.get_summary()
    # → {"overall": "HEALTHY", "engines": {"ai_router": "HEALTHY", ...}}
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kernel import HealthSnapshot
from app.services.kernel.event_bus import get_event_bus

log = logging.getLogger(__name__)

HealthCheckFn = Callable[[], Coroutine[Any, Any, dict]]


@dataclass
class EngineHealthResult:
    engine_name: str
    status: str          # HEALTHY / DEGRADED / CRITICAL / UNKNOWN
    details: dict = field(default_factory=dict)
    checked_at: float = field(default_factory=time.monotonic)
    error: Optional[str] = None


class HealthAggregator:
    """Poll registered engine health checks on a 30s interval.

    Designed to run as a long-lived background task (asyncio.Task).
    """

    POLL_INTERVAL = 30  # seconds
    CHECK_TIMEOUT = 10  # seconds per check

    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None) -> None:
        self._checks: dict[str, HealthCheckFn] = {}
        self._last_results: dict[str, EngineHealthResult] = {}
        self._session_factory = session_factory
        self._running = False
        self._task: asyncio.Task | None = None

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, engine_name: str, check_fn: HealthCheckFn) -> None:
        """Register an async health check function for an engine.

        check_fn must:
          - Be an async callable with no required arguments
          - Return a dict with at least {"status": "HEALTHY"|"DEGRADED"|"CRITICAL"}
          - Raise on critical errors (the aggregator catches and marks UNKNOWN)
        """
        self._checks[engine_name] = check_fn
        log.debug("HealthAggregator: registered engine '%s'", engine_name)

    def deregister(self, engine_name: str) -> None:
        self._checks.pop(engine_name, None)
        self._last_results.pop(engine_name, None)

    # ── Polling loop ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="health_aggregator")
        self._task.add_done_callback(self._on_task_done)
        log.info("HealthAggregator: started (interval=%ds)", self.POLL_INTERVAL)

    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("HealthAggregator: stopped")

    def _on_task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception():
            log.error("HealthAggregator: polling loop crashed: %s", task.exception())

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._run_all_checks()
            except Exception as exc:
                log.error("HealthAggregator: poll cycle error: %s", exc)
            await asyncio.sleep(self.POLL_INTERVAL)

    # ── Check execution ───────────────────────────────────────────────────────

    async def _run_all_checks(self) -> None:
        if not self._checks:
            return

        results = await asyncio.gather(
            *[self._run_one_check(name, fn) for name, fn in self._checks.items()],
            return_exceptions=True,
        )

        engine_names = list(self._checks.keys())
        for name, result in zip(engine_names, results):
            if isinstance(result, EngineHealthResult):
                self._last_results[name] = result
                await self._persist_and_publish(result)
            else:
                err_result = EngineHealthResult(
                    engine_name=name,
                    status="UNKNOWN",
                    error=str(result),
                )
                self._last_results[name] = err_result
                await self._persist_and_publish(err_result)

    async def _run_one_check(
        self,
        engine_name: str,
        fn: HealthCheckFn,
    ) -> EngineHealthResult:
        try:
            raw = await asyncio.wait_for(fn(), timeout=self.CHECK_TIMEOUT)
            return EngineHealthResult(
                engine_name=engine_name,
                status=raw.get("status", "UNKNOWN"),
                details=raw,
            )
        except asyncio.TimeoutError:
            return EngineHealthResult(
                engine_name=engine_name,
                status="UNKNOWN",
                error=f"check timed out after {self.CHECK_TIMEOUT}s",
            )
        except Exception as exc:
            return EngineHealthResult(
                engine_name=engine_name,
                status="UNKNOWN",
                error=str(exc),
            )

    # ── Persistence + events ──────────────────────────────────────────────────

    async def _persist_and_publish(self, result: EngineHealthResult) -> None:
        # Persist snapshot to DB (best-effort — don't crash the aggregator)
        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    snap = HealthSnapshot(
                        engine_name=result.engine_name,
                        status=result.status,
                        details={
                            **(result.details or {}),
                            "error": result.error,
                        },
                    )
                    session.add(snap)
                    await session.commit()
            except Exception as exc:
                log.warning(
                    "HealthAggregator: DB persist failed for %s: %s",
                    result.engine_name, exc,
                )

        # Publish to Event Bus if degraded/critical
        if result.status in ("DEGRADED", "CRITICAL", "UNKNOWN"):
            try:
                event_type = (
                    "health.critical" if result.status == "CRITICAL" else "health.degraded"
                )
                await get_event_bus().emit(
                    event_type,
                    payload={
                        "engine": result.engine_name,
                        "status": result.status,
                        "error": result.error,
                        "details": result.details,
                    },
                    source_engine="health_aggregator",
                )
            except Exception as exc:
                log.warning(
                    "HealthAggregator: event publish failed for %s: %s",
                    result.engine_name, exc,
                )

    # ── Query interface ───────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """Return the current aggregated health summary (in-memory, fast)."""
        if not self._last_results:
            return {"overall": "UNKNOWN", "engines": {}, "checked_at": None}

        status_priority = {"CRITICAL": 0, "UNKNOWN": 1, "DEGRADED": 2, "HEALTHY": 3}
        worst = min(
            self._last_results.values(),
            key=lambda r: status_priority.get(r.status, 4),
        )

        return {
            "overall": worst.status,
            "engines": {
                name: {
                    "status": r.status,
                    "error": r.error,
                    "details": r.details,
                }
                for name, r in self._last_results.items()
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_once(self) -> dict:
        """Run all checks now (blocking) and return summary. For on-demand use."""
        await self._run_all_checks()
        return self.get_summary()


# Module-level singleton
_aggregator: HealthAggregator | None = None


def get_health_aggregator() -> HealthAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = HealthAggregator()
    return _aggregator
