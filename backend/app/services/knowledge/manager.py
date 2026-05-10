"""
JARVIS Knowledge System — SOPs, learning records, and centralized operational knowledge base.
Everything JARVIS learns from execution is archived here for reuse and continuous improvement.
"""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.knowledge import SOPDocument, LearningRecord, KnowledgeBase
from app.services.ai.base_provider import Message

logger = logging.getLogger(__name__)

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
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        sop = SOPDocument(
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
) -> dict:
    record = LearningRecord(
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
) -> dict:
    entry = KnowledgeBase(
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


async def get_sops(db: AsyncSession, category: str | None = None) -> list[dict]:
    q = select(SOPDocument).where(SOPDocument.is_active == True).order_by(SOPDocument.created_at.desc())
    if category:
        q = q.where(SOPDocument.category == category)
    result = await db.execute(q)
    return [_serialize_sop(s) for s in result.scalars().all()]


async def get_learnings(db: AsyncSession, category: str | None = None, limit: int = 50) -> list[dict]:
    q = select(LearningRecord).order_by(LearningRecord.created_at.desc()).limit(limit)
    if category:
        q = q.where(LearningRecord.category == category)
    result = await db.execute(q)
    return [_serialize_learning(r) for r in result.scalars().all()]


async def search_knowledge(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.content.ilike(f"%{query}%") |
            KnowledgeBase.title.ilike(f"%{query}%")
        )
        .order_by(KnowledgeBase.use_count.desc())
        .limit(limit)
    )
    entries = result.scalars().all()
    # Increment use count
    for e in entries:
        e.use_count += 1
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
