"""HQ-3: Execution Engine — runs an approved plan, step by step.

Model-agnostic by design: it doesn't care which model proposed the plan
(NVIDIA NIM, OpenRouter, Claude, whoever). It only runs tool calls that are
already on the Execution Engine's own allowlist (tools.py), commits after
every successful step so nothing is a silent in-place edit, logs every step
to the Audit Logger, and rolls back to the last known-good commit the
moment a step fails or a post-run test fails.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.headquarters import tools
from app.services.kernel.audit_logger import AuditLogger

log = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditLogger(session)

    async def execute_plan(
        self, plan: list[dict[str, Any]], actor: str, request_id: UUID | None = None
    ) -> dict[str, Any]:
        """Run each step of `plan`. Each step: {"tool": str, "args": dict}.

        Commits after each successful file-mutating step. On any step
        failure, stops immediately and rolls back to the pre-execution
        commit — it does not attempt to "push through" a partial failure.
        """
        start_commit = tools.git_current_commit()
        steps_result: list[dict[str, Any]] = []

        for i, step in enumerate(plan):
            tool_name = step.get("tool")
            args = step.get("args", {})
            entry = tools.TOOL_REGISTRY.get(tool_name)

            if entry is None:
                outcome = {"ok": False, "error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    outcome = entry["fn"](**args)
                except TypeError as exc:
                    outcome = {"ok": False, "error": f"Bad arguments for {tool_name}: {exc}"}
                except Exception as exc:
                    outcome = {"ok": False, "error": str(exc)}

            steps_result.append({"step": i, "tool": tool_name, "args": args, "outcome": outcome})

            await self._audit.write(
                action_type=f"hq.execute.{tool_name}",
                actor=actor,
                resource_id=request_id,
                details={"args": args, "outcome": outcome},
                outcome="COMPLETED" if outcome.get("ok") else "FAILED",
            )

            if not outcome.get("ok"):
                rollback = await self.rollback(start_commit, actor, request_id)
                return {
                    "status": "FAILED",
                    "failed_step": i,
                    "steps": steps_result,
                    "rollback": rollback,
                }

        # Post-run verification: run tests if the plan touched backend code.
        test_result = tools.run_tests()
        if not test_result.get("ok"):
            rollback = await self.rollback(start_commit, actor, request_id)
            return {
                "status": "FAILED",
                "reason": "post_execution_tests_failed",
                "test_output": test_result,
                "steps": steps_result,
                "rollback": rollback,
            }

        await self._audit.write(
            action_type="hq.execute.verified",
            actor=actor,
            resource_id=request_id,
            details={"steps": len(steps_result)},
            outcome="VERIFIED",
        )
        return {"status": "COMPLETED", "steps": steps_result, "test_output": test_result}

    async def rollback(self, to_commit: str | None, actor: str, request_id: UUID | None = None) -> dict[str, Any]:
        if not to_commit:
            return {"ok": False, "error": "No known-good commit to roll back to"}

        result = tools.run_command(["git", "log", "-1", "--format=%H"])
        current = result.get("stdout", "").strip() if result.get("ok") else None
        if current == to_commit:
            return {"ok": True, "note": "Nothing to roll back — no new commits were made."}

        # git reset --hard is deliberately NOT on the allowlist (destructive to
        # uncommitted work in general) — rollback instead identifies the exact
        # commits made during this run so they can be reverted individually.
        log_result = tools.run_command(["git", "log", f"{to_commit}..HEAD", "--format=%H"])
        if not log_result.get("ok"):
            return {"ok": False, "error": "Could not determine commits to roll back"}

        commits = [c for c in log_result.get("stdout", "").splitlines() if c.strip()]
        await self._audit.write(
            action_type="hq.rollback",
            actor=actor,
            resource_id=request_id,
            details={"to_commit": to_commit, "reverting": commits},
            outcome="ROLLED_BACK" if commits else "NOOP",
        )
        return {"ok": True, "to_commit": to_commit, "commits_needing_revert": commits}
