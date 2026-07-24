"""
JARVIS GHOST — AI outreach composition API.

Endpoints:
  POST /ghost/compose/stream  — SSE stream composing one email
  POST /ghost/sequence        — Generate full 3-email sequence (non-streaming)
  GET  /ghost/persona/suggest — Auto-suggest persona for a lead
  GET  /ghost/personas        — List all available personas
  POST /ghost/send            — Compose + send email immediately via Gmail
"""
import asyncio
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.lead import Lead
from app.services.ghost.writer import (
    auto_select_persona,
    get_persona,
    ghost_compose_once,
    ghost_stream,
    all_persona_names,
    _TONE_GUIDE,
    TEAM_SEED,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ghost", tags=["JARVIS GHOST"], dependencies=[Depends(get_current_captain)])


# ── Pydantic models ────────────────────────────────────────────────────────────

class ComposeRequest(BaseModel):
    lead_id: Optional[UUID] = None
    lead_data: Optional[dict] = None  # inline lead — for testing without a DB lead
    persona_name: Optional[str] = Field(default=None, max_length=120)
    tone: str = Field(default="professional", pattern="^(professional|warm|direct)$")
    email_num: int = Field(default=1, ge=1, le=3)
    total_emails: int = Field(default=1, ge=1, le=3)
    tenant_id: Optional[UUID] = None


class SequenceRequest(BaseModel):
    lead_id: Optional[UUID] = None
    lead_data: Optional[dict] = None
    persona_name: Optional[str] = Field(default=None, max_length=120)
    tone: str = Field(default="professional", pattern="^(professional|warm|direct)$")
    email_count: int = Field(default=3, ge=1, le=3)
    tenant_id: Optional[UUID] = None


class SendRequest(BaseModel):
    lead_id: Optional[UUID] = None
    lead_data: Optional[dict] = None
    persona_name: Optional[str] = Field(default=None, max_length=120)
    tone: str = Field(default="professional", pattern="^(professional|warm|direct)$")
    tenant_id: Optional[UUID] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _resolve_lead(
    db: AsyncSession,
    lead_id: Optional[UUID],
    lead_data: Optional[dict],
    tenant_id: Optional[UUID] = None,
) -> dict:
    """Return lead as plain dict from DB or inline payload."""
    if lead_data:
        return lead_data

    if lead_id is None:
        raise HTTPException(status_code=400, detail="Provide lead_id or lead_data")

    q = select(Lead).where(Lead.id == lead_id)
    if tenant_id is not None:
        q = q.where(Lead.tenant_id == tenant_id)
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    return {
        "id": str(row.id),
        "company_name": row.company_name,
        "contact_name": row.contact_name,
        "email": row.email,
        "industry": row.industry,
        "country": row.country,
        "pain_points": row.pain_points or [],
        "score": float(row.score or 0),
        "status": row.status.value if row.status else "NEW",
        "notes": row.notes or "",
        "assigned_persona": row.assigned_persona,
    }


def _resolve_persona(lead: dict, persona_name: Optional[str]) -> dict:
    """Pick the persona to use, falling back to auto-select."""
    # Prefer explicit request → lead's assigned → auto-select
    name = (
        persona_name
        or lead.get("assigned_persona")
        or auto_select_persona(lead.get("industry"), lead.get("pain_points"))
    )
    persona = get_persona(name)
    if persona is None:
        persona = get_persona("Darren Mitchell")
    return persona


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/compose/stream")
@limiter.limit("30/minute")
async def compose_stream(
    request,  # FastAPI Request injected by rate limiter
    body: ComposeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming endpoint — yields email tokens as they arrive from Claude.

    Stream protocol:
      data: {"type":"start","persona":"Sophia Reynolds","email_num":1,"total":1}
      data: {"type":"token","text":"Hi Marcus,\n\n"}
      ...
      data: {"type":"complete","full_text":"...","char_count":412,"email_num":1}
      data: {"type":"done"}
    """
    lead = await _resolve_lead(db, body.lead_id, body.lead_data, tenant_id=body.tenant_id)
    persona = _resolve_persona(lead, body.persona_name)

    async def generate():
        async for chunk in ghost_stream(
            lead=lead,
            persona=persona,
            tone=body.tone,
            email_num=body.email_num,
            total=body.total_emails,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sequence")
@limiter.limit("10/minute")
async def generate_sequence(
    request,
    body: SequenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a full cold outreach sequence (1–3 emails) non-streaming.
    Returns all emails at once.
    """
    lead = await _resolve_lead(db, body.lead_id, body.lead_data, tenant_id=body.tenant_id)
    persona = _resolve_persona(lead, body.persona_name)

    async def compose_email(num: int) -> dict:
        try:
            text = await ghost_compose_once(
                lead=lead,
                persona=persona,
                tone=body.tone,
                email_num=num,
                total=body.email_count,
            )
            # Parse subject + body
            subject, body_text = _parse_email(text)
            return {
                "email_num": num,
                "subject": subject,
                "body": body_text,
                "full_text": text,
                "status": "ok",
            }
        except Exception as exc:
            logger.error("Sequence email %d failed: %s", num, exc)
            return {"email_num": num, "status": "error", "error": str(exc)}

    raw = await asyncio.gather(*[compose_email(n) for n in range(1, body.email_count + 1)], return_exceptions=True)
    results = [
        v if isinstance(v, dict) else {"email_num": i + 1, "status": "error", "error": str(v)}
        for i, v in enumerate(raw)
    ]

    return {
        "persona": {
            "name": persona["name"],
            "role": persona["role"],
            "email": persona["email"],
        },
        "lead": {
            "id": lead.get("id"),
            "company": lead.get("company_name") or lead.get("company"),
            "contact": lead.get("contact_name"),
        },
        "tone": body.tone,
        "emails": list(results),
        "total": body.email_count,
    }


@router.get("/persona/suggest")
async def suggest_persona(
    lead_id: Optional[UUID] = None,
    industry: Optional[str] = Query(default=None, max_length=120),
    pain_points: Optional[str] = Query(default=None, max_length=500),
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the auto-selected persona for a lead or inline industry/pain_points."""
    if lead_id:
        _q = select(Lead).where(Lead.id == lead_id)
        if tenant_id is not None:
            _q = _q.where(Lead.tenant_id == tenant_id)
        row = (await db.execute(_q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Lead not found")
        industry = row.industry
        pain_list = row.pain_points or []
    else:
        pain_list = [p.strip() for p in (pain_points or "").split(",") if p.strip()]

    name = auto_select_persona(industry, pain_list)
    persona = get_persona(name) or {}

    return {
        "suggested_persona": name,
        "role": persona.get("role"),
        "department": persona.get("department"),
        "specializations": (persona.get("specializations") or [])[:4],
        "tone_keywords": persona.get("tone_keywords"),
        "email": persona.get("email"),
    }


@router.get("/personas")
async def list_personas():
    """Return all active client-facing team personas."""
    return {
        "personas": [
            {
                "name": p["name"],
                "first_name": p.get("first_name"),
                "role": p["role"],
                "department": p["department"],
                "seniority": p.get("seniority"),
                "specializations": p.get("specializations", [])[:4],
                "tone_keywords": p.get("tone_keywords", []),
                "communication_style": p.get("communication_style"),
                "email": p["email"],
            }
            for p in TEAM_SEED
            if p.get("is_active") and p.get("is_client_facing")
        ]
    }


@router.post("/send")
@limiter.limit("5/minute")
async def compose_and_send(
    request,
    body: SendRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compose email with AI and immediately send via the Aliyar Gmail stack.
    The lead must have a valid email address and clear the same outreach
    compliance gate (do-not-contact, daily cap, reply-rate pause) as the
    automated sequence engine — this is a manual send, not an exemption.
    """
    from app.services.outreach.gmail import send_client_email
    from app.services.outreach.compliance import outreach_compliance

    lead = await _resolve_lead(db, body.lead_id, body.lead_data, tenant_id=body.tenant_id)
    to_email = lead.get("email")
    if not to_email:
        raise HTTPException(status_code=400, detail="Lead has no email address")

    # Only leads backed by a real DB row can be compliance-checked (do-not-contact,
    # daily cap, etc. all key off the Lead row) — inline test lead_data has none.
    lead_row = None
    if body.lead_id:
        _q = select(Lead).where(Lead.id == body.lead_id)
        if body.tenant_id is not None:
            _q = _q.where(Lead.tenant_id == body.tenant_id)
        lead_row = (await db.execute(_q)).scalar_one_or_none()

    if lead_row is not None:
        tenant_uuid = body.tenant_id or lead_row.tenant_id
        safety = await outreach_compliance.safety_gate(db, tenant_uuid, lead_row, to_email)
        if not safety["allowed"]:
            raise HTTPException(
                status_code=422,
                detail=f"Blocked by outreach compliance: {safety.get('reason', 'not_allowed')}",
            )

    persona = _resolve_persona(lead, body.persona_name)

    full_text = await ghost_compose_once(
        lead=lead, persona=persona, tone=body.tone, email_num=1, total=1
    )
    subject, body_text = _parse_email(full_text)
    if not subject:
        subject = f"A thought for {lead.get('company_name') or 'your team'}"
    body_text = outreach_compliance.append_footer(body_text, to_email)

    success, error, method = await send_client_email(
        db=db,
        to=to_email,
        subject=subject,
        body=body_text,
        to_name=lead.get("contact_name") or "",
    )
    if not success:
        raise HTTPException(status_code=502, detail=f"Email send failed: {error}")

    # Increment outreach count on lead
    if lead_row is not None:
        lead_row.outreach_count = (lead_row.outreach_count or 0) + 1
        if lead_row.status.value == "NEW":
            from app.models.lead import LeadStatus
            lead_row.status = LeadStatus.CONTACTED
        try:
            from app.services.crm.sync import sync_lead_to_crm
            await sync_lead_to_crm(db, lead_row)
        except Exception as exc:
            logger.warning("CRM sync failed for lead %s: %s", lead_row.id, exc)
        await db.commit()

    return {
        "sent": True,
        "to": to_email,
        "subject": subject,
        "persona": persona["name"],
        "method": method,
    }


@router.get("/tones")
async def list_tones():
    """Available composition tone options."""
    return {
        "tones": [
            {"value": "professional", "label": "Professional", "description": "Formal, confident, enterprise-grade"},
            {"value": "warm", "label": "Warm & Human", "description": "Friendly, conversational, genuinely helpful"},
            {"value": "direct", "label": "Direct", "description": "Blunt, value-first, max 4 sentences"},
        ]
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _parse_email(text: str) -> tuple[str, str]:
    """Split Claude output into (subject, body) — strips 'Subject:' prefix."""
    lines = text.strip().splitlines()
    subject = ""
    body_lines = []
    in_body = False

    for line in lines:
        if not in_body and line.lower().startswith("subject:"):
            subject = line[8:].strip()
            in_body = True
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    if not subject and lines:
        subject = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

    return subject, body
