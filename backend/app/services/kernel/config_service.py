"""K2-1: Config Service — feature flags, dynamic thresholds, hot-reload.

Captain can change any runtime behaviour (feature flags, thresholds, routing
weights) by writing to the kernel_config table. The in-memory cache refreshes
every RELOAD_INTERVAL seconds so the change takes effect without a redeploy.

Value schema: every config entry stores its value as a JSON object with a
`v` key holding the actual typed value, e.g. `{"v": true}` or `{"v": 0.8}`.
This allows JSONB columns to hold any scalar type uniformly.

Usage:
    cfg = get_config_service()
    enabled = await cfg.get_bool("feature.failover_auto_switch", default=False)
    threshold = await cfg.get_float("health.degraded_threshold", default=0.7)
    await cfg.set("feature.failover_auto_switch", True, updated_by="captain")
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.kernel import KernelConfig

log = logging.getLogger(__name__)

_cfg: Optional["ConfigService"] = None

# Built-in defaults — used when key is missing from DB.
_DEFAULTS: dict[str, Any] = {
    "feature.failover_auto_switch": False,
    "feature.council_required_confidence": 0.75,
    "health.degraded_threshold_seconds": 60,
    "health.critical_threshold_seconds": 120,
    "retry.default_max_retries": 3,
    "retry.default_base_delay": 1.0,
    "retry.default_max_delay": 30.0,
    "audit.enabled": True,
    "task_queue.max_depth_alert": 500,
    "ai.token_budget_alert_pct": 0.8,
    "sync.read_after_write_timeout_ms": 2000,
    "plugin.hot_reload_enabled": False,
}


class ConfigService:
    """DB-backed runtime config with in-memory cache and background hot-reload.

    All values are stored as ``{"v": <typed_value>}`` in the JSONB column so
    that booleans, floats, ints, strings, and dicts all round-trip correctly.
    """

    RELOAD_INTERVAL = 60  # seconds between background cache refreshes

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._factory = session_factory
        self._cache: dict[str, Any] = dict(_DEFAULTS)  # key → typed value
        self._cache_loaded_at: float = 0.0
        self._lock = asyncio.Lock()
        self._poll_task: Optional[asyncio.Task] = None

    # ── Read ──────────────────────────────────────────────────────────────

    async def get(self, key: str, default: Any = None) -> Any:
        """Return the typed value for *key*, loading from cache."""
        await self._ensure_loaded()
        return self._cache.get(key, _DEFAULTS.get(key, default))

    async def get_bool(self, key: str, default: bool = False) -> bool:
        v = await self.get(key, default)
        return bool(v)

    async def get_float(self, key: str, default: float = 0.0) -> float:
        v = await self.get(key, default)
        return float(v)

    async def get_int(self, key: str, default: int = 0) -> int:
        v = await self.get(key, default)
        return int(v)

    async def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the full merged cache."""
        await self._ensure_loaded()
        return dict(self._cache)

    # ── Write ─────────────────────────────────────────────────────────────

    async def set(self, key: str, value: Any, updated_by: str = "system") -> None:
        """Upsert *key* → *value* in DB and invalidate cache."""
        async with self._factory() as session:
            stmt = (
                pg_insert(KernelConfig)
                .values(key=key, value={"v": value}, updated_by=updated_by)
                .on_conflict_do_update(
                    index_elements=["key"],
                    set_={
                        "value": {"v": value},
                        "updated_by": updated_by,
                        "version": KernelConfig.version + 1,
                        "updated_at": text("now()"),
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
        async with self._lock:
            self._cache[key] = value
        log.info("config.set key=%s updated_by=%s", key, updated_by)

    async def delete(self, key: str, updated_by: str = "system") -> bool:
        """Remove a key from DB and cache. Returns True if key existed."""
        async with self._factory() as session:
            result = await session.execute(
                delete(KernelConfig).where(KernelConfig.key == key)
            )
            await session.commit()
            deleted = result.rowcount > 0
        async with self._lock:
            self._cache.pop(key, None)
        if deleted:
            log.info("config.delete key=%s updated_by=%s", key, updated_by)
        return deleted

    # ── Reload ────────────────────────────────────────────────────────────

    async def reload(self) -> int:
        """Force a full reload from DB. Returns number of entries loaded."""
        async with self._factory() as session:
            rows = (await session.execute(select(KernelConfig))).scalars().all()
        async with self._lock:
            # Start from built-in defaults, then overlay DB values.
            merged = dict(_DEFAULTS)
            for row in rows:
                raw = row.value
                # Support both {"v": x} envelope and bare values.
                merged[row.key] = raw.get("v", raw) if isinstance(raw, dict) and "v" in raw else raw
            self._cache = merged
            self._cache_loaded_at = time.monotonic()
        log.debug("config.reload loaded=%d keys", len(rows))
        return len(rows)

    # ── Background hot-reload loop ────────────────────────────────────────

    async def start(self) -> None:
        """Begin background polling loop. Call once at application startup."""
        await self.reload()
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._poll_loop(), name="config-hot-reload")
            self._poll_task.add_done_callback(self._on_poll_done)
            log.info("config_service: hot-reload loop started (interval=%ds)", self.RELOAD_INTERVAL)

    async def stop(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        log.info("config_service: hot-reload loop stopped")

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.RELOAD_INTERVAL)
            try:
                await self.reload()
            except Exception:
                log.exception("config_service: reload error (cache retained)")

    def _on_poll_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            exc = task.exception()
            if exc:
                log.error("config_service: poll loop exited with error: %s", exc)

    # ── Internal ──────────────────────────────────────────────────────────

    async def _ensure_loaded(self) -> None:
        if self._cache_loaded_at == 0.0:
            await self.reload()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_config_service() -> "ConfigService":
    """Return the module-level ConfigService singleton."""
    global _cfg
    if _cfg is None:
        from app.core.database import AsyncSessionLocal
        _cfg = ConfigService(AsyncSessionLocal)
    return _cfg


async def shutdown_config_service() -> None:
    global _cfg
    if _cfg is not None:
        await _cfg.stop()
        _cfg = None
