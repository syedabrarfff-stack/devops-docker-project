"""Tests for K2-2: SyncProtocol — read-after-write consistency."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.kernel.sync_protocol import SyncProtocol


class TestRecordAndCommit:
    def test_record_write_increments_epoch(self):
        sp = SyncProtocol()
        e1 = sp.record_write("memory", "market_position")
        e2 = sp.record_write("memory", "market_position")
        assert e2 == e1 + 1

    def test_record_write_different_keys_independent(self):
        sp = SyncProtocol()
        e1 = sp.record_write("memory", "key_a")
        e2 = sp.record_write("memory", "key_b")
        assert e1 == 1
        assert e2 == 1   # separate counters

    @pytest.mark.asyncio
    async def test_commit_updates_epoch(self):
        sp = SyncProtocol()
        epoch = sp.record_write("bi_engine", "report")
        await sp.commit("bi_engine", "report", epoch)
        assert sp.current_epoch("bi_engine", "report") == epoch

    @pytest.mark.asyncio
    async def test_commit_ignores_stale_epoch(self):
        sp = SyncProtocol()
        e1 = sp.record_write("e", "k")
        e2 = sp.record_write("e", "k")
        await sp.commit("e", "k", e2)  # commit the newer one
        await sp.commit("e", "k", e1)  # older should be a no-op
        assert sp.current_epoch("e", "k") == e2


class TestWaitFor:
    @pytest.mark.asyncio
    async def test_wait_already_committed(self):
        sp = SyncProtocol()
        epoch = sp.record_write("eng", "key")
        await sp.commit("eng", "key", epoch)
        # Should return immediately — no blocking
        result = await asyncio.wait_for(
            sp.wait_for("eng", "key", min_epoch=epoch), timeout=1.0
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_unblocked_by_commit(self):
        sp = SyncProtocol()
        epoch = sp.record_write("eng", "key")

        async def delayed_commit():
            await asyncio.sleep(0.05)
            await sp.commit("eng", "key", epoch)

        task = asyncio.create_task(delayed_commit())
        result = await sp.wait_for("eng", "key", min_epoch=epoch, timeout=1.0)
        await task
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_timeout_returns_false(self):
        sp = SyncProtocol()
        # Never commit epoch 99
        result = await sp.wait_for("eng", "missing", min_epoch=99, timeout=0.05)
        assert result is False

    @pytest.mark.asyncio
    async def test_snapshot_returns_all_epochs(self):
        sp = SyncProtocol()
        e = sp.record_write("a", "x")
        await sp.commit("a", "x", e)
        snap = await sp.snapshot()
        assert "a:x" in snap
        assert snap["a:x"] == e
