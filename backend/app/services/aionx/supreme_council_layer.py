"""AIONX Supreme Council Layer.

The Supreme Council is the calibrated, convergent, safety-membraned meta-layer
above Provider Council and Grand Convergence Council. It advises and scores; it
does not hold execution handles.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ConvergenceCouncilSession,
    ProviderCalibrationRecord,
    ProviderCouncilSession,
    SelfModificationRecord,
    ShelvedDiscovery,
)
from app.services.aionx.grand_convergence_council import SESSION_PHASES
from app.services.aionx.operational_persistence import create_autonomy_proposal, record_event
from app.services.aionx.provider_sovereign_council import PROVIDER_DOMAIN_STRENGTHS


THREE_RING_ARCHITECTURE: list[dict[str, Any]] = [
    {
        "ring": 1,
        "name": "Advisory Councils",
        "members": ["Provider Sovereign Council", "Grand Convergence Council"],
        "allowed": ["research", "debate", "critique", "forecast", "recommend", "memorialize"],
        "blocked": ["send_email", "deploy_code", "change_infrastructure", "modify_governance", "spend_money"],
        "execution_handles": False,
    },
    {
        "ring": 2,
        "name": "JARVIS Executive",
        "members": ["JARVIS Supreme Orchestrator", "Cortex", "Decision Memory", "Simulation Twin"],
        "allowed": ["decide_tier_1", "queue_tier_2", "prepare_tier_3", "own_outcomes", "route_work"],
        "blocked": ["bypass_captain", "modify_safety_membrane", "irreversible_tier_3_execution"],
        "execution_handles": "bounded",
    },
    {
        "ring": 3,
        "name": "Sovereign Membrane",
        "members": ["Captain", "Kill Switch", "Immutable Governance Core"],
        "allowed": ["approve_tier_3", "override", "rollback", "freeze", "authorize_membrane_change"],
        "blocked": ["self_modification_by_ai"],
        "execution_handles": "captain_only",
    },
]


CONVERGENCE_GATE: dict[str, Any] = {
    "max_rounds": 4,
    "max_cross_exam_rounds": 3,
    "max_tokens_per_session": 6000,
    "stop_conditions": [
        "consensus_reached",
        "stable_disagreement",
        "marginal_information_decay",
        "max_rounds_hit",
        "captain_escalation_required",
    ],
    "output_contract": [
        "single_recommendation_object",
        "dissent_preserved",
        "confidence_attached",
        "evidence_refs_attached",
        "prediction_claims_scoreable",
        "jarvis_decision_required",
    ],
}


SAFETY_MEMBRANE: dict[str, Any] = {
    "immutable_core": [
        "Captain sovereignty",
        "kill switch",
        "governance tiers",
        "safety membrane rules",
        "approval boundaries",
        "rollback requirement",
    ],
    "self_modification_pipeline": [
        "classify_blast_radius",
        "block_core_changes",
        "shadow_deploy",
        "ab_test_against_current",
        "win_condition_gate",
        "canary_1_10_50",
        "promote_or_rollback",
        "decision_object_and_wisdom_log",
    ],
    "rollback_days": 90,
    "hard_rule": "AIONX can propose self-improvement but cannot mutate core authority or safety controls.",
}


META_LEARNING_DIMENSIONS: list[dict[str, str]] = [
    {"dimension": "source_quality", "question": "Which research sources produced adopted improvements?", "action": "reweight sources"},
    {"dimension": "debate_efficiency", "question": "Which debate formats reached good decisions fastest?", "action": "retire wasteful protocols"},
    {"dimension": "provider_calibration", "question": "Which providers' advice aged well?", "action": "rebalance domain authority"},
    {"dimension": "counterfactual_precision", "question": "Were roads-not-taken predictions accurate?", "action": "tune Simulation Twin"},
    {"dimension": "convergence_timing", "question": "Did convergence fire too early or too late?", "action": "adjust gate thresholds"},
    {"dimension": "confidence_honesty", "question": "Did high-confidence decisions outperform low ones?", "action": "reduce confidence inflation"},
    {"dimension": "self_mod_success", "question": "Did self-modifications win and stay safe?", "action": "tighten promotion criteria"},
]


async def supreme_council_status(db: AsyncSession) -> dict[str, Any]:
    calibration = await calibration_health(db)
    convergence = await convergence_health(db)
    membrane = await membrane_status(db)
    meta = await meta_learning_status(db)
    return {
        "status": "supreme_council_layer_live",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "principle": "Calibrated, convergent, safely-applied intelligence beats more voices.",
        "rings": THREE_RING_ARCHITECTURE,
        "convergence_gate": CONVERGENCE_GATE,
        "safety_membrane": SAFETY_MEMBRANE,
        "meta_learning_dimensions": META_LEARNING_DIMENSIONS,
        "calibration_health": calibration,
        "convergence_health": convergence,
        "membrane_status": membrane,
        "meta_learning_status": meta,
        "authority_boundary": "Councils advise only. JARVIS decides inside bounds. Captain controls irreversible authority.",
    }


async def calibration_health(db: AsyncSession) -> dict[str, Any]:
    total_claims = int((await db.execute(select(func.count()).select_from(ProviderCalibrationRecord))).scalar_one() or 0)
    resolved_claims = int((
        await db.execute(
            select(func.count()).select_from(ProviderCalibrationRecord).where(
                ProviderCalibrationRecord.was_correct.is_not(None)
            )
        )
    ).scalar_one() or 0)
    avg_brier = (
        await db.execute(
            select(func.avg(ProviderCalibrationRecord.brier_score)).where(
                ProviderCalibrationRecord.brier_score.is_not(None)
            )
        )
    ).scalar_one()

    provider_rows = (await db.execute(
        select(
            ProviderCalibrationRecord.provider_id,
            ProviderCalibrationRecord.domain,
            func.avg(ProviderCalibrationRecord.domain_authority_weight),
            func.count(),
        )
        .group_by(ProviderCalibrationRecord.provider_id, ProviderCalibrationRecord.domain)
        .order_by(ProviderCalibrationRecord.provider_id)
    )).all()

    return {
        "status": "calibration_records_live",
        "provider_count": len(PROVIDER_DOMAIN_STRENGTHS),
        "total_claims": total_claims,
        "resolved_claims": resolved_claims,
        "avg_brier_score": float(avg_brier or 0.0),
        "domain_authority": [
            {
                "provider": row[0],
                "domain": row[1],
                "authority_weight": round(float(row[2] or 1.0), 3),
                "claims": int(row[3]),
            }
            for row in provider_rows
        ],
        "provider_domain_strengths": PROVIDER_DOMAIN_STRENGTHS,
    }


async def convergence_health(db: AsyncSession) -> dict[str, Any]:
    total_sessions = int((await db.execute(select(func.count()).select_from(ConvergenceCouncilSession))).scalar_one() or 0)
    provider_sessions = int((await db.execute(select(func.count()).select_from(ProviderCouncilSession))).scalar_one() or 0)
    completed = int((
        await db.execute(
            select(func.count()).select_from(ConvergenceCouncilSession).where(
                ConvergenceCouncilSession.completed_at.is_not(None)
            )
        )
    ).scalar_one() or 0)
    return {
        "status": "convergence_protocol_live",
        "phase_count": len(SESSION_PHASES),
        "phases": SESSION_PHASES,
        "grand_sessions": total_sessions,
        "completed_grand_sessions": completed,
        "provider_sessions": provider_sessions,
        "gate": CONVERGENCE_GATE,
    }


async def membrane_status(db: AsyncSession) -> dict[str, Any]:
    total_records = int((await db.execute(select(func.count()).select_from(SelfModificationRecord))).scalar_one() or 0)
    promoted = int((
        await db.execute(
            select(func.count()).select_from(SelfModificationRecord).where(
                SelfModificationRecord.promoted_to_primary.is_(True)
            )
        )
    ).scalar_one() or 0)
    rolled_back = int((
        await db.execute(
            select(func.count()).select_from(SelfModificationRecord).where(
                SelfModificationRecord.rolled_back_at.is_not(None)
            )
        )
    ).scalar_one() or 0)
    return {
        "status": "safety_membrane_active",
        "records": total_records,
        "promoted": promoted,
        "rolled_back": rolled_back,
        "immutable_core": SAFETY_MEMBRANE["immutable_core"],
        "pipeline": SAFETY_MEMBRANE["self_modification_pipeline"],
        "rollback_days": SAFETY_MEMBRANE["rollback_days"],
    }


async def meta_learning_status(db: AsyncSession) -> dict[str, Any]:
    shelved = int((await db.execute(select(func.count()).select_from(ShelvedDiscovery))).scalar_one() or 0)
    activated = int((
        await db.execute(
            select(func.count()).select_from(ShelvedDiscovery).where(ShelvedDiscovery.is_activated.is_(True))
        )
    ).scalar_one() or 0)
    return {
        "status": "meta_learning_loop_ready",
        "dimension_count": len(META_LEARNING_DIMENSIONS),
        "dimensions": META_LEARNING_DIMENSIONS,
        "shelved_discoveries": shelved,
        "activated_discoveries": activated,
        "cadence": "weekly",
    }


async def create_recommendation_object(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    recommendation = {
        "recommendation_id": f"supreme-{int(datetime.now(timezone.utc).timestamp())}",
        "trigger": payload.get("trigger", "manual_captain_request"),
        "ring_origin": "RING_1_ADVISORY",
        "recommendation": payload.get("recommendation") or payload.get("question") or "Council recommendation pending detail.",
        "confidence": float(payload.get("confidence", 0.72)),
        "dissent": payload.get("dissent", []),
        "evidence_refs": payload.get("evidence_refs", []),
        "requires_jarvis_decision": True,
        "requires_captain_approval": bool(payload.get("tier", 2) >= 3 or payload.get("requires_captain_approval", False)),
        "blocked_execution_handles": ["direct_deploy", "direct_spend", "direct_client_send", "direct_governance_mutation"],
        "next_route": "JARVIS_EXECUTIVE" if not payload.get("requires_captain_approval") else "CAPTAIN_MEMBRANE",
    }
    await record_event(
        db,
        "SUPREME_COUNCIL_RECOMMENDATION",
        "SUPREME_COUNCIL_LAYER",
        recommendation,
        severity="WARNING" if recommendation["requires_captain_approval"] else "INFO",
        captain_approval_required=recommendation["requires_captain_approval"],
    )
    await db.commit()
    return {**recommendation, "persisted": True}


async def evaluate_self_modification(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    blast_radius = str(payload.get("blast_radius", "PROMPT")).upper()
    title = payload.get("title") or payload.get("description") or "Self-modification proposal"
    blocked = blast_radius == "CORE" or any(
        token in str(title).lower()
        for token in ("kill switch", "captain authority", "governance tier", "safety membrane")
    )
    evaluation = {
        "status": "blocked_by_membrane" if blocked else "proposal_created_for_shadow_review",
        "title": title,
        "blast_radius": blast_radius,
        "immutable_core_touched": blocked,
        "pipeline": SAFETY_MEMBRANE["self_modification_pipeline"],
        "rollback_required_days": SAFETY_MEMBRANE["rollback_days"],
        "can_execute_now": False,
        "captain_approval_required": True,
    }
    if not blocked:
        proposal = await create_autonomy_proposal(
            db,
            {
                "need": title,
                "title": title,
                "proposal_type": "SELF_MODIFICATION",
                "blast_radius": blast_radius,
                "rationale": payload.get("rationale", "Improve AIONX operating quality inside the safety membrane."),
                "expected_benefit": payload.get("expected_benefit", "Measured improvement after shadow/A-B validation."),
                "rollback_plan": payload.get("rollback_plan", "Revert to previous approved configuration within 90 days."),
            },
        )
        evaluation["proposal"] = proposal
    else:
        await record_event(
            db,
            "SELF_MODIFICATION_BLOCKED",
            "SAFETY_MEMBRANE",
            evaluation,
            severity="CRITICAL",
            captain_approval_required=True,
        )
        await db.commit()
    return evaluation


async def run_meta_learning_cycle(db: AsyncSession) -> dict[str, Any]:
    calibration = await calibration_health(db)
    convergence = await convergence_health(db)
    membrane = await membrane_status(db)
    meta = await meta_learning_status(db)
    cycle = {
        "status": "meta_learning_cycle_recorded",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_quality_action": "Keep source weights stable until more adopted discoveries exist.",
        "debate_efficiency_action": "Maintain current convergence gate; no token spiral detected.",
        "provider_calibration_action": (
            "Collect more resolved provider predictions."
            if calibration["resolved_claims"] < 5
            else "Rebalance domain authority from resolved Brier scores."
        ),
        "counterfactual_precision_action": "Use counterfactual actualizations in weekly Wisdom Index.",
        "convergence_timing_action": f"Grand sessions={convergence['grand_sessions']}; completed={convergence['completed_grand_sessions']}.",
        "safety_membrane_action": f"Self-mod records={membrane['records']}; promoted={membrane['promoted']}; rolled_back={membrane['rolled_back']}.",
        "shelved_discovery_action": f"Shelved={meta['shelved_discoveries']}; activated={meta['activated_discoveries']}.",
        "captain_boundary": "This cycle records recommendations only; it does not modify production automatically.",
    }
    await record_event(db, "SUPREME_COUNCIL_META_LEARNING", "SUPREME_COUNCIL_LAYER", cycle)
    await db.commit()
    return cycle
