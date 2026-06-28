"""
JARVIS Memory Manager — three-tier memory system.
  episodic    : specific interactions and events
  semantic    : extracted facts and knowledge
  instruction : Captain's standing orders
  working     : current session scratchpad
  learning    : self-improvement insights from outcome analysis
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, func as sqlfunc
from app.models.memory import Memory, ConversationSummary
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)
SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

SUMMARY_THRESHOLD = 20


async def store_memory(
    db: AsyncSession,
    content: str,
    memory_type: str = "episodic",
    session_id: Optional[str] = None,
    importance: float = 0.5,
    tags: list = None,
    key: str = None,
) -> Memory:
    k = key or content[:200]
    m = Memory(
        tenant_id=SYSTEM_TENANT_ID,
        key=k, value=content, memory_type=memory_type,
        session_id=session_id, importance=importance, tags=tags or []
    )
    db.add(m)
    await db.flush()
    return m


async def recall(
    db: AsyncSession,
    query: str,
    limit: int = 5,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
) -> list[Memory]:
    """Keyword + importance-ranked recall."""
    q = select(Memory).order_by(desc(Memory.importance), desc(Memory.created_at)).limit(limit * 4)
    if session_id:
        q = q.where((Memory.session_id == session_id) | (Memory.session_id.is_(None)))
    if memory_type:
        q = q.where(Memory.memory_type == memory_type)
    rows = (await db.execute(q)).scalars().all()

    if not query.strip():
        results = list(rows[:limit])
    else:
        query_lower = query.lower()
        scored = []
        for m in rows:
            hits = sum(1 for w in query_lower.split() if len(w) > 2 and (w in m.key.lower() or w in m.value.lower()))
            scored.append((hits, m))
        scored.sort(key=lambda x: (-x[0], -x[1].importance))
        results = [m for _, m in scored[:limit]]

    if results:
        result_ids = [m.id for m in results]
        await db.execute(
            update(Memory)
            .where(Memory.id.in_(result_ids))
            .values(
                access_count=Memory.access_count + 1,
                last_accessed=datetime.now(timezone.utc),
            )
        )
    return results


async def store_instruction(
    db: AsyncSession,
    content: str,
    category: str = "general",
    priority: int = 5,
    key: str = None,
) -> Memory:
    """Store a standing order from Captain (persists globally)."""
    k = key or f"instruction:{category}:{content[:80]}"
    existing = (await db.execute(
        select(Memory).where(Memory.memory_type == "instruction").where(Memory.key == k)
    )).scalar_one_or_none()
    if existing:
        existing.value = content
        existing.importance = min(priority / 10.0, 1.0)
        existing.tags = [category]
        await db.flush()
        return existing
    return await store_memory(db, content, "instruction", importance=min(priority / 10.0, 1.0), tags=[category], key=k)


async def get_instructions(
    db: AsyncSession,
    category: Optional[str] = None,
) -> list[Memory]:
    q = select(Memory).where(Memory.memory_type == "instruction").order_by(desc(Memory.importance)).limit(200)
    if category:
        q = q.where(Memory.tags.contains([category]))
    r = await db.execute(q)
    return list(r.scalars().all())


async def auto_save_exchange(
    db: AsyncSession,
    captain_message: str,
    jarvis_response: str,
    session_id: Optional[str] = None,
    tags: list = None,
) -> None:
    """Auto-save a Captain ↔ JARVIS exchange as episodic memory."""
    try:
        content = f"Captain: {captain_message[:300]}\nJARVIS: {jarvis_response[:500]}"
        await store_memory(
            db,
            content=content,
            memory_type="episodic",
            session_id=session_id,
            importance=0.6,
            tags=tags or ["conversation"],
            key=f"exchange:{captain_message[:100]}"
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Auto-save exchange failed: {e}")


async def build_context(
    db: AsyncSession,
    session_id: Optional[str] = None,
    query: str = "",
    limit: int = 6,
) -> str:
    """Build a concise memory context string to prepend to AI prompts."""
    instructions = await get_instructions(db)
    relevant = await recall(db, query=query, limit=limit, session_id=session_id)
    learnings = await recall(db, query=query, limit=3, memory_type="learning")

    summary_row = None
    if session_id:
        summary_row = (await db.execute(
            select(ConversationSummary)
            .where(ConversationSummary.session_id == session_id)
            .order_by(desc(ConversationSummary.created_at))
            .limit(1)
        )).scalar_one_or_none()

    parts = []
    if instructions:
        inst_text = "\n".join(f"- {m.value[:200]}" for m in instructions[:5])
        parts.append(f"CAPTAIN'S STANDING ORDERS:\n{inst_text}")
    if summary_row:
        parts.append(f"PREVIOUS SESSION SUMMARY:\n{summary_row.summary}")
    if relevant:
        facts = "\n".join(f"- {m.value[:300]}" for m in relevant)
        parts.append(f"RELEVANT MEMORY:\n{facts}")
    if learnings:
        learn_text = "\n".join(f"- {m.value[:200]}" for m in learnings)
        parts.append(f"JARVIS LEARNINGS:\n{learn_text}")

    return "\n\n".join(parts) if parts else ""


async def get_memory_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(sqlfunc.count()).select_from(Memory)) or 0
    by_type = {}
    for mtype in ["episodic", "semantic", "instruction", "learning", "working"]:
        count = await db.scalar(
            select(sqlfunc.count()).select_from(Memory).where(Memory.memory_type == mtype)
        ) or 0
        if count:
            by_type[mtype] = count
    return {"total": total, "by_type": by_type}


async def maybe_summarise(
    db: AsyncSession,
    session_id: str,
    force: bool = False,
) -> Optional[ConversationSummary]:
    """If session has > SUMMARY_THRESHOLD turns, summarise to compress context."""
    last_summary_turns = await db.scalar(
        select(ConversationSummary.turn_count)
        .where(ConversationSummary.session_id == session_id)
        .order_by(desc(ConversationSummary.created_at))
        .limit(1)
    ) or 0

    total = await db.scalar(
        select(sqlfunc.count()).select_from(Conversation)
        .where(Conversation.session_id == session_id)
    ) or 0

    if not force and (total - last_summary_turns) < SUMMARY_THRESHOLD:
        return None

    rows = (await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .offset(last_summary_turns)
        .limit(SUMMARY_THRESHOLD + 5)
    )).scalars().all()

    if not rows:
        return None

    transcript = "\n".join(f"{r.role.upper()}: {r.content[:200]}" for r in rows)
    prompt = (
        "Summarise this JARVIS conversation in 4-6 bullet points.\n"
        "Extract: key decisions made, topics discussed, Captain preferences, action items agreed, insights shared.\n\n"
        f"{transcript}"
    )
    try:
        from app.services.ai.router import ai_router
        resp, _ = await asyncio.wait_for(
            ai_router.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type="FAST",
                max_tokens=600,
            ),
            timeout=30.0,
        )
        summary_text = resp.content or f"Conversation of {len(rows)} turns."
    except Exception:
        summary_text = f"Conversation covering {len(rows)} turns."

    s = ConversationSummary(
        tenant_id=SYSTEM_TENANT_ID,
        session_id=session_id, summary=summary_text,
        topics=[], turn_count=total
    )
    db.add(s)
    await db.flush()
    return s
