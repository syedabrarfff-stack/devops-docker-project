"""Tests for K2-5: FailoverController — CRITICAL threshold, state transitions."""
from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.kernel.failover_controller import FailoverController, FailoverState

# _check() does lazy imports — patch at source module level.
AGG_PATH = "app.services.kernel.health_aggregator.get_health_aggregator"
CFG_PATH = "app.services.kernel.config_service.get_config_service"


def make_controller():
    return FailoverController()


def _mock_agg(overall: str):
    m = MagicMock()
    m.get_summary = MagicMock(return_value={"overall": overall, "engines": {}})
    return MagicMock(return_value=m)


def _mock_cfg(threshold: float = 60.0, auto_switch: bool = False):
    m = AsyncMock()
    m.get_float = AsyncMock(return_value=threshold)
    m.get_bool  = AsyncMock(return_value=auto_switch)
    return MagicMock(return_value=m)


class TestStateTransitions:
    @pytest.mark.asyncio
    async def test_initial_state_nominal(self):
        fc = make_controller()
        assert fc.state == FailoverState.NOMINAL

    @pytest.mark.asyncio
    async def test_healthy_stays_nominal(self):
        fc = make_controller()
        with patch(AGG_PATH, new=_mock_agg("HEALTHY")):
            with patch(CFG_PATH, new=_mock_cfg()):
                await fc._check()
        assert fc.state == FailoverState.NOMINAL
        assert fc._critical_since is None

    @pytest.mark.asyncio
    async def test_critical_sets_timer(self):
        fc = make_controller()
        with patch(AGG_PATH, new=_mock_agg("CRITICAL")):
            with patch(CFG_PATH, new=_mock_cfg()):
                await fc._check()
        assert fc.state == FailoverState.CRITICAL
        assert fc._critical_since is not None

    @pytest.mark.asyncio
    async def test_threshold_exceeded_triggers_alerting(self):
        fc = make_controller()
        # Pretend CRITICAL started 70s ago.
        fc._critical_since = time.monotonic() - 70

        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock(add_done_callback=MagicMock())
            with patch(AGG_PATH, new=_mock_agg("CRITICAL")):
                with patch(CFG_PATH, new=_mock_cfg(threshold=60.0)):
                    await fc._check()

        assert fc.state == FailoverState.ALERTING
        assert fc._alert_sent is True

    @pytest.mark.asyncio
    async def test_recovery_resets_timer(self):
        fc = make_controller()
        fc._critical_since = time.monotonic() - 10
        fc._state = FailoverState.CRITICAL

        with patch(AGG_PATH, new=_mock_agg("HEALTHY")):
            with patch(CFG_PATH, new=_mock_cfg()):
                await fc._check()

        assert fc._critical_since is None
        assert fc.state == FailoverState.NOMINAL

    @pytest.mark.asyncio
    async def test_no_duplicate_alerts(self):
        fc = make_controller()
        fc._critical_since = time.monotonic() - 70
        fc._alert_sent = True   # already alerted

        with patch("asyncio.create_task") as mock_task:
            with patch(AGG_PATH, new=_mock_agg("CRITICAL")):
                with patch(CFG_PATH, new=_mock_cfg(threshold=60.0)):
                    await fc._check()
            mock_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_degraded_sets_degraded_state(self):
        fc = make_controller()
        with patch(AGG_PATH, new=_mock_agg("DEGRADED")):
            with patch(CFG_PATH, new=_mock_cfg()):
                await fc._check()
        assert fc.state == FailoverState.DEGRADED

    @pytest.mark.asyncio
    async def test_acknowledge_dr_active(self):
        fc = make_controller()
        fc._critical_since = time.monotonic()
        await fc.acknowledge_dr_active()
        assert fc.state == FailoverState.DR_ACTIVE
        assert fc._critical_since is None

    @pytest.mark.asyncio
    async def test_acknowledge_recovery(self):
        fc = make_controller()
        fc._state = FailoverState.DR_ACTIVE
        fc._alert_sent = True
        await fc.acknowledge_recovery()
        assert fc.state == FailoverState.NOMINAL
        assert fc._alert_sent is False

    @pytest.mark.asyncio
    async def test_status_serialisable(self):
        fc = make_controller()
        status = await fc.status()
        assert "state" in status
        assert "alert_sent" in status
        assert status["critical_since_s"] is None
