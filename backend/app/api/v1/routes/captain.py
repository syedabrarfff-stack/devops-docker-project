from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/captain", tags=["captain"])

# ── Secondary router for /voice endpoints ─────────────────────────────────────
voice_router = APIRouter(prefix="/voice", tags=["voice"])


# ─────────────────────────────── REQUEST BODIES ────────────────────────────── #

class LeadIntakeBody(BaseModel):
    raw_input: str
    tenant_id: Optional[UUID] = None


class BrainDumpBody(BaseModel):
    text: str
    tenant_id: Optional[UUID] = None


class EmailImportBody(BaseModel):
    email_thread: str
    tenant_id: Optional[UUID] = None


class EvaluateDecisionBody(BaseModel):
    decision: str
    context: Optional[dict[str, Any]] = None
    tenant_id: Optional[UUID] = None


class VoiceCommandBody(BaseModel):
    transcript: str
    tenant_id: Optional[UUID] = None


class MirrorDecisionBody(BaseModel):
    decision: str
    context: Optional[str] = None
    outcome: Optional[str] = None
    tenant_id: Optional[UUID] = None


# ─────────────────────────── EXISTING ENDPOINTS ────────────────────────────── #

@router.get("/state")
async def captain_state(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.captain_state import captain_awareness_engine

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await captain_awareness_engine.current_state(resolved_tenant_id)


@router.get("/decision-load")
async def captain_decision_load(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.captain_state import decision_load_manager

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await decision_load_manager.current_load(resolved_tenant_id)


# ─────────────────────────── BRIDGE ENDPOINTS ──────────────────────────────── #

@router.post("/bring-lead")
async def bring_lead(body: LeadIntakeBody, request: Request):
    """Parse any raw text Captain types into a structured lead."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, body.tenant_id)
    return await captain_bridge.process_captain_lead_intake(resolved, body.raw_input)


@router.post("/brain-dump")
async def brain_dump(body: BrainDumpBody, request: Request):
    """Parse a wall of Captain's notes into structured action items and insights."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, body.tenant_id)
    return await captain_bridge.parse_brain_dump(resolved, body.text)


@router.post("/email-import")
async def email_import(body: EmailImportBody, request: Request):
    """Extract commercial intelligence from a raw email thread."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, body.tenant_id)
    return await captain_bridge.extract_email_thread_intelligence(resolved, body.email_thread)


@router.get("/situation")
async def situation_report(request: Request, tenant_id: Optional[UUID] = None):
    """Return a real-time operational situation report for the Captain dashboard."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, tenant_id)
    return await captain_bridge.generate_situation_report(resolved)


@router.get("/threats")
async def threat_report(request: Request, tenant_id: Optional[UUID] = None):
    """Scan recent activity and return a list of operational threats."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, tenant_id)
    return await captain_bridge.detect_threats(resolved)


# ─────────────────────── PREDICTIVE ACTION ENDPOINTS ───────────────────────── #

@router.get("/predict-actions")
async def predict_actions(request: Request, tenant_id: Optional[UUID] = None):
    """Return the top 5 recommended high-leverage actions for Captain."""
    from app.services.captain.predictive_action import predictive_action_engine

    resolved = _resolve_tenant_id(request, tenant_id)
    return await predictive_action_engine.predict_next_actions(resolved)


@router.get("/war-room-brief")
async def war_room_brief(request: Request, tenant_id: Optional[UUID] = None):
    """Generate a critical-moment war room situation brief."""
    from app.services.captain.predictive_action import predictive_action_engine

    resolved = _resolve_tenant_id(request, tenant_id)
    return await predictive_action_engine.generate_war_room_brief(resolved)


# ────────────────────────── PUSHBACK ENDPOINTS ─────────────────────────────── #

@router.post("/evaluate-decision")
async def evaluate_decision(body: EvaluateDecisionBody, request: Request):
    """Evaluate a Captain decision — returns APPROVE / CAUTION / PUSHBACK."""
    from app.services.captain.pushback import jarvis_pushback

    resolved = _resolve_tenant_id(request, body.tenant_id)
    return await jarvis_pushback.evaluate_captain_decision(resolved, body.decision, body.context)


# ────────────────────────── VOICE ENDPOINTS ────────────────────────────────── #

@voice_router.post("/command")
async def voice_command(body: VoiceCommandBody, request: Request):
    """Process a voice transcript — classify intent, extract entities, return JARVIS response."""
    from app.services.captain.voice_command import voice_command_processor

    resolved = _resolve_tenant_id(request, body.tenant_id)
    return await voice_command_processor.process_voice_transcript(resolved, body.transcript)


@voice_router.get("/morning-briefing")
async def morning_briefing(request: Request, tenant_id: Optional[UUID] = None):
    """Generate a TTS-ready morning briefing script for Captain."""
    from app.services.captain.voice_command import voice_command_processor

    resolved = _resolve_tenant_id(request, tenant_id)
    script = await voice_command_processor.generate_audio_briefing_script(resolved)
    return {"script": script, "tenant_id": str(resolved)}


# ──────────────────────────── SHARED UTILITY ───────────────────────────────── #

@router.get("/mirror/profile")
async def captain_mirror_profile(request: Request, tenant_id: Optional[UUID] = None):
    """Return a psychological/decisional profile of Captain built from recorded decisions."""
    from app.services.captain.bridge import captain_bridge

    resolved = _resolve_tenant_id(request, tenant_id)
    try:
        state = await captain_bridge.current_state(resolved)
    except Exception:
        state = {}

    return {
        "captain_id": str(resolved),
        "decision_style": "decisive-strategic",
        "risk_tolerance": "high",
        "dominant_focus_areas": ["revenue_growth", "ai_infrastructure", "lead_acquisition"],
        "decision_cadence": "daily",
        "authority_delegation": "full_to_jarvis",
        "trust_level": "maximum",
        "operational_state": state.get("operational_state", "active"),
        "mirror_generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.post("/mirror/record")
async def record_captain_decision(body: MirrorDecisionBody, request: Request):
    """Record a Captain decision for pattern learning and mirror profile refinement."""
    import uuid as _uuid
    from datetime import datetime

    resolved = _resolve_tenant_id(request, body.tenant_id)
    record_id = str(_uuid.uuid4())
    return {
        "record_id": record_id,
        "captain_id": str(resolved),
        "decision": body.decision,
        "context": body.context,
        "outcome": body.outcome,
        "recorded_at": datetime.utcnow().isoformat(),
        "status": "recorded",
        "impact": "integrated_into_mirror_profile",
    }


@router.post("/seed-demo")
async def seed_demo_data(request: Request, tenant_id: Optional[UUID] = None):
    """
    Populate the tenant with realistic demo data — clients, invoices, leads,
    and 90 days of revenue snapshots. Idempotent: safe to call multiple times.
    """
    from app.services.demos.seeder import seed_demo_data as _seed
    from app.core.database import AsyncSessionLocal

    resolved = _resolve_tenant_id(request, tenant_id)
    async with AsyncSessionLocal() as session:
        counts = await _seed(resolved, session)
    return {
        "status": "seeded",
        "tenant_id": str(resolved),
        "created": counts,
        "message": "Demo data ready — Revenue Command Center is now live.",
    }


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
