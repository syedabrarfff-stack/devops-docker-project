"""Tests for K2-3: ServiceDiscovery — engine registry, heartbeat, reaping."""
from __future__ import annotations

import asyncio
import pytest

from app.services.kernel.service_discovery import ServiceDiscovery, EngineStatus


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        disc = ServiceDiscovery()
        await disc.register("ai_router", version="2.0", capabilities=["llm"])
        rec = await disc.get("ai_router")
        assert rec is not None
        assert rec.name == "ai_router"
        assert rec.version == "2.0"
        assert "llm" in rec.capabilities

    @pytest.mark.asyncio
    async def test_register_idempotent(self):
        disc = ServiceDiscovery()
        await disc.register("eng", version="1.0")
        await disc.register("eng", version="1.1")
        rec = await disc.get("eng")
        assert rec.version == "1.1"   # updated

    @pytest.mark.asyncio
    async def test_deregister(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        existed = await disc.deregister("eng")
        assert existed is True
        assert await disc.get("eng") is None

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_returns_false(self):
        disc = ServiceDiscovery()
        assert await disc.deregister("nope") is False

    @pytest.mark.asyncio
    async def test_drain(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        ok = await disc.drain("eng")
        assert ok is True
        rec = await disc.get("eng")
        assert rec.status == EngineStatus.DRAINING

    @pytest.mark.asyncio
    async def test_drain_nonexistent_returns_false(self):
        disc = ServiceDiscovery()
        assert await disc.drain("ghost") is False


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_updates_timestamp(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        import time
        before = time.monotonic()
        result = await disc.heartbeat("eng")
        assert result is True
        rec = await disc.get("eng")
        assert rec.last_heartbeat >= before

    @pytest.mark.asyncio
    async def test_heartbeat_unknown_engine_returns_false(self):
        disc = ServiceDiscovery()
        assert await disc.heartbeat("ghost") is False

    @pytest.mark.asyncio
    async def test_heartbeat_revives_unavailable(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        rec = disc._registry["eng"]
        rec.status = EngineStatus.UNAVAILABLE
        await disc.heartbeat("eng")
        assert rec.status == EngineStatus.ALIVE


class TestLiveness:
    @pytest.mark.asyncio
    async def test_is_alive_true_for_fresh_engine(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        assert await disc.is_alive("eng") is True

    @pytest.mark.asyncio
    async def test_is_alive_false_for_unknown(self):
        disc = ServiceDiscovery()
        assert await disc.is_alive("nope") is False

    @pytest.mark.asyncio
    async def test_list_alive_excludes_stale(self):
        import time
        disc = ServiceDiscovery()
        await disc.register("alive")
        await disc.register("stale")
        # Simulate stale heartbeat
        disc._registry["stale"].last_heartbeat = time.monotonic() - disc.HEARTBEAT_TIMEOUT - 10
        alive = await disc.list_alive()
        assert "alive" in alive
        assert "stale" not in alive

    @pytest.mark.asyncio
    async def test_snapshot_contains_all_entries(self):
        disc = ServiceDiscovery()
        await disc.register("eng1", version="1.0")
        await disc.register("eng2", version="2.0")
        snap = await disc.snapshot()
        assert "eng1" in snap
        assert "eng2" in snap
        assert snap["eng1"]["version"] == "1.0"


class TestReaper:
    @pytest.mark.asyncio
    async def test_reap_marks_stale_unavailable(self):
        import time
        disc = ServiceDiscovery()
        await disc.register("eng")
        disc._registry["eng"].last_heartbeat = time.monotonic() - disc.HEARTBEAT_TIMEOUT - 5
        await disc._reap()
        assert disc._registry["eng"].status == EngineStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_reap_leaves_fresh_engine_alive(self):
        disc = ServiceDiscovery()
        await disc.register("eng")
        await disc._reap()
        assert disc._registry["eng"].status == EngineStatus.ALIVE
