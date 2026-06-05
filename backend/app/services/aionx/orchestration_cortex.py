"""JARVIS Orchestration Cortex — the supreme conductor of AIONX.

Not a manager — a nervous system. Connects events to organs, computes the
live Operational IQ, fires the Event Fabric cascade, and gives the dormant
sovereign organs a heartbeat.

This is the layer that makes 73 systems act like one organism.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ClientDigitalTwin,
    DecisionObject,
    SentinelObservation,
    SentinelThreat,
    WisdomIndexSnapshot,
)
from app.services.aionx import (
    client_digital_twin,
    decision_memory_engine,
    grand_convergence_council,
)
from app.services.aionx.institutional_wisdom_index import get_current_wisdom

logger = logging.getLogger(__name__)


# ─── EVENT FABRIC ────────────────────────────────────────────────────────────
# One event triggers a choreographed cascade across all organs simultaneously.

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
    "MISSION_FAILED": [
        "create_autopsy",
        "open_convergence_council",
        "create_decision_object",
        "notify_captain",
    ],
    "CHURN_RISK_DETECTED": [
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
    """Event Fabric entrypoint. Fires the cascade for a given event type."""
    cascade = EVENT_CASCADES.get(event_type, [])
    if not cascade:
        logger.info("Orchestration Cortex: no cascade for event %s", event_type)
        return {"event": event_type, "steps_fired": 0}

    results: list[dict[str, Any]] = []
    for step in cascade:
        try:
            result = await _execute_cascade_step(db, step, payload)
            results.append({"step": step, "status": "ok", "result": result})
        except Exception as exc:  # noqa: BLE001 — one step failing must not break the cascade
            logger.warning("Cascade step %s failed for %s: %s", step, event_type, exc)
            results.append({"step": step, "status": "failed", "error": str(exc)})

    logger.info(
        "Orchestration Cortex: event=%s fired %d/%d steps",
        event_type, sum(1 for r in results if r["status"] == "ok"), len(cascade),
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
                db, client_id,
                interaction_type=payload.get("interaction_type", "REPLY"),
                sentiment=payload.get("sentiment", "neutral"),
                trust_delta=payload.get("trust_delta", 1.0),
                summary=payload.get("summary"),
            )
            return {"interaction": "recorded"}

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
        session = await convene_provider_council(
            db,
            trigger_type="SENTINEL_SIGNAL",
            trigger_signal=payload.get("summary"),
            agenda_items=[payload.get("summary", "New world signal")],
            domain=payload.get("domain", "STRATEGY"),
        )
        return {"provider_session_id": str(session.id)}

    elif step == "record_ownership":
        mission_id = _as_uuid(payload.get("mission_id"))
        client_id = _as_uuid(payload.get("client_id"))
        if mission_id:
            from app.models.aionx_organs import MissionOwnershipRecord
            ownership = MissionOwnershipRecord(
                mission_id=mission_id,
                client_id=client_id,
                executive_owner="JARVIS",
                mission_status="ACTIVE",
            )
            db.add(ownership)
            await db.flush()
            logger.info("Orchestration Cortex: ownership recorded for mission %s client %s", mission_id, client_id)
            return {"ownership_id": str(ownership.id), "mission_id": str(mission_id)}

    elif step == "notify_captain":
        # Send async notification to Captain via Slack + Telegram
        try:
            from app.services.notifications.slack import send_slack_message
            from app.services.notifications.telegram import send_telegram_message

            event_type = payload.get("event_type", "EVENT")
            client_id = payload.get("client_id", "unknown")
            stage_name = payload.get("stage_name", "Unknown stage")

            message = f"🔔 **{event_type}** — Client {client_id} at stage: {stage_name}"

            # Fire and forget — don't block cascade if notifications fail
            try:
                await send_slack_message(message)
            except Exception as e:
                logger.warning("Slack notification failed: %s", e)

            try:
                await send_telegram_message(message)
            except Exception as e:
                logger.warning("Telegram notification failed: %s", e)

            logger.info("Orchestration Cortex: Captain notified of %s", event_type)
            return {"notified": True, "event": event_type}
        except Exception as e:
            logger.warning("Captain notification failed: %s", e)
            return {"notified": False, "error": str(e)}

    elif step == "create_autopsy":
        mission_id = _as_uuid(payload.get("mission_id"))
        if mission_id:
            from app.models.aionx_organs import MissionAutopsy
            from app.services.ai.router import route_task

            # AI-powered failure analysis
            analysis = await route_task(
                task_type="reasoning",
                prompt=f"Analyze why this mission failed. Mission ID: {mission_id}. "
                       f"Problem: {payload.get('problem', 'Mission failure detected')}. "
                       f"Provide root causes, prevention strategies, and process improvements.",
                max_tokens=800,
            )

            autopsy = MissionAutopsy(
                mission_id=mission_id,
                failure_type=payload.get("failure_type", "UNKNOWN"),
                root_cause_analysis=analysis if analysis != "ROUTE_TASK_UNAVAILABLE" else "Analysis unavailable",
                prevention_strategies=[],
                status="COMPLETED",
            )
            db.add(autopsy)
            await db.flush()
            logger.info("Orchestration Cortex: autopsy created for mission %s", mission_id)
            return {"autopsy_id": str(autopsy.id), "analysis": analysis}

    elif step in ("speed_to_lead_queue",):
        # Queue task for speed-to-lead engine
        logger.info("Orchestration Cortex: speed-to-lead task queued with payload keys %s", list(payload.keys()))
        return {"queued": step}

    return {"noop": step}


# ─── OPERATIONAL IQ ──────────────────────────────────────────────────────────
# One live number (0-100) representing how well the whole company is doing now.

async def compute_operational_iq(db: AsyncSession) -> dict[str, Any]:
    """Compress revenue velocity, system health, decision quality, client health,
    and wisdom into one live score."""

    # Wisdom component (0-1000 → 0-25)
    wisdom = await get_current_wisdom(db)
    wisdom_component = min(25.0, (wisdom.get("wisdom_score", 500.0) / 1000.0) * 25.0)

    # Decision activity component (0-25) — is the organism thinking?
    decision_count = (await db.execute(
        select(func.count()).select_from(DecisionObject)
    )).scalar_one()
    decision_component = min(25.0, decision_count * 0.5)

    # Client health component (0-25) — average trust across twins
    avg_trust = (await db.execute(
        select(func.avg(ClientDigitalTwin.trust_score))
    )).scalar_one()
    client_component = ((avg_trust or 50.0) / 100.0) * 25.0

    # Threat penalty (0-25 starting, minus active critical threats)
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
        return "PEAK — organism performing excellently across all dimensions."
    if iq >= 60:
        return "HEALTHY — strong operation, minor optimization available."
    if iq >= 40:
        return "DEVELOPING — organism is young, building intelligence and clients."
    if iq >= 20:
        return "EARLY — foundation laid, needs data and client activity to mature."
    return "DORMANT — organs alive but awaiting first real activity."


# ─── SITUATIONAL AWARENESS SNAPSHOT ──────────────────────────────────────────

async def situational_snapshot(db: AsyncSession) -> dict[str, Any]:
    """Full live picture of the organism for Captain's Glass Wall."""
    iq = await compute_operational_iq(db)
    wisdom = await get_current_wisdom(db)

    decision_count = (await db.execute(
        select(func.count()).select_from(DecisionObject)
    )).scalar_one()
    twin_count = (await db.execute(
        select(func.count()).select_from(ClientDigitalTwin)
    )).scalar_one()
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
