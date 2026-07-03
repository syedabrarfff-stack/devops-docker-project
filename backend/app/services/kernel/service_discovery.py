"""K2-3: Service Discovery — engine registry with heartbeat-based liveness.

Every JARVIS engine (Decision, Memory, BI, Budget, Scheduler, …) registers
itself on startup by calling `register()`. Periodic `heartbeat()` calls keep
the entry alive. If an engine misses HEARTBEAT_TIMEOUT seconds of heartbeats
it is marked UNAVAILABLE — other subsystems and the Ops Dashboard can react.

This is the *single source of truth* for what engines are running. The Plugin
Loader (K2-4) builds on top of this registry when loading pluggable engines.

Usage:
    disc = get_service_discovery()
    disc.register("ai_router", version="2.3.1", capabilities=["llm", "routing"])
    disc.heartbeat("ai_router")         # call every ~10s from the engine
    alive = disc.list_alive()           # → ["ai_router", ...]
    info  = disc.get("ai_router")       # → ServiceRecord
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)

_disc: Optional["ServiceDiscovery"] = None


class EngineStatus(str, Enum):
    ALIVE = "ALIVE"
    UNAVAILABLE = "UNAVAILABLE"
    DRAINING = "DRAINING"    # registered but intentionally winding down


@dataclass
class ServiceRecord:
    name: str
    version: str = "unknown"
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    status: EngineStatus = EngineStatus.ALIVE
    registered_at: float = field(default_factory=time.monotonic)
    last_heartbeat: float = field(default_factory=time.monotonic)


class ServiceDiscovery:
    """In-memory engine registry with TTL-based liveness.

    Designed for single-process JARVIS. When JARVIS goes multi-process the
    backing store can be swapped to Redis without changing the public API.
    """

    HEARTBEAT_TIMEOUT = 90   # seconds — engine considered UNAVAILABLE after this
    REAP_INTERVAL = 30       # seconds between background reaper runs

    def __init__(self) -> None:
        self._registry: dict[str, ServiceRecord] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task] = None

    # ── Registration ──────────────────────────────────────────────────────

    async def register(
        self,
        name: str,
        version: str = "unknown",
        capabilities: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> ServiceRecord:
        """Register (or re-register) an engine. Idempotent."""
        async with self._lock:
            now = time.monotonic()
            if name in self._registry:
                rec = self._registry[name]
                rec.status = EngineStatus.ALIVE
                rec.version = version
                rec.capabilities = capabilities or []
                rec.metadata = metadata or {}
                rec.last_heartbeat = now
                log.info("service_discovery.re-register name=%s", name)
            else:
                rec = ServiceRecord(
                    name=name,
                    version=version,
                    capabilities=capabilities or [],
                    metadata=metadata or {},
                )
                self._registry[name] = rec
                log.info("service_discovery.register name=%s version=%s", name, version)
        return rec

    async def deregister(self, name: str) -> bool:
        """Remove an engine from the registry. Returns True if it existed."""
        async with self._lock:
            existed = name in self._registry
            self._registry.pop(name, None)
        if existed:
            log.info("service_discovery.deregister name=%s", name)
        return existed

    async def drain(self, name: str) -> bool:
        """Mark an engine as DRAINING (winding down gracefully)."""
        async with self._lock:
            if name not in self._registry:
                return False
            self._registry[name].status = EngineStatus.DRAINING
        log.info("service_discovery.drain name=%s", name)
        return True

    # ── Heartbeat ─────────────────────────────────────────────────────────

    async def heartbeat(self, name: str) -> bool:
        """Update last_heartbeat for *name*. Returns False if not registered."""
        async with self._lock:
            if name not in self._registry:
                return False
            rec = self._registry[name]
            rec.last_heartbeat = time.monotonic()
            if rec.status == EngineStatus.UNAVAILABLE:
                rec.status = EngineStatus.ALIVE
                log.info("service_discovery.recovered name=%s", name)
        return True

    # ── Queries ───────────────────────────────────────────────────────────

    async def get(self, name: str) -> Optional[ServiceRecord]:
        async with self._lock:
            return self._registry.get(name)

    async def is_alive(self, name: str) -> bool:
        async with self._lock:
            rec = self._registry.get(name)
            if rec is None:
                return False
            return rec.status == EngineStatus.ALIVE and self._is_fresh(rec)

    async def list_alive(self) -> list[str]:
        async with self._lock:
            return [
                name for name, rec in self._registry.items()
                if rec.status == EngineStatus.ALIVE and self._is_fresh(rec)
            ]

    async def list_all(self) -> list[ServiceRecord]:
        async with self._lock:
            return list(self._registry.values())

    async def snapshot(self) -> dict[str, dict]:
        """Return a serialisable dict for the Ops Dashboard."""
        async with self._lock:
            now = time.monotonic()
            return {
                name: {
                    "version": rec.version,
                    "status": rec.status.value,
                    "capabilities": rec.capabilities,
                    "registered_ago_s": round(now - rec.registered_at, 1),
                    "last_heartbeat_ago_s": round(now - rec.last_heartbeat, 1),
                    "metadata": rec.metadata,
                }
                for name, rec in self._registry.items()
            }

    # ── Background reaper ─────────────────────────────────────────────────

    async def start(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(
                self._reap_loop(), name="service-discovery-reaper"
            )
            self._reaper_task.add_done_callback(self._on_reaper_done)
            log.info("service_discovery: reaper started (timeout=%ds)", self.HEARTBEAT_TIMEOUT)

    async def stop(self) -> None:
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(self.REAP_INTERVAL)
            try:
                await self._reap()
            except Exception:
                log.exception("service_discovery: reap error")

    async def _reap(self) -> None:
        async with self._lock:
            now = time.monotonic()
            for name, rec in self._registry.items():
                if rec.status == EngineStatus.ALIVE and not self._is_fresh(rec, now):
                    rec.status = EngineStatus.UNAVAILABLE
                    log.warning(
                        "service_discovery.unavailable name=%s last_hb=%.0fs ago",
                        name, now - rec.last_heartbeat,
                    )

    def _is_fresh(self, rec: ServiceRecord, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.monotonic()
        return (t - rec.last_heartbeat) < self.HEARTBEAT_TIMEOUT

    def _on_reaper_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            exc = task.exception()
            if exc:
                log.error("service_discovery: reaper exited with error: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_service_discovery() -> ServiceDiscovery:
    global _disc
    if _disc is None:
        _disc = ServiceDiscovery()
    return _disc
