"""K2-2: Sync Protocol — read-after-write consistency between engines.

Problem: Engine A writes to DB, then Engine B immediately reads — it may get
stale data if the write hasn't propagated (replica lag, cache staleness, etc.).

Solution: Each engine that writes increments a logical clock for that
(engine, key) pair. Before reading, an engine can call `wait_for_version` to
block until the writer's version is visible. The Sync Protocol coordinates this
through Event Bus notifications rather than busy-polling.

Terminology:
  write_epoch  — monotonic counter per (engine, key) that the writer increments
  sync_event   — 'sync.write_committed' event published to Event Bus
  barrier      — asyncio.Event that unblocks waiters when a version arrives

Architecture:
    Writer:
        epoch = sync.record_write("memory_engine", "market_position")
        # ... do the DB write ...
        await sync.commit("memory_engine", "market_position", epoch)

    Reader (in another engine):
        await sync.wait_for("memory_engine", "market_position", min_epoch=epoch)
        result = await db.read(...)   # guaranteed fresh
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from app.services.kernel.event_bus import get_event_bus

log = logging.getLogger(__name__)

_sync: Optional["SyncProtocol"] = None

_RAW_EPOCH: dict[tuple[str, str], int] = defaultdict(int)   # (engine, key) → epoch


@dataclass
class SyncEntry:
    engine: str
    key: str
    epoch: int
    committed_at: float = field(default_factory=time.monotonic)


class SyncProtocol:
    """Coordinate read-after-write consistency across JARVIS engines.

    Thread/task-safe: internal state is protected by an asyncio.Lock.
    The event bus is used to notify cross-engine waiters; local waiters
    use asyncio.Event for zero-overhead unblocking.
    """

    DEFAULT_TIMEOUT = 2.0   # seconds; overridden by config_service in practice

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # (engine, key) → current committed epoch
        self._epochs: dict[tuple[str, str], int] = defaultdict(int)
        # (engine, key, min_epoch) → set of asyncio.Event waiting for that epoch
        self._waiters: dict[tuple[str, str, int], list[asyncio.Event]] = defaultdict(list)

    # ── Writer side ───────────────────────────────────────────────────────

    def record_write(self, engine: str, key: str) -> int:
        """Increment and return the next write epoch for (engine, key).

        Call BEFORE performing the DB write so the epoch is allocated
        before any reader can race.
        """
        _RAW_EPOCH[(engine, key)] += 1
        epoch = _RAW_EPOCH[(engine, key)]
        log.debug("sync.record_write engine=%s key=%s epoch=%d", engine, key, epoch)
        return epoch

    async def commit(self, engine: str, key: str, epoch: int) -> None:
        """Mark an epoch as committed and unblock all waiters at or below it."""
        async with self._lock:
            current = self._epochs[(engine, key)]
            if epoch > current:
                self._epochs[(engine, key)] = epoch
                self._unblock_waiters(engine, key, epoch)

        # Publish to Event Bus so cross-process watchers also get notified.
        try:
            bus = get_event_bus()
            await bus.emit(
                "sync.write_committed",
                payload={"engine": engine, "key": key, "epoch": epoch},
                source_engine="sync_protocol",
            )
        except Exception:
            log.debug("sync.commit: event bus unavailable (local unblock succeeded)")

    # ── Reader side ───────────────────────────────────────────────────────

    async def wait_for(
        self,
        engine: str,
        key: str,
        min_epoch: int,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """Block until (engine, key) has been committed at >= min_epoch.

        Returns True if the epoch arrived in time, False on timeout.
        """
        async with self._lock:
            if self._epochs[(engine, key)] >= min_epoch:
                return True   # already visible
            event = asyncio.Event()
            self._waiters[(engine, key, min_epoch)].append(event)

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            async with self._lock:
                lst = self._waiters.get((engine, key, min_epoch), [])
                try:
                    lst.remove(event)
                except ValueError:
                    pass
            log.warning(
                "sync.wait_for timeout engine=%s key=%s min_epoch=%d timeout=%.1fs",
                engine, key, min_epoch, timeout,
            )
            return False

    def current_epoch(self, engine: str, key: str) -> int:
        """Return the latest committed epoch for (engine, key) — 0 if unknown."""
        return self._epochs[(engine, key)]

    async def snapshot(self) -> dict[str, int]:
        """Return a copy of all current (engine, key) epochs for observability."""
        async with self._lock:
            return {f"{e}:{k}": v for (e, k), v in self._epochs.items()}

    # ── Internal ──────────────────────────────────────────────────────────

    def _unblock_waiters(self, engine: str, key: str, up_to_epoch: int) -> None:
        """Must be called inside self._lock. Unblocks all waiters <= up_to_epoch."""
        to_remove = []
        for (e, k, min_ep), events in self._waiters.items():
            if e == engine and k == key and min_ep <= up_to_epoch:
                for ev in events:
                    ev.set()
                to_remove.append((e, k, min_ep))
        for key_tuple in to_remove:
            del self._waiters[key_tuple]


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_sync_protocol() -> SyncProtocol:
    global _sync
    if _sync is None:
        _sync = SyncProtocol()
    return _sync
