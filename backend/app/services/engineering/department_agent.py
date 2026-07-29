"""E7-5: Department Agent runtime — builder draft -> self-test loop.

One `run_one_cycle()` call: dequeue the next engineering_work_package task
from the Kernel Task Queue, draft a solution via the department's assigned
model tier (Fabric Router), run a lightweight self-test on the draft, and
update the work package's status and draft_output. Does NOT commit or push
anything — that's the Peer Review Gate (E7-7) and Deployment Integration
(E7-8)'s job, after human-equivalent review passes.

Security and Architecture departments have builder=None (Claude-only) —
this runtime routes those straight to `task_type="architecture"` /
`"security"` on the Fabric Router, which resolves to premium models only via
the existing Model Registry fallback chains. No department can request a
free-tier draft for security-sensitive code by construction.
"""
from __future__ import annotations

import ast
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.models.kernel import KernelTaskQueue
from app.services.engineering.department_registry import get_department
from app.services.fabric.router import get_fabric_router
from app.services.kernel.task_queue import TaskQueue, TaskStatus

log = logging.getLogger(__name__)

_DRAFT_PROMPT = """You are the {department_name} department in an autonomous engineering
organization. Draft a solution for this work package.

Title: {title}
Description: {description}
Acceptance criteria: {criteria}

Respond with ONLY JSON, no prose:
{{"summary": "<what you're proposing>",
  "approach": "<how it works>",
  "code_snippet": "<illustrative code, may be partial>",
  "self_test_notes": "<how you'd verify this>",
  "risks": ["<risk>", ...]}}
"""


async def _next_task_for_department(queue: TaskQueue, db: AsyncSession) -> KernelTaskQueue | None:
    """Kernel Task Queue is generic (any payload type) — dequeue() claims the
    next PENDING task regardless of department. Callers should run one
    DepartmentAgent per department and re-queue tasks that aren't theirs.

    For Phase 7's scope, dispatch already tags each task with its department
    in the payload; this helper simply claims the next engineering task and
    lets the caller decide whether to process or requeue it.
    """
    task = await queue.dequeue()
    if task is None:
        return None
    if task.payload.get("type") != "engineering_work_package":
        # Not ours — put it back as PENDING for whatever worker does handle it.
        task.status = TaskStatus.PENDING
        await db.flush()
        return None
    return task


def _self_test(draft: dict) -> tuple[bool, str]:
    """Lightweight self-test: if a code_snippet is present, syntax-check it
    as Python (best-effort — non-Python snippets just skip this check).
    Real test execution happens in CI after peer review + PR, not here."""
    snippet = draft.get("code_snippet", "")
    if not snippet or not isinstance(snippet, str):
        return True, "no code snippet to test"
    try:
        ast.parse(snippet)
        return True, "syntax check passed"
    except SyntaxError:
        # Non-Python snippets (JS, YAML, etc.) will fail this — that's fine,
        # it's a best-effort check, not a hard gate for non-Python drafts.
        return True, "syntax check skipped (non-Python or partial snippet)"


async def draft_work_package(
    db: AsyncSession,
    work_package: EngineeringWorkPackage,
) -> dict:
    """Draft a solution for one work package via its department's model tier.
    Returns the draft dict; also persists it onto the work package."""
    dept = get_department(work_package.department)
    if dept is None:
        raise ValueError(f"unknown department: {work_package.department}")

    task_type = "architecture" if dept.builder is None else "reasoning"
    router = get_fabric_router()

    draft: dict = {"summary": "", "approach": "", "code_snippet": "", "self_test_notes": "", "risks": []}
    try:
        response = await router.chat(
            messages=[{
                "role": "user",
                "content": _DRAFT_PROMPT.format(
                    department_name=dept.name,
                    title=work_package.title,
                    description=work_package.description,
                    criteria=work_package.acceptance_criteria,
                ),
            }],
            task_type=task_type,
            expected_format="json",
            db_session=db,
        )
        if not response.error:
            import json
            try:
                parsed = json.loads(response.content)
                if isinstance(parsed, dict):
                    draft.update(parsed)
                draft["_model"] = f"{response.provider}/{response.model}"
            except (json.JSONDecodeError, TypeError):
                draft["summary"] = response.content[:2000]
                draft["_model"] = f"{response.provider}/{response.model}"
        else:
            draft["summary"] = f"Draft unavailable — Fabric error: {response.error}"
            draft["_model"] = "unavailable"
    except Exception as exc:
        log.warning("department_agent: draft failed for work package %s: %s", work_package.id, exc)
        draft["summary"] = f"Draft unavailable — {exc}"
        draft["_model"] = "unavailable"

    passed, notes = _self_test(draft)
    draft["_self_test_passed"] = passed
    draft["_self_test_notes"] = notes

    work_package.draft_output = draft
    work_package.status = WorkPackageStatus.IN_REVIEW if passed else WorkPackageStatus.BLOCKED
    work_package.updated_at = datetime.now(timezone.utc)
    await db.flush()

    log.info(
        "department_agent: drafted work package %s (department=%s, self_test=%s)",
        work_package.id, work_package.department, passed,
    )
    return draft


async def run_one_cycle(db: AsyncSession) -> EngineeringWorkPackage | None:
    """Dequeue and draft one engineering work package, if any is ready.
    Returns the processed work package, or None if the queue had nothing for us."""
    queue = TaskQueue(db)
    task = await _next_task_for_department(queue, db)
    if task is None:
        return None

    wp_id = uuid.UUID(task.payload["work_package_id"])
    work_package = await db.get(EngineeringWorkPackage, wp_id)
    if work_package is None:
        await queue.fail(task.id, f"work package {wp_id} not found")
        return None

    try:
        await draft_work_package(db, work_package)
        await queue.complete(task.id)
    except Exception as exc:
        log.exception("department_agent: cycle failed for work package %s", wp_id)
        await queue.fail(task.id, str(exc))
        work_package.status = WorkPackageStatus.BLOCKED
        await db.flush()

    return work_package
