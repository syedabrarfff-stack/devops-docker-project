"""JARVIS Orchestration Cortex - the conductor of AIONX.

Connects business events to sovereign organs, computes Operational IQ, and
keeps the organ layer wired into production-safe persistence.
"""
from __future__ import annotations

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.aionx_organs import (
    ClientDigitalTwin,
    DecisionObject,
    MissionAutopsy,
    MissionOwnershipRecord,
    SentinelObservation,
    SentinelThreat,
)
from app.models.revenue_activation import SpeedToLeadEvent
from app.services.aionx import (
    client_digital_twin,
    decision_memory_engine,
    grand_convergence_council,
)
from app.services.aionx.institutional_wisdom_index import get_current_wisdom

logger = logging.getLogger(__name__)


EVENT_CASCADES: dict[str, list[str]] = {
    "CLIENT_SIGNED": [
        "create_digital_twin",
        "create_decision_object",
        "open_delivery_council",
        "record_ownership",
        "notify_captain",
    ],
    "LEAD_REPLIED": [
        "create_decision_object",
        "update_twin_interaction",
        "speed_to_lead_queue",
    ],
    # Fired when reply classification = INTERESTED — highest-value lead signal
    "LEAD_INTERESTED": [
        "update_twin_interaction",
        "create_decision_object",
        "open_convergence_council",
        "speed_to_lead_queue",
        "notify_captain",
    ],
    # Fired when reply classification = QUESTION — nurture, do not close prematurely
    "LEAD_QUESTION": [
        "update_twin_interaction",
        "create_decision_object",
        "speed_to_lead_queue",
        "notify_captain",
    ],
    "EMAIL_REPLY_RECEIVED": [
        "update_twin_interaction",
        "create_decision_object",
        "speed_to_lead_queue",
    ],
    "MISSION_FAILED": [
        "create_autopsy",
        "open_convergence_council",
        "convene_provider_council",
        "create_decision_object",
        "notify_captain",
    ],
    "CHURN_RISK_DETECTED": [
        "update_twin_profile",
        "open_convergence_council",
        "create_decision_object",
        "notify_captain",
    ],
    "SENTINEL_STRONG_SIGNAL": [
        "convene_provider_council",
        "create_decision_object",
    ],
}


async def fire_event(
    db: AsyncSession,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Fire the cascade for a given event type."""
    payload = dict(payload or {})
    payload.setdefault("event_type", event_type)
    cascade = EVENT_CASCADES.get(event_type, [])
    if not cascade:
        logger.info("Orchestration Cortex: no cascade for event %s", event_type)
        return {"event": event_type, "steps_fired": 0}

    results: list[dict[str, Any]] = []
    for step in cascade:
        try:
            result = await _execute_cascade_step(db, step, payload)
            results.append({"step": step, "status": "ok", "result": result})
        except Exception as exc:  # One step failing must not break the cascade.
            logger.warning("Cascade step %s failed for %s: %s", step, event_type, exc)
            results.append({"step": step, "status": "failed", "error": str(exc)})

    logger.info(
        "Orchestration Cortex: event=%s fired %d/%d steps",
        event_type,
        sum(1 for result in results if result["status"] == "ok"),
        len(cascade),
    )
    return {"event": event_type, "steps_fired": len(results), "results": results}


async def _execute_cascade_step(
    db: AsyncSession,
    step: str,
    payload: dict[str, Any],
) -> Any:
    if step == "create_digital_twin":
        client_id = _as_uuid(payload.get("client_id"))
        if client_id:
            twin = await client_digital_twin.get_or_create_twin(db, client_id)
            return {"twin_id": str(twin.id)}

    elif step == "update_twin_interaction":
        client_id = _as_uuid(payload.get("client_id"))
        if client_id:
            await client_digital_twin.record_interaction(
                db,
                client_id,
                interaction_type=payload.get("interaction_type", "REPLY"),
                sentiment=payload.get("sentiment", "neutral"),
                trust_delta=payload.get("trust_delta", 1.0),
                summary=payload.get("summary"),
            )
            return {"interaction": "recorded"}

    elif step == "update_twin_profile":
        client_id = _as_uuid(payload.get("client_id"))
        if client_id:
            twin = await client_digital_twin.get_or_create_twin(db, client_id)
            churn_risk = float(payload.get("churn_risk_score", max(twin.churn_risk_score, 75.0)))
            twin.churn_risk_score = min(100.0, max(0.0, churn_risk))
            twin.successful_strategies = list(twin.successful_strategies or []) + [{
                "event": payload.get("event_type", "CHURN_RISK_DETECTED"),
                "action": "opened_convergence_council",
                "at": datetime.utcnow().isoformat(),
            }]
            await db.flush()
            return {"twin_id": str(twin.id), "churn_risk_score": twin.churn_risk_score}

    elif step == "create_decision_object":
        decision = await decision_memory_engine.create_decision_object(
            db,
            trigger_event=payload.get("event_type", "ORCHESTRATION_EVENT"),
            problem_statement=payload.get("problem", "Auto-generated from event cascade"),
            tier=payload.get("tier", 2),
            decision_category=payload.get("category", "OPERATIONAL"),
            client_id=_as_uuid(payload.get("client_id")),
            mission_id=_as_uuid(payload.get("mission_id")),
            confidence_score=payload.get("confidence", 0.7),
        )
        return {"decision_id": str(decision.id)}

    elif step in ("open_delivery_council", "open_convergence_council"):
        session = await grand_convergence_council.open_session(
            db,
            trigger_event=payload.get("event_type", step),
            trigger_type=payload.get("trigger_type", "OPPORTUNITY"),
        )
        return {"session_id": str(session.id)}

    elif step == "convene_provider_council":
        from app.services.aionx.provider_sovereign_council import convene_provider_council

        signal = payload.get("summary") or payload.get("problem") or "New world signal"
        session = await convene_provider_council(
            db,
            trigger_type=payload.get("trigger_type", "SENTINEL_SIGNAL"),
            trigger_signal=signal,
            agenda_items=[signal],
            domain=payload.get("domain", "STRATEGY"),
        )
        return {"provider_session_id": str(session.id)}

    elif step == "record_ownership":
        mission_id = _as_uuid(payload.get("mission_id"))
        client_id = _as_uuid(payload.get("client_id"))
        if mission_id:
            ownership = (await db.execute(
                select(MissionOwnershipRecord).where(MissionOwnershipRecord.mission_id == mission_id)
            )).scalars().first()
            if not ownership:
                ownership = MissionOwnershipRecord(
                    mission_id=mission_id,
                    client_id=client_id,
                    executive_owner=payload.get("executive_owner", "JARVIS"),
                    mission_status=payload.get("mission_status", "ACTIVE"),
                )
                db.add(ownership)
            else:
                ownership.client_id = ownership.client_id or client_id
                ownership.mission_status = payload.get("mission_status", ownership.mission_status)
            await db.flush()
            return {"ownership_id": str(ownership.id), "mission_id": str(mission_id)}

    elif step == "notify_captain":
        try:
            from app.services.notifications import notify_business_event

            event_type = payload.get("event_type", "EVENT")
            client_id = payload.get("client_id", "unknown")
            stage_name = payload.get("stage_name", "Unknown stage")
            summary = f"Client {client_id} at stage: {stage_name}"
            notified = await notify_business_event(event_type, f"AIONX event: {event_type}", summary)
            return {"notified": notified, "event": event_type}
        except Exception as exc:
            logger.warning("Captain notification failed: %s", exc)
            return {"notified": False, "error": str(exc)}

    elif step == "create_autopsy":
        mission_id = _as_uuid(payload.get("mission_id"))
        if mission_id:
            existing = (await db.execute(
                select(MissionAutopsy).where(MissionAutopsy.mission_id == mission_id)
            )).scalars().first()
            if existing:
                return {"autopsy_id": str(existing.id), "mission_id": str(mission_id), "existing": True}

            analysis = await _route_task_bounded(
                task_type="reasoning",
                prompt=(
                    f"Analyze why this mission failed. Mission ID: {mission_id}. "
                    f"Problem: {payload.get('problem', 'Mission failure detected')}. "
                    "Provide root causes, prevention strategies, and process improvements."
                ),
                max_tokens=800,
                timeout_seconds=8.0,
            )

            autopsy = MissionAutopsy(
                mission_id=mission_id,
                client_id=_as_uuid(payload.get("client_id")),
                failure_type=payload.get("failure_type", "UNKNOWN"),
                failure_summary=payload.get("summary") or payload.get("problem") or "Mission failure detected",
                causal_chain=[{"source": "orchestration_cortex", "analysis": analysis}],
                what_failed=payload.get("problem", "Mission failure detected"),
                why_it_failed=analysis if analysis != "ROUTE_TASK_UNAVAILABLE" else "Analysis unavailable",
                who_detected=payload.get("detected_by", "AIONX_CORTEX"),
                alternative_path_that_would_succeed="Review convergence council recommendation before retry.",
                institutional_doctrine="Mission failures must create an auditable autopsy before retry.",
            )
            db.add(autopsy)
            await db.flush()
            return {"autopsy_id": str(autopsy.id), "analysis": analysis}

    elif step == "speed_to_lead_queue":
        tenant_id = _tenant_id()
        source_id = str(payload.get("event_id") or payload.get("source_id") or uuid.uuid4())
        existing = (await db.execute(
            select(SpeedToLeadEvent).where(
                SpeedToLeadEvent.tenant_id == tenant_id,
                SpeedToLeadEvent.source_type == "AIONX_CORTEX",
                SpeedToLeadEvent.source_id == source_id,
            )
        )).scalars().first()
        if existing:
            return {"queued": step, "speed_to_lead_event_id": str(existing.id), "existing": True}

        event = SpeedToLeadEvent(
            tenant_id=tenant_id,
            lead_id=_as_uuid(payload.get("lead_id")),
            source_type="AIONX_CORTEX",
            source_id=source_id,
            trigger_type=payload.get("event_type", "LEAD_REPLIED"),
            captain_online=bool(payload.get("captain_online", False)),
            action_taken="QUEUED",
            draft_subject=payload.get("draft_subject"),
            draft_body=payload.get("draft_body"),
            payload=payload,
        )
        db.add(event)
        await db.flush()
        return {"queued": step, "speed_to_lead_event_id": str(event.id)}

    return {"noop": step}


async def compute_operational_iq(db: AsyncSession) -> dict[str, Any]:
    """Compress wisdom, decision activity, client health, and threats into one score."""
    _tid = _tenant_id()

    wisdom = await get_current_wisdom(db)
    wisdom_component = min(25.0, (wisdom.get("wisdom_score", 500.0) / 1000.0) * 25.0)

    decision_count = (await db.execute(
        select(func.count()).select_from(DecisionObject).where(
            DecisionObject.tenant_id == _tid
        )
    )).scalar_one()
    decision_component = min(25.0, decision_count * 0.5)

    avg_trust = (await db.execute(
        select(func.avg(ClientDigitalTwin.trust_score)).where(
            ClientDigitalTwin.tenant_id == _tid
        )
    )).scalar_one()
    client_component = ((avg_trust or 50.0) / 100.0) * 25.0

    # SentinelThreat has no tenant_id — global threat intelligence
    critical_threats = (await db.execute(
        select(func.count()).select_from(SentinelThreat).where(
            SentinelThreat.severity == "CRITICAL",
            SentinelThreat.status == "ACTIVE",
        )
    )).scalar_one()
    health_component = max(0.0, 25.0 - (critical_threats * 5.0))

    iq = round(wisdom_component + decision_component + client_component + health_component, 1)
    return {
        "operational_iq": iq,
        "components": {
            "wisdom": round(wisdom_component, 1),
            "decision_activity": round(decision_component, 1),
            "client_health": round(client_component, 1),
            "system_health": round(health_component, 1),
        },
        "interpretation": _interpret_iq(iq),
        "computed_at": datetime.utcnow().isoformat(),
    }


def _interpret_iq(iq: float) -> str:
    if iq >= 80:
        return "PEAK - organism performing excellently across all dimensions."
    if iq >= 60:
        return "HEALTHY - strong operation, minor optimization available."
    if iq >= 40:
        return "DEVELOPING - organism is young, building intelligence and clients."
    if iq >= 20:
        return "EARLY - foundation laid, needs data and client activity to mature."
    return "DORMANT - organs alive but awaiting first real activity."


async def situational_snapshot(db: AsyncSession) -> dict[str, Any]:
    """Full live picture of the organism for Captain's Glass Wall."""
    _tid = _tenant_id()

    iq = await compute_operational_iq(db)
    wisdom = await get_current_wisdom(db)

    decision_count = (await db.execute(
        select(func.count()).select_from(DecisionObject).where(
            DecisionObject.tenant_id == _tid
        )
    )).scalar_one()
    twin_count = (await db.execute(
        select(func.count()).select_from(ClientDigitalTwin).where(
            ClientDigitalTwin.tenant_id == _tid
        )
    )).scalar_one()
    # SentinelObservation and SentinelThreat have no tenant_id — global intelligence
    obs_count = (await db.execute(
        select(func.count()).select_from(SentinelObservation)
    )).scalar_one()
    active_threats = (await db.execute(
        select(func.count()).select_from(SentinelThreat).where(SentinelThreat.status == "ACTIVE")
    )).scalar_one()

    return {
        "operational_iq": iq["operational_iq"],
        "iq_interpretation": iq["interpretation"],
        "iq_components": iq["components"],
        "wisdom_index": wisdom.get("wisdom_score", 500.0),
        "wisdom_narrative": wisdom.get("narrative"),
        "live_counts": {
            "decisions_recorded": decision_count,
            "client_digital_twins": twin_count,
            "sentinel_observations": obs_count,
            "active_threats": active_threats,
        },
        "organism_status": (
            "ALIVE_AND_LEARNING" if decision_count > 0 else "ALIVE_AWAITING_FIRST_ACTIVITY"
        ),
        "snapshot_at": datetime.utcnow().isoformat(),
    }


def _as_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _tenant_id() -> uuid.UUID:
    configured = getattr(settings, "JARVIS_DEFAULT_TENANT_ID", None)
    if configured:
        parsed = _as_uuid(configured)
        if parsed:
            return parsed
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _route_task_bounded(
    *,
    task_type: str,
    prompt: str,
    max_tokens: int,
    timeout_seconds: float,
) -> str:
    from app.services.ai.router import route_task

    try:
        return await asyncio.wait_for(
            route_task(task_type=task_type, prompt=prompt, max_tokens=max_tokens),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("AIONX route_task timed out after %.1fs", timeout_seconds)
        return "ROUTE_TASK_TIMEOUT"
    except Exception as exc:
        logger.warning("AIONX route_task failed: %s", exc)
        return "ROUTE_TASK_UNAVAILABLE"
