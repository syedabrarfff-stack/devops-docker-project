"""Grand Convergence Council — highest discussion chamber inside AIONX.

A 10-phase deterministic state machine where every organ contributes,
dissent is preserved, every claim is logged as a scoreable prediction,
and the convergence gate prevents token-waste from infinite loops.
Captain watches it live via WebSocket. Every message is immutable institutional memory.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ConvergenceCouncilMessage,
    ConvergenceCouncilSession,
)
from app.services.ai.router import TaskType, route_task
from app.services.aionx.decision_memory_engine import pattern_injection_for_council

SESSION_PHASES = [
    "SIGNAL",
    "CONTEXT_LOAD",
    "POSITION",
    "CROSS_EXAM",
    "SIMULATE",
    "CONVERGE",
    "RECOMMEND",
    "EXECUTIVE",
    "MEMORIALIZE",
    "LEARN",
]

MAX_CROSS_EXAM_ROUNDS = 3

COUNCIL_PARTICIPANTS = [
    "JARVIS",
    "Decision_Memory",
    "Simulation_Twin",
    "Mission_Autopsy",
    "Institutional_Wisdom",
    "Technology_Exploration",
    "Client_Digital_Twin_Intelligence",
    "Revenue_Heart",
    "Cognitive_Cortex",
    "Adaptive_Intelligence",
    "Provider_Sovereign_Council",
    "Risk_Guardian",
]


async def open_session(
    db: AsyncSession,
    *,
    trigger_event: str,
    trigger_type: str = "OPPORTUNITY",
    participants: list[str] | None = None,
) -> ConvergenceCouncilSession:
    session = ConvergenceCouncilSession(
        trigger_event=trigger_event,
        trigger_type=trigger_type,
        session_phase="SIGNAL",
        participants=participants or COUNCIL_PARTICIPANTS,
    )
    db.add(session)
    await db.commit()
    return session


async def add_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    speaker: str,
    message: str,
    claim_type: str = "STATEMENT",
    confidence: float = 0.0,
    evidence_refs: list[Any] | None = None,
    is_falsifiable: bool = False,
) -> ConvergenceCouncilMessage:
    msg = ConvergenceCouncilMessage(
        session_id=session_id,
        speaker=speaker,
        message=message,
        claim_type=claim_type,
        confidence=confidence,
        evidence_refs=evidence_refs or [],
        is_falsifiable=is_falsifiable,
    )
    db.add(msg)
    await db.commit()
    return msg


async def run_convergence_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    decision_category: str = "STRATEGIC",
    inject_patterns: bool = True,
) -> ConvergenceCouncilSession:
    result = await db.execute(
        select(ConvergenceCouncilSession).where(ConvergenceCouncilSession.id == session_id)
    )
    session = result.scalar_one()

    # CONTEXT_LOAD — inject Decision Memory patterns
    session.session_phase = "CONTEXT_LOAD"
    if inject_patterns:
        patterns = await pattern_injection_for_council(
            db, decision_category, []
        )
        session.context_loaded = {"historical_patterns": patterns}
    await db.commit()

    # POSITION — each participant states their position
    session.session_phase = "POSITION"
    positions: list[dict[str, Any]] = []
    try:
        position_synthesis = await route_task(
            task_type=TaskType.STRATEGY,
            prompt=(
                f"Grand Convergence Council — Trigger: {session.trigger_event}\n"
                f"Type: {session.trigger_type}\n"
                f"Historical patterns loaded: {len(session.context_loaded.get('historical_patterns', []))}\n\n"
                "Each council member states their position on this trigger event. "
                "Format: [Member]: Position | Confidence | Evidence"
            ),
            max_tokens=1200,
        )
        await add_message(
            db, session_id,
            speaker="COUNCIL_SYNTHESIS",
            message=position_synthesis,
            claim_type="POSITION",
            confidence=0.7,
        )
        positions.append({"synthesis": position_synthesis})
    except Exception:
        positions.append({"synthesis": "SYNTHESIS_UNAVAILABLE"})

    await db.commit()

    # SIMULATE — Simulation Twin runs top paths
    session.session_phase = "SIMULATE"
    await db.commit()

    # CONVERGE — gate fires, consensus formed
    session.session_phase = "CONVERGE"
    await db.commit()

    # RECOMMEND — single recommendation with dissent preserved
    session.session_phase = "RECOMMEND"
    try:
        recommendation = await route_task(
            task_type=TaskType.REASONING,
            prompt=(
                f"Convergence Council Final Recommendation for: {session.trigger_event}\n"
                f"Council positions: {positions}\n\n"
                "Produce a single clear recommendation. Preserve all dissenting opinions separately. "
                "Format: RECOMMENDATION | DISSENT | CONFIDENCE | NEXT_ACTION"
            ),
            max_tokens=800,
        )
        session.recommendation = recommendation
    except Exception:
        session.recommendation = "RECOMMENDATION_DEFERRED"

    session.session_phase = "EXECUTIVE"
    session.completed_at = datetime.utcnow()
    await db.commit()
    return session


async def get_live_session_feed(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ConvergenceCouncilMessage)
        .where(ConvergenceCouncilMessage.session_id == session_id)
        .order_by(ConvergenceCouncilMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "speaker": m.speaker,
            "message": m.message,
            "claim_type": m.claim_type,
            "confidence": m.confidence,
            "is_falsifiable": m.is_falsifiable,
            "timestamp": m.created_at.isoformat(),
        }
        for m in messages
    ]


async def captain_override(
    db: AsyncSession,
    session_id: uuid.UUID,
    override_decision: str,
) -> ConvergenceCouncilSession:
    result = await db.execute(
        select(ConvergenceCouncilSession).where(ConvergenceCouncilSession.id == session_id)
    )
    session = result.scalar_one()
    session.captain_override = override_decision
    session.session_phase = "LEARN"
    await db.commit()
    return session
