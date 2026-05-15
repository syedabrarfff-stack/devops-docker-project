"""
JARVIS Memory Manager — three-tier memory system.
  episodic   : specific interactions and events
  semantic   : extracted facts and knowledge
  instruction: Captain's standing orders
  working    : current session scratchpad
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from app.models.memory import Memory, ConversationSummary
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

SUMMARY_THRESHOLD = 20  # summarise after this many turns


async def store_memory(db: AsyncSession, key: str, value: str,
                       memory_type: str = "semantic",
                       session_id: Optional[str] = None,
                       importance: float = 0.5,
                       tags: list = None) -> Memory:
    m = Memory(
        key=key, value=value, memory_type=memory_type,
        session_id=session_id, importance=importance, tags=tags or []
    )
    db.add(m)
    await db.flush()
    return m


async def recall(db: AsyncSession, query: str = "", limit: int = 5,
                 session_id: Optional[str] = None,
                 memory_type: Optional[str] = None) -> list[Memory]:
    """Keyword + importance-ranked recall."""
    q = select(Memory).order_by(desc(Memory.importance), desc(Memory.created_at)).limit(limit * 3)
    if session_id:
        q = q.where((Memory.session_id == session_id) | (Memory.session_id.is_(None)))
    if memory_type:
        q = q.where(Memory.memory_type == memory_type)
    rows = (await db.execute(q)).scalars().all()

    query_lower = query.lower()
    scored = []
    for m in rows:
        hits = sum(
            1 for w in query_lower.split()
            if w in (m.key or "").lower() or w in (m.value or "").lower()
        )
        scored.append((hits, m))
    scored.sort(key=lambda x: (-x[0], -x[1].importance))

    results = [m for _, m in scored[:limit]]
    # bump access counts
    for m in results:
        await db.execute(update(Memory).where(Memory.id == m.id).values(
            access_count=m.access_count + 1,
            last_accessed=datetime.now(timezone.utc)
        ))
    return results


async def store_instruction(
    db: AsyncSession,
    key: str,
    instruction: str,
    category: str = "general",
    priority: float = 1.0,
) -> Memory:
    """Store a standing order from Captain (persists globally)."""
    existing = (await db.execute(
        select(Memory).where(Memory.memory_type == "instruction").where(Memory.key == key)
    )).scalar_one_or_none()
    if existing:
        existing.value = instruction
        existing.importance = priority
        existing.tags = [category]
        await db.flush()
        return existing
    return await store_memory(db, key, instruction, "instruction", importance=priority, tags=[category])


async def get_instructions(db: AsyncSession, category: Optional[str] = None) -> list[Memory]:
    q = select(Memory).where(Memory.memory_type == "instruction").order_by(desc(Memory.importance))
    if category:
        q = q.where(Memory.tags.contains([category]))
    r = await db.execute(q)
    return list(r.scalars().all())


async def build_context(
    db: AsyncSession,
    session_id: Optional[str],
    query: str = "",
    limit: int = 6,
) -> str:
    """Build a concise memory context string to prepend to AI prompts."""
    instructions = await get_instructions(db)
    facts = await recall(db, query, limit=limit, session_id=session_id, memory_type="semantic")
    episodes = await recall(db, query, limit=limit, session_id=session_id, memory_type="episodic")
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
        inst_text = "\n".join(f"- {m.value}" for m in instructions[:5])
        parts.append(f"CAPTAIN'S STANDING ORDERS:\n{inst_text}")
    if summary_row:
        parts.append(f"SESSION SUMMARY:\n{summary_row.summary}")
    if facts:
        fact_text = "\n".join(f"- [{m.key}] {m.value}" for m in facts)
        parts.append(f"RELEVANT FACTS:\n{fact_text}")
    if episodes:
        episode_text = "\n".join(f"- {m.value[:1200]}" for m in episodes)
        parts.append(f"RECENT / RELEVANT CONVERSATION MEMORY:\n{episode_text}")

    return "\n\n".join(parts) if parts else ""


async def maybe_summarise(
    db: AsyncSession,
    session_id: str,
    force: bool = False,
) -> Optional[ConversationSummary]:
    """If session has > SUMMARY_THRESHOLD turns, ask Gemini to summarise."""
    count = await db.scalar(
        select(ConversationSummary.turn_count)
        .where(ConversationSummary.session_id == session_id)
        .order_by(desc(ConversationSummary.created_at))
        .limit(1)
    ) or 0
    from sqlalchemy import func as sqlfunc
    total = await db.scalar(
        select(sqlfunc.count()).select_from(Conversation)
        .where(Conversation.session_id == session_id)
    ) or 0
    if not force and total - count < SUMMARY_THRESHOLD:
        return None

    rows = (await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .offset(count)
        .limit(SUMMARY_THRESHOLD + 5)
    )).scalars().all()
    if not rows:
        return None

    transcript = "\n".join(f"{r.role.upper()}: {r.content[:200]}" for r in rows)
    prompt = (
        f"Summarise this conversation in 3-5 bullet points for JARVIS memory context.\n"
        f"Extract: key decisions, topics discussed, Captain preferences, action items.\n\n"
        f"{transcript}"
    )
    try:
        from app.services.ai.router import ai_router
        from app.services.ai.base_provider import Message, TaskType
        resp, _ = await ai_router.chat(
            [Message(role="user", content=prompt)],
            task_type=TaskType.FAST,
            force_provider="google",
        )
        summary_text = resp.content
    except Exception:
        summary_text = f"Conversation covering {len(rows)} turns."

    s = ConversationSummary(
        session_id=session_id, summary=summary_text,
        topics=[], turn_count=total
    )
    db.add(s)
    await db.flush()
    return s
