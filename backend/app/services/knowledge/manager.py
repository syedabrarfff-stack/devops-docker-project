"""
JARVIS Knowledge System — SOPs, learning records, and centralized operational knowledge base.
Everything JARVIS learns from execution is archived here for reuse and continuous improvement.
"""
import json
import logging
import uuid as _uuid_mod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.knowledge import SOPDocument, LearningRecord, KnowledgeBase
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

_SYSTEM_TENANT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _resolve_tenant(tenant_id=None) -> _uuid_mod.UUID:
    if tenant_id:
        return _uuid_mod.UUID(str(tenant_id))
    try:
        from app.core.config import settings
        tid = settings.JARVIS_DEFAULT_TENANT_ID
        if tid:
            return _uuid_mod.UUID(str(tid))
    except Exception:
        pass
    return _uuid_mod.UUID(_SYSTEM_TENANT)

SOP_GEN_PROMPT = """You are JARVIS — the operations intelligence of Aliyar Solutions.

Generate a complete Standard Operating Procedure (SOP) for the following process.

PROCESS: {title}
CATEGORY: {category}
CONTEXT: {context}

Return ONLY valid JSON with exactly these fields:
{{
  "title": "...",
  "summary": "1-2 sentence overview",
  "steps": [
    {{"step": 1, "description": "...", "agent_responsible": "...", "tools": ["..."]}}
  ],
  "triggers": ["condition that activates this SOP"],
  "estimated_duration": "e.g. 15 minutes"
}}

Steps should be specific, actionable, and assigned to the correct JARVIS agent.
Return ONLY the JSON object."""


async def generate_sop(
    db: AsyncSession,
    title: str,
    category: str,
    context: str = "",
    tenant_id=None,
) -> dict | None:
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import TaskType

    prompt = SOP_GEN_PROMPT.format(title=title, category=category, context=context)
    messages = [Message(role="user", content=prompt)]
    try:
        response, _ = await ai_router.chat(
            messages,
            task_type=TaskType.REASONING,
            system_prompt="You are an operations expert. Return only valid JSON.",
            max_tokens=2000,
        )
        if response.error:
            raise ValueError(response.error)
        raw = (response.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        sop = SOPDocument(
            tenant_id=_resolve_tenant(tenant_id),
            title=str(data.get("title", title)),
            category=category,
            summary=data.get("summary", ""),
            steps=data.get("steps", []),
            triggers=data.get("triggers", []),
            estimated_duration=data.get("estimated_duration", ""),
            is_active=True,
        )
        db.add(sop)
        await db.flush()
        return _serialize_sop(sop)
    except Exception as e:
        logger.warning(f"SOP generation failed: {e}")
        return None


async def log_learning(
    db: AsyncSession,
    category: str,
    event_type: str,
    title: str,
    what_happened: str,
    lesson: str,
    what_worked: str = "",
    what_failed: str = "",
    impact_score: int = 5,
    source: str = "system",
    tenant_id=None,
) -> dict:
    record = LearningRecord(
        tenant_id=_resolve_tenant(tenant_id),
        category=category,
        event_type=event_type,
        title=title,
        what_happened=what_happened,
        what_worked=what_worked,
        what_failed=what_failed,
        lesson=lesson,
        applied_to=[],
        impact_score=impact_score,
        source=source,
    )
    db.add(record)
    await db.flush()
    return _serialize_learning(record)


async def add_knowledge(
    db: AsyncSession,
    title: str,
    category: str,
    content: str,
    tags: list[str] = None,
    source: str = "manual",
    tenant_id=None,
) -> dict:
    entry = KnowledgeBase(
        tenant_id=_resolve_tenant(tenant_id),
        title=title,
        category=category,
        content=content,
        tags=tags or [],
        source=source,
        is_verified=False,
    )
    db.add(entry)
    await db.flush()
    return _serialize_kb(entry)


async def get_sops(db: AsyncSession, category: str | None = None, tenant_id=None) -> list[dict]:
    tid = _resolve_tenant(tenant_id)
    q = (
        select(SOPDocument)
        .where(SOPDocument.is_active == True, SOPDocument.tenant_id == tid)
        .order_by(SOPDocument.created_at.desc())
    )
    if category:
        q = q.where(SOPDocument.category == category)
    result = await db.execute(q)
    return [_serialize_sop(s) for s in result.scalars().all()]


async def get_learnings(db: AsyncSession, category: str | None = None, limit: int = 50, tenant_id=None) -> list[dict]:
    tid = _resolve_tenant(tenant_id)
    q = (
        select(LearningRecord)
        .where(LearningRecord.tenant_id == tid)
        .order_by(LearningRecord.created_at.desc())
        .limit(limit)
    )
    if category:
        q = q.where(LearningRecord.category == category)
    result = await db.execute(q)
    return [_serialize_learning(r) for r in result.scalars().all()]


async def search_knowledge(db: AsyncSession, query: str, limit: int = 20, tenant_id=None) -> list[dict]:
    tid = _resolve_tenant(tenant_id)
    result = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.tenant_id == tid,
            KnowledgeBase.content.ilike(f"%{query}%") |
            KnowledgeBase.title.ilike(f"%{query}%")
        )
        .order_by(KnowledgeBase.use_count.desc())
        .limit(limit)
    )
    entries = result.scalars().all()
    for e in entries:
        e.use_count += 1
    await db.flush()
    return [_serialize_kb(e) for e in entries]


def _serialize_sop(s: SOPDocument) -> dict:
    return {
        "id": s.id, "title": s.title, "category": s.category,
        "summary": s.summary, "steps": s.steps or [], "triggers": s.triggers or [],
        "estimated_duration": s.estimated_duration, "version": s.version,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _serialize_learning(r: LearningRecord) -> dict:
    return {
        "id": r.id, "category": r.category, "event_type": r.event_type,
        "title": r.title, "what_happened": r.what_happened,
        "what_worked": r.what_worked, "what_failed": r.what_failed,
        "lesson": r.lesson, "impact_score": r.impact_score, "source": r.source,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_kb(e: KnowledgeBase) -> dict:
    return {
        "id": e.id, "title": e.title, "category": e.category,
        "content": e.content, "tags": e.tags or [], "source": e.source,
        "is_verified": e.is_verified, "use_count": e.use_count,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
