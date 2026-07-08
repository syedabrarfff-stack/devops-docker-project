"""E7-4: Work Package Dispatcher — routes TaskGraph nodes to their owning
department via the existing Kernel Task Queue (K1-5). No new queue.

Authority enforcement happens HERE, not just at Mission Planner decomposition
time: a work package whose `authority_tier` is ASK_CAPTAIN or NEVER is never
auto-enqueued for execution — it's marked BLOCKED and surfaced for Captain
approval, exactly like every other Headquarters action. No department can
bypass this by construction.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import EngineeringTaskGraph, EngineeringWorkPackage, TaskGraphStatus, WorkPackageStatus
from app.services.kernel.authority_matrix import AuthorityTier
from app.services.kernel.task_queue import TaskPriority, TaskQueue

log = logging.getLogger(__name__)


async def _get_work_packages(db: AsyncSession, task_graph_id: uuid.UUID) -> list[EngineeringWorkPackage]:
    result = await db.execute(
        select(EngineeringWorkPackage).where(EngineeringWorkPackage.task_graph_id == task_graph_id)
    )
    return list(result.scalars().all())


def _dependencies_satisfied(wp: EngineeringWorkPackage, by_id: dict[uuid.UUID, EngineeringWorkPackage]) -> bool:
    for dep_id in wp.depends_on or []:
        dep = by_id.get(dep_id)
        if dep is None or dep.status != WorkPackageStatus.DEPLOYED:
            return False
    return True


async def dispatch_ready_packages(db: AsyncSession, task_graph_id: uuid.UUID) -> dict[str, int]:
    """Scan a task graph and dispatch every PENDING work package whose
    dependencies are satisfied. Returns counts by outcome for observability.

    Idempotent — safe to call repeatedly (e.g. from a scheduler tick) since it
    only acts on packages still in PENDING status.
    """
    packages = await _get_work_packages(db, task_graph_id)
    by_id = {wp.id: wp for wp in packages}
    queue = TaskQueue(db)

    counts = {"enqueued": 0, "blocked": 0, "waiting_on_deps": 0, "skipped": 0}

    for wp in packages:
        if wp.status != WorkPackageStatus.PENDING:
            counts["skipped"] += 1
            continue

        if not _dependencies_satisfied(wp, by_id):
            counts["waiting_on_deps"] += 1
            continue

        tier = wp.authority_tier or AuthorityTier.ASK_CAPTAIN.value
        if tier in (AuthorityTier.ASK_CAPTAIN.value, AuthorityTier.NEVER.value):
            wp.status = WorkPackageStatus.BLOCKED
            counts["blocked"] += 1
            log.info(
                "dispatcher: work package %s (%s) BLOCKED — authority tier %s requires Captain approval",
                wp.id, wp.title, tier,
            )
            continue

        kernel_task_id = await queue.enqueue(
            payload={
                "type": "engineering_work_package",
                "work_package_id": str(wp.id),
                "task_graph_id": str(wp.task_graph_id),
                "department": wp.department,
                "operation": wp.operation,
                "title": wp.title,
                "description": wp.description,
                "acceptance_criteria": wp.acceptance_criteria,
            },
            priority=TaskPriority.NORMAL,
        )
        wp.kernel_task_id = kernel_task_id
        wp.status = WorkPackageStatus.DRAFTING
        counts["enqueued"] += 1
        log.info("dispatcher: enqueued work package %s (%s) to department=%s", wp.id, wp.title, wp.department)

    await db.flush()
    return counts


async def refresh_graph_status(db: AsyncSession, task_graph_id: uuid.UUID) -> str:
    """Recompute and persist the parent TaskGraph's status from its work
    packages' current statuses. Returns the new status string."""
    graph = await db.get(EngineeringTaskGraph, task_graph_id)
    if graph is None:
        raise ValueError(f"unknown task_graph_id: {task_graph_id}")

    packages = await _get_work_packages(db, task_graph_id)
    if not packages:
        return graph.status

    if any(wp.status == WorkPackageStatus.REJECTED for wp in packages):
        graph.status = TaskGraphStatus.FAILED
    elif all(wp.status == WorkPackageStatus.DEPLOYED for wp in packages):
        graph.status = TaskGraphStatus.COMPLETED
        from datetime import datetime, timezone
        graph.completed_at = datetime.now(timezone.utc)
    else:
        graph.status = TaskGraphStatus.IN_PROGRESS

    await db.flush()
    return graph.status
