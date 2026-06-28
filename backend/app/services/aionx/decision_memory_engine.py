"""Decision Memory Engine — institutional executive consciousness of AIONX.

Captures every Tier 2/3 decision as a permanent Decision Object, runs 30/90-day
retrospectives, extracts reusable patterns, and injects historical precedent into
Council deliberations before they begin.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    CounterfactualSimulation,
    DecisionDebtAssessment,
    DecisionObject,
    DecisionOption,
    DecisionOutcome,
    DecisionPattern,
    DecisionRetrospective,
)


def _resolve_tenant(tenant_id=None) -> uuid.UUID | None:
    if tenant_id:
        return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    from app.core.config import settings as _cfg
    raw = getattr(_cfg, "JARVIS_DEFAULT_TENANT_ID", None)
    if raw:
        try:
            return uuid.UUID(str(raw))
        except (ValueError, AttributeError):
            pass
    return None


# ─── DECISION CREATION ───────────────────────────────────────────────────────

async def create_decision_object(
    db: AsyncSession,
    *,
    trigger_event: str,
    problem_statement: str,
    tier: int = 2,
    decision_category: str = "GENERAL",
    executor_role: str = "JARVIS_AUTONOMOUS",
    options: list[dict[str, Any]] | None = None,
    confidence_score: float = 0.0,
    risk_flags: list[str] | None = None,
    assumptions: list[str] | None = None,
    client_id: uuid.UUID | None = None,
    mission_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> DecisionObject:
    decision = DecisionObject(
        tier=tier,
        decision_category=decision_category,
        trigger_event=trigger_event,
        problem_statement=problem_statement,
        executor_role=executor_role,
        confidence_score=confidence_score,
        risk_flags=risk_flags or [],
        assumptions=assumptions or [],
        client_id=client_id,
        mission_id=mission_id,
        tenant_id=tenant_id,
    )
    db.add(decision)
    await db.flush()

    if options:
        for opt in options:
            db.add(DecisionOption(
                decision_id=decision.id,
                option_text=opt.get("text", ""),
                was_chosen=opt.get("was_chosen", False),
                proponent_brains=opt.get("proponent_brains", []),
                opponent_brains=opt.get("opponent_brains", []),
                confidence_score=opt.get("confidence", 0.0),
                predicted_outcome_30d=opt.get("predicted_30d"),
                predicted_outcome_90d=opt.get("predicted_90d"),
                predicted_revenue_impact=opt.get("revenue_impact", 0.0),
                opportunity_cost=opt.get("opportunity_cost", 0.0),
            ))

    await db.commit()
    return decision


async def create_decision_from_council_session(
    db: AsyncSession,
    session_data: dict[str, Any],
    tier: int = 2,
) -> DecisionObject:
    return await create_decision_object(
        db,
        trigger_event=f"COUNCIL_SESSION:{session_data.get('session_id', 'unknown')}",
        problem_statement=session_data.get("question", "Council deliberation"),
        tier=tier,
        decision_category=session_data.get("category", "STRATEGIC"),
        executor_role="JARVIS_AUTONOMOUS" if tier < 3 else "CAPTAIN_APPROVAL",
        options=session_data.get("options", []),
        confidence_score=session_data.get("consensus_confidence", 0.0),
        risk_flags=session_data.get("risk_flags", []),
        assumptions=session_data.get("assumptions", []),
    )


async def create_decision_from_tier_action(
    db: AsyncSession,
    action_data: dict[str, Any],
    tier: int = 2,
) -> DecisionObject:
    return await create_decision_object(
        db,
        trigger_event=f"TIER_{tier}_ACTION:{action_data.get('action_type', 'unknown')}",
        problem_statement=action_data.get("description", "Tier action decision"),
        tier=tier,
        decision_category=action_data.get("category", "OPERATIONAL"),
        executor_role="JARVIS_AUTONOMOUS" if tier < 3 else "CAPTAIN_APPROVAL",
        client_id=action_data.get("client_id"),
        mission_id=action_data.get("mission_id"),
        confidence_score=action_data.get("confidence", 0.0),
        risk_flags=action_data.get("risk_flags", []),
    )


# ─── OUTCOME RECORDING ───────────────────────────────────────────────────────

async def record_outcome(
    db: AsyncSession,
    decision_id: uuid.UUID,
    actual_result: str,
    lessons_learned: str | None = None,
) -> DecisionOutcome:
    outcome = DecisionOutcome(
        decision_id=decision_id,
        actual_result=actual_result,
        lessons_learned=lessons_learned,
    )
    db.add(outcome)
    await db.execute(
        update(DecisionObject)
        .where(DecisionObject.id == decision_id)
        .values(outcome_summary=actual_result, outcome_at=datetime.utcnow())
    )
    await db.commit()
    return outcome


# ─── RETROSPECTIVE SYNC ──────────────────────────────────────────────────────

async def retrospective_sync(
    db: AsyncSession,
    days: int = 30,
    tenant_id=None,
) -> list[DecisionOutcome]:
    _tid = _resolve_tenant(tenant_id)
    cutoff = datetime.utcnow() - timedelta(days=days)
    _dq = select(DecisionObject).where(
        DecisionObject.created_at <= cutoff,
        DecisionObject.outcome_at.is_(None),
    )
    if _tid:
        _dq = _dq.where(DecisionObject.tenant_id == _tid)
    result = await db.execute(_dq)
    pending = result.scalars().all()

    outcomes_due = []
    for decision in pending:
        outcome_result = await db.execute(
            select(DecisionOutcome).where(DecisionOutcome.decision_id == decision.id)
        )
        outcome = outcome_result.scalar_one_or_none()
        if outcome:
            if days == 30 and not outcome.day_30_reviewed_at:
                outcomes_due.append(outcome)
            elif days == 90 and not outcome.day_90_reviewed_at:
                outcomes_due.append(outcome)
    return outcomes_due


# ─── PATTERN ANALYSIS ────────────────────────────────────────────────────────

async def extract_patterns(
    db: AsyncSession,
    min_usage: int = 3,
    min_success_rate: float = 0.75,
) -> list[DecisionPattern]:
    result = await db.execute(
        select(DecisionPattern).where(
            DecisionPattern.usage_count >= min_usage,
            DecisionPattern.historical_success_rate >= min_success_rate,
        ).limit(100)
    )
    return result.scalars().all()


async def pattern_injection_for_council(
    db: AsyncSession,
    decision_category: str,
    problem_keywords: list[str],
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(DecisionPattern).where(
            DecisionPattern.pattern_category == decision_category,
            DecisionPattern.confidence_for_automation >= 0.6,
        ).order_by(DecisionPattern.historical_success_rate.desc()).limit(5)
    )
    patterns = result.scalars().all()
    return [
        {
            "pattern_name": p.pattern_name,
            "when_to_apply": p.when_to_apply,
            "success_rate": p.historical_success_rate,
            "template": p.decision_template,
            "confidence_for_automation": p.confidence_for_automation,
        }
        for p in patterns
    ]


# ─── GLASS WALL — CAPTAIN QUERY ──────────────────────────────────────────────

async def get_decision_genealogy(
    db: AsyncSession,
    client_id: uuid.UUID | None = None,
    mission_id: uuid.UUID | None = None,
    limit: int = 50,
    tenant_id=None,
) -> list[dict[str, Any]]:
    _tid = _resolve_tenant(tenant_id)
    query = select(DecisionObject).order_by(DecisionObject.created_at.desc()).limit(limit)
    if _tid:
        query = query.where(DecisionObject.tenant_id == _tid)
    if client_id:
        query = query.where(DecisionObject.client_id == client_id)
    if mission_id:
        query = query.where(DecisionObject.mission_id == mission_id)

    result = await db.execute(query)
    decisions = result.scalars().all()
    if not decisions:
        return []

    decision_ids = [d.id for d in decisions]

    options_rows = (await db.execute(
        select(DecisionOption).where(DecisionOption.decision_id.in_(decision_ids)).limit(500)
    )).scalars().all()
    options_by_decision: dict[uuid.UUID, list] = {}
    for o in options_rows:
        options_by_decision.setdefault(o.decision_id, []).append(o)

    outcomes_rows = (await db.execute(
        select(DecisionOutcome).where(DecisionOutcome.decision_id.in_(decision_ids)).limit(500)
    )).scalars().all()
    outcome_by_decision: dict[uuid.UUID, Any] = {o.decision_id: o for o in outcomes_rows}

    genealogy = []
    for d in decisions:
        options = options_by_decision.get(d.id, [])
        outcome = outcome_by_decision.get(d.id)
        genealogy.append({
            "decision_id": str(d.id),
            "created_at": d.created_at.isoformat(),
            "tier": d.tier,
            "category": d.decision_category,
            "trigger": d.trigger_event,
            "problem": d.problem_statement,
            "confidence": d.confidence_score,
            "executor": d.executor_role,
            "options_count": len(options),
            "chosen_option": next(
                (o.option_text for o in options if o.was_chosen), None
            ),
            "outcome": outcome.actual_result if outcome else None,
            "lessons": outcome.lessons_learned if outcome else None,
            "pattern_approved": d.pattern_approved_for_reuse,
        })
    return genealogy


# ─── WEEKLY RETROSPECTIVE REPORT ─────────────────────────────────────────────

async def generate_weekly_retrospective(
    db: AsyncSession,
    week_of: datetime | None = None,
    tenant_id=None,
) -> DecisionRetrospective:
    _tid = _resolve_tenant(tenant_id)
    if not week_of:
        week_of = datetime.utcnow()

    week_start = week_of - timedelta(days=7)
    _dq = select(DecisionObject).where(
        DecisionObject.created_at >= week_start,
        DecisionObject.created_at <= week_of,
    )
    if _tid:
        _dq = _dq.where(DecisionObject.tenant_id == _tid)
    result = await db.execute(_dq)
    decisions = result.scalars().all()

    correct = sum(1 for d in decisions if d.outcome_summary and "success" in d.outcome_summary.lower())
    incorrect = sum(1 for d in decisions if d.outcome_summary and "fail" in d.outcome_summary.lower())
    avg_conf = (
        sum(d.confidence_score for d in decisions) / len(decisions)
        if decisions else 0.0
    )

    retro = DecisionRetrospective(
        week_of=week_of.date(),
        total_decisions=len(decisions),
        avg_confidence=avg_conf,
        correct_count=correct,
        incorrect_count=incorrect,
        wisdom_delta=float(correct - incorrect),
    )
    db.add(retro)
    await db.commit()
    return retro
