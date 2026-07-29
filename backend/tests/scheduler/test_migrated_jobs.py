"""Tests for jobs migrated into the canonical scheduler.py per Task #23
Phase B: weekly_competitor_monitoring, routing_optimizer_sweep,
linkedin_outreach_sweep_job, voice_analytics_daily, and the restored
self-healer Headquarters reporting.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler import scheduler


class TestProductionJobRegistryIsComplete:
    def test_specs_and_production_job_ids_match_exactly(self):
        spec_ids = {spec["job_id"] for spec in scheduler._production_job_specs()}
        assert spec_ids == set(scheduler.PRODUCTION_JOB_IDS)

    def test_new_jobs_are_registered(self):
        spec_ids = {spec["job_id"] for spec in scheduler._production_job_specs()}
        for job_id in (
            "weekly_competitor_monitoring",
            "routing_optimizer_sweep",
            "linkedin_outreach_sweep",
            "voice_analytics_daily",
        ):
            assert job_id in spec_ids


class TestWeeklyCompetitorMonitoring:
    @pytest.mark.asyncio
    async def test_calls_monitor_competitors_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["tenant-1"]),
            patch("app.services.intelligence.market_intel.MarketIntelligenceEngine.monitor_competitors", new_callable=AsyncMock, return_value=[{"change": "x"}]),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.weekly_competitor_monitoring()
        record_mock.assert_awaited_once()
        assert record_mock.call_args.args[0] == "weekly_competitor_monitoring"
        assert record_mock.call_args.args[2]["changes_detected"] == 1

    @pytest.mark.asyncio
    async def test_tenant_failure_does_not_abort_other_tenants(self):
        async def failing_monitor(self, tenant_id):
            raise RuntimeError("boom")

        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["tenant-1", "tenant-2"]),
            patch("app.services.intelligence.market_intel.MarketIntelligenceEngine.monitor_competitors", failing_monitor),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.weekly_competitor_monitoring()
        record_mock.assert_awaited_once()


class TestRoutingOptimizerSweep:
    @pytest.mark.asyncio
    async def test_runs_optimizer_with_fresh_session(self):
        fake_result = {"models_updated": 3, "models_skipped": 1, "run_at": "now"}
        fake_session = AsyncMock()

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.fabric.routing_optimizer.run_routing_optimizer", new_callable=AsyncMock, return_value=fake_result) as opt_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_session)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await scheduler.routing_optimizer_sweep()

        opt_mock.assert_awaited_once_with(fake_session)
        record_mock.assert_awaited_once_with("routing_optimizer_sweep", "success", fake_result)


class TestLinkedInOutreachSweepJob:
    @pytest.mark.asyncio
    async def test_delegates_to_linkedin_sweep(self):
        fake_result = {"processed": 5, "errors": 0}
        with (
            patch("app.services.outreach.linkedin_outreach.linkedin_outreach_sweep", new_callable=AsyncMock, return_value=fake_result) as sweep_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.linkedin_outreach_sweep_job()
        sweep_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("linkedin_outreach_sweep", "success", fake_result)


class TestVoiceAnalyticsDaily:
    @pytest.mark.asyncio
    async def test_delegates_to_voice_analytics_job(self):
        fake_result = {"inbound_voice_messages": 2, "call_recordings_processed": 1}
        with (
            patch("app.services.voice.analytics.run_voice_analytics_job", new_callable=AsyncMock, return_value=fake_result) as job_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.voice_analytics_daily()
        job_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("voice_analytics_daily", "success", fake_result)


class TestSelfHealerHeadquartersReporting:
    @pytest.mark.asyncio
    async def test_reports_to_headquarters_when_actions_taken(self):
        report = {"actions": ["reset breaker"], "alerts": [], "duration_ms": 42}
        with (
            patch("app.services.monitoring.self_healer.run_self_healing_cycle", new_callable=AsyncMock, return_value=report),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.headquarters.reporter.log_autonomous_operation", new_callable=AsyncMock) as log_mock,
        ):
            mock_db = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await scheduler._job_self_healer()

        log_mock.assert_awaited_once()
        assert log_mock.call_args.kwargs["source"] == "self_healer"

    @pytest.mark.asyncio
    async def test_silent_when_no_actions_or_alerts(self):
        report = {"actions": [], "alerts": [], "duration_ms": 10}
        with (
            patch("app.services.monitoring.self_healer.run_self_healing_cycle", new_callable=AsyncMock, return_value=report),
            patch("app.services.headquarters.reporter.log_autonomous_operation", new_callable=AsyncMock) as log_mock,
        ):
            await scheduler._job_self_healer()

        log_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reports_alerts_that_could_not_self_recover(self):
        report = {"actions": [], "alerts": ["scheduler stuck"], "duration_ms": 5}
        with (
            patch("app.services.monitoring.self_healer.run_self_healing_cycle", new_callable=AsyncMock, return_value=report),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.headquarters.reporter.log_autonomous_operation", new_callable=AsyncMock) as log_mock,
        ):
            mock_db = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await scheduler._job_self_healer()

        log_mock.assert_awaited_once()
        summary = log_mock.call_args.kwargs["summary"]
        assert "scheduler stuck" in summary
