"""K2-5: Failover Controller — deep health → DR switch logic.

Monitors the HealthAggregator continuously. If overall system health remains
CRITICAL for longer than the configured threshold (default 60s), the Failover
Controller:
  1. Publishes a 'failover.triggered' Event Bus event
  2. Notifies Captain via Telegram (non-blocking)
  3. Records a decision_record with full evidence
  4. Optionally enqueues a 'failover.switch_dr' task to the Task Queue

Authority: Autonomous DR switch is ASK_CAPTAIN tier — the controller raises
the alert and prepares the switch but does NOT execute it without explicit
Captain command (per §2.1 of the architecture).

Config keys (via ConfigService):
  health.critical_threshold_seconds   — seconds of CRITICAL before alert (default 60)
  feature.failover_auto_switch        — if True, auto-enqueue switch task (default False)

Usage:
    fc = get_failover_controller()
    await fc.start()
    # Runs in background, monitoring HealthAggregator
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)

_fc: Optional["FailoverController"] = None


class FailoverState(str, Enum):
    NOMINAL = "NOMINAL"        # primary healthy
    DEGRADED = "DEGRADED"      # some services unhealthy but not critical
    CRITICAL = "CRITICAL"      # primary critical — timer running
    ALERTING = "ALERTING"      # threshold exceeded — Captain notified, awaiting command
    SWITCHING = "SWITCHING"    # DR switch in progress (only with auto_switch=True)
    DR_ACTIVE = "DR_ACTIVE"    # running on DR region


@dataclass
class FailoverEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: FailoverState = FailoverState.NOMINAL
    overall_health: str = "UNKNOWN"
    critical_since: Optional[float] = None
    critical_duration_s: float = 0.0
    triggered_at: Optional[datetime] = None
    evidence: dict = field(default_factory=dict)


class FailoverController:
    """Monitor health and trigger DR failover recommendation when threshold crossed.

    Polling interval matches the HealthAggregator (30s). The CRITICAL timer
    starts when overall health first becomes CRITICAL and resets on recovery.
    """

    MONITOR_INTERVAL = 30   # seconds between health checks

    def __init__(self) -> None:
        self._state = FailoverState.NOMINAL
        self._critical_since: Optional[float] = None
        self._last_event: Optional[FailoverEvent] = None
        self._alert_sent = False          # prevent duplicate alerts per incident
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def state(self) -> FailoverState:
        return self._state

    async def status(self) -> dict:
        """Serialisable status for the Ops Dashboard."""
        async with self._lock:
            now = time.monotonic()
            crit_duration = 0.0
            if self._critical_since is not None:
                crit_duration = now - self._critical_since
            return {
                "state": self._state.value,
                "critical_since_s": round(crit_duration, 1) if self._critical_since else None,
                "alert_sent": self._alert_sent,
                "last_event": (
                    {
                        "event_id": self._last_event.event_id,
                        "overall_health": self._last_event.overall_health,
                        "triggered_at": self._last_event.triggered_at.isoformat()
                        if self._last_event.triggered_at else None,
                    }
                    if self._last_event else None
                ),
            }

    async def start(self) -> None:
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(
                self._monitor_loop(), name="failover-monitor"
            )
            self._monitor_task.add_done_callback(self._on_done)
            log.info("failover_controller: monitor started")

    async def stop(self) -> None:
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        log.info("failover_controller: monitor stopped")

    async def acknowledge_dr_active(self) -> None:
        """Captain confirms DR is now active (called by Override Controller)."""
        async with self._lock:
            self._state = FailoverState.DR_ACTIVE
            self._alert_sent = False
            self._critical_since = None
        log.info("failover_controller: DR_ACTIVE acknowledged by Captain")

    async def acknowledge_recovery(self) -> None:
        """Reset to NOMINAL when primary is restored."""
        async with self._lock:
            self._state = FailoverState.NOMINAL
            self._critical_since = None
            self._alert_sent = False
        log.info("failover_controller: primary recovered, state=NOMINAL")

    # ── Monitor loop ──────────────────────────────────────────────────────

    async def _monitor_loop(self) -> None:
        while True:
            await asyncio.sleep(self.MONITOR_INTERVAL)
            try:
                await self._check()
            except Exception:
                log.exception("failover_controller: check error")

    async def _check(self) -> None:
        from app.services.kernel.health_aggregator import get_health_aggregator
        from app.services.kernel.config_service import get_config_service

        aggregator = get_health_aggregator()
        summary = aggregator.get_summary()
        overall = summary.get("overall", "UNKNOWN")

        cfg = get_config_service()
        threshold = await cfg.get_float("health.critical_threshold_seconds", 60.0)
        auto_switch = await cfg.get_bool("feature.failover_auto_switch", False)

        now = time.monotonic()

        async with self._lock:
            if overall == "CRITICAL":
                if self._critical_since is None:
                    self._critical_since = now
                    self._state = FailoverState.CRITICAL
                    log.warning("failover_controller: CRITICAL state detected, timer started")

                elapsed = now - self._critical_since
                if elapsed >= threshold and not self._alert_sent:
                    self._state = FailoverState.ALERTING
                    event = FailoverEvent(
                        state=FailoverState.ALERTING,
                        overall_health=overall,
                        critical_since=self._critical_since,
                        critical_duration_s=elapsed,
                        triggered_at=datetime.now(timezone.utc),
                        evidence=summary,
                    )
                    self._last_event = event
                    self._alert_sent = True
                    # Publish and notify outside the lock
                    asyncio.create_task(
                        self._trigger_failover_alert(event, auto_switch),
                        name="failover-alert",
                    ).add_done_callback(
                        lambda t: log.error("failover-alert error: %s", t.exception()) if not t.cancelled() and t.exception() else None
                    )

            elif overall in ("HEALTHY", "DEGRADED"):
                if self._critical_since is not None:
                    log.info(
                        "failover_controller: health recovered (was CRITICAL for %.0fs), state=NOMINAL",
                        now - self._critical_since,
                    )
                self._critical_since = None
                self._alert_sent = False
                if self._state not in (FailoverState.DR_ACTIVE, FailoverState.SWITCHING):
                    self._state = (
                        FailoverState.DEGRADED if overall == "DEGRADED" else FailoverState.NOMINAL
                    )

    async def _trigger_failover_alert(self, event: FailoverEvent, auto_switch: bool) -> None:
        log.critical(
            "FAILOVER ALERT: JARVIS primary CRITICAL for %.0fs. auto_switch=%s",
            event.critical_duration_s, auto_switch,
        )

        # 1. Event Bus
        try:
            from app.services.kernel.event_bus import get_event_bus
            bus = get_event_bus()
            await bus.emit(
                "failover.triggered",
                payload={
                    "event_id": event.event_id,
                    "critical_duration_s": event.critical_duration_s,
                    "evidence": event.evidence,
                    "auto_switch": auto_switch,
                },
                source_engine="failover_controller",
            )
        except Exception:
            log.exception("failover_controller: event bus publish failed")

        # 2. Captain notification (Telegram)
        try:
            from app.services.kernel.override_controller import _notify_captain  # type: ignore
            msg = (
                f"🚨 *FAILOVER ALERT*\n"
                f"Primary region has been CRITICAL for {event.critical_duration_s:.0f}s.\n"
                f"Auto-switch: {'ENABLED' if auto_switch else 'disabled (manual action required)'}.\n"
                f"Event ID: `{event.event_id}`\n"
                f"Evidence: {list(event.evidence.get('engines', {}).keys())}"
            )
            await _notify_captain(msg)
        except Exception:
            log.exception("failover_controller: captain notification failed")

        # 3. Auto-switch: enqueue task if configured
        if auto_switch:
            try:
                from app.services.kernel.task_queue import TaskQueue, Priority
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    tq = TaskQueue(session)
                    await tq.enqueue(
                        payload={
                            "action": "failover.switch_dr",
                            "event_id": event.event_id,
                            "initiated_by": "failover_controller",
                        },
                        priority=Priority.CRITICAL,
                    )
                    log.critical("failover_controller: DR switch task enqueued (auto_switch=True)")
            except Exception:
                log.exception("failover_controller: failed to enqueue DR switch task")

    def _on_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            exc = task.exception()
            if exc:
                log.error("failover_controller: monitor loop exited with error: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_failover_controller() -> FailoverController:
    global _fc
    if _fc is None:
        _fc = FailoverController()
    return _fc
