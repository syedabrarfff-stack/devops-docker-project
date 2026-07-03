"""Tests for K1-4: EventBus — typed events, pub/sub, singleton."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kernel.event_bus import (
    EventBus,
    KernelEvent,
    get_event_bus,
    shutdown_event_bus,
)


# ── KernelEvent serialisation ─────────────────────────────────────────────────

class TestKernelEventSerialisation:
    def test_to_json_roundtrip(self):
        evt = KernelEvent(
            event_type="decision.made",
            source_engine="decision_engine",
            payload={"decision_id": "abc-123"},
        )
        raw = evt.to_json()
        restored = KernelEvent.from_json(raw)

        assert restored.event_type == evt.event_type
        assert restored.source_engine == evt.source_engine
        assert restored.payload == evt.payload
        assert restored.event_id == evt.event_id

    def test_from_json_partial(self):
        """Missing optional fields should not raise."""
        raw = json.dumps({"event_type": "alert.budget", "source_engine": "governor"})
        evt = KernelEvent.from_json(raw)
        assert evt.event_type == "alert.budget"
        assert evt.payload == {}
        assert evt.event_id  # auto-generated UUID

    def test_auto_fields(self):
        e1 = KernelEvent(event_type="x")
        e2 = KernelEvent(event_type="x")
        assert e1.event_id != e2.event_id   # unique per instance
        assert e1.created_at                 # non-empty


# ── EventBus.publish ──────────────────────────────────────────────────────────

class TestEventBusPublish:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        """publish() returns the subscriber count from Redis."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=2)

        bus = EventBus()
        bus._publish_client = mock_redis

        event = KernelEvent(event_type="decision.made", payload={"id": "1"})
        count = await bus.publish(event)

        assert count == 2
        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        assert channel == "jarvis:kernel:events:decision.made"

    @pytest.mark.asyncio
    async def test_emit_shorthand(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        bus = EventBus()
        bus._publish_client = mock_redis

        count = await bus.emit("alert.budget", payload={"pct": 80})

        assert count == 1
        channel = mock_redis.publish.call_args[0][0]
        assert channel == "jarvis:kernel:events:alert.budget"

    @pytest.mark.asyncio
    async def test_publish_many_uses_pipeline(self):
        # Use MagicMock (not AsyncMock) for pipeline.publish — Redis pipelines
        # queue commands synchronously; only .execute() is awaited.
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[1, 1])

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        bus = EventBus()
        bus._publish_client = mock_redis

        events = [
            KernelEvent(event_type="decision.made"),
            KernelEvent(event_type="verification.passed"),
        ]
        await bus.publish_many(events)

        mock_redis.pipeline.assert_called_once()
        assert mock_pipe.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_many_noop_on_empty(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        bus = EventBus()
        bus._publish_client = mock_redis
        await bus.publish_many([])
        mock_redis.pipeline.assert_not_called()


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSingleton:
    @pytest.mark.asyncio
    async def test_get_event_bus_returns_same_instance(self):
        import app.services.kernel.event_bus as eb_module
        eb_module._bus = None  # reset

        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2

    @pytest.mark.asyncio
    async def test_shutdown_clears_singleton(self):
        import app.services.kernel.event_bus as eb_module

        bus = EventBus()
        bus._publish_client = AsyncMock()
        bus._publish_client.aclose = AsyncMock()
        eb_module._bus = bus

        await shutdown_event_bus()
        assert eb_module._bus is None
