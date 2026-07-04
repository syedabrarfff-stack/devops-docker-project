"""HQ-4: Headquarters Orchestrator — the single entry point for the
Headquarters Chat UI.

Flow for every message:
  1. Classify: status_query (read-only) or change_request (wants something
     built/fixed/deployed).
  2. status_query -> answer directly from existing health/audit/task-book
     data via the Fabric. No execution, no approval needed.
  3. change_request ->
       a. NVIDIA NIM / OpenRouter draft a plan (list of tool calls)
       b. Claude reviews the plan (correctness, safety, in-scope)
       c. Policy Engine looks up the authority tier for the inferred operation
       d. AUTO  -> Execution Engine runs it immediately
          ASK_CAPTAIN -> saved as PENDING_APPROVAL, Captain must call /approve
          NEVER -> refused, explained, nothing runs
  4. Every request is recorded in hq_action_requests; every executed step is
     recorded in audit_log (existing L6 table).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.headquarters import HQActionRequest
from app.services.fabric.router import FabricRouter
from app.services.ai.base_provider import TaskType
from app.services.headquarters.execution_engine import ExecutionEngine
from app.services.kernel.policy_engine import PolicyEngine, PolicyViolationError
from app.services.kernel.authority_matrix import AuthorityTier

log = logging.getLogger(__name__)

_CHANGE_VERBS = re.compile(
    r"\b(fix|build|add|create|update|upgrade|deploy|refactor|remove|delete|change|"
    r"implement|migrate|rewrite|patch|optimi[sz]e)\b",
    re.IGNORECASE,
)

_OPERATION_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfix|bug\b", re.IGNORECASE), "bug.fix"),
    (re.compile(r"\bsecurity|patch|vulnerab", re.IGNORECASE), "security.patch"),
    (re.compile(r"\bdeploy|production|release\b", re.IGNORECASE), "ci.fix_and_redeploy"),
    (re.compile(r"\bendpoint|route|api\b", re.IGNORECASE), "endpoint.add"),
    (re.compile(r"\bscheduler|cron|job\b", re.IGNORECASE), "scheduler.job.add"),
    (re.compile(r"\bcolumn|migration|schema\b", re.IGNORECASE), "db.add_column"),
    (re.compile(r"\bmonitor|dashboard|metric\b", re.IGNORECASE), "monitoring.configure"),
]


def _infer_operation(text: str) -> str:
    for pattern, op in _OPERATION_HINTS:
        if pattern.search(text):
            return op
    return "performance.improvement"  # safe AUTO-tier default for ambiguous asks


class HeadquartersOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._fabric = FabricRouter()
        self._policy = PolicyEngine(session)
        self._executor = ExecutionEngine(session)

    async def handle_message(self, text: str, session_id: str, actor: str = "captain") -> dict[str, Any]:
        is_change_request = bool(_CHANGE_VERBS.search(text))

        record = HQActionRequest(
            session_id=session_id,
            request_text=text,
            kind="change_request" if is_change_request else "status_query",
            status="DRAFTED",
        )
        self._session.add(record)
        await self._session.flush()

        if not is_change_request:
            answer = await self._answer_status_query(text)
            record.status = "COMPLETED"
            record.answer_text = answer
            await self._session.commit()
            return {"request_id": str(record.id), "kind": "status_query", "answer": answer}

        return await self._handle_change_request(record, text, actor)

    # ── Status queries — read-only, always AUTO tier (kernel.state.read) ──────

    async def _answer_status_query(self, text: str) -> str:
        response = await self._fabric.chat(
            messages=[{
                "role": "user",
                "content": (
                    "You are JARVIS Headquarters. Answer this Captain question using "
                    "only what you actually know about this system's state; if you "
                    "don't have live data, say what you'd need to check.\n\n"
                    f"Question: {text}"
                ),
            }],
            task_type=TaskType.ANALYSIS,
            force_provider="anthropic",
        )
        return response.content or "No response — Fabric call failed."

    # ── Change requests — draft (NIM/OpenRouter) -> review (Claude) -> gate ──

    async def _handle_change_request(self, record: HQActionRequest, text: str, actor: str) -> dict[str, Any]:
        operation = _infer_operation(text)
        record.operation = operation

        plan, driver_model = await self._draft_plan(text)
        record.plan = plan
        record.driver_model = driver_model

        verdict, reviewer_model = await self._review_plan(text, plan)
        record.reviewer_model = reviewer_model
        record.reviewer_verdict = verdict

        if "reject" in verdict.lower():
            record.status = "REJECTED"
            record.answer_text = verdict
            await self._session.commit()
            return {"request_id": str(record.id), "kind": "change_request", "status": "REJECTED", "reason": verdict}

        try:
            decision = await self._policy.check(
                operation, actor=actor, resource_id=record.id,
                details={"request_text": text, "driver_model": driver_model},
            )
        except PolicyViolationError as exc:
            record.status = "REJECTED"
            record.error = str(exc)
            await self._session.commit()
            return {"request_id": str(record.id), "kind": "change_request", "status": "NEVER_BLOCKED", "reason": str(exc)}

        record.tier = decision.tier.value

        if decision.tier == AuthorityTier.ASK_CAPTAIN:
            record.status = "PENDING_APPROVAL"
            await self._session.commit()
            return {
                "request_id": str(record.id),
                "kind": "change_request",
                "status": "PENDING_APPROVAL",
                "plan": plan,
                "reason": decision.reason,
            }

        # AUTO tier — execute immediately.
        record.status = "EXECUTING"
        await self._session.commit()
        result = await self._executor.execute_plan(plan, actor=actor, request_id=record.id)
        record.status = result["status"]
        record.result = result
        await self._session.commit()
        return {"request_id": str(record.id), "kind": "change_request", **result}

    async def approve(self, request_id: uuid.UUID, actor: str = "captain") -> dict[str, Any]:
        record = await self._session.get(HQActionRequest, request_id)
        if record is None:
            return {"ok": False, "error": "Request not found"}
        if record.status != "PENDING_APPROVAL":
            return {"ok": False, "error": f"Request is '{record.status}', not awaiting approval"}

        record.status = "EXECUTING"
        await self._session.commit()
        result = await self._executor.execute_plan(record.plan, actor=actor, request_id=record.id)
        record.status = result["status"]
        record.result = result
        await self._session.commit()
        return {"request_id": str(record.id), **result}

    async def reject(self, request_id: uuid.UUID) -> dict[str, Any]:
        record = await self._session.get(HQActionRequest, request_id)
        if record is None:
            return {"ok": False, "error": "Request not found"}
        record.status = "REJECTED"
        await self._session.commit()
        return {"ok": True, "request_id": str(record.id)}

    # ── Draft / review steps ───────────────────────────────────────────────────

    async def _draft_plan(self, text: str) -> tuple[list[dict], str]:
        prompt = (
            "You are the Headquarters drafting model. Produce a JSON list of tool "
            "calls to satisfy this request. Available tools: read_file(path), "
            "write_file(path, content), list_dir(path), run_command(argv), "
            "git_commit(message, paths), run_tests(path). "
            'Format: [{"tool": "...", "args": {...}}, ...]. '
            "Return ONLY the JSON array, nothing else.\n\n"
            f"Request: {text}"
        )
        response = await self._fabric.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.CODE,
            force_provider="nvidia",
        )
        plan = self._parse_plan(response.content)
        return plan, f"{response.provider}/{response.model}"

    async def _review_plan(self, text: str, plan: list[dict]) -> tuple[str, str]:
        prompt = (
            "You are the Headquarters reviewer. A drafting model proposed this plan "
            "for the Captain's request below. Check it is correct, safe, and in scope "
            "(nothing destructive, nothing outside what was asked). "
            "Reply starting with 'APPROVE' or 'REJECT', then one sentence why.\n\n"
            f"Request: {text}\n\nProposed plan: {json.dumps(plan)}"
        )
        response = await self._fabric.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.ANALYSIS,
            force_provider="anthropic",
        )
        return response.content or "REJECT: reviewer call failed", f"{response.provider}/{response.model}"

    @staticmethod
    def _parse_plan(content: str) -> list[dict]:
        if not content:
            return []
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group())
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
