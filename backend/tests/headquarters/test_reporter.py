"""Tests for HQ-6: Reporting — deep briefings and autonomous operation surfacing."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.headquarters.reporter import (
    AUTONOMOUS_SESSION_ID,
    log_autonomous_operation,
    narrate_execution,
)


class TestNarrateExecution:
    def test_completed_run_lists_every_step(self):
        result = {
            "status": "COMPLETED",
            "steps": [
                {"step": 0, "tool": "read_file", "outcome": {"ok": True}},
                {"step": 1, "tool": "write_file", "outcome": {"ok": True}},
            ],
            "test_output": {"ok": True},
        }
        text = narrate_execution("bug.fix", "nvidia/deepseek-v4-pro", result)
        assert "Operation: bug.fix" in text
        assert "nvidia/deepseek-v4-pro" in text
        assert "2 step(s) taken" in text
        assert "1. read_file — done" in text
        assert "2. write_file — done" in text
        assert "Tests: passed" in text
        assert "Verified" in text

    def test_failed_run_explains_rollback(self):
        result = {
            "status": "FAILED",
            "failed_step": 1,
            "steps": [
                {"step": 0, "tool": "read_file", "outcome": {"ok": True}},
                {"step": 1, "tool": "write_file", "outcome": {"ok": False, "error": "disk full"}},
            ],
            "rollback": {"ok": True},
        }
        text = narrate_execution("bug.fix", "nvidia/x", result)
        assert "1. read_file — done" in text
        assert "2. write_file — FAILED" in text
        assert "Rolled back" in text

    def test_failed_test_stage_explains_reason(self):
        result = {
            "status": "FAILED",
            "reason": "post_execution_tests_failed",
            "steps": [{"step": 0, "tool": "write_file", "outcome": {"ok": True}}],
            "rollback": {"ok": True},
        }
        text = narrate_execution("bug.fix", "nvidia/x", result)
        assert "post_execution_tests_failed" in text
        assert "Rolled back" in text

    def test_no_operation_still_produces_readable_text(self):
        result = {"status": "COMPLETED", "steps": [], "test_output": {"ok": True}}
        text = narrate_execution(None, None, result)
        assert "0 step(s) taken" in text
        assert "Verified" in text

    def test_rollback_failure_reports_error_note(self):
        result = {
            "status": "FAILED",
            "failed_step": 0,
            "steps": [{"step": 0, "tool": "run_command", "outcome": {"ok": False}}],
            "rollback": {"ok": False, "error": "no commits to revert"},
        }
        text = narrate_execution("bug.fix", "nvidia/x", result)
        assert "Rollback note: no commits to revert" in text


class TestLogAutonomousOperation:
    @pytest.mark.asyncio
    async def test_skips_when_no_action_taken(self):
        session = AsyncMock()
        session.add = MagicMock()
        await log_autonomous_operation(session, "self_healer", "nothing happened", {}, had_action=False)
        session.add.assert_not_called()
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_when_action_taken(self):
        session = AsyncMock()
        session.add = MagicMock()
        await log_autonomous_operation(
            session, "self_healer", "reset a circuit breaker", {"actions": ["x"]}, had_action=True,
        )
        session.add.assert_called_once()
        session.commit.assert_called_once()
        record = session.add.call_args[0][0]
        assert record.session_id == AUTONOMOUS_SESSION_ID
        assert record.kind == "autonomous_operation"
        assert record.driver_model == "self_healer"
        assert record.answer_text == "reset a circuit breaker"

    @pytest.mark.asyncio
    async def test_db_error_does_not_raise(self):
        session = AsyncMock()
        session.add = MagicMock(side_effect=Exception("db down"))
        # Should not raise — autonomous reporting failures must never break the
        # underlying job (self-healer) that's calling it.
        await log_autonomous_operation(session, "self_healer", "x", {}, had_action=True)
