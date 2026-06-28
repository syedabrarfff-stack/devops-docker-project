"""
JARVIS AI Task Queue — asyncio-backed with SQLite persistence.
Background worker processes tasks using Gemini (primary) with fallback chain.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func, desc
from app.models.tasks import AgentTask
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# In-memory priority queue: (priority, task_id)
_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
_worker_running = False


async def enqueue(db: AsyncSession, title: str, description: str,
                  task_type: str = "research",
                  payload: dict = None,
                  priority: int = 5,
                  assigned_to: str = "jarvis",
                  created_by: str = "captain",
                  parent_id: Optional[int] = None) -> AgentTask:
    task = AgentTask(
        title=title, description=description, task_type=task_type,
        payload=payload or {}, priority=priority,
        assigned_to=assigned_to, created_by=created_by,
        status="queued", parent_id=parent_id,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await _queue.put((priority, task.id))
    logger.info(f"Task queued: [{task.id}] {title}")
    return task


async def _process_task(task_id: int):
    """Execute a single task using Gemini and persist result."""
    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(AgentTask).where(AgentTask.id == task_id))).scalar_one_or_none()
        if not task or task.status != "queued":
            return

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            result = await _execute(task)
            task.status = "completed"
            task.result = result
            task.model_used = "gemini-flash-latest"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Task {task_id} failed: {e}")
        finally:
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

        # Broadcast via WebSocket
        try:
            from app.api.v1.routes.ws import broadcast
            await broadcast("task_completed", {
                "id": task.id, "title": task.title,
                "status": task.status, "result": (task.result or "")[:300],
            })
        except Exception as exc:
            logger.warning("WebSocket broadcast failed for task %s: %s", task.id, exc)


async def _execute(task: AgentTask) -> str:
    from app.services.ai.router import ai_router, JARVIS_SYSTEM_PROMPT
    from app.services.ai.base_provider import Message, TaskType

    type_map = {
        "research":   TaskType.RESEARCH,
        "write":      TaskType.GENERAL,
        "analyze":    TaskType.RESEARCH,
        "summarize":  TaskType.FAST,
        "code":       TaskType.CODE,
        "math":       TaskType.MATH,
    }
    task_type = type_map.get(task.task_type, TaskType.GENERAL)

    payload_ctx = ""
    if task.payload:
        payload_ctx = "\n\nContext data:\n" + "\n".join(f"  {k}: {v}" for k, v in task.payload.items())

    prompt = f"{task.title}\n\n{task.description or ''}{payload_ctx}"
    messages = [Message(role="user", content=prompt)]

    resp, _ = await asyncio.wait_for(
        ai_router.chat(
            messages,
            task_type=task_type,
            force_provider="google",
            system_prompt=JARVIS_SYSTEM_PROMPT,
        ),
        timeout=60.0,
    )
    if resp.error:
        raise RuntimeError(resp.error)
    return (resp.content or "").strip()


async def worker():
    """Background worker — processes tasks from queue indefinitely."""
    global _worker_running
    _worker_running = True
    logger.info("JARVIS Task Worker started")
    while True:
        try:
            priority, task_id = await asyncio.wait_for(_queue.get(), timeout=5.0)
            asyncio.create_task(_process_task(task_id))
            _queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"Worker error: {e}")


async def requeue_pending():
    """On startup, re-queue any tasks that were interrupted (status=queued/running)."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(AgentTask)
            .where(AgentTask.status.in_(["queued", "running"]))
            .order_by(desc(AgentTask.priority))
            .limit(500)
        )).scalars().all()
        for t in rows:
            if t.status == "running":
                t.status = "queued"  # reset interrupted
            await _queue.put((t.priority, t.id))
        if rows:
            await db.commit()
            logger.info(f"Re-queued {len(rows)} interrupted tasks")


async def get_queue_stats(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(AgentTask.status, func.count().label("n"))
        .group_by(AgentTask.status)
    )).all()
    stats = {s: 0 for s in ("queued", "running", "completed", "failed")}
    for status, count in rows:
        if status in stats:
            stats[status] = count
    stats["queue_depth"] = _queue.qsize()
    return stats
