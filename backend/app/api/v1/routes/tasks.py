from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rate_limit import limiter

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default="", max_length=10_000)
    task_type: Optional[str] = Field(default="general", max_length=100)
    priority: Optional[int] = Field(default=5, ge=1, le=10)
    assigned_to: Optional[str] = Field(default="jarvis", max_length=100)
    payload: Optional[dict] = None


class MessageIn(BaseModel):
    from_agent: str = Field(..., max_length=100)
    to_agent: str = Field(..., max_length=100)
    content: str = Field(..., min_length=1, max_length=32_000)
    message_type: Optional[str] = Field(default="request", max_length=50)
    payload: Optional[dict] = None


class DelegateIn(BaseModel):
    from_agent: str = Field(..., max_length=100)
    to_agent: str = Field(..., max_length=100)
    task_title: str = Field(..., min_length=1, max_length=500)
    task_description: Optional[str] = Field(default="", max_length=10_000)
    task_type: Optional[str] = Field(default="research", max_length=100)
    priority: Optional[int] = Field(default=5, ge=1, le=10)
    payload: Optional[dict] = None


# ── Task Queue ────────────────────────────────────────────────────────────

@router.post("/enqueue")
@limiter.limit("20/minute")
async def enqueue_task(request: Request, body: TaskIn, db: AsyncSession = Depends(get_db)):
    from app.services.tasks.queue import enqueue
    task = await enqueue(
        db=db, title=body.title, description=body.description or "",
        task_type=body.task_type, priority=body.priority,
        payload=body.payload or {}, assigned_to=body.assigned_to,
    )
    await db.commit()
    return {"id": task.id, "title": task.title, "status": task.status,
            "priority": task.priority}


@router.get("/queue")
async def queue_stats(db: AsyncSession = Depends(get_db)):
    from app.services.tasks.queue import get_queue_stats
    return await get_queue_stats(db)


@router.get("/")
async def list_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, desc
    from app.models.tasks import AgentTask
    q = select(AgentTask).order_by(desc(AgentTask.created_at)).limit(limit)
    if status:
        q = q.where(AgentTask.status == status)
    if assigned_to:
        q = q.where(AgentTask.assigned_to == assigned_to)
    rows = (await db.execute(q)).scalars().all()
    return [{
        "id": t.id, "title": t.title, "status": t.status,
        "task_type": t.task_type, "priority": t.priority,
        "assigned_to": t.assigned_to, "created_by": t.created_by,
        "result": t.result, "error": t.error,
        "created_at": str(t.created_at),
    } for t in rows]


@router.get("/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.tasks import AgentTask
    task = (await db.execute(select(AgentTask).where(AgentTask.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "status": task.status, "task_type": task.task_type, "priority": task.priority,
        "assigned_to": task.assigned_to, "result": task.result, "error": task.error,
        "payload": task.payload, "created_at": str(task.created_at),
        "completed_at": str(task.completed_at) if task.completed_at else None,
    }


# ── Agent Messages ────────────────────────────────────────────────────────

@router.post("/messages/send")
@limiter.limit("10/minute")
async def send_agent_message(request: Request, body: MessageIn, db: AsyncSession = Depends(get_db)):
    from app.services.agents.communication import send_message
    msg = await send_message(
        db=db, from_agent=body.from_agent, to_agent=body.to_agent,
        content=body.content, message_type=body.message_type,
        payload=body.payload or {},
    )
    await db.commit()
    return {"id": msg.id, "from": msg.from_agent, "to": msg.to_agent,
            "type": msg.message_type}


@router.get("/messages/inbox/{agent}")
async def agent_inbox(
    agent: str,
    unread_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    from app.services.agents.communication import get_inbox
    messages = await get_inbox(db, agent=agent, unread_only=unread_only)
    return [{
        "id": m.id, "from": m.from_agent, "content": m.content,
        "type": m.message_type, "status": m.status,
        "task_id": m.task_id, "created_at": str(m.created_at),
    } for m in messages]


@router.post("/messages/{message_id}/read")
@limiter.limit("30/minute")
async def mark_message_read(request: Request, message_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.agents.communication import mark_read
    msg = await mark_read(db, message_id)
    if not msg:
        raise HTTPException(404, "Message not found")
    await db.commit()
    return {"id": msg.id, "status": msg.status}


@router.post("/delegate")
@limiter.limit("10/minute")
async def delegate_task(request: Request, body: DelegateIn, db: AsyncSession = Depends(get_db)):
    from app.services.agents.communication import delegate_task as do_delegate
    task, msg = await do_delegate(
        db=db, from_agent=body.from_agent, to_agent=body.to_agent,
        task_title=body.task_title, task_description=body.task_description or "",
        task_type=body.task_type, priority=body.priority,
        payload=body.payload or {},
    )
    await db.commit()
    return {"task_id": task.id, "message_id": msg.id,
            "from": body.from_agent, "to": body.to_agent}


@router.get("/agents/status")
async def agents_status(db: AsyncSession = Depends(get_db)):
    from app.services.agents.communication import get_agent_status
    return await get_agent_status(db)


@router.post("/agents/broadcast")
@limiter.limit("5/minute")
async def broadcast_to_agents(
    request: Request,
    from_agent: str,
    content: str,
    db: AsyncSession = Depends(get_db),
):
    from app.services.agents.communication import broadcast_to_all
    msgs = await broadcast_to_all(db, from_agent=from_agent, content=content)
    await db.commit()
    return {"broadcast_to": len(msgs), "from": from_agent}
