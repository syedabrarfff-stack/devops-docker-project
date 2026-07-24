"""Tests for the 14 jobs migrated into scheduler.py in Task #23 Phase C:
captain_dashboard_briefing, weekly_performance_briefing, daily_self_learning,
drift_auditor, daily_strategy_report, weekly_strategy_review,
milestone_bulk_review, dio_health_check, tech_evolution_scan,
daily_scout_network, lead_embedding_sweep, pre_call_briefing_trigger,
nexus_heartbeat, nightly_signal_scan.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler import scheduler


def _db_ctx_mock(db_ctx, mock_session):
    db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)


class TestCaptainDashboardBriefing:
    @pytest.mark.asyncio
    async def test_delegates_to_notify_captain_morning_briefing(self):
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.notifications.telegram_bot.notify_captain_morning_briefing", new_callable=AsyncMock) as notify_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.captain_dashboard_briefing()
        notify_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("captain_dashboard_briefing", "success", {})


class TestWeeklyPerformanceBriefing:
    @pytest.mark.asyncio
    async def test_delegates_to_notify_weekly_performance_briefing(self):
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.notifications.telegram_bot.notify_weekly_performance_briefing", new_callable=AsyncMock) as notify_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.weekly_performance_briefing()
        notify_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("weekly_performance_briefing", "success", {})


class TestDailySelfLearning:
    @pytest.mark.asyncio
    async def test_delegates_to_learning_cycle(self):
        fake_result = {"learnings_stored": 3}
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.intelligence.jarvis_self_learning.run_daily_learning_cycle", new_callable=AsyncMock, return_value=fake_result) as cycle_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.daily_self_learning()
        cycle_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("daily_self_learning", "success", fake_result)


class TestDriftAuditor:
    @pytest.mark.asyncio
    async def test_reports_to_headquarters_when_issues_found(self):
        report = {"actions": ["fixed x"], "alerts": ["needs review"], "duration_ms": 100}
        with (
            patch("app.services.monitoring.drift_auditor.run_drift_audit", new_callable=AsyncMock, return_value=report),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.headquarters.reporter.log_autonomous_operation", new_callable=AsyncMock) as log_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.drift_auditor()
        log_mock.assert_awaited_once()
        assert log_mock.call_args.kwargs["source"] == "drift_auditor"
        record_mock.assert_awaited_once_with("drift_auditor", "success", report)

    @pytest.mark.asyncio
    async def test_silent_when_clean(self):
        report = {"actions": [], "alerts": [], "duration_ms": 5}
        with (
            patch("app.services.monitoring.drift_auditor.run_drift_audit", new_callable=AsyncMock, return_value=report),
            patch("app.services.headquarters.reporter.log_autonomous_operation", new_callable=AsyncMock) as log_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock),
        ):
            await scheduler.drift_auditor()
        log_mock.assert_not_awaited()


class TestDailyStrategyReport:
    @pytest.mark.asyncio
    async def test_generates_report_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["t1", "t2"]),
            patch(
                "app.services.departments.strategy_report_service.strategy_report_service.generate_daily_strategy_report",
                new_callable=AsyncMock, return_value={"council_score": 8.5, "directives_issued": 3},
            ) as gen_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.daily_strategy_report()
        assert gen_mock.await_count == 2
        record_mock.assert_awaited_once()
        assert len(record_mock.call_args.args[2]["tenants"]) == 2


class TestWeeklyStrategyReview:
    @pytest.mark.asyncio
    async def test_generates_review_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch(
                "app.services.departments.strategy_report_service.strategy_report_service.generate_weekly_strategy_report",
                new_callable=AsyncMock, return_value={"council_score": 9.0},
            ) as gen_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.weekly_strategy_review()
        gen_mock.assert_awaited_once()
        record_mock.assert_awaited_once()


class TestMilestoneBulkReview:
    @pytest.mark.asyncio
    async def test_reviews_milestones_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch(
                "app.services.departments.milestone_engine.milestone_engine.run_bulk_milestone_review",
                new_callable=AsyncMock, return_value={"processed": 4, "failed": 1},
            ) as review_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.milestone_bulk_review()
        review_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["tenants"][0]["processed"] == 4


class TestDioHealthCheck:
    @pytest.mark.asyncio
    async def test_initializes_dios_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["t1", "t2"]),
            patch(
                "app.services.departments.department_agent_service.department_agent_service.initialize_all_dios",
                new_callable=AsyncMock, return_value=[],
            ) as init_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.dio_health_check()
        assert init_mock.await_count == 2
        record_mock.assert_awaited_once_with("dio_health_check", "success", {"tenants_checked": 2})


class TestTechEvolutionScan:
    @pytest.mark.asyncio
    async def test_runs_discovery_per_tenant(self):
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch(
                "app.services.departments.tech_evolution_engine.tech_evolution_engine.run_discovery_cycle",
                new_callable=AsyncMock, return_value={"new_saved": 2, "high_priority_count": 1},
            ) as discovery_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.tech_evolution_scan()
        discovery_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["tenants"][0]["new"] == 2


class TestDailyScoutNetwork:
    @pytest.mark.asyncio
    async def test_delegates_to_scout_network_per_tenant_and_records_real_fields(self):
        fake_result = {"scouts_run": 9, "successful": 8, "failed": 1, "companies_found": 20, "leads_inserted": 14}
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["tenant-1"]),
            patch("app.services.leads.scout_network.scout_network.run_all_scouts", new_callable=AsyncMock, return_value=fake_result) as run_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.daily_scout_network()
        run_mock.assert_awaited_once_with("tenant-1")
        payload = record_mock.call_args.args[2]
        assert payload["tenants"] == 1
        assert payload["companies_found"] == 20
        assert payload["leads_inserted"] == 14
        assert payload["scouts_run"] == 9

    @pytest.mark.asyncio
    async def test_sums_across_multiple_tenants(self):
        results = [
            {"scouts_run": 9, "companies_found": 10, "leads_inserted": 5},
            {"scouts_run": 9, "companies_found": 6, "leads_inserted": 2},
        ]
        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["t1", "t2"]),
            patch("app.services.leads.scout_network.scout_network.run_all_scouts", new_callable=AsyncMock, side_effect=results),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            await scheduler.daily_scout_network()
        payload = record_mock.call_args.args[2]
        assert payload["tenants"] == 2
        assert payload["companies_found"] == 16
        assert payload["leads_inserted"] == 7


class TestLeadEmbeddingSweep:
    @pytest.mark.asyncio
    async def test_delegates_to_embed_pending_leads(self):
        fake_result = {"embedded": 10}
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.intelligence.lead_embeddings.embed_pending_leads", new_callable=AsyncMock, return_value=fake_result) as embed_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.lead_embedding_sweep()
        embed_mock.assert_awaited_once()
        record_mock.assert_awaited_once_with("lead_embedding_sweep", "success", fake_result)


class TestPreCallBriefingTrigger:
    @pytest.mark.asyncio
    async def test_generates_briefings_for_calls_in_window(self):
        fake_call = MagicMock(tenant_id=uuid.uuid4(), id=uuid.uuid4())
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [fake_call]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch(
                "app.services.departments.call_intelligence_service.call_intelligence_service.generate_pre_call_briefing",
                new_callable=AsyncMock,
            ) as briefing_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, mock_session)
            await scheduler.pre_call_briefing_trigger()

        briefing_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["calls_found"] == 1
        assert record_mock.call_args.args[2]["briefings_generated"] == 1

    @pytest.mark.asyncio
    async def test_no_calls_in_window_is_a_no_op(self):
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, mock_session)
            await scheduler.pre_call_briefing_trigger()

        assert record_mock.call_args.args[2]["calls_found"] == 0


class TestNexusHeartbeat:
    @pytest.mark.asyncio
    async def test_no_autonomous_trigger_when_drafts_pending(self):
        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.nexus.heartbeat.run_pulse", new_callable=AsyncMock, return_value={"action_signal": "OUTREACH_READY"}),
            patch("app.services.autopilot.pipeline.get_pending_drafts", new_callable=AsyncMock, return_value=[{"id": "d1"}]),
            patch("app.services.notifications.telegram_bot.notify_autopilot_drafts_pending", new_callable=AsyncMock) as notify_mock,
            patch("app.api.v1.routes.ws.broadcast", new_callable=AsyncMock),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.nexus_heartbeat()

        notify_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["autonomous_triggered"] is False

    @pytest.mark.asyncio
    async def test_autonomous_trigger_fires_when_ready_and_lock_acquired(self):
        fake_redis = AsyncMock()
        fake_redis.set = AsyncMock(return_value=True)

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.nexus.heartbeat.run_pulse", new_callable=AsyncMock, return_value={"action_signal": "OUTREACH_READY"}),
            patch("app.services.autopilot.pipeline.get_pending_drafts", new_callable=AsyncMock, return_value=[]),
            patch("redis.asyncio.from_url", return_value=fake_redis),
            patch("app.services.autopilot.pipeline.run_autopilot_cycle", new_callable=AsyncMock, return_value={"composed": 3}) as autopilot_mock,
            patch("app.services.nexus.heartbeat.log_decision", new_callable=AsyncMock),
            patch("app.api.v1.routes.ws.broadcast", new_callable=AsyncMock),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.nexus_heartbeat()

        autopilot_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["autonomous_triggered"] is True

    @pytest.mark.asyncio
    async def test_no_trigger_when_lock_already_held(self):
        fake_redis = AsyncMock()
        fake_redis.set = AsyncMock(return_value=False)  # lock already held elsewhere

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.nexus.heartbeat.run_pulse", new_callable=AsyncMock, return_value={"action_signal": "OUTREACH_READY"}),
            patch("app.services.autopilot.pipeline.get_pending_drafts", new_callable=AsyncMock, return_value=[]),
            patch("redis.asyncio.from_url", return_value=fake_redis),
            patch("app.services.autopilot.pipeline.run_autopilot_cycle", new_callable=AsyncMock) as autopilot_mock,
            patch("app.api.v1.routes.ws.broadcast", new_callable=AsyncMock),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, AsyncMock())
            await scheduler.nexus_heartbeat()

        autopilot_mock.assert_not_awaited()
        assert record_mock.call_args.args[2]["autonomous_triggered"] is False


class TestNightlySignalScan:
    @pytest.mark.asyncio
    async def test_no_leads_is_a_no_op(self):
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, mock_session)
            await scheduler.nightly_signal_scan()

        assert record_mock.call_args.args[2]["signals_found"] == 0
        assert record_mock.call_args.args[2]["proposals_queued"] == 0

    @pytest.mark.asyncio
    async def test_hot_high_confidence_lead_queues_one_proposal(self):
        fake_lead = MagicMock(
            id=uuid.uuid4(), company_name="AcmeCo", company="AcmeCo", industry="SaaS",
            score=80, status=MagicMock(value="NEW"), pain_points="", contact_name="Jane",
            email="jane@acme.com", country="UK", notes="", outreach_count=1,
        )
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [fake_lead]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        hot_signal = {
            "intent_tier": "HOT", "confidence": 90, "lead_score": 80,
            "lead_id": str(fake_lead.id), "lead_company": "AcmeCo",
            "lead_contact": "Jane", "lead_email": "jane@acme.com", "why_now": "budget approved",
        }

        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.signal.scanner.scan_lead", new_callable=AsyncMock, return_value=hot_signal),
            patch("app.services.notifications.telegram.notify_telegram", new_callable=AsyncMock),
            patch(
                "app.services.governance.auto_proposal.auto_generate_proposal_for_lead",
                new_callable=AsyncMock, return_value={"proposal_id": "p-1"},
            ) as proposal_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, mock_session)
            await scheduler.nightly_signal_scan()

        proposal_mock.assert_awaited_once()
        assert record_mock.call_args.args[2]["signals_found"] == 1
        assert record_mock.call_args.args[2]["proposals_queued"] == 1

    @pytest.mark.asyncio
    async def test_warm_signal_does_not_queue_a_proposal(self):
        fake_lead = MagicMock(
            id=uuid.uuid4(), company_name="WarmCo", company="WarmCo", industry="SaaS",
            score=50, status=MagicMock(value="NEW"), pain_points="", contact_name="Bob",
            email="bob@warm.com", country="UK", notes="", outreach_count=0,
        )
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [fake_lead]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        warm_signal = {"intent_tier": "WARM", "confidence": 60, "lead_score": 50, "lead_id": str(fake_lead.id)}

        with (
            patch("app.services.scheduler.scheduler._target_tenant_ids", new_callable=AsyncMock, return_value=["11111111-1111-4111-8111-111111111111"]),
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.signal.scanner.scan_lead", new_callable=AsyncMock, return_value=warm_signal),
            patch("app.services.notifications.telegram.notify_telegram", new_callable=AsyncMock),
            patch(
                "app.services.governance.auto_proposal.auto_generate_proposal_for_lead",
                new_callable=AsyncMock,
            ) as proposal_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            _db_ctx_mock(db_ctx, mock_session)
            await scheduler.nightly_signal_scan()

        proposal_mock.assert_not_awaited()
        assert record_mock.call_args.args[2]["signals_found"] == 1
        assert record_mock.call_args.args[2]["proposals_queued"] == 0
