"""AIONX Sovereign Organs — REST API endpoints.

Captain Glass Wall, Council operations, Digital Twins, Wisdom Index,
Sentinel observations, Mission Autopsy, and Self-Modification registry.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.aionx_organs import (
    ConvergenceCouncilSession,
    MissionAutopsy,
    MissionOwnershipRecord,
    SentinelObservation,
    SentinelThreat,
)
from app.services.aionx.client_digital_twin import (
    get_or_create_twin,
    get_twin_for_hia,
    record_interaction,
    update_twin_profile,
)
from app.services.aionx.decision_memory_engine import (
    create_decision_object,
    generate_weekly_retrospective,
    get_decision_genealogy,
    pattern_injection_for_council,
)
from app.services.aionx.grand_convergence_council import (
    captain_override,
    get_live_session_feed,
    open_session,
    run_convergence_session,
)
from app.services.aionx.institutional_wisdom_index import (
    compute_weekly_wisdom,
    get_current_wisdom,
)
from app.services.aionx.provider_sovereign_council import (
    check_wake_conditions,
    convene_provider_council,
    get_domain_authority,
    shelve_discovery,
)
from app.services.aionx.sentinel_layer import (
    get_active_threats,
    get_pending_escalations,
    record_observation,
    register_threat,
)

from app.services.aionx.orchestration_cortex import (
    compute_operational_iq,
    fire_event,
    situational_snapshot,
)
from app.services.aionx.batch1_client_pipeline import (
    advance_stage,
    get_pipeline,
)

router = APIRouter(prefix="/aionx", tags=["AIONX"])


# ─── ORCHESTRATION CORTEX ────────────────────────────────────────────────────

@router.get("/cortex/operational-iq")
async def operational_iq(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await compute_operational_iq(db)


@router.get("/cortex/snapshot")
async def cortex_snapshot(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await situational_snapshot(db)


@router.post("/cortex/event")
async def cortex_fire_event(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    event_type = payload.get("event_type")
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type required")
    return await fire_event(db, event_type, payload)


# ─── BATCH 1 CLIENT PIPELINE ORCHESTRATOR ────────────────────────────────────

@router.post("/pipeline/stage-transition")
async def pipeline_stage_transition(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        client_id = uuid.UUID(payload["client_id"])
        target_stage = int(payload["target_stage"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="client_id and target_stage are required") from exc

    try:
        mission_id = uuid.UUID(payload["mission_id"]) if payload.get("mission_id") else None
        return await advance_stage(
            db,
            client_id=client_id,
            target_stage=target_stage,
            engagement_score=payload.get("engagement_score"),
            mission_id=mission_id,
            metadata=payload.get("metadata") or {},
            reason=payload.get("reason"),
            actor=payload.get("actor", "JARVIS"),
            captain_approved=bool(payload.get("captain_approved", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/{client_id}")
async def client_pipeline(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await get_pipeline(db, client_id)


# ─── WISDOM INDEX ────────────────────────────────────────────────────────────

@router.get("/wisdom")
async def get_wisdom_index(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await get_current_wisdom(db)


@router.post("/wisdom/compute")
async def compute_wisdom(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    snapshot = await compute_weekly_wisdom(db)
    return {
        "wisdom_score": snapshot.wisdom_score,
        "delta": snapshot.delta,
        "narrative": snapshot.narrative,
        "week_of": snapshot.week_of.isoformat(),
        "recommendations": snapshot.recommendations,
    }


# ─── DECISION MEMORY — GLASS WALL ────────────────────────────────────────────

@router.get("/decisions/genealogy")
async def decision_genealogy(
    client_id: uuid.UUID | None = Query(None),
    mission_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await get_decision_genealogy(db, client_id=client_id, mission_id=mission_id, limit=limit)


@router.post("/decisions")
async def create_decision(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    decision = await create_decision_object(
        db,
        trigger_event=payload["trigger_event"],
        problem_statement=payload["problem_statement"],
        tier=payload.get("tier", 2),
        decision_category=payload.get("category", "GENERAL"),
        options=payload.get("options"),
        confidence_score=payload.get("confidence", 0.0),
        risk_flags=payload.get("risk_flags"),
        assumptions=payload.get("assumptions"),
    )
    return {"decision_id": str(decision.id), "created_at": decision.created_at.isoformat()}


@router.get("/decisions/patterns")
async def get_patterns(
    category: str = Query("GENERAL"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await pattern_injection_for_council(db, category, [])


@router.post("/decisions/retrospective")
async def run_retrospective(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    retro = await generate_weekly_retrospective(db)
    return {
        "week_of": retro.week_of.isoformat(),
        "total_decisions": retro.total_decisions,
        "correct": retro.correct_count,
        "incorrect": retro.incorrect_count,
        "avg_confidence": retro.avg_confidence,
        "wisdom_delta": retro.wisdom_delta,
    }


# ─── GRAND CONVERGENCE COUNCIL ───────────────────────────────────────────────

@router.post("/convergence/session")
async def create_convergence_session(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    session = await open_session(
        db,
        trigger_event=payload["trigger_event"],
        trigger_type=payload.get("trigger_type", "OPPORTUNITY"),
    )
    return {"session_id": str(session.id), "phase": session.session_phase}


@router.post("/convergence/session/{session_id}/run")
async def run_session(
    session_id: uuid.UUID,
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    session = await run_convergence_session(
        db,
        session_id,
        decision_category=(payload or {}).get("category", "STRATEGIC"),
    )
    return {
        "session_id": str(session.id),
        "phase": session.session_phase,
        "recommendation": session.recommendation,
        "dissent": session.dissenting_opinions,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.get("/convergence/session/{session_id}/feed")
async def live_session_feed(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await get_live_session_feed(db, session_id)


@router.post("/convergence/session/{session_id}/override")
async def captain_session_override(
    session_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    session = await captain_override(db, session_id, payload["override_decision"])
    return {"session_id": str(session.id), "override": session.captain_override}


# ─── PROVIDER SOVEREIGN COUNCIL ──────────────────────────────────────────────

@router.post("/provider-council/convene")
async def convene_council(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    session = await convene_provider_council(
        db,
        trigger_type=payload.get("trigger_type", "SIGNAL"),
        trigger_signal=payload.get("signal"),
        agenda_items=payload.get("agenda", []),
        domain=payload.get("domain", "STRATEGY"),
    )
    return {
        "session_id": str(session.id),
        "participants": session.participants,
        "rounds": session.debate_rounds,
        "convergence": session.convergence_reason,
        "recommendations": session.recommendations,
    }


@router.post("/provider-council/shelve")
async def shelve_a_discovery(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    discovery = await shelve_discovery(
        db,
        title=payload["title"],
        source=payload["source"],
        summary=payload["summary"],
        wake_condition=payload["wake_condition"],
        wake_metric=payload.get("wake_metric"),
        wake_threshold=payload.get("wake_threshold"),
        roi_estimate=payload.get("roi_estimate", 0.0),
    )
    return {"id": str(discovery.id), "shelved": True}


@router.post("/provider-council/wake-check")
async def check_wake_triggers(
    metrics: dict[str, float],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    activated = await check_wake_conditions(db, metrics)
    return {"activated_count": len(activated), "activated": [str(d.id) for d in activated]}


# ─── CLIENT DIGITAL TWINS ────────────────────────────────────────────────────

@router.get("/digital-twin/{client_id}")
async def get_digital_twin(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await get_twin_for_hia(db, client_id)


@router.put("/digital-twin/{client_id}")
async def update_digital_twin(
    client_id: uuid.UUID,
    updates: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    twin = await update_twin_profile(db, client_id, updates)
    return {"client_id": str(twin.client_id), "trust_score": twin.trust_score, "updated": True}


@router.post("/digital-twin/{client_id}/interaction")
async def log_interaction(
    client_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    interaction = await record_interaction(
        db,
        client_id,
        interaction_type=payload.get("type", "EMAIL"),
        hia_agent=payload.get("hia_agent"),
        sentiment=payload.get("sentiment", "neutral"),
        trust_delta=payload.get("trust_delta", 0.0),
        summary=payload.get("summary"),
        raw_notes=payload.get("notes"),
    )
    return {"interaction_id": str(interaction.id), "recorded": True}


# ─── SENTINEL LAYER ──────────────────────────────────────────────────────────

@router.post("/sentinel/observe")
async def record_sentinel_observation(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    obs = await record_observation(
        db,
        source=payload["source"],
        category=payload.get("category", "TECHNOLOGY"),
        signal_strength=payload.get("signal_strength", "WEAK"),
        title=payload["title"],
        summary=payload["summary"],
        url=payload.get("url"),
        raw_data=payload.get("raw_data"),
    )
    return {"id": str(obs.id), "escalated": obs.escalated}


@router.get("/sentinel/escalations")
async def pending_escalations(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    obs_list = await get_pending_escalations(db)
    return [
        {
            "id": str(o.id),
            "source": o.source,
            "category": o.category,
            "title": o.title,
            "signal_strength": o.signal_strength,
            "observed_at": o.observed_at.isoformat(),
        }
        for o in obs_list
    ]


@router.get("/sentinel/threats")
async def active_threats(
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    threats = await get_active_threats(db, severity=severity)
    return [
        {
            "id": str(t.id),
            "type": t.threat_type,
            "name": t.threat_name,
            "severity": t.severity,
            "description": t.description,
            "response": t.recommended_response,
        }
        for t in threats
    ]


# ─── MISSION AUTOPSY ─────────────────────────────────────────────────────────

@router.post("/autopsy")
async def create_autopsy(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    autopsy = MissionAutopsy(
        mission_id=uuid.UUID(payload["mission_id"]),
        client_id=uuid.UUID(payload["client_id"]) if payload.get("client_id") else None,
        failure_type=payload.get("failure_type", "MISSION_FAILURE"),
        failure_summary=payload["failure_summary"],
        causal_chain=payload.get("causal_chain", []),
        what_failed=payload.get("what_failed"),
        why_it_failed=payload.get("why_it_failed"),
        who_detected=payload.get("who_detected"),
        who_missed=payload.get("who_missed"),
        which_assumption_broke=payload.get("which_assumption_broke"),
        which_warning_ignored=payload.get("which_warning_ignored"),
        alternative_path_that_would_succeed=payload.get("alternative_path"),
        institutional_doctrine=payload.get("doctrine"),
    )
    db.add(autopsy)
    await db.commit()
    return {"autopsy_id": str(autopsy.id), "created": True}


@router.get("/autopsy/{mission_id}")
async def get_autopsy(
    mission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(MissionAutopsy).where(MissionAutopsy.mission_id == mission_id)
    )
    autopsy = result.scalar_one_or_none()
    if not autopsy:
        raise HTTPException(status_code=404, detail="Autopsy not found")
    return {
        "id": str(autopsy.id),
        "failure_summary": autopsy.failure_summary,
        "causal_chain": autopsy.causal_chain,
        "what_failed": autopsy.what_failed,
        "why_it_failed": autopsy.why_it_failed,
        "institutional_doctrine": autopsy.institutional_doctrine,
        "doctrine_approved": autopsy.doctrine_approved,
    }


# ─── EXECUTIVE ACCOUNTABILITY ────────────────────────────────────────────────

@router.post("/accountability/mission")
async def create_ownership_record(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    record = MissionOwnershipRecord(
        mission_id=uuid.UUID(payload["mission_id"]),
        client_id=uuid.UUID(payload["client_id"]) if payload.get("client_id") else None,
        executive_owner=payload.get("executive_owner", "JARVIS"),
        primary_hia=payload.get("primary_hia"),
        council_lead=payload.get("council_lead"),
        department_leads=payload.get("department_leads", []),
    )
    db.add(record)
    await db.commit()
    return {"record_id": str(record.id), "created": True}


@router.get("/accountability/mission/{mission_id}")
async def get_ownership(
    mission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(MissionOwnershipRecord).where(MissionOwnershipRecord.mission_id == mission_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Ownership record not found")
    return {
        "mission_id": str(record.mission_id),
        "executive_owner": record.executive_owner,
        "primary_hia": record.primary_hia,
        "status": record.mission_status,
        "profitability": record.profitability_usd,
        "satisfaction": record.client_satisfaction_score,
        "repair_loops": record.repair_loops_count,
    }
