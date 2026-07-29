"""collect_department_metrics() used to ask an LLM to invent department health
scores with zero real data fed in — confirmed decorative by this session's
audit. These tests verify it's now grounded in real, queryable telemetry
(scheduled job status counts, open failures, AI provider health, revenue),
and that a failure gathering any one piece of telemetry doesn't take down
the whole metrics collection.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.departments.department_agent_service import (
    DepartmentAgentService,
    SYSTEM_TENANT_ID,
)


class _NoopBeginCtx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *a):
        return False


def _fake_sys_db(status_rows, open_failures, latest_audit_log):
    db = MagicMock()
    db.begin = MagicMock(return_value=_NoopBeginCtx())
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(all=MagicMock(return_value=status_rows)),
        ]
    )
    db.scalar = AsyncMock(side_effect=[open_failures, latest_audit_log])
    return db


class TestGatherRealTelemetry:
    @pytest.mark.asyncio
    async def test_returns_real_job_ai_and_revenue_numbers(self):
        service = DepartmentAgentService()
        tenant_uuid = uuid.uuid4()
        fake_audit_log = MagicMock(details={"drafted": 3, "reviewed": 2, "integrated": 1, "errors": 0})
        fake_sys_db = _fake_sys_db(
            status_rows=[("success", 40), ("failed", 2), (None, 1)],
            open_failures=2,
            latest_audit_log=fake_audit_log,
        )

        with (
            patch("app.services.departments.department_agent_service.AsyncSessionLocal") as db_ctx,
            patch("app.services.departments.department_agent_service.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.departments.department_agent_service.ai_router.operational_providers",
                return_value=["nvidia", "google"],
            ),
            patch(
                "app.services.departments.department_agent_service.ai_router.available_providers",
                return_value=["nvidia", "google", "anthropic"],
            ),
            patch("app.services.governance.invoice_engine.invoice_engine.revenue_snapshot", new_callable=AsyncMock) as rev_mock,
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_sys_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            rev_mock.return_value = {"mrr_usd": 12000.0, "total_revenue_usd": 45000.0, "active_clients": 6}

            telemetry = await service._gather_real_telemetry(tenant_uuid)

        assert telemetry["scheduled_jobs_by_last_status"] == {"success": 40, "failed": 2, "never_run": 1}
        assert telemetry["open_job_failures"] == 2
        assert telemetry["engineering_org_cycle_last_run"] == {"drafted": 3, "reviewed": 2, "integrated": 1, "errors": 0}
        assert telemetry["ai_providers_operational"] == 2
        assert telemetry["ai_providers_total"] == 3
        assert telemetry["revenue_snapshot"]["mrr_usd"] == 12000.0
        assert telemetry["revenue_snapshot"]["active_clients"] == 6

    @pytest.mark.asyncio
    async def test_job_telemetry_failure_does_not_break_other_telemetry(self):
        service = DepartmentAgentService()
        tenant_uuid = uuid.uuid4()

        with (
            patch(
                "app.services.departments.department_agent_service.AsyncSessionLocal",
                side_effect=RuntimeError("db unavailable"),
            ),
            patch(
                "app.services.departments.department_agent_service.ai_router.operational_providers",
                return_value=["nvidia"],
            ),
            patch(
                "app.services.departments.department_agent_service.ai_router.available_providers",
                return_value=["nvidia", "google"],
            ),
            patch("app.services.governance.invoice_engine.invoice_engine.revenue_snapshot", new_callable=AsyncMock) as rev_mock,
        ):
            rev_mock.return_value = {"mrr_usd": 500.0, "total_revenue_usd": 500.0, "active_clients": 1}
            telemetry = await service._gather_real_telemetry(tenant_uuid)

        assert "scheduled_jobs_by_last_status" not in telemetry
        assert telemetry["ai_providers_operational"] == 1
        assert telemetry["revenue_snapshot"]["mrr_usd"] == 500.0

    @pytest.mark.asyncio
    async def test_revenue_failure_does_not_break_job_telemetry(self):
        service = DepartmentAgentService()
        tenant_uuid = uuid.uuid4()
        fake_sys_db = _fake_sys_db(
            status_rows=[("success", 10)],
            open_failures=0,
            latest_audit_log=None,
        )

        with (
            patch("app.services.departments.department_agent_service.AsyncSessionLocal") as db_ctx,
            patch("app.services.departments.department_agent_service.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.departments.department_agent_service.ai_router.operational_providers",
                return_value=[],
            ),
            patch(
                "app.services.departments.department_agent_service.ai_router.available_providers",
                return_value=[],
            ),
            patch(
                "app.services.governance.invoice_engine.invoice_engine.revenue_snapshot",
                new_callable=AsyncMock,
                side_effect=RuntimeError("revenue engine down"),
            ),
        ):
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=fake_sys_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            telemetry = await service._gather_real_telemetry(tenant_uuid)

        assert telemetry["scheduled_jobs_by_last_status"] == {"success": 10}
        assert telemetry["open_job_failures"] == 0
        assert "revenue_snapshot" not in telemetry


class TestCollectDepartmentMetrics:
    @pytest.mark.asyncio
    async def test_prompt_is_grounded_in_real_telemetry_and_response_includes_it(self):
        service = DepartmentAgentService()
        tenant_id = str(uuid.uuid4())
        fake_telemetry = {"open_job_failures": 5, "ai_providers_operational": 2}
        fake_ai_response = MagicMock(error=None, content='{"engineering": {"health": 60}}')

        with (
            patch.object(service, "_gather_real_telemetry", new_callable=AsyncMock, return_value=fake_telemetry),
            patch(
                "app.services.departments.department_agent_service.ai_router.chat",
                new_callable=AsyncMock,
                return_value=(fake_ai_response, None),
            ) as chat_mock,
        ):
            result = await service.collect_department_metrics(MagicMock(), tenant_id)

        assert result["real_telemetry"] == fake_telemetry
        assert result["department_metrics"] == {"engineering": {"health": 60}}
        sent_prompt = chat_mock.call_args.args[0][0].content
        assert '"open_job_failures": 5' in sent_prompt
        assert "REAL TELEMETRY" in sent_prompt

    @pytest.mark.asyncio
    async def test_ai_failure_still_returns_real_telemetry(self):
        service = DepartmentAgentService()
        tenant_id = str(uuid.uuid4())
        fake_telemetry = {"open_job_failures": 0}

        with (
            patch.object(service, "_gather_real_telemetry", new_callable=AsyncMock, return_value=fake_telemetry),
            patch(
                "app.services.departments.department_agent_service.ai_router.chat",
                new_callable=AsyncMock,
                side_effect=RuntimeError("all providers down"),
            ),
        ):
            result = await service.collect_department_metrics(MagicMock(), tenant_id)

        assert result["real_telemetry"] == fake_telemetry
        assert result["department_metrics"] == {"raw": "unavailable"}
