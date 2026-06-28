"""
JARVIS Self-Optimization Engine — analyzes live operational metrics and generates
prioritized improvement recommendations across architecture, sales, and automation.
"""
import json
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import set_tenant_context
from app.core.config import settings
from app.core.tenant_context import get_current_tenant_id
from app.models.intelligence import OptimizationRecommendation
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

OPTIMIZER_PROMPT = """You are JARVIS — the AI operating system of Aliyar Solutions.

Analyze the current system operational context below and generate exactly 6 actionable optimization recommendations.

CURRENT SYSTEM CONTEXT:
{context}

Return ONLY a valid JSON array — no markdown, no explanation.

Each item must have exactly these fields:
- area (one of: architecture, ai_routing, security, performance, automation, devops, sales_strategy, client_experience, infrastructure)
- title (short, action-oriented, max 80 chars)
- current_state (1 sentence describing what exists now)
- recommended_state (1 sentence describing the target state)
- estimated_impact (1 sentence quantifying or qualifying the benefit)
- priority (one of: critical, high, medium, low)
- action_steps (array of 2-4 concise strings, each a concrete step)

Return ONLY the JSON array."""


async def _gather_context(db: AsyncSession) -> str:
    """Collect lightweight operational stats to inform the AI."""
    lines = []
    try:
        from app.models.lead import Lead
        lead_count = (await db.execute(select(func.count()).select_from(Lead))).scalar() or 0
        lines.append(f"Active leads in CRM: {lead_count}")
    except Exception as exc:
        logger.debug("optimizer context: lead count unavailable: %s", exc)
    try:
        from app.models.outreach import OutreachEmail
        email_count = (await db.execute(select(func.count()).select_from(OutreachEmail))).scalar() or 0
        lines.append(f"Outreach emails tracked: {email_count}")
    except Exception as exc:
        logger.debug("optimizer context: email count unavailable: %s", exc)
    try:
        from app.models.tasks import AgentTask
        task_count = (await db.execute(select(func.count()).select_from(AgentTask))).scalar() or 0
        lines.append(f"Agent tasks processed: {task_count}")
    except Exception as exc:
        logger.debug("optimizer context: task count unavailable: %s", exc)
    try:
        from app.models.crm import Contact
        contact_count = (await db.execute(select(func.count()).select_from(Contact))).scalar() or 0
        lines.append(f"CRM contacts: {contact_count}")
    except Exception as exc:
        logger.debug("optimizer context: contact count unavailable: %s", exc)

    lines += [
        "Stack: FastAPI + PostgreSQL/SQLite + APScheduler + Redis + multi-AI router (11 providers)",
        "Phase 1-4: Chat, approvals, CRM, leads, outreach, memory, tasks, OAuth, scheduler, calendar, sync, intelligence",
        "Deployment: Docker Compose (dev), AWS ECS ready (prod)",
        "Notifications: Slack Block Kit + Telegram bot + WebSocket",
    ]
    return "\n".join(lines)


async def analyze_system(db: AsyncSession, tenant_id=None) -> int:
    """Generate fresh optimization recommendations and persist them."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    tenant_uuid = _tenant_uuid(tenant_id)
    await _safe_set_tenant_context(db, tenant_uuid)
    context = await _gather_context(db)
    prompt = OPTIMIZER_PROMPT.format(context=context)
    messages = [Message(role="user", content=prompt)]

    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.REASONING,
            system_prompt="You are an expert systems architect. Return only valid JSON arrays.",
            max_tokens=3000,
        )
        if response.error:
            raise ValueError(response.error)

        if not response.content:
            logger.warning("Optimizer: AI returned empty content")
            return 0
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        items = json.loads(raw)
        if not isinstance(items, list):
            raise ValueError("Expected JSON array")

        count = 0
        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            priority = str(item.get("priority", "medium")).strip()
            if priority not in _PRIORITY_ORDER:
                priority = "medium"
            rec = OptimizationRecommendation(
                tenant_id=tenant_uuid,
                area=str(item.get("area", "architecture")).strip(),
                title=title,
                current_state=item.get("current_state", ""),
                recommended_state=item.get("recommended_state", ""),
                estimated_impact=item.get("estimated_impact", ""),
                priority=priority,
                status="pending",
                action_steps=item.get("action_steps", []),
            )
            db.add(rec)
            count += 1

        return count

    except json.JSONDecodeError as e:
        logger.warning(f"Optimizer JSON parse error: {e}")
        return 0
    except Exception as e:
        logger.warning(f"Optimizer analysis failed: {e}")
        return 0


def _tenant_uuid(tenant_id) -> uuid.UUID:
    resolved = tenant_id or get_current_tenant_id() or settings.JARVIS_DEFAULT_TENANT_ID
    if not resolved:
        raise ValueError("tenant_id is required")
    return resolved if isinstance(resolved, uuid.UUID) else uuid.UUID(str(resolved))


async def _safe_set_tenant_context(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    await set_tenant_context(db, str(tenant_id))


async def get_recommendations(db: AsyncSession, status: str | None = None) -> list[dict]:
    """Return recommendations sorted by priority."""
    q = select(OptimizationRecommendation)
    if status:
        q = q.where(OptimizationRecommendation.status == status)
    result = await db.execute(q)
    recs = result.scalars().all()
    recs.sort(key=lambda r: (_PRIORITY_ORDER.get(r.priority, 4), r.id))
    return [
        {
            "id": r.id,
            "area": r.area,
            "title": r.title,
            "current_state": r.current_state,
            "recommended_state": r.recommended_state,
            "estimated_impact": r.estimated_impact,
            "priority": r.priority,
            "status": r.status,
            "action_steps": r.action_steps or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recs
    ]


async def update_recommendation_status(db: AsyncSession, rec_id: int, new_status: str) -> bool:
    result = await db.execute(
        select(OptimizationRecommendation).where(OptimizationRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return False
    rec.status = new_status
    return True
