"""AIONX Batch 1 client pipeline orchestrator.

This service is the event-producing spine for the 33-stage client journey.
It persists each client's current stage, keeps the next milestones visible,
and fires Cortex events when stage transitions cross operational thresholds.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.aionx_organs import ClientPipelineMilestone, ClientPipelineState
from app.services.aionx.orchestration_cortex import fire_event

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

PIPELINE_STAGES: dict[int, dict[str, Any]] = {
    1: {"name": "Lead source identified", "phase": "Lead discovery & qualification", "department": "Market Intelligence"},
    2: {"name": "Lead enriched", "phase": "Lead discovery & qualification", "department": "Lead Intelligence"},
    3: {"name": "ICP fit scored", "phase": "Lead discovery & qualification", "department": "Sales Intelligence"},
    4: {"name": "Pain hypothesis formed", "phase": "Lead discovery & qualification", "department": "Strategy"},
    5: {"name": "Qualified opportunity approved", "phase": "Lead discovery & qualification", "department": "Captain Bridge"},
    6: {"name": "First outreach sent", "phase": "Outreach & engagement", "department": "Outreach"},
    7: {"name": "Reply captured", "phase": "Outreach & engagement", "department": "Outreach"},
    8: {"name": "Discovery conversation booked", "phase": "Outreach & engagement", "department": "Sales"},
    9: {"name": "Discovery notes analyzed", "phase": "Outreach & engagement", "department": "Sales Intelligence"},
    10: {"name": "Buying committee mapped", "phase": "Outreach & engagement", "department": "Relationship Intelligence"},
    11: {"name": "Solution fit validated", "phase": "Outreach & engagement", "department": "Engineering"},
    12: {"name": "Engagement readiness approved", "phase": "Outreach & engagement", "department": "Council"},
    13: {"name": "Proposal scope drafted", "phase": "Proposal & negotiation", "department": "Proposal Intelligence"},
    14: {"name": "Technical feasibility validated", "phase": "Proposal & negotiation", "department": "Engineering"},
    15: {"name": "ROI model prepared", "phase": "Proposal & negotiation", "department": "Finance"},
    16: {"name": "Proposal reviewed by council", "phase": "Proposal & negotiation", "department": "Council"},
    17: {"name": "Negotiation objections resolved", "phase": "Proposal & negotiation", "department": "Sales"},
    18: {"name": "Final offer approved", "phase": "Proposal & negotiation", "department": "Captain Bridge"},
    19: {"name": "Deal terms accepted", "phase": "Deal closure & onboarding", "department": "Sales"},
    20: {"name": "Contract generated", "phase": "Deal closure & onboarding", "department": "Operations"},
    21: {"name": "Payment path confirmed", "phase": "Deal closure & onboarding", "department": "Finance"},
    22: {"name": "Onboarding packet created", "phase": "Deal closure & onboarding", "department": "Client Success"},
    23: {"name": "Kickoff scheduled", "phase": "Deal closure & onboarding", "department": "Client Success"},
    24: {"name": "Delivery mission designed", "phase": "Deal closure & onboarding", "department": "Delivery"},
    25: {"name": "Client signed and mission activated", "phase": "Deal closure & onboarding", "department": "Captain Bridge"},
    26: {"name": "Delivery sprint opened", "phase": "Delivery & execution", "department": "Delivery"},
    27: {"name": "Milestones decomposed", "phase": "Delivery & execution", "department": "Operations"},
    28: {"name": "Quality checkpoint passed", "phase": "Delivery & execution", "department": "QA"},
    29: {"name": "Client validation completed", "phase": "Delivery & execution", "department": "Client Success"},
    30: {"name": "Production handoff completed", "phase": "Delivery & execution", "department": "Engineering"},
    31: {"name": "Success metrics reviewed", "phase": "Success & renewal", "department": "Client Success"},
    32: {"name": "Renewal or expansion path proposed", "phase": "Success & renewal", "department": "Growth"},
    33: {"name": "Relationship doctrine captured", "phase": "Success & renewal", "department": "Wisdom"},
}

COUNCIL_GATE_STAGES = {5, 12, 16, 18, 25, 28, 30, 33}
QA_STAGES = {14, 16, 24, 28, 30}
VALIDATION_STAGES = {5, 11, 14, 18, 24, 25, 28, 30}


async def get_pipeline(db: AsyncSession, client_id: uuid.UUID) -> dict[str, Any]:
    """Return current pipeline state and next three milestones for a client."""
    state = await _get_or_create_state(db, client_id)
    milestones = await _ensure_next_milestones(db, state)
    await db.commit()
    return _state_payload(state, milestones[:3])


async def advance_stage(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    target_stage: int,
    engagement_score: float | None = None,
    mission_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Advance a client stage and fire any Cortex events unlocked by transition."""
    if target_stage < 1 or target_stage > 33:
        raise ValueError("target_stage must be between 1 and 33")

    state = await _get_or_create_state(db, client_id)
    previous_stage = int(state.current_stage or 1)
    previous_engagement = float(state.engagement_score or 50.0)
    now = datetime.now(timezone.utc)

    stage = PIPELINE_STAGES[target_stage]
    state.current_stage = target_stage
    state.stage_name = stage["name"]
    state.phase = stage["phase"]
    state.previous_engagement_score = previous_engagement
    if engagement_score is not None:
        state.engagement_score = max(0.0, min(100.0, float(engagement_score)))
    state.stage_entered_at = now
    state.last_activity_at = now
    state.mission_id = mission_id or state.mission_id
    state.council_gate_status = "REQUIRED" if target_stage in COUNCIL_GATE_STAGES else "NOT_REQUIRED"
    state.validation_status = "REQUIRED" if target_stage in VALIDATION_STAGES else "NOT_REQUIRED"
    state.qa_status = "REQUIRED" if target_stage in QA_STAGES else "NOT_REQUIRED"
    state.metadata_json = {**(state.metadata_json or {}), **(metadata or {})}
    state.status = "ACTIVE" if target_stage < 33 else "COMPLETE"

    await _mark_stage_milestones_done(db, state, target_stage)
    milestones = await _ensure_next_milestones(db, state)
    events = await _fire_transition_events(db, state, previous_stage, previous_engagement)
    await db.commit()

    return {
        **_state_payload(state, milestones[:3]),
        "previous_stage": previous_stage,
        "events_fired": events,
    }


async def detect_pipeline_risks(db: AsyncSession, client_id: uuid.UUID) -> list[dict[str, Any]]:
    """Detect stall and trust-risk conditions without mutating stage position."""
    state = await _get_or_create_state(db, client_id)
    risks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    if state.last_activity_at and now - _aware(state.last_activity_at) > timedelta(days=30):
        risks.append({"type": "MISSION_FAILED", "reason": "pipeline stalled for more than 30 days"})
    if float(state.engagement_score or 0) <= 30:
        risks.append({"type": "CHURN_RISK_DETECTED", "reason": "engagement score at or below 30"})
    return risks


async def _get_or_create_state(db: AsyncSession, client_id: uuid.UUID) -> ClientPipelineState:
    result = await db.execute(select(ClientPipelineState).where(ClientPipelineState.client_id == client_id))
    state = result.scalar_one_or_none()
    if state:
        return state

    stage = PIPELINE_STAGES[1]
    state = ClientPipelineState(
        tenant_id=_tenant_id(),
        client_id=client_id,
        current_stage=1,
        stage_name=stage["name"],
        phase=stage["phase"],
    )
    db.add(state)
    await db.flush()
    return state


async def _ensure_next_milestones(db: AsyncSession, state: ClientPipelineState) -> list[ClientPipelineMilestone]:
    await db.execute(
        delete(ClientPipelineMilestone).where(
            ClientPipelineMilestone.client_id == state.client_id,
            ClientPipelineMilestone.status == "PENDING",
        )
    )
    next_stages = [s for s in range(int(state.current_stage) + 1, min(33, int(state.current_stage) + 3) + 1)]
    milestones: list[ClientPipelineMilestone] = []
    for order, stage_number in enumerate(next_stages, start=1):
        stage = PIPELINE_STAGES[stage_number]
        milestone = ClientPipelineMilestone(
            tenant_id=state.tenant_id,
            client_id=state.client_id,
            pipeline_state_id=state.id,
            stage_number=stage_number,
            milestone_order=order,
            title=stage["name"],
            department=stage["department"],
            due_at=datetime.now(timezone.utc) + timedelta(days=order * 3),
            evidence={
                "phase": stage["phase"],
                "council_gate": stage_number in COUNCIL_GATE_STAGES,
                "validation_required": stage_number in VALIDATION_STAGES,
                "qa_required": stage_number in QA_STAGES,
            },
        )
        db.add(milestone)
        milestones.append(milestone)
    await db.flush()
    return milestones


async def _mark_stage_milestones_done(db: AsyncSession, state: ClientPipelineState, target_stage: int) -> None:
    result = await db.execute(
        select(ClientPipelineMilestone).where(
            ClientPipelineMilestone.client_id == state.client_id,
            ClientPipelineMilestone.stage_number <= target_stage,
            ClientPipelineMilestone.status == "PENDING",
        )
    )
    for milestone in result.scalars().all():
        milestone.status = "DONE"


async def _fire_transition_events(
    db: AsyncSession,
    state: ClientPipelineState,
    previous_stage: int,
    previous_engagement: float,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    payload = {
        "client_id": str(state.client_id),
        "mission_id": str(state.mission_id) if state.mission_id else None,
        "pipeline_stage": state.current_stage,
        "stage_name": state.stage_name,
        "phase": state.phase,
        "category": "CLIENT_PIPELINE",
    }

    if previous_stage < 6 <= state.current_stage:
        events.append(await _safe_fire(db, "LEAD_REPLIED", {**payload, "event_type": "LEAD_REPLIED", "problem": "Client replied; convert engagement into qualified next action."}))
    if previous_stage < 25 <= state.current_stage:
        events.append(await _safe_fire(db, "CLIENT_SIGNED", {**payload, "event_type": "CLIENT_SIGNED", "problem": "Client signed; activate delivery mission and ownership."}))
    if previous_engagement - float(state.engagement_score or 0) >= 20:
        events.append(await _safe_fire(db, "CHURN_RISK_DETECTED", {**payload, "event_type": "CHURN_RISK_DETECTED", "problem": "Engagement score dropped sharply during pipeline transition."}))

    now = datetime.now(timezone.utc)
    if state.last_activity_at and now - _aware(state.last_activity_at) > timedelta(days=30):
        events.append(await _safe_fire(db, "MISSION_FAILED", {**payload, "event_type": "MISSION_FAILED", "problem": "Pipeline stalled for more than 30 days."}))

    if (state.metadata_json or {}).get("market_signal_strength") == "STRONG":
        events.append(await _safe_fire(db, "SENTINEL_STRONG_SIGNAL", {**payload, "event_type": "SENTINEL_STRONG_SIGNAL", "summary": "Client pipeline affected by strong market signal."}))

    return events


async def _safe_fire(db: AsyncSession, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = await fire_event(db, event_type, payload)
        return {"event_type": event_type, "status": "ok", "result": result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Batch 1 Cortex event failed: %s: %s", event_type, exc)
        return {"event_type": event_type, "status": "failed", "error": str(exc)}


def _state_payload(state: ClientPipelineState, milestones: list[ClientPipelineMilestone]) -> dict[str, Any]:
    return {
        "client_id": str(state.client_id),
        "stage": state.current_stage,
        "stage_name": state.stage_name,
        "phase": state.phase,
        "status": state.status,
        "engagement_score": state.engagement_score,
        "mission_id": str(state.mission_id) if state.mission_id else None,
        "council_gate_status": state.council_gate_status,
        "validation_status": state.validation_status,
        "qa_status": state.qa_status,
        "repair_loop_count": state.repair_loop_count,
        "next_milestones": [
            {
                "stage": milestone.stage_number,
                "title": milestone.title,
                "department": milestone.department,
                "status": milestone.status,
                "due_at": milestone.due_at.isoformat() if milestone.due_at else None,
                "evidence": milestone.evidence,
            }
            for milestone in milestones
        ],
    }


def _tenant_id() -> uuid.UUID:
    raw = settings.JARVIS_DEFAULT_TENANT_ID
    return uuid.UUID(str(raw)) if raw else SYSTEM_TENANT_ID


def _aware(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)
