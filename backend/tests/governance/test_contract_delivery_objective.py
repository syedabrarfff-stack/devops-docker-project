"""Tests for the contract-signed -> Engineering Organization delivery hook.

Closes the audited gap: signing a contract created a Client + draft Invoice
but nothing ever turned the contracted scope into actual work getting built.
_create_delivery_objective() is the missing link — it calls
mission_planner.decompose_objective() so the newly-wired engineering_org_cycle
scheduler job picks the resulting task graph up automatically.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.routes.governance import _create_delivery_objective


class _NoopBeginCtx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *a):
        return False


def _fake_db():
    db = MagicMock()
    db.begin = MagicMock(return_value=_NoopBeginCtx())
    return db


class TestCreateDeliveryObjective:
    @pytest.mark.asyncio
    async def test_builds_objective_from_contract_and_returns_graph_id(self):
        db = _fake_db()
        graph_id = uuid.uuid4()
        fake_graph = MagicMock(id=graph_id)
        resolved_tenant = uuid.uuid4()
        contract = {
            "client_company": "Acme Corp",
            "client_name": "Jane Doe",
            "service_type": "AI Automation Retainer",
            "scope": "Build a lead-scoring pipeline and weekly reporting dashboard.",
        }

        with (
            patch("app.core.database.set_tenant_context", new_callable=AsyncMock) as set_ctx_mock,
            patch(
                "app.services.engineering.mission_planner.decompose_objective",
                new_callable=AsyncMock,
                return_value=fake_graph,
            ) as decompose_mock,
            patch("app.services.notifications.telegram.notify_telegram", new_callable=AsyncMock) as notify_mock,
        ):
            result = await _create_delivery_objective(db, contract, 42, resolved_tenant)

        assert result == str(graph_id)
        set_ctx_mock.assert_awaited_once_with(db, str(resolved_tenant))
        decompose_mock.assert_awaited_once()
        _, kwargs = decompose_mock.call_args
        assert "Acme Corp" in kwargs["objective"]
        assert "AI Automation Retainer" in kwargs["objective"]
        assert "lead-scoring pipeline" in kwargs["objective"]
        assert kwargs["objective_type"] == "feature"
        assert kwargs["context"] == {"source": "contract_signed", "contract_id": 42}
        notify_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_contract_fields_fall_back_to_defaults(self):
        db = _fake_db()
        fake_graph = MagicMock(id=uuid.uuid4())
        contract = {}  # no client_company, service_type, or scope captured

        with (
            patch("app.core.database.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.engineering.mission_planner.decompose_objective",
                new_callable=AsyncMock,
                return_value=fake_graph,
            ) as decompose_mock,
            patch("app.services.notifications.telegram.notify_telegram", new_callable=AsyncMock),
        ):
            result = await _create_delivery_objective(db, contract, 7, uuid.uuid4())

        assert result == str(fake_graph.id)
        _, kwargs = decompose_mock.call_args
        assert "the client" in kwargs["objective"]
        assert "Services" in kwargs["objective"]
        assert "as described in the signed contract" in kwargs["objective"]

    @pytest.mark.asyncio
    async def test_decompose_failure_is_swallowed_and_returns_none(self):
        db = _fake_db()
        contract = {"service_type": "Web App", "client_company": "Beta LLC"}

        with (
            patch("app.core.database.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.engineering.mission_planner.decompose_objective",
                new_callable=AsyncMock,
                side_effect=RuntimeError("fabric router unavailable"),
            ),
        ):
            result = await _create_delivery_objective(db, contract, 9, uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_notify_failure_does_not_prevent_returning_graph_id(self):
        db = _fake_db()
        fake_graph = MagicMock(id=uuid.uuid4())
        contract = {"service_type": "Web App"}

        with (
            patch("app.core.database.set_tenant_context", new_callable=AsyncMock),
            patch(
                "app.services.engineering.mission_planner.decompose_objective",
                new_callable=AsyncMock,
                return_value=fake_graph,
            ),
            patch(
                "app.services.notifications.telegram.notify_telegram",
                new_callable=AsyncMock,
                side_effect=RuntimeError("telegram down"),
            ),
        ):
            result = await _create_delivery_objective(db, contract, 11, uuid.uuid4())

        assert result == str(fake_graph.id)
