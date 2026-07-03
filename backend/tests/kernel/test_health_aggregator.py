"""Tests for K1-7: HealthAggregator — check registration, status aggregation."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.kernel.health_aggregator import (
    EngineHealthResult,
    HealthAggregator,
)


@pytest.mark.asyncio
async def test_empty_summary():
    agg = HealthAggregator()
    summary = agg.get_summary()
    assert summary["overall"] == "UNKNOWN"
    assert summary["engines"] == {}


@pytest.mark.asyncio
async def test_register_and_check():
    agg = HealthAggregator()

    async def healthy_check():
        return {"status": "HEALTHY", "latency_ms": 12}

    agg.register("ai_router", healthy_check)

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    summary = agg.get_summary()
    assert summary["overall"] == "HEALTHY"
    assert "ai_router" in summary["engines"]
    assert summary["engines"]["ai_router"]["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_degraded_propagates_to_overall():
    agg = HealthAggregator()

    async def healthy():
        return {"status": "HEALTHY"}

    async def degraded():
        return {"status": "DEGRADED"}

    agg.register("engine_a", healthy)
    agg.register("engine_b", degraded)

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    summary = agg.get_summary()
    assert summary["overall"] == "DEGRADED"


@pytest.mark.asyncio
async def test_critical_beats_degraded():
    agg = HealthAggregator()

    async def degraded():
        return {"status": "DEGRADED"}

    async def critical():
        return {"status": "CRITICAL"}

    agg.register("engine_a", degraded)
    agg.register("engine_b", critical)

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    summary = agg.get_summary()
    assert summary["overall"] == "CRITICAL"


@pytest.mark.asyncio
async def test_timeout_marks_unknown():
    agg = HealthAggregator()
    agg.CHECK_TIMEOUT = 0.01  # 10ms

    async def slow_check():
        await asyncio.sleep(1.0)
        return {"status": "HEALTHY"}

    agg.register("slow_engine", slow_check)

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    summary = agg.get_summary()
    assert summary["engines"]["slow_engine"]["status"] == "UNKNOWN"
    assert "timed out" in summary["engines"]["slow_engine"]["error"]


@pytest.mark.asyncio
async def test_exception_marks_unknown():
    agg = HealthAggregator()

    async def crashing_check():
        raise ConnectionRefusedError("redis down")

    agg.register("redis", crashing_check)

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    assert agg._last_results["redis"].status == "UNKNOWN"


@pytest.mark.asyncio
async def test_deregister():
    agg = HealthAggregator()

    async def healthy():
        return {"status": "HEALTHY"}

    agg.register("engine", healthy)
    agg.deregister("engine")

    with patch.object(agg, "_persist_and_publish", new_callable=AsyncMock):
        await agg._run_all_checks()

    # Nothing was checked
    assert agg._last_results == {}
