"""K1-4: JARVIS Kernel Event Bus — Redis pub/sub with typed events.

Every engine in the system communicates through this bus rather than calling
each other directly. This decouples producers from consumers, making every
engine independently restartable and testable.

Standard event types (producers / subscribers):
  decision.made       — Decision Intelligence Engine / any interested engine
  decision.approved   — Policy Engine / Kernel Task Queue
  verification.passed — Verification Engine / Audit Logger
  verification.failed — Verification Engine / Retry Coordinator + Captain Bridge
  alert.budget        — Token Governor / Budget Intelligence Engine + Captain
  health.degraded     — Health Aggregator / Failover Controller + Retry Coordinator
  health.critical     — Health Aggregator / Override Controller + Captain Bridge
  task.completed      — Task Queue / Dependent engines
  task.failed         — Task Queue / Retry Coordinator
  override.pause      — Override Controller / All engines
  override.shutdown   — Override Controller / All engines

Usage:
    bus = EventBus()
    await bus.publish(KernelEvent(event_type="decision.made", payload={"id": "..."}))
    async for event in bus.subscribe("decision.made", "alert.budget"):
        handle(event)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator

log = logging.getLogger(__name__)

# Channel prefix so kernel events never collide with other Redis keys.
_CHANNEL_PREFIX = "jarvis:kernel:events:"


@dataclass
class KernelEvent:
    event_type: str
    source_engine: str = "kernel"
    payload: dict = field(default_factory=dict)
    # Set by the bus on publish; callers may leave as None.
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_engine": self.source_engine,
            "payload": self.payload,
            "created_at": self.created_at,
        })

    @classmethod
    def from_json(cls, raw: str) -> "KernelEvent":
        data = json.loads(raw)
        return cls(
            event_type=data["event_type"],
            source_engine=data.get("source_engine", "unknown"),
            payload=data.get("payload", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class EventBus:
    """Async Redis pub/sub event bus for the JARVIS v4 Kernel.

    Lifecycle:
        bus = EventBus()
        # Use publish / subscribe. The bus lazily creates a Redis connection.
        # Call bus.close() on shutdown or use as async context manager.

    Note: every EventBus instance owns its own Redis connection(s). For a
    long-lived singleton, create one per process and share it.
    """

    def __init__(self) -> None:
        self._publish_client = None
        self._lock = asyncio.Lock()

    # ── Redis client management ───────────────────────────────────────────────

    async def _get_client(self):
        """Return (or lazily create) the publish-side Redis client."""
        if self._publish_client is not None:
            return self._publish_client

        async with self._lock:
            if self._publish_client is not None:
                return self._publish_client

            try:
                import redis.asyncio as aioredis
                from app.core.config import settings

                url = settings.REDIS_URL or "redis://localhost:6379"
                self._publish_client = aioredis.from_url(
                    url,
                    socket_connect_timeout=3,
                    decode_responses=True,
                )
                await self._publish_client.ping()
                log.debug("EventBus: Redis client connected (%s)", url)
            except Exception as exc:
                self._publish_client = None
                raise RuntimeError(f"EventBus: Redis unavailable — {exc}") from exc

        return self._publish_client

    async def close(self) -> None:
        """Close the publish client; safe to call multiple times."""
        if self._publish_client is not None:
            try:
                await self._publish_client.aclose()
            except Exception:
                pass
            self._publish_client = None

    # ── Publish ───────────────────────────────────────────────────────────────

    async def publish(self, event: KernelEvent) -> int:
        """Publish event to all subscribers. Returns subscriber count."""
        channel = _CHANNEL_PREFIX + event.event_type
        client = await self._get_client()
        try:
            count = await client.publish(channel, event.to_json())
            log.debug("EventBus: published %s → %d subscribers", event.event_type, count)
            return count
        except Exception as exc:
            log.error("EventBus: publish failed (%s): %s", event.event_type, exc)
            raise

    async def publish_many(self, events: list[KernelEvent]) -> None:
        """Publish multiple events in a pipeline for efficiency."""
        if not events:
            return
        client = await self._get_client()
        pipe = client.pipeline()
        for evt in events:
            pipe.publish(_CHANNEL_PREFIX + evt.event_type, evt.to_json())
        try:
            await pipe.execute()
        except Exception as exc:
            log.error("EventBus: pipeline publish failed: %s", exc)
            raise

    # ── Subscribe ─────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def subscribe(self, *event_types: str) -> AsyncIterator[AsyncIterator[KernelEvent]]:
        """Async context manager that yields an async iterator of KernelEvents.

        Usage:
            async with bus.subscribe("decision.made", "alert.budget") as events:
                async for event in events:
                    await handle(event)
        """
        import redis.asyncio as aioredis
        from app.core.config import settings

        url = settings.REDIS_URL or "redis://localhost:6379"
        sub_client = aioredis.from_url(url, socket_connect_timeout=3, decode_responses=True)

        channels = [_CHANNEL_PREFIX + et for et in event_types]
        pubsub = sub_client.pubsub()
        await pubsub.subscribe(*channels)

        async def _iter() -> AsyncIterator[KernelEvent]:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    yield KernelEvent.from_json(message["data"])
                except Exception as exc:
                    log.warning("EventBus: failed to parse message: %s", exc)

        try:
            yield _iter()
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()
            await sub_client.aclose()

    # ── Convenience helpers ───────────────────────────────────────────────────

    async def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        source_engine: str = "kernel",
    ) -> int:
        """Shorthand for publish without constructing KernelEvent manually."""
        return await self.publish(KernelEvent(
            event_type=event_type,
            source_engine=source_engine,
            payload=payload or {},
        ))


# Module-level singleton — import and use directly in services.
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the process-level EventBus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


async def shutdown_event_bus() -> None:
    """Call during application shutdown to close Redis connections."""
    global _bus
    if _bus is not None:
        await _bus.close()
        _bus = None
