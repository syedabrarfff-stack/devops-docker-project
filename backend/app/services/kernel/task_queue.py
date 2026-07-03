"""K1-5: JARVIS Kernel Task Queue — priority, persistent, observable.

Priorities (lower number = higher urgency):
  1 = CRITICAL   — infrastructure emergency, data integrity
  2 = HIGH       — customer-facing operations, revenue
  3 = NORMAL     — routine automation (default)
  4 = LOW        — background tasks, analytics, optimizations

All tasks are persisted in `kernel_task_queue` before execution begins —
a crash or restart can recover pending tasks by querying status='PENDING'.
The Event Bus receives 'task.completed' or 'task.failed' after each task.

Usage:
    queue = TaskQueue(db_session)
    task_id = await queue.enqueue(
        payload={"type": "lead_score", "lead_id": "..."},
        priority=TaskPriority.NORMAL,
    )
    task = await queue.dequeue()       # get next pending task
    await queue.complete(task.id)
    await queue.fail(task.id, "timeout")
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kernel import KernelTaskQueue
from app.services.kernel.event_bus import KernelEvent, get_event_bus

log = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD = "DEAD"  # max retries exhausted, awaiting Captain review


class TaskQueue:
    """Async task queue backed by PostgreSQL for durability.

    One instance per request (or long-lived with explicit session management).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(
        self,
        payload: dict,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ) -> uuid.UUID:
        """Persist a new task and return its ID. Publishes 'task.queued' event."""
        task = KernelTaskQueue(
            priority=int(priority),
            status=TaskStatus.PENDING,
            retry_count=0,
            max_retries=max_retries,
            payload=payload,
        )
        self._session.add(task)
        await self._session.flush()

        log.debug(
            "TaskQueue: enqueued %s (priority=%s, id=%s)",
            payload.get("type", "unknown"),
            priority.name,
            task.id,
        )

        try:
            await get_event_bus().emit(
                "task.queued",
                payload={"task_id": str(task.id), "priority": int(priority)},
                source_engine="task_queue",
            )
        except Exception as exc:
            log.warning("TaskQueue: event bus emit failed (non-fatal): %s", exc)

        return task.id

    # ── Dequeue ───────────────────────────────────────────────────────────────

    async def dequeue(self) -> Optional[KernelTaskQueue]:
        """Claim the highest-priority PENDING task (SKIP LOCKED for concurrency).

        Returns None if the queue is empty.
        """
        # SELECT ... FOR UPDATE SKIP LOCKED ensures no two workers grab the same task.
        result = await self._session.execute(
            select(KernelTaskQueue)
            .where(KernelTaskQueue.status == TaskStatus.PENDING)
            .order_by(KernelTaskQueue.priority, KernelTaskQueue.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return None

        await self._session.execute(
            update(KernelTaskQueue)
            .where(KernelTaskQueue.id == task.id)
            .values(
                status=TaskStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )
        return task

    # ── Completion ────────────────────────────────────────────────────────────

    async def complete(self, task_id: uuid.UUID) -> None:
        """Mark a task COMPLETED. Publishes 'task.completed' event."""
        await self._session.execute(
            update(KernelTaskQueue)
            .where(KernelTaskQueue.id == task_id)
            .values(
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
            )
        )
        try:
            await get_event_bus().emit(
                "task.completed",
                payload={"task_id": str(task_id)},
                source_engine="task_queue",
            )
        except Exception as exc:
            log.warning("TaskQueue: event bus emit failed (non-fatal): %s", exc)

    async def fail(
        self,
        task_id: uuid.UUID,
        error_message: str = "",
    ) -> KernelTaskQueue | None:
        """Increment retry_count; if max_retries exhausted, mark DEAD.

        Returns the updated task record.
        """
        result = await self._session.execute(
            select(KernelTaskQueue).where(KernelTaskQueue.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            log.error("TaskQueue: fail() called on unknown task %s", task_id)
            return None

        new_retry_count = task.retry_count + 1
        new_status = (
            TaskStatus.DEAD
            if new_retry_count > task.max_retries
            else TaskStatus.PENDING
        )

        await self._session.execute(
            update(KernelTaskQueue)
            .where(KernelTaskQueue.id == task_id)
            .values(
                status=new_status,
                retry_count=new_retry_count,
                error_message=error_message[:2000] if error_message else None,
                completed_at=datetime.now(timezone.utc) if new_status == TaskStatus.DEAD else None,
            )
        )

        event_type = "task.dead" if new_status == TaskStatus.DEAD else "task.failed"
        try:
            await get_event_bus().emit(
                event_type,
                payload={
                    "task_id": str(task_id),
                    "retry_count": new_retry_count,
                    "error": error_message,
                },
                source_engine="task_queue",
            )
        except Exception as exc:
            log.warning("TaskQueue: event bus emit failed (non-fatal): %s", exc)

        if new_status == TaskStatus.DEAD:
            log.error(
                "TaskQueue: task %s DEAD after %d retries — requires Captain review",
                task_id,
                new_retry_count,
            )

        return task

    # ── Introspection ─────────────────────────────────────────────────────────

    async def depth(self) -> dict[str, int]:
        """Return pending count per priority level for observability."""
        from sqlalchemy import func, case
        result = await self._session.execute(
            select(
                KernelTaskQueue.priority,
                func.count(KernelTaskQueue.id).label("count"),
            )
            .where(KernelTaskQueue.status == TaskStatus.PENDING)
            .group_by(KernelTaskQueue.priority)
        )
        rows = result.all()
        priority_names = {1: "CRITICAL", 2: "HIGH", 3: "NORMAL", 4: "LOW"}
        return {priority_names.get(row.priority, str(row.priority)): row.count for row in rows}

    async def dead_tasks(self) -> list[KernelTaskQueue]:
        """Return all DEAD tasks for Captain review."""
        result = await self._session.execute(
            select(KernelTaskQueue)
            .where(KernelTaskQueue.status == TaskStatus.DEAD)
            .order_by(KernelTaskQueue.created_at.desc())
        )
        return list(result.scalars().all())
