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
from app.services.aionx.completion_matrix import completion_matrix
from app.services.aionx.cross_department_validation import (
    validate_client_fit,
    validate_delivery_readiness,
    validate_sales_accuracy,
    validate_stage_transition,
    validation_status,
)
from app.services.aionx.living_operating_intelligence import (
    adaptive_intelligence_status,
    captain_interface_status,
    data_backbone_status,
    full_operating_intelligence,
    gateway_experience_status,
    module_dependency_status,
    revenue_pipeline_status,
    technology_exploration_status,
)
from app.services.aionx.operational_integrity import (
    operational_integrity_status,
)
from app.services.aionx.operational_persistence import (
    capture_preventive_monitoring_snapshot,
    capture_system_state_snapshot,
    create_autonomy_proposal,
    latest_persisted_records,
    operational_persistence_status,
    persist_fallback_drill,
    persist_knowledge_synthesis,
    persist_mission_plan,
    persist_qa_certificate,
    persist_repair_instruction,
    record_external_scan,
    run_governed_integrity_cycle,
)
from app.services.aionx.sovereign_organs import (
    cognitive_debate,
    genesis_proposal,
    immune_scan,
    simulate_strategy,
    sovereign_organs_status,
    system_state_snapshot,
)
from app.services.aionx.supreme_council_layer import (
    calibration_health,
    convergence_health,
    create_recommendation_object,
    evaluate_self_modification,
    membrane_status,
    meta_learning_status,
    run_meta_learning_cycle,
    supreme_council_status,
)
from app.services.aionx.ultimate_client_journey import (
    hie_briefing,
    post_call_extraction,
    preventive_monitoring_status,
    ultimate_journey_status,
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


# CANONICAL LIVING OPERATING INTELLIGENCE

@router.get("/operating-intelligence")
async def operating_intelligence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await full_operating_intelligence(db)


@router.get("/adaptive-intelligence")
async def adaptive_intelligence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await adaptive_intelligence_status(db)


@router.get("/technology-exploration")
async def technology_exploration() -> dict[str, Any]:
    return technology_exploration_status()


@router.get("/revenue-pipeline")
async def revenue_pipeline() -> dict[str, Any]:
    return revenue_pipeline_status()


@router.get("/module-dependencies")
async def module_dependencies() -> dict[str, Any]:
    return module_dependency_status()


@router.get("/data-backbone")
async def data_backbone(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await data_backbone_status(db)


@router.get("/gateway-experience")
async def gateway_experience() -> dict[str, Any]:
    return gateway_experience_status()


@router.get("/captain-interface")
async def captain_interface(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await captain_interface_status(db)


@router.get("/operational-integrity")
async def operational_integrity() -> dict[str, Any]:
    return operational_integrity_status()


@router.get("/operational-integrity/teams")
async def operational_integrity_teams() -> dict[str, Any]:
    data = operational_integrity_status()
    return {"status": data["status"], "total": data["team_count"], "teams": data["teams"]}


@router.get("/operational-integrity/pipeline")
async def full_operational_pipeline() -> dict[str, Any]:
    data = operational_integrity_status()
    return {"status": data["status"], "stage_count": data["pipeline_stage_count"], "stages": data["pipeline"]}


@router.get("/operational-integrity/milestone-governance")
async def milestone_governance() -> dict[str, Any]:
    data = operational_integrity_status()
    return {
        "status": data["status"],
        "stage_count": data["milestone_governance_stage_count"],
        "workflow": data["milestone_governance"],
    }


@router.get("/operational-integrity/hia-profiles")
async def hia_profiles() -> dict[str, Any]:
    data = operational_integrity_status()
    return {"status": data["status"], "total": data["hia_count"], "profiles": data["hia_profiles"]}


@router.get("/operational-integrity/fallback-matrix")
async def fallback_matrix() -> dict[str, Any]:
    data = operational_integrity_status()
    return {"status": data["status"], "total": data["fallback_rule_count"], "fallback_matrix": data["fallback_matrix"]}


@router.post("/operational-integrity/mission-plan")
async def mission_plan(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await persist_mission_plan(db, payload)


@router.post("/operational-integrity/qa-certificate")
async def qa_certificate(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await persist_qa_certificate(db, payload)


@router.post("/operational-integrity/repair-instruction")
async def repair_instruction(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await persist_repair_instruction(db, payload)


@router.post("/operational-integrity/fallback-drill")
async def fallback_drill(
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await persist_fallback_drill(db, payload)


@router.post("/operational-integrity/knowledge-synthesis")
async def knowledge_synthesis(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await persist_knowledge_synthesis(db, payload)


@router.get("/operational-persistence")
async def operational_persistence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await operational_persistence_status(db)


@router.get("/operational-persistence/latest")
async def operational_persistence_latest(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await latest_persisted_records(db, limit)


@router.post("/system-state/snapshot")
async def create_system_state_snapshot(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await capture_system_state_snapshot(db, captured_by="CAPTAIN_API")


@router.post("/preventive-monitoring/snapshot")
async def create_preventive_monitoring_snapshot(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await capture_preventive_monitoring_snapshot(db)


@router.post("/autonomy/proposal")
async def autonomy_proposal(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await create_autonomy_proposal(db, payload)


@router.post("/external-scan/record")
async def external_scan_record(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await record_external_scan(db, payload)


@router.post("/governed-integrity-cycle")
async def governed_integrity_cycle(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await run_governed_integrity_cycle(db)


@router.get("/supreme-council")
async def supreme_council(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await supreme_council_status(db)


@router.get("/supreme-council/calibration")
async def supreme_council_calibration(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await calibration_health(db)


@router.get("/supreme-council/convergence")
async def supreme_council_convergence(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await convergence_health(db)


@router.get("/supreme-council/safety-membrane")
async def supreme_council_safety_membrane(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await membrane_status(db)


@router.get("/supreme-council/meta-learning")
async def supreme_council_meta_learning(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await meta_learning_status(db)


@router.post("/supreme-council/recommendation")
async def supreme_council_recommendation(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await create_recommendation_object(db, payload)


@router.post("/supreme-council/self-modification/evaluate")
async def supreme_council_self_modification_evaluate(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await evaluate_self_modification(db, payload)


@router.post("/supreme-council/meta-learning-cycle")
async def supreme_council_meta_learning_cycle(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await run_meta_learning_cycle(db)


@router.get("/sovereign-organs")
async def sovereign_organs() -> dict[str, Any]:
    return sovereign_organs_status()


@router.get("/system-state")
async def system_state() -> dict[str, Any]:
    return system_state_snapshot()


@router.post("/cognitive-cortex/debate")
async def cognitive_cortex_debate(payload: dict[str, Any]) -> dict[str, Any]:
    return cognitive_debate(payload)


@router.post("/genesis/propose")
async def genesis_create_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    return genesis_proposal(payload)


@router.post("/immune-system/scan")
async def immune_system_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return immune_scan(payload)


@router.post("/simulation-twin/scenario")
async def simulation_twin_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    return simulate_strategy(payload)


@router.get("/ultimate-journey")
async def ultimate_journey() -> dict[str, Any]:
    return ultimate_journey_status()


@router.get("/preventive-monitoring")
async def preventive_monitoring() -> dict[str, Any]:
    return preventive_monitoring_status()


@router.post("/hie/briefing")
async def create_hie_briefing(payload: dict[str, Any]) -> dict[str, Any]:
    return hie_briefing(payload)


@router.post("/hie/post-call-extraction")
async def create_post_call_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    return post_call_extraction(payload)


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


# ─── INTELLIGENCE ENGINES ────────────────────────────────────────────────────

# Counterfactual Engine
@router.post("/intelligence/counterfactual/simulate")
async def simulate_decision(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.counterfactual_engine import simulate_decision as sim
    return await sim(db, uuid.UUID(payload["decision_id"]))


@router.post("/intelligence/counterfactual/actuality")
async def record_actuality(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.counterfactual_engine import record_actuality as rec
    return await rec(
        db,
        uuid.UUID(payload["decision_id"]),
        payload["actual_outcome"],
        payload.get("revenue_delta", 0.0),
        payload.get("timeline_delta_days", 0),
    )


@router.get("/intelligence/counterfactual/learning")
async def extract_counterfactual_learning(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.aionx.counterfactual_engine import extract_learning
    return await extract_learning(db)


# Decision Debt Engine
@router.post("/intelligence/debt/compute")
async def compute_debt(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.decision_debt_engine import compute_decision_debt
    return await compute_decision_debt(
        db,
        uuid.UUID(payload["decision_id"]),
        payload.get("lost_revenue_usd", 0.0),
        payload.get("remediation_effort_hours", 0),
        payload.get("opportunity_cost_usd", 0.0),
    )


@router.get("/intelligence/debt/assess")
async def assess_debt(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.aionx.decision_debt_engine import assess_institutional_debt
    return await assess_institutional_debt(db)


@router.get("/intelligence/debt/reduction-plan")
async def debt_reduction_plan(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.aionx.decision_debt_engine import recommend_debt_reduction
    recommendations = await recommend_debt_reduction(db)
    return {"recommendations": recommendations, "count": len(recommendations)}


# Mission Autopsy Engine
@router.post("/intelligence/autopsy/analyze")
async def analyze_failure(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_autopsy_engine import analyze_mission_failure
    return await analyze_mission_failure(
        db,
        uuid.UUID(payload["mission_id"]),
        payload.get("failure_type", "UNKNOWN"),
        payload.get("failure_summary", ""),
    )


@router.get("/intelligence/autopsy/patterns")
async def failure_patterns(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.aionx.mission_autopsy_engine import extract_failure_patterns
    return await extract_failure_patterns(db)


@router.get("/intelligence/autopsy/improvements/{failure_type}")
async def improvement_recommendations(
    failure_type: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_autopsy_engine import recommend_process_improvement
    improvements = await recommend_process_improvement(db, failure_type)
    return {"failure_type": failure_type, "improvements": improvements}


# Executive Accountability Engine
@router.post("/intelligence/accountability/score-decision")
async def score_decision(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.executive_accountability_engine import score_decision_quality
    return await score_decision_quality(
        db,
        uuid.UUID(payload["decision_id"]),
        payload.get("actual_outcome_quality", 0.5),
    )


@router.get("/intelligence/accountability/maker/{maker_id}")
async def maker_accuracy(
    maker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.executive_accountability_engine import track_maker_accuracy
    return await track_maker_accuracy(db, maker_id)


@router.get("/intelligence/accountability/decay/{maker_id}")
async def authority_decay_check(
    maker_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.executive_accountability_engine import compute_authority_decay
    return await compute_authority_decay(db, maker_id)


@router.post("/intelligence/accountability/escalate")
async def escalate_decision(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.executive_accountability_engine import escalate_for_captain_review
    return await escalate_for_captain_review(db, uuid.UUID(payload["decision_id"]))


# Client Trust Index Engine
@router.post("/intelligence/trust/compute")
async def compute_trust(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.client_trust_index import compute_trust_score
    return await compute_trust_score(db, uuid.UUID(payload["client_id"]))


@router.get("/intelligence/trust/erosion/{client_id}")
async def trust_erosion_check(
    client_id: uuid.UUID,
    threshold: float = Query(20.0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.client_trust_index import escalate_trust_erosion
    return await escalate_trust_erosion(db, client_id, threshold)


@router.get("/intelligence/trust/recovery/{client_id}")
async def recovery_actions(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.client_trust_index import recovery_protocol
    actions = await recovery_protocol(db, client_id)
    return {"client_id": str(client_id), "recovery_actions": actions}


# ─── OPTIONAL SYSTEMS (Steps 26-30) ──────────────────────────────────────────

# HIA Certification Engine (Step 26)
@router.get("/hia/certification/{hia_agent_id}")
async def get_hia_certification(
    hia_agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.hia_certification_engine import compute_hia_certification
    return await compute_hia_certification(db, hia_agent_id)


@router.get("/hia/certification/{hia_agent_id}/renewal")
async def check_hia_renewal(
    hia_agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.hia_certification_engine import check_certification_renewal
    return await check_certification_renewal(db, hia_agent_id)


# Voice Integration (Step 27)
@router.post("/voice/briefing")
async def generate_briefing_audio(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.voice_integration import generate_briefing_voice
    return await generate_briefing_voice(
        payload.get("text", ""),
        payload.get("voice_persona", "BRIEFING")
    )


@router.post("/voice/alert")
async def generate_alert_audio(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.voice_integration import generate_alert_voice
    return await generate_alert_voice(
        payload.get("text", ""),
        payload.get("severity", "HIGH")
    )


@router.post("/voice/council")
async def generate_council_audio(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.voice_integration import generate_council_voice
    return await generate_council_voice(
        payload.get("text", ""),
        payload.get("council_name", "Convergence Council")
    )


# Mission File System (Step 28)
@router.post("/mission-file/archive")
async def archive_mission_doc(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_file_system import archive_mission_document
    return await archive_mission_document(
        db,
        uuid.UUID(payload["mission_id"]),
        payload["document_type"],
        payload["content"],
        payload.get("author", "JARVIS"),
        payload.get("metadata")
    )


@router.get("/mission-file/{mission_id}/archive")
async def retrieve_mission_archive(
    mission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_file_system import retrieve_mission_archive
    return await retrieve_mission_archive(db, mission_id)


@router.post("/mission-file/{mission_id}/verify")
async def verify_mission_integrity(
    mission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_file_system import verify_mission_integrity
    return await verify_mission_integrity(db, mission_id)


@router.get("/mission-file/{mission_id}/dossier")
async def export_dossier(
    mission_id: uuid.UUID,
    format: str = Query("pdf"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.mission_file_system import export_mission_dossier
    return await export_mission_dossier(db, mission_id, format)


# Validation Layer (Step 29)
@router.post("/validation/decision/{decision_id}")
async def validate_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.validation_layer import validate_decision_before_execution
    return await validate_decision_before_execution(db, decision_id)


@router.post("/validation/preflight/{decision_id}")
async def preflight_check(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.validation_layer import pre_flight_check
    return await pre_flight_check(db, decision_id)


# Final Integration & Captain Dashboard (Step 30)
@router.get("/dashboard")
async def captain_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.final_integration import generate_captain_intelligence_dashboard
    return await generate_captain_intelligence_dashboard(db)


@router.get("/architecture")
async def architecture_reconciliation(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.final_integration import get_aionx_architecture_reconciliation
    return await get_aionx_architecture_reconciliation(db)


@router.get("/system-info")
async def system_info() -> dict[str, Any]:
    from app.services.aionx.final_integration import get_aionx_system_info
    return await get_aionx_system_info()


@router.get("/frontier")
async def aionx_frontier_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import frontier_status
    return await frontier_status(db)


@router.post("/frontier/founder-mirror/predict")
async def aionx_frontier_founder_mirror_predict(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import predict_captain_decision
    return await predict_captain_decision(db, payload)


@router.post("/frontier/service-concepts/generate")
async def aionx_frontier_generate_service_concept(
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import generate_service_concept
    return await generate_service_concept(db, payload)


@router.post("/frontier/threats/scan")
async def aionx_frontier_scan_threats(
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import scan_threats
    return await scan_threats(db, payload)


@router.post("/frontier/cascade/trigger")
async def aionx_frontier_cascade(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import cascade_intelligence
    return await cascade_intelligence(db, payload)


@router.get("/frontier/brain/recall")
async def aionx_frontier_brain_recall(
    q: str = Query("what worked"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import recall_knowledge
    return await recall_knowledge(db, q)


@router.post("/frontier/agents/capacity")
async def aionx_frontier_agent_capacity(
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.services.aionx.frontier_intelligence import agent_capacity
    return await agent_capacity(db, payload)


@router.get("/completion-matrix")
async def aionx_completion_matrix(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await completion_matrix(db)


@router.get("/cross-validation")
async def cross_validation_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await validation_status(db)


@router.post("/cross-validation/delivery-readiness/{mission_id}")
async def cross_validate_delivery_readiness(
    mission_id: str,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await validate_delivery_readiness(db, mission_id, payload)


@router.post("/cross-validation/sales-accuracy/{proposal_id}")
async def cross_validate_sales_accuracy(
    proposal_id: str,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await validate_sales_accuracy(db, proposal_id, payload)


@router.post("/cross-validation/client-fit/{client_id}")
async def cross_validate_client_fit(
    client_id: str,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await validate_client_fit(db, client_id, payload)


@router.post("/cross-validation/stage-transition/{subject_id}")
async def cross_validate_stage_transition(
    subject_id: str,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await validate_stage_transition(db, subject_id, payload)
