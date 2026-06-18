"""
JARVIS Agent-to-Agent Communication Bus.
Agents delegate, request, broadcast, and respond to each other.
All inter-agent messages are persisted and broadcast via WebSocket.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.tasks import AgentMessage, AgentTask

logger = logging.getLogger(__name__)

# Known agents in the JARVIS hierarchy
AGENTS = {
    # Managers
    "jarvis":            {"role": "CEO/Orchestrator", "focus": "Overall coordination"},
    "growth_manager":    {"role": "Growth Manager",   "focus": "Leads, outreach, revenue"},
    "ops_manager":       {"role": "Ops Manager",      "focus": "Workflows, automation"},
    "content_manager":   {"role": "Content Manager",  "focus": "Copy, proposals, reports"},
    "tech_manager":      {"role": "Tech Manager",     "focus": "DevOps, cloud, code"},
    "data_manager":      {"role": "Data Manager",     "focus": "Analytics, insights"},
    # Specialists
    "lead_scout":        {"role": "Lead Scout",       "focus": "Finding new leads"},
    "outreach_agent":    {"role": "Outreach Agent",   "focus": "Writing + sending emails"},
    "crm_agent":         {"role": "CRM Agent",        "focus": "Updating contacts/deals"},
    "research_agent":    {"role": "Research Agent",   "focus": "Market and company intel"},
    "content_writer":    {"role": "Content Writer",   "focus": "Blog, proposals, decks"},
    "approval_agent":    {"role": "Approval Agent",   "focus": "Managing approval queue"},
    "memory_agent":      {"role": "Memory Agent",     "focus": "Storing and recalling info"},
    "scheduler_agent":   {"role": "Scheduler Agent",  "focus": "Calendar and timing"},
    "reporting_agent":   {"role": "Reporting Agent",  "focus": "Daily/weekly reports"},
    "automation_agent":  {"role": "Automation Agent", "focus": "n8n workflow triggers"},
}


async def send_message(db: AsyncSession,
                       from_agent: str, to_agent: str,
                       content: str,
                       message_type: str = "request",
                       payload: dict = None,
                       task_id: Optional[int] = None) -> AgentMessage:
    msg = AgentMessage(
        from_agent=from_agent, to_agent=to_agent,
        content=content, message_type=message_type,
        payload=payload or {}, task_id=task_id,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    logger.info(f"Agent msg: {from_agent} → {to_agent} [{message_type}]")

    try:
        from app.api.v1.routes.ws import broadcast
        await broadcast("agent_message", {
            "id": msg.id,
            "from": from_agent, "to": to_agent,
            "type": message_type, "content": content[:200],
            "task_id": task_id,
        })
    except Exception as exc:
        logger.warning("WebSocket broadcast failed for agent message %s: %s", msg.id, exc)

    return msg


async def get_inbox(db: AsyncSession, agent: str, unread_only: bool = True) -> list[AgentMessage]:
    q = select(AgentMessage).where(AgentMessage.to_agent == agent).order_by(desc(AgentMessage.created_at)).limit(50)
    if unread_only:
        q = q.where(AgentMessage.status == "sent")
    r = await db.execute(q)
    return list(r.scalars().all())


async def mark_read(db: AsyncSession, message_id: int) -> Optional[AgentMessage]:
    r = await db.execute(select(AgentMessage).where(AgentMessage.id == message_id))
    msg = r.scalar_one_or_none()
    if msg:
        msg.status = "read"
        msg.read_at = datetime.now(timezone.utc)
        await db.flush()
    return msg


async def delegate_task(db: AsyncSession,
                        from_agent: str, to_agent: str,
                        task_title: str, task_description: str,
                        task_type: str = "research",
                        priority: int = 5,
                        payload: dict = None) -> tuple[AgentTask, AgentMessage]:
    """Delegate a task from one agent to another — creates both task and message."""
    from app.services.tasks.queue import enqueue
    task = await enqueue(
        db=db, title=task_title, description=task_description,
        task_type=task_type, priority=priority,
        payload=payload or {}, assigned_to=to_agent, created_by=from_agent,
    )
    msg = await send_message(
        db=db, from_agent=from_agent, to_agent=to_agent,
        content=f"Delegated: {task_title}",
        message_type="delegate", task_id=task.id,
        payload={"task_id": task.id, "priority": priority},
    )
    return task, msg


async def broadcast_to_all(db: AsyncSession, from_agent: str,
                           content: str, payload: dict = None) -> list[AgentMessage]:
    """Broadcast a message to all agents (e.g. morning brief from JARVIS)."""
    msgs = []
    for agent_name in AGENTS:
        if agent_name != from_agent:
            msg = await send_message(db, from_agent, agent_name, content,
                                     "broadcast", payload)
            msgs.append(msg)
    return msgs


async def get_agent_status(db: AsyncSession) -> dict:
    """Return all agents with their pending task counts."""
    from sqlalchemy import func
    result = {}
    for name, info in AGENTS.items():
        pending = await db.scalar(
            select(func.count()).select_from(AgentTask)
            .where(AgentTask.assigned_to == name)
            .where(AgentTask.status.in_(["queued", "running"]))
        ) or 0
        unread = await db.scalar(
            select(func.count()).select_from(AgentMessage)
            .where(AgentMessage.to_agent == name)
            .where(AgentMessage.status == "sent")
        ) or 0
        result[name] = {**info, "pending_tasks": pending, "unread_messages": unread}
    return result
