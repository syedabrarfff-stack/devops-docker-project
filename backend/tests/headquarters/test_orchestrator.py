"""Tests for HQ-4: Headquarters Orchestrator — classification, draft/review, policy gate."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.headquarters.orchestrator import HeadquartersOrchestrator, _infer_deploy_action, _infer_operation
from app.services.kernel.authority_matrix import AuthorityTier
from app.services.kernel.policy_engine import PolicyDecision, PolicyViolationError


def _mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _fabric_response(content, provider="anthropic", model="claude-sonnet"):
    return MagicMock(content=content, provider=provider, model=model, error=None)


class TestOperationInference:
    def test_fix_maps_to_bug_fix(self):
        assert _infer_operation("please fix the dashboard bug") == "bug.fix"

    def test_deploy_maps_to_production_deploy(self):
        assert _infer_operation("deploy the latest backend to production") == "production.deploy"

    def test_migration_maps_to_db_add_column(self):
        assert _infer_operation("add a migration for a new column") == "db.add_column"

    def test_unrecognized_defaults_to_performance_improvement(self):
        assert _infer_operation("make the onboarding flow nicer somehow") == "performance.improvement"


class TestHandleMessageClassification:
    @pytest.mark.asyncio
    async def test_status_query_does_not_touch_execution_engine(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with patch.object(orch, "_fabric") as fabric:
            fabric.chat = AsyncMock(return_value=_fabric_response("Production is healthy."))
            result = await orch.handle_message("is production okay?", "sess-1")
            assert result["kind"] == "status_query"
            assert result["answer"] == "Production is healthy."

    @pytest.mark.asyncio
    async def test_change_request_detected_by_verb(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock(return_value=([], "nvidia/deepseek-v4-pro"))),
            patch.object(orch, "_review_plan", new=AsyncMock(return_value=("APPROVE: looks fine", "anthropic/claude-sonnet"))),
            patch.object(orch._policy, "check", new=AsyncMock(return_value=PolicyDecision(
                operation="bug.fix", tier=AuthorityTier.AUTO, permitted=True, requires_captain=False, reason="ok",
            ))),
            patch.object(orch._executor, "execute_plan", new=AsyncMock(return_value={"status": "COMPLETED", "steps": []})),
        ):
            result = await orch.handle_message("fix the dashboard bug", "sess-1")
            assert result["kind"] == "change_request"
            assert result["status"] == "COMPLETED"


class TestChangeRequestTierBranching:
    @pytest.mark.asyncio
    async def test_auto_tier_executes_immediately(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock(return_value=([{"tool": "list_dir", "args": {}}], "nvidia/x"))),
            patch.object(orch, "_review_plan", new=AsyncMock(return_value=("APPROVE", "anthropic/claude-sonnet"))),
            patch.object(orch._policy, "check", new=AsyncMock(return_value=PolicyDecision(
                operation="bug.fix", tier=AuthorityTier.AUTO, permitted=True, requires_captain=False, reason="ok",
            ))),
            patch.object(orch._executor, "execute_plan", new=AsyncMock(return_value={"status": "COMPLETED", "steps": []})) as exec_mock,
        ):
            result = await orch.handle_message("fix the login bug", "sess-1")
            exec_mock.assert_called_once()
            assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_ask_captain_tier_holds_for_approval_without_executing(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock(return_value=([{"tool": "run_command", "args": {}}], "nvidia/x"))),
            patch.object(orch, "_review_plan", new=AsyncMock(return_value=("APPROVE", "anthropic/claude-sonnet"))),
            patch.object(orch._policy, "check", new=AsyncMock(return_value=PolicyDecision(
                operation="db.drop_column", tier=AuthorityTier.ASK_CAPTAIN, permitted=False, requires_captain=True, reason="destructive",
            ))),
            patch.object(orch._executor, "execute_plan", new=AsyncMock()) as exec_mock,
        ):
            result = await orch.handle_message("remove the old column from leads table", "sess-1")
            exec_mock.assert_not_called()
            assert result["status"] == "PENDING_APPROVAL"

    @pytest.mark.asyncio
    async def test_never_tier_blocks_and_never_executes(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock(return_value=([{"tool": "run_command", "args": {}}], "nvidia/x"))),
            patch.object(orch, "_review_plan", new=AsyncMock(return_value=("APPROVE", "anthropic/claude-sonnet"))),
            patch.object(orch._policy, "check", new=AsyncMock(
                side_effect=PolicyViolationError("blocked: db.drop_table is NEVER tier")
            )),
            patch.object(orch._executor, "execute_plan", new=AsyncMock()) as exec_mock,
        ):
            result = await orch.handle_message("delete the entire leads table completely", "sess-1")
            exec_mock.assert_not_called()
            assert result["status"] == "NEVER_BLOCKED"

    @pytest.mark.asyncio
    async def test_reviewer_rejection_stops_before_policy_check(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock(return_value=([{"tool": "run_command", "args": {}}], "nvidia/x"))),
            patch.object(orch, "_review_plan", new=AsyncMock(return_value=("REJECT: plan deletes unrelated files", "anthropic/claude-sonnet"))),
            patch.object(orch._policy, "check", new=AsyncMock()) as policy_mock,
        ):
            result = await orch.handle_message("fix the bug", "sess-1")
            policy_mock.assert_not_called()
            assert result["status"] == "REJECTED"


class TestApproveReject:
    @pytest.mark.asyncio
    async def test_approve_nonexistent_request_returns_error(self):
        session = _mock_session()
        session.get = AsyncMock(return_value=None)
        orch = HeadquartersOrchestrator(session)
        result = await orch.approve(uuid.uuid4())
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_approve_non_pending_request_refused(self):
        session = _mock_session()
        record = MagicMock(status="COMPLETED")
        session.get = AsyncMock(return_value=record)
        orch = HeadquartersOrchestrator(session)
        result = await orch.approve(uuid.uuid4())
        assert result["ok"] is False
        assert "not awaiting approval" in result["error"]


class TestDeployActionInference:
    def test_frontend_keyword_maps_to_frontend_only(self):
        assert _infer_deploy_action("deploy the frontend changes") == "frontend-only"

    def test_backend_keyword_maps_to_backend_only(self):
        assert _infer_deploy_action("deploy the new backend code") == "backend-only"

    def test_no_keyword_defaults_to_git_pull_only(self):
        assert _infer_deploy_action("deploy production") == "git-pull-only"


class TestDeployRequestFlow:
    @pytest.mark.asyncio
    async def test_deploy_request_skips_draft_and_review(self):
        session = _mock_session()
        orch = HeadquartersOrchestrator(session)
        with (
            patch.object(orch, "_draft_plan", new=AsyncMock()) as draft_mock,
            patch.object(orch, "_review_plan", new=AsyncMock()) as review_mock,
            patch.object(orch._policy, "check", new=AsyncMock(return_value=PolicyDecision(
                operation="production.deploy", tier=AuthorityTier.ASK_CAPTAIN,
                permitted=False, requires_captain=True, reason="blast radius",
            ))),
        ):
            result = await orch.handle_message("deploy production", "sess-1")
            draft_mock.assert_not_called()
            review_mock.assert_not_called()
            assert result["status"] == "PENDING_APPROVAL"
            assert result["plan"] == [{"tool": "production_deploy", "args": {"action": "git-pull-only"}}]

    @pytest.mark.asyncio
    async def test_approve_deploy_calls_run_deploy_not_execution_engine(self):
        session = _mock_session()
        record = MagicMock(
            status="PENDING_APPROVAL",
            operation="production.deploy",
            plan=[{"tool": "production_deploy", "args": {"action": "backend-only"}}],
        )
        session.get = AsyncMock(return_value=record)
        orch = HeadquartersOrchestrator(session)
        with (
            patch("app.services.headquarters.orchestrator.deploy.run_deploy", new=AsyncMock(
                return_value={"ok": True, "action": "backend-only", "ssm_status": "Success", "output_tail": "BACKEND_HEALTHY"},
            )) as deploy_mock,
            patch.object(orch._executor, "execute_plan", new=AsyncMock()) as exec_mock,
        ):
            result = await orch.approve(uuid.uuid4())
            deploy_mock.assert_called_once_with("backend-only")
            exec_mock.assert_not_called()
            assert record.status == "COMPLETED"
            assert "Deploy action: backend-only" in result["briefing"]

    @pytest.mark.asyncio
    async def test_approve_failed_deploy_marks_record_failed(self):
        session = _mock_session()
        record = MagicMock(
            status="PENDING_APPROVAL",
            operation="production.deploy",
            plan=[{"tool": "production_deploy", "args": {"action": "git-pull-only"}}],
        )
        session.get = AsyncMock(return_value=record)
        orch = HeadquartersOrchestrator(session)
        with patch("app.services.headquarters.orchestrator.deploy.run_deploy", new=AsyncMock(
            return_value={"ok": False, "error": "SSM send_command failed: boom"},
        )):
            result = await orch.approve(uuid.uuid4())
            assert record.status == "FAILED"
            assert "Failed" in result["briefing"]


class TestPlanParsing:
    def test_parses_valid_json_array_embedded_in_text(self):
        content = 'Here is the plan:\n[{"tool": "read_file", "args": {"path": "x.py"}}]\nDone.'
        plan = HeadquartersOrchestrator._parse_plan(content)
        assert plan == [{"tool": "read_file", "args": {"path": "x.py"}}]

    def test_malformed_json_returns_empty_list(self):
        assert HeadquartersOrchestrator._parse_plan("[not valid json") == []

    def test_empty_content_returns_empty_list(self):
        assert HeadquartersOrchestrator._parse_plan("") == []

    def test_non_array_json_returns_empty_list(self):
        assert HeadquartersOrchestrator._parse_plan('{"tool": "x"}') == []
