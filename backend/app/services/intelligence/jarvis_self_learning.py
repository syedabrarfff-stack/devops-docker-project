"""
JARVIS Self-Learning & Evolution Engine
Runs daily. Reviews all conversations, outcomes, and activities from the last 24h.
Extracts learnings. Stores as semantic memory. JARVIS gets smarter every day.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, cast, select, desc, func as sqlfunc
from app.models.memory import Memory, OutcomeRecord
from app.models.conversation import Conversation
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

SELF_LEARNING_PROMPT = """
You are JARVIS — Supreme Operational Manager of Aliyar Solutions.

You are running your daily self-learning cycle. Below is a summary of the last 24 hours of activity:

{activity_summary}

Your task:
1. Extract 5-10 key learnings from this data (what worked, what didn't, patterns you noticed)
2. Identify Captain's preferences and working style from conversations
3. Note any strategic opportunities or risks you observed
4. Suggest 2-3 specific improvements JARVIS should make to operate better
5. Rate your own performance today: what you did well, what to improve

Format each learning as a clear, actionable insight.
Start with: "JARVIS Self-Learning Report — {date}"
"""

EXTRACT_FACTS_PROMPT = """
From this conversation between Captain and JARVIS, extract 3-5 key facts, decisions, or preferences.

Conversation:
{conversation}

Return each fact on a new line starting with "FACT:". Be specific and concise.
Focus on: decisions made, Captain preferences, business strategy, company context, client information.
"""

OUTCOME_LEARNING_PROMPT = """
JARVIS Action: {action}
Result: {outcome}
Note: {note}

What should JARVIS learn from this outcome? Write one clear, actionable lesson (2-3 sentences max).
"""


async def run_daily_learning_cycle(db: AsyncSession) -> dict:
    """
    Main daily learning cycle. Called by scheduler at midnight.
    Returns a summary of what was learned.
    """
    logger.info("JARVIS self-learning cycle starting...")
    results = {
        "conversations_reviewed": 0,
        "facts_extracted": 0,
        "outcomes_processed": 0,
        "learnings_stored": 0,
        "report": "",
        "ran_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        # 1. Get recent conversations
        recent_convs = (await db.execute(
            select(Conversation)
            .where(Conversation.created_at >= since)
            .order_by(Conversation.created_at.asc())
            .limit(100)
        )).scalars().all()

        results["conversations_reviewed"] = len(recent_convs)

        # 2. Extract facts from conversations
        if recent_convs:
            facts_count = await _extract_and_store_facts(db, recent_convs)
            results["facts_extracted"] = facts_count

        # 3. Process pending outcomes
        pending_outcomes = (await db.execute(
            select(OutcomeRecord)
            .where(OutcomeRecord.outcome != None)
            .where(OutcomeRecord.learning == None)
            .limit(20)
        )).scalars().all()

        for outcome in pending_outcomes:
            await _learn_from_outcome(db, outcome)
            results["outcomes_processed"] += 1

        # 4. Generate overall learning report
        activity_summary = _build_activity_summary(recent_convs, pending_outcomes)
        report = await _generate_learning_report(activity_summary)
        results["report"] = report

        # 5. Store the learning report as a memory
        if report:
            from app.services.memory.manager import store_memory
            await store_memory(
                db,
                content=report,
                memory_type="learning",
                importance=0.9,
                tags=["daily_learning", "self_evolution"],
                key=f"daily_learning:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            )
            results["learnings_stored"] += 1

        await db.commit()
        logger.info(f"JARVIS self-learning complete: {results}")

    except Exception as e:
        logger.error(f"Self-learning cycle failed: {e}")
        results["error"] = str(e)

    return results


async def _extract_and_store_facts(db: AsyncSession, conversations: list) -> int:
    """Extract semantic facts from recent conversations."""
    if not conversations:
        return 0

    # Group into transcript chunks of 10 turns
    count = 0
    chunk_size = 10
    for i in range(0, min(len(conversations), 50), chunk_size):
        chunk = conversations[i:i + chunk_size]
        transcript = "\n".join(
            f"{c.role.upper()}: {c.content[:300]}" for c in chunk
        )
        try:
            resp, _ = await asyncio.wait_for(
                ai_router.chat(
                    messages=[{
                        "role": "user",
                        "content": EXTRACT_FACTS_PROMPT.format(conversation=transcript)
                    }],
                    task_type="FAST",
                    max_tokens=400,
                ),
                timeout=60.0,
            )
            content = resp.content or ""
            for line in content.split("\n"):
                if line.startswith("FACT:"):
                    fact = line[5:].strip()
                    if len(fact) > 20:
                        from app.services.memory.manager import store_memory
                        await store_memory(
                            db,
                            content=fact,
                            memory_type="semantic",
                            importance=0.7,
                            tags=["auto_extracted", "conversation"],
                        )
                        count += 1
        except Exception as e:
            logger.warning(f"Fact extraction failed for chunk: {e}")

    return count


async def _learn_from_outcome(db: AsyncSession, outcome: OutcomeRecord) -> None:
    """Generate a learning from a completed outcome."""
    try:
        resp, _ = await asyncio.wait_for(
            ai_router.chat(
                messages=[{
                    "role": "user",
                    "content": OUTCOME_LEARNING_PROMPT.format(
                        action=outcome.action_detail or outcome.action_type,
                        outcome=outcome.outcome,
                        note=outcome.outcome_note or "No additional notes"
                    )
                }],
                task_type="FAST",
                max_tokens=200,
            ),
            timeout=60.0,
        )
        learning_text = resp.content or ""
        if learning_text:
            outcome.learning = learning_text
            await db.flush()

            # Also store as a memory
            from app.services.memory.manager import store_memory
            await store_memory(
                db,
                content=f"[{outcome.action_type} → {outcome.outcome}] {learning_text}",
                memory_type="learning",
                importance=0.8,
                tags=["outcome_learning", outcome.action_type],
            )
    except Exception as e:
        logger.warning(f"Outcome learning failed: {e}")


def _build_activity_summary(conversations: list, outcomes: list) -> str:
    """Build a text summary of 24h activity for the learning prompt."""
    parts = []

    if conversations:
        parts.append(f"CONVERSATIONS ({len(conversations)} turns):")
        sample = conversations[-20:]  # last 20 turns
        for c in sample:
            role = "Captain" if c.role == "user" else "JARVIS"
            parts.append(f"  {role}: {c.content[:150]}")

    if outcomes:
        parts.append(f"\nOUTCOMES ({len(outcomes)} actions resolved):")
        for o in outcomes:
            parts.append(f"  {o.action_type} → {o.outcome}: {o.outcome_note or 'no note'}")

    return "\n".join(parts) if parts else "No significant activity in last 24 hours."


async def _generate_learning_report(activity_summary: str) -> str:
    """Generate the full self-learning report."""
    try:
        date_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        prompt = SELF_LEARNING_PROMPT.format(
            activity_summary=activity_summary,
            date=date_str
        )
        resp, _ = await asyncio.wait_for(
            ai_router.chat(
                messages=[
                    {"role": "system", "content": "You are JARVIS — self-improving AI operational manager of Aliyar Solutions."},
                    {"role": "user", "content": prompt}
                ],
                task_type="RESEARCH",
                max_tokens=1500,
            ),
            timeout=60.0,
        )
        return resp.content or ""
    except Exception as e:
        logger.error(f"Learning report generation failed: {e}")
        return ""


async def record_outcome(
    db: AsyncSession,
    action_type: str,
    action_detail: str,
    action_ref: Optional[str] = None,
    outcome: Optional[str] = "pending",
    importance: float = 0.6,
) -> OutcomeRecord:
    """Record a JARVIS action for future outcome tracking."""
    record = OutcomeRecord(
        action_type=action_type,
        action_ref=action_ref,
        action_detail=action_detail,
        outcome=outcome,
        importance=importance,
    )
    db.add(record)
    await db.flush()
    return record


async def resolve_outcome(
    db: AsyncSession,
    outcome_id: int,
    outcome: str,
    note: Optional[str] = None,
) -> Optional[OutcomeRecord]:
    """Captain marks what happened. JARVIS learns from it."""
    record = (await db.execute(
        select(OutcomeRecord).where(OutcomeRecord.id == outcome_id)
    )).scalar_one_or_none()

    if not record:
        return None

    record.outcome = outcome
    record.outcome_note = note
    record.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    # Immediately extract a learning
    await _learn_from_outcome(db, record)

    return record


async def get_evolution_history(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get JARVIS's self-learning reports — the evolution log."""
    rows = (await db.execute(
        select(Memory)
        .where(Memory.memory_type == "learning")
        .where(cast(Memory.tags, String).ilike("%daily_learning%"))
        .order_by(desc(Memory.created_at))
        .limit(limit)
    )).scalars().all()

    return [{
        "date": str(m.created_at),
        "report": m.value,
        "tags": m.tags,
    } for m in rows]
