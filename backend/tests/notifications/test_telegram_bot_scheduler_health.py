"""Tests for the scheduler-health line in the Captain morning dashboard
briefing (notify_captain_morning_briefing) — Task #23 Phase A.

Before this fix, this function imported get_scheduler/get_jobs from the dead
engine.py module, so Captain was shown "Scheduler: STOPPED" every single
morning via Telegram regardless of the real scheduler's actual state.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def patched_env():
    with (
        patch("app.services.notifications.telegram_bot.settings") as cfg,
        patch("app.services.autopilot.pipeline.get_pending_drafts", new_callable=AsyncMock, return_value=[]),
        patch("app.services.nexus.heartbeat.get_latest_pulse", new_callable=AsyncMock, return_value=None),
        patch("app.services.nexus.heartbeat.get_decisions", new_callable=AsyncMock, return_value=[]),
        patch("app.services.notifications.telegram_bot.send_message", new_callable=AsyncMock) as send_mock,
    ):
        cfg.TELEGRAM_CHAT_ID = "-100123456"
        cfg.JARVIS_DEFAULT_TENANT_ID = None
        yield send_mock


class TestSchedulerHealthLine:
    @pytest.mark.asyncio
    async def test_running_scheduler_reports_job_count(self, patched_env):
        send_mock = patched_env
        fake_sched = MagicMock(running=True)

        with (
            patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched),
            patch("app.services.scheduler.scheduler.get_jobs", return_value=[{"id": "a"}, {"id": "b"}]),
        ):
            from app.services.notifications.telegram_bot import notify_captain_morning_briefing
            await notify_captain_morning_briefing(AsyncMock())

        send_mock.assert_awaited_once()
        message = send_mock.call_args.args[1]
        assert "Scheduler: 2 jobs running" in message
        assert "STOPPED" not in message

    @pytest.mark.asyncio
    async def test_stopped_scheduler_reports_stopped(self, patched_env):
        send_mock = patched_env
        fake_sched = MagicMock(running=False)

        with patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_sched):
            from app.services.notifications.telegram_bot import notify_captain_morning_briefing
            await notify_captain_morning_briefing(AsyncMock())

        message = send_mock.call_args.args[1]
        assert "STOPPED" in message

    def test_uses_canonical_scheduler_module_not_engine(self):
        import inspect
        from app.services.notifications import telegram_bot

        source = inspect.getsource(telegram_bot.notify_captain_morning_briefing)
        assert "app.services.scheduler.scheduler" in source
        assert "app.services.scheduler.engine" not in source
