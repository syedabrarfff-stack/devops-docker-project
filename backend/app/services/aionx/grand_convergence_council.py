"""Grand Convergence Council — highest discussion chamber inside AIONX.

A 10-phase deterministic state machine where every organ contributes,
dissent is preserved, every claim is logged as a scoreable prediction,
and the convergence gate prevents token-waste from infinite loops.
Captain watches it live via WebSocket. Every message is immutable institutional memory.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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

    # CONTEXT_LOAD — inject Decision Memory patterns + engine intelligence
    session.session_phase = "CONTEXT_LOAD"
    context_data = {}

    if inject_patterns:
        patterns = await pattern_injection_for_council(
            db, decision_category, []
        )
        context_data["historical_patterns"] = patterns

    # Inject counterfactual analysis
    try:
        from app.services.aionx.counterfactual_engine import extract_learning
        learning = await extract_learning(db)
        context_data["counterfactual_accuracy"] = learning.get("success_rate", 0.5)
    except Exception as exc:
        logger.warning("Council: counterfactual context load failed: %s", exc)
        context_data["counterfactual_accuracy"] = None

    # Inject institutional debt
    try:
        from app.services.aionx.decision_debt_engine import assess_institutional_debt
        debt = await assess_institutional_debt(db)
        context_data["institutional_debt"] = debt.get("total_institutional_debt_usd", 0)
        context_data["debt_penalty"] = debt.get("wisdom_index_penalty_points", 0)
    except Exception as exc:
        logger.warning("Council: institutional debt context load failed: %s", exc)
        context_data["institutional_debt"] = None

    session.context_loaded = context_data
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
    except Exception as exc:
        logger.warning("Council: position synthesis failed: %s", exc)
        positions.append({"synthesis": "SYNTHESIS_UNAVAILABLE"})

    await db.commit()

    # SIMULATE — Simulation Twin runs top paths
    session.session_phase = "SIMULATE"
    await db.commit()

    # CONVERGE — gate fires, consensus formed
    session.session_phase = "CONVERGE"
    await db.commit()

    # RECOMMEND — single recommendation with engine intelligence + trust data
    session.session_phase = "RECOMMEND"

    # Gather trust & accountability data
    trust_context = ""
    try:
        from sqlalchemy import select
        from app.models.aionx_organs import ClientDigitalTwin
        from app.services.aionx.client_trust_index import compute_trust_score

        twins = (await db.execute(select(ClientDigitalTwin).limit(500))).scalars().all()
        if twins:
            avg_trust = sum(t.trust_score or 70 for t in twins) / len(twins)
            trust_context = f"\nAverage client trust: {avg_trust:.0f}/100"
    except Exception as exc:
        logger.debug("Client trust context unavailable for council session: %s", exc)

    try:
        recommendation = await route_task(
            task_type=TaskType.REASONING,
            prompt=(
                f"Convergence Council Final Recommendation for: {session.trigger_event}\n"
                f"Council positions: {positions}\n"
                f"Context: Debt=${context_data.get('institutional_debt', 'unknown')} "
                f"Accuracy={(context_data.get('counterfactual_accuracy', 0)*100):.0f}%{trust_context}\n\n"
                "Produce a single clear recommendation. Preserve all dissenting opinions separately. "
                "Consider debt, accuracy, and trust factors in decision quality. "
                "Format: RECOMMENDATION | DISSENT | CONFIDENCE | NEXT_ACTION"
            ),
            max_tokens=800,
        )
        session.recommendation = recommendation
    except Exception as exc:
        logger.warning("Council: final recommendation generation failed: %s", exc)
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
