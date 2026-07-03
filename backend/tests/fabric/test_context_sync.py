"""Tests for F3-5: ContextSync — transient memory snapshots and OCC merge."""
from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.fabric.context_sync import ContextSync, ContextMergeConflict


def make_sync() -> ContextSync:
    return ContextSync()


def make_session():
    """Return a mock AsyncSession with a scalar-returning execute()."""
    session = AsyncMock()
    # execute returns a result whose .scalars().all() gives an empty list by default.
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)
    return session


class TestSnapshot:
    @pytest.mark.asyncio
    async def test_creates_snapshot(self):
        sync = make_sync()
        task_id = "task-1"
        snap = await sync.snapshot(task_id, make_session())
        assert snap.task_id == task_id
        assert snap.snapshot_id is not None
        assert not snap.locked

    @pytest.mark.asyncio
    async def test_snapshot_is_stored(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        stored = sync.get_snapshot(snap.snapshot_id)
        assert stored is snap

    @pytest.mark.asyncio
    async def test_active_count_increases(self):
        sync = make_sync()
        assert sync.active_count() == 0
        await sync.snapshot("t1", make_session())
        assert sync.active_count() == 1


class TestLocking:
    @pytest.mark.asyncio
    async def test_lock_succeeds(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        ok = await sync.lock(snap.snapshot_id, "owner-A")
        assert ok is True
        assert snap.locked
        assert snap.lock_holder == "owner-A"

    @pytest.mark.asyncio
    async def test_double_lock_fails(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        await sync.lock(snap.snapshot_id, "owner-A")
        with pytest.raises(RuntimeError):
            await sync.lock(snap.snapshot_id, "owner-B")

    @pytest.mark.asyncio
    async def test_same_owner_relock_raises(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        await sync.lock(snap.snapshot_id, "owner-A")
        # asyncio.Lock raises RuntimeError even for the same holder (re-entry)
        with pytest.raises(RuntimeError):
            await sync.lock(snap.snapshot_id, "owner-A")

    @pytest.mark.asyncio
    async def test_unlock_releases(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        await sync.lock(snap.snapshot_id, "owner-A")
        ok = await sync.unlock(snap.snapshot_id, "owner-A")
        assert ok is True
        assert not snap.locked

    @pytest.mark.asyncio
    async def test_unlock_wrong_owner_raises(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        await sync.lock(snap.snapshot_id, "owner-A")
        with pytest.raises(RuntimeError):
            await sync.unlock(snap.snapshot_id, "owner-B")
        assert snap.locked

    @pytest.mark.asyncio
    async def test_lock_unknown_snapshot(self):
        sync = make_sync()
        with pytest.raises(KeyError):
            await sync.lock("does-not-exist", "owner-A")


class TestMerge:
    @pytest.mark.asyncio
    async def test_merge_returns_count(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        await sync.lock(snap.snapshot_id, "worker-1")
        # updates is dict[(layer, key) -> new_value].
        # With no matching DB rows, rowcount==0 triggers a conflict.
        # Use an empty dict so no conflicts are raised.
        merged = await sync.merge(snap.snapshot_id, {}, "worker-1", make_session())
        assert merged == 0

    @pytest.mark.asyncio
    async def test_merge_unknown_snapshot(self):
        sync = make_sync()
        with pytest.raises(KeyError):
            await sync.merge("does-not-exist", {}, "worker-1", make_session())


class TestDiscard:
    @pytest.mark.asyncio
    async def test_discard_removes_snapshot(self):
        sync = make_sync()
        snap = await sync.snapshot("t1", make_session())
        sync.discard(snap.snapshot_id)
        assert sync.get_snapshot(snap.snapshot_id) is None
        assert sync.active_count() == 0

    @pytest.mark.asyncio
    async def test_discard_unknown_is_noop(self):
        sync = make_sync()
        sync.discard("nonexistent")   # must not raise
