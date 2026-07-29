"""Tests for nexus/healer.py's scheduler health check — Task #23 Phase A.

Before this fix, diagnose_all() and heal_subsystem() both imported
get_scheduler/start_scheduler from the dead engine.py module — a scheduler
instance that is never started, so diagnose_all() always reported the
scheduler as "stopped" (a false alert on every self-heal cycle) and
heal_subsystem("scheduler") would "restart" an empty, meaningless instance
that has no bearing on the real, running scheduler.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.nexus import healer


class TestDiagnoseScheduler:
    @pytest.mark.asyncio
    async def test_running_scheduler_reports_healthy(self):
        fake_sched = MagicMock(running=True)
        with patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched):
            results = await healer.diagnose_all(db=AsyncMock())
        assert results["scheduler"]["status"] == "healthy"
        assert results["scheduler"]["healable"] is False

    @pytest.mark.asyncio
    async def test_stopped_scheduler_reports_stopped(self):
        fake_sched = MagicMock(running=False)
        with patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched):
            results = await healer.diagnose_all(db=AsyncMock())
        assert results["scheduler"]["status"] == "stopped"
        assert results["scheduler"]["healable"] is True
        assert results["scheduler"]["heal_action"] == "restart_scheduler"

    def test_uses_canonical_scheduler_module_not_engine(self):
        import inspect

        source = inspect.getsource(healer.diagnose_all)
        assert "app.services.scheduler.scheduler" in source
        assert "app.services.scheduler.engine" not in source


class TestHealScheduler:
    @pytest.mark.asyncio
    async def test_restarts_stopped_scheduler(self):
        fake_sched = MagicMock(running=False)
        with (
            patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched),
            patch("app.services.scheduler.scheduler.start_scheduler", new_callable=AsyncMock) as start_mock,
        ):
            result = await healer.heal_subsystem("scheduler", db=AsyncMock())
        start_mock.assert_awaited_once()
        assert result["success"] is True
        assert result["action"] == "scheduler_restart"

    @pytest.mark.asyncio
    async def test_noop_when_already_running(self):
        fake_sched = MagicMock(running=True)
        with (
            patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched),
            patch("app.services.scheduler.scheduler.start_scheduler", new_callable=AsyncMock) as start_mock,
        ):
            result = await healer.heal_subsystem("scheduler", db=AsyncMock())
        start_mock.assert_not_awaited()
        assert result["action"] == "noop"

    def test_uses_canonical_scheduler_module_not_engine(self):
        import inspect

        source = inspect.getsource(healer.heal_subsystem)
        assert "app.services.scheduler.scheduler" in source
        assert "app.services.scheduler.engine" not in source
