"""E7-10: Tests for the Work Package Dispatcher (E7-4)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.services.engineering.dispatcher import _dependencies_satisfied, dispatch_ready_packages
from app.services.kernel.authority_matrix import AuthorityTier


def _wp(status=WorkPackageStatus.PENDING, depends_on=None, authority_tier=None, operation="bug.fix"):
    return EngineeringWorkPackage(
        id=uuid.uuid4(),
        task_graph_id=uuid.uuid4(),
        department="backend",
        title="test package",
        depends_on=depends_on or [],
        status=status,
        authority_tier=authority_tier,
        operation=operation,
    )


class TestDependenciesSatisfied:
    def test_no_dependencies_is_satisfied(self):
        wp = _wp(depends_on=[])
        assert _dependencies_satisfied(wp, {}) is True

    def test_dependency_deployed_is_satisfied(self):
        dep = _wp(status=WorkPackageStatus.DEPLOYED)
        wp = _wp(depends_on=[dep.id])
        assert _dependencies_satisfied(wp, {dep.id: dep}) is True

    def test_dependency_not_deployed_is_not_satisfied(self):
        dep = _wp(status=WorkPackageStatus.IN_REVIEW)
        wp = _wp(depends_on=[dep.id])
        assert _dependencies_satisfied(wp, {dep.id: dep}) is False

    def test_missing_dependency_is_not_satisfied(self):
        wp = _wp(depends_on=[uuid.uuid4()])
        assert _dependencies_satisfied(wp, {}) is False

    def test_all_of_multiple_dependencies_must_be_deployed(self):
        dep1 = _wp(status=WorkPackageStatus.DEPLOYED)
        dep2 = _wp(status=WorkPackageStatus.IN_REVIEW)
        wp = _wp(depends_on=[dep1.id, dep2.id])
        assert _dependencies_satisfied(wp, {dep1.id: dep1, dep2.id: dep2}) is False


class TestDispatchReadyPackages:
    @pytest.mark.asyncio
    async def test_ask_captain_tier_is_blocked_not_enqueued(self):
        graph_id = uuid.uuid4()
        wp = _wp(authority_tier=AuthorityTier.ASK_CAPTAIN.value)
        wp.task_graph_id = graph_id

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [wp]))))
        db.flush = AsyncMock()

        with patch("app.services.engineering.dispatcher.TaskQueue") as MockQueue:
            MockQueue.return_value.enqueue = AsyncMock()
            counts = await dispatch_ready_packages(db, graph_id)

        assert wp.status == WorkPackageStatus.BLOCKED
        assert counts["blocked"] == 1
        assert counts["enqueued"] == 0
        MockQueue.return_value.enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_never_tier_is_blocked_not_enqueued(self):
        graph_id = uuid.uuid4()
        wp = _wp(authority_tier=AuthorityTier.NEVER.value)
        wp.task_graph_id = graph_id

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [wp]))))
        db.flush = AsyncMock()

        with patch("app.services.engineering.dispatcher.TaskQueue") as MockQueue:
            MockQueue.return_value.enqueue = AsyncMock()
            counts = await dispatch_ready_packages(db, graph_id)

        assert wp.status == WorkPackageStatus.BLOCKED
        assert counts["enqueued"] == 0

    @pytest.mark.asyncio
    async def test_auto_tier_with_satisfied_deps_is_enqueued(self):
        graph_id = uuid.uuid4()
        wp = _wp(authority_tier=AuthorityTier.AUTO.value)
        wp.task_graph_id = graph_id

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [wp]))))
        db.flush = AsyncMock()

        with patch("app.services.engineering.dispatcher.TaskQueue") as MockQueue:
            MockQueue.return_value.enqueue = AsyncMock(return_value=uuid.uuid4())
            counts = await dispatch_ready_packages(db, graph_id)

        assert wp.status == WorkPackageStatus.DRAFTING
        assert counts["enqueued"] == 1
        MockQueue.return_value.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_pending_packages_are_skipped(self):
        graph_id = uuid.uuid4()
        wp = _wp(status=WorkPackageStatus.DEPLOYED, authority_tier=AuthorityTier.AUTO.value)
        wp.task_graph_id = graph_id

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [wp]))))
        db.flush = AsyncMock()

        with patch("app.services.engineering.dispatcher.TaskQueue") as MockQueue:
            MockQueue.return_value.enqueue = AsyncMock()
            counts = await dispatch_ready_packages(db, graph_id)

        assert counts["skipped"] == 1
        assert counts["enqueued"] == 0

    @pytest.mark.asyncio
    async def test_unsatisfied_dependency_waits(self):
        graph_id = uuid.uuid4()
        dep = _wp(status=WorkPackageStatus.IN_REVIEW)
        dep.task_graph_id = graph_id
        wp = _wp(depends_on=[dep.id], authority_tier=AuthorityTier.AUTO.value)
        wp.task_graph_id = graph_id

        db = MagicMock()
        db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [dep, wp])))
        )
        db.flush = AsyncMock()

        with patch("app.services.engineering.dispatcher.TaskQueue") as MockQueue:
            MockQueue.return_value.enqueue = AsyncMock()
            counts = await dispatch_ready_packages(db, graph_id)

        assert counts["waiting_on_deps"] == 1
