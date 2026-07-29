"""E7-10: Tests for Deployment Pipeline Integration (E7-8)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.services.engineering.deployment_integration import build_pr_summary, integrate_work_package


def _wp(status=WorkPackageStatus.APPROVED, operation="bug.fix", draft_output=None):
    return EngineeringWorkPackage(
        id=uuid.uuid4(),
        task_graph_id=uuid.uuid4(),
        department="backend",
        title="Add rate limiting",
        acceptance_criteria=["endpoint returns 429 after limit"],
        operation=operation,
        status=status,
        draft_output=draft_output or {"summary": "s", "approach": "a", "code_snippet": "x = 1"},
    )


class TestIntegrateWorkPackage:
    @pytest.mark.asyncio
    async def test_raises_if_not_approved(self):
        wp = _wp(status=WorkPackageStatus.IN_REVIEW)
        with pytest.raises(ValueError, match="not APPROVED"):
            await integrate_work_package(MagicMock(), wp)

    @pytest.mark.asyncio
    async def test_general_code_work_returns_pending_manual_integration(self):
        wp = _wp(operation="bug.fix")
        db = MagicMock()
        db.flush = AsyncMock()

        with patch("app.services.engineering.deployment_integration.get_event_bus") as mock_bus:
            mock_bus.return_value.emit = AsyncMock()
            result = await integrate_work_package(db, wp)

        assert result["mode"] == "pending_manual_integration"
        assert "pr_summary" in result
        assert wp.status == WorkPackageStatus.APPROVED  # unchanged — not auto-deployed

    @pytest.mark.asyncio
    async def test_safe_deploy_action_calls_existing_run_deploy(self):
        wp = _wp(operation="ci.fix_and_redeploy")
        db = MagicMock()
        db.flush = AsyncMock()

        with patch("app.services.engineering.deployment_integration.get_event_bus") as mock_bus, \
             patch("app.services.headquarters.deploy.run_deploy", new=AsyncMock(return_value={"ok": True})) as mock_deploy:
            mock_bus.return_value.emit = AsyncMock()
            result = await integrate_work_package(db, wp)

        mock_deploy.assert_awaited_once_with("verify-status")
        assert result["mode"] == "auto_deploy"
        assert wp.status == WorkPackageStatus.DEPLOYED

    @pytest.mark.asyncio
    async def test_failed_safe_deploy_blocks_work_package(self):
        wp = _wp(operation="ci.fix_and_redeploy")
        db = MagicMock()
        db.flush = AsyncMock()

        with patch("app.services.engineering.deployment_integration.get_event_bus") as mock_bus, \
             patch("app.services.headquarters.deploy.run_deploy", new=AsyncMock(return_value={"ok": False})):
            mock_bus.return_value.emit = AsyncMock()
            result = await integrate_work_package(db, wp)

        assert wp.status == WorkPackageStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_emits_observability_event(self):
        wp = _wp()
        db = MagicMock()
        db.flush = AsyncMock()

        with patch("app.services.engineering.deployment_integration.get_event_bus") as mock_bus:
            mock_bus.return_value.emit = AsyncMock()
            await integrate_work_package(db, wp)

        mock_bus.return_value.emit.assert_awaited_once()
        args, _ = mock_bus.return_value.emit.call_args
        assert args[0] == "engineering.work_package.approved"


class TestBuildPrSummary:
    def test_includes_title_and_department(self):
        wp = _wp()
        summary = build_pr_summary(wp)
        assert wp.department in summary["suggested_title"]
        assert summary["department"] == wp.department

    def test_includes_acceptance_criteria_in_body(self):
        wp = _wp()
        summary = build_pr_summary(wp)
        assert "endpoint returns 429 after limit" in summary["body"]

    def test_includes_code_snippet(self):
        wp = _wp()
        summary = build_pr_summary(wp)
        assert summary["code_snippet"] == "x = 1"
