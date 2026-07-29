"""Tests for F3-2: ModelRegistry — cache, fallback chain, status transitions."""
from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.fabric.model_registry import (
    ModelRegistry,
    ModelRegistryEntry,
    ROLE_BUILDER,
    ROLE_REVIEWER,
    _DEGRADED_THRESHOLD,
    _UNAVAILABLE_THRESHOLD,
    _CONSECUTIVE_FAIL_CAP,
)


def _make_entry(
    provider="anthropic",
    model_name="claude-sonnet",
    role=ROLE_REVIEWER,
    status="active",
) -> ModelRegistryEntry:
    return ModelRegistryEntry(
        id=uuid.uuid4(),
        provider=provider,
        model_name=model_name,
        role=role,
        status=status,
        latency_p50=0.0,
        latency_p95=0.0,
        error_rate=0.0,
        cost_per_mtok=1.0,
        availability_pct=100.0,
        last_health_check=None,
    )


class TestModelRegistryEntryRecord:
    def test_records_success(self):
        entry = _make_entry()
        entry.record(120.0, True, 100, 0.01)
        assert entry._call_count == 1
        assert entry._fail_count == 0
        assert entry.error_rate == 0.0
        assert entry.status == "active"

    def test_records_failure_increases_error_rate(self):
        entry = _make_entry()
        entry.record(120.0, False, 100, 0.01)
        assert entry._fail_count == 1
        assert entry.error_rate == 1.0   # 1/1

    def test_degrades_at_threshold(self):
        entry = _make_entry()
        for i in range(10):
            # 4 failures out of 10 = 40% > 30%
            entry.record(100.0, i >= 6, 0, 0.0)
        assert entry.status == "degraded"

    def test_unavailable_on_consecutive_fails(self):
        entry = _make_entry()
        for _ in range(_CONSECUTIVE_FAIL_CAP):
            entry.record(100.0, False, 0, 0.0)
        assert entry.status == "unavailable"

    def test_recovers_on_success_resets_consecutive(self):
        entry = _make_entry()
        for _ in range(_CONSECUTIVE_FAIL_CAP - 1):
            entry.record(100.0, False, 0, 0.0)
        # One success resets the consecutive counter.
        entry.record(100.0, True, 0, 0.0)
        assert entry._consecutive_fails == 0

    def test_latency_window_capped_at_100(self):
        entry = _make_entry()
        for i in range(200):
            entry.record(float(i), True, 0, 0.0)
        assert len(entry._latency_samples) <= 100

    def test_to_dict(self):
        entry = _make_entry()
        d = entry.to_dict()
        assert d["provider"] == "anthropic"
        assert d["model_name"] == "claude-sonnet"
        assert "status" in d
        assert "error_rate" in d


class TestModelRegistryCache:
    def test_get_returns_none_if_not_seeded(self):
        reg = ModelRegistry()
        assert reg.get("anthropic", "claude-sonnet") is None

    def test_list_active_empty_initially(self):
        reg = ModelRegistry()
        assert reg.list_active() == []

    def test_list_by_role_filters(self):
        reg = ModelRegistry()
        reg._cache[("anthropic", "claude-sonnet")] = _make_entry(role=ROLE_REVIEWER)
        reg._cache[("nvidia", "llama-4")] = _make_entry(
            provider="nvidia", model_name="llama-4", role=ROLE_BUILDER
        )
        reviewers = reg.list_by_role(ROLE_REVIEWER)
        builders = reg.list_by_role(ROLE_BUILDER)
        assert len(reviewers) == 1
        assert len(builders) == 1
        assert reviewers[0].provider == "anthropic"

    def test_list_active_excludes_unavailable(self):
        reg = ModelRegistry()
        reg._cache[("anthropic", "claude-sonnet")] = _make_entry(status="active")
        reg._cache[("openai", "gpt-4o")] = _make_entry(
            provider="openai", model_name="gpt-4o", status="unavailable"
        )
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].provider == "anthropic"

    def test_snapshot_serializes(self):
        reg = ModelRegistry()
        reg._cache[("anthropic", "claude-sonnet")] = _make_entry()
        snap = reg.snapshot()
        assert "anthropic/claude-sonnet" in snap
        assert isinstance(snap["anthropic/claude-sonnet"], dict)


class TestGetFallbackChain:
    def test_returns_list_of_tuples(self):
        reg = ModelRegistry()
        chain = reg.get_fallback_chain("general")
        assert isinstance(chain, list)
        # Each element is (provider, model_key)
        for item in chain:
            assert len(item) == 2

    def test_filters_unavailable(self):
        reg = ModelRegistry()
        # Seed one unavailable entry that might appear in ROUTING_TABLE.
        from app.services.ai.router import ROUTING_TABLE
        from app.services.ai.base_provider import TaskType
        chain_entries = ROUTING_TABLE.get(TaskType.GENERAL, [])
        if chain_entries:
            first_provider, first_model = chain_entries[0]
            reg._cache[(first_provider, first_model)] = _make_entry(
                provider=first_provider, model_name=first_model, status="unavailable"
            )
            chain = reg.get_fallback_chain("general")
            provider_model_pairs = [(p, m) for p, m in chain]
            assert (first_provider, first_model) not in provider_model_pairs

    def test_unknown_task_type_uses_general(self):
        reg = ModelRegistry()
        chain = reg.get_fallback_chain("nonexistent_task_xyz")
        # Should not raise, falls back to GENERAL
        assert isinstance(chain, list)


class TestSeed:
    @pytest.mark.asyncio
    async def test_seed_populates_cache(self):
        reg = ModelRegistry()

        # Build a session mock that returns None on scalar_one_or_none (no existing rows).
        async def mock_execute(stmt):
            m = MagicMock()
            m.scalar_one_or_none.return_value = None
            return m

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=mock_execute)
        session.add = MagicMock()
        session.commit = AsyncMock()

        count = await reg.seed(session)
        assert count > 0
        assert len(reg._cache) > 0
        assert reg._seeded is True
