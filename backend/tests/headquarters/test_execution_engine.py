"""Tests for HQ-3: Execution Engine — plan execution, audit logging, rollback."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.headquarters.execution_engine import ExecutionEngine


def _mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


class TestExecutePlan:
    @pytest.mark.asyncio
    async def test_all_steps_succeed_and_tests_pass(self):
        session = _mock_session()
        engine = ExecutionEngine(session)

        plan = [{"tool": "list_dir", "args": {"path": "."}}]

        with (
            patch("app.services.headquarters.execution_engine.tools.git_current_commit", return_value="abc123"),
            patch("app.services.headquarters.execution_engine.tools.run_tests", return_value={"ok": True, "stdout": "5 passed"}),
        ):
            result = await engine.execute_plan(plan, actor="test")
            assert result["status"] == "COMPLETED"
            assert len(result["steps"]) == 1
            assert result["steps"][0]["outcome"]["ok"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_fails_and_rolls_back(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        plan = [{"tool": "delete_everything", "args": {}}]

        with (
            patch("app.services.headquarters.execution_engine.tools.git_current_commit", return_value="abc123"),
            patch.object(engine, "rollback", new=AsyncMock(return_value={"ok": True})) as rollback_mock,
        ):
            result = await engine.execute_plan(plan, actor="test")
            assert result["status"] == "FAILED"
            assert result["failed_step"] == 0
            rollback_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_step_failure_stops_immediately_no_further_steps_run(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        plan = [
            {"tool": "read_file", "args": {"path": "/nonexistent/../../../etc/passwd"}},
            {"tool": "list_dir", "args": {"path": "."}},
        ]

        with (
            patch("app.services.headquarters.execution_engine.tools.git_current_commit", return_value="abc123"),
            patch.object(engine, "rollback", new=AsyncMock(return_value={"ok": True})),
        ):
            result = await engine.execute_plan(plan, actor="test")
            assert result["status"] == "FAILED"
            assert len(result["steps"]) == 1  # second step never ran

    @pytest.mark.asyncio
    async def test_post_execution_test_failure_triggers_rollback(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        plan = [{"tool": "list_dir", "args": {"path": "."}}]

        with (
            patch("app.services.headquarters.execution_engine.tools.git_current_commit", return_value="abc123"),
            patch("app.services.headquarters.execution_engine.tools.run_tests", return_value={"ok": False, "stderr": "1 failed"}),
            patch.object(engine, "rollback", new=AsyncMock(return_value={"ok": True})) as rollback_mock,
        ):
            result = await engine.execute_plan(plan, actor="test")
            assert result["status"] == "FAILED"
            assert result["reason"] == "post_execution_tests_failed"
            rollback_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_bad_arguments_reported_not_raised(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        plan = [{"tool": "read_file", "args": {"wrong_kwarg": "x"}}]

        with (
            patch("app.services.headquarters.execution_engine.tools.git_current_commit", return_value="abc123"),
            patch.object(engine, "rollback", new=AsyncMock(return_value={"ok": True})),
        ):
            result = await engine.execute_plan(plan, actor="test")
            assert result["status"] == "FAILED"
            assert "Bad arguments" in result["steps"][0]["outcome"]["error"]


class TestRollback:
    @pytest.mark.asyncio
    async def test_no_commit_to_roll_back_to(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        result = await engine.rollback(None, actor="test")
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_no_new_commits_is_a_noop(self):
        session = _mock_session()
        engine = ExecutionEngine(session)
        with patch(
            "app.services.headquarters.execution_engine.tools.run_command",
            return_value={"ok": True, "stdout": "abc123\n"},
        ):
            result = await engine.rollback("abc123", actor="test")
            assert result["ok"] is True
            assert "Nothing to roll back" in result["note"]
