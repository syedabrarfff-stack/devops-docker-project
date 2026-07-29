"""Tests for engineering_org_cycle — the scheduler job that finally calls
department_agent.run_one_cycle / peer_review.review_work_package /
deployment_integration.integrate_work_package in production. Phase 7 shipped
these functions fully tested but nothing ever invoked them past dispatch;
this job is that missing caller.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler import scheduler


def _scalars_result(items):
    return MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: items)))


class TestProductionJobRegistryIncludesEngineeringOrgCycle:
    def test_specs_and_production_job_ids_match_exactly(self):
        spec_ids = {spec["job_id"] for spec in scheduler._production_job_specs()}
        assert spec_ids == set(scheduler.PRODUCTION_JOB_IDS)

    def test_engineering_org_cycle_is_registered_as_interval_job(self):
        specs = {spec["job_id"]: spec for spec in scheduler._production_job_specs()}
        assert "engineering_org_cycle" in specs
        assert specs["engineering_org_cycle"]["kind"] == "interval"


class TestEngineeringOrgCycle:
    @pytest.mark.asyncio
    async def test_drains_dispatch_draft_review_integrate_for_in_progress_graphs(self):
        graph_id = uuid.uuid4()
        wp_in_review = MagicMock(id=uuid.uuid4())
        wp_approved = MagicMock(id=uuid.uuid4())

        fake_db = MagicMock()

        # db.begin() used as `async with db.begin():` — give it a real async ctx manager.
        class _NoopCtx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_db.begin = MagicMock(return_value=_NoopCtx())

        fake_db.execute = AsyncMock(
            side_effect=[
                _scalars_result([graph_id]),   # IN_PROGRESS task graph ids
                _scalars_result([wp_in_review]),  # IN_REVIEW work packages
                _scalars_result([wp_approved]),   # APPROVED, deploy_result is None
            ]
        )

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.engineering.dispatcher.dispatch_ready_packages", new_callable=AsyncMock) as dispatch_mock,
            patch("app.services.engineering.dispatcher.refresh_graph_status", new_callable=AsyncMock) as refresh_mock,
            patch(
                "app.services.engineering.department_agent.run_one_cycle",
                new_callable=AsyncMock,
                side_effect=[MagicMock(), None],
            ) as draft_mock,
            patch("app.services.engineering.peer_review.review_work_package", new_callable=AsyncMock) as review_mock,
            patch(
                "app.services.engineering.deployment_integration.integrate_work_package",
                new_callable=AsyncMock,
                return_value={"mode": "pending_manual_integration", "pr_summary": {}},
            ) as integrate_mock,
            patch("app.services.notifications.notify_business_event", new_callable=AsyncMock) as notify_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await scheduler.engineering_org_cycle()

        dispatch_mock.assert_awaited_once_with(fake_db, graph_id)
        refresh_mock.assert_awaited_once_with(fake_db, graph_id)
        assert draft_mock.await_count == 2
        review_mock.assert_awaited_once_with(fake_db, wp_in_review)
        integrate_mock.assert_awaited_once_with(fake_db, wp_approved)
        notify_mock.assert_awaited_once()

        record_mock.assert_awaited_once()
        payload = record_mock.call_args.args[2]
        assert payload["drafted"] == 1
        assert payload["reviewed"] == 1
        assert payload["integrated"] == 1
        assert payload["pending_manual_integration"] == [str(wp_approved.id)]
        assert payload["errors"] == 0

    @pytest.mark.asyncio
    async def test_no_in_progress_graphs_is_a_clean_noop(self):
        fake_db = MagicMock()

        class _NoopCtx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_db.begin = MagicMock(return_value=_NoopCtx())

        fake_db.execute = AsyncMock(
            side_effect=[
                _scalars_result([]),  # no IN_PROGRESS graphs
                _scalars_result([]),  # no IN_REVIEW packages
                _scalars_result([]),  # no APPROVED packages
            ]
        )

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch("app.services.engineering.dispatcher.dispatch_ready_packages", new_callable=AsyncMock) as dispatch_mock,
            patch(
                "app.services.engineering.department_agent.run_one_cycle",
                new_callable=AsyncMock,
                return_value=None,
            ) as draft_mock,
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await scheduler.engineering_org_cycle()

        dispatch_mock.assert_not_called()
        draft_mock.assert_awaited_once()  # loop still tries once, sees None, stops
        payload = record_mock.call_args.args[2]
        assert payload == {
            "task_graphs_scanned": 0,
            "drafted": 0,
            "reviewed": 0,
            "integrated": 0,
            "pending_manual_integration": [],
            "errors": 0,
        }

    @pytest.mark.asyncio
    async def test_peer_review_failure_is_isolated_and_counted(self):
        wp_in_review = MagicMock(id=uuid.uuid4())

        fake_db = MagicMock()

        class _NoopCtx:
            async def __aenter__(self):
                return None
            async def __aexit__(self, *a):
                return False
        fake_db.begin = MagicMock(return_value=_NoopCtx())

        fake_db.execute = AsyncMock(
            side_effect=[
                _scalars_result([]),
                _scalars_result([wp_in_review]),
                _scalars_result([]),
            ]
        )

        with (
            patch("app.core.database.AsyncSessionLocal") as db_ctx,
            patch(
                "app.services.engineering.department_agent.run_one_cycle",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.engineering.peer_review.review_work_package",
                new_callable=AsyncMock,
                side_effect=RuntimeError("council unavailable"),
            ),
            patch("app.services.scheduler.scheduler._record_job_result", new_callable=AsyncMock) as record_mock,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            await scheduler.engineering_org_cycle()

        payload = record_mock.call_args.args[2]
        assert payload["reviewed"] == 0
        assert payload["errors"] == 1
