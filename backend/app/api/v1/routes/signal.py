"""
JARVIS SIGNAL — AI Pipeline Intelligence Scanner API.

GET  /signal/status                — pipeline stats + last scan summary
POST /signal/scan/lead/{lead_id}   — SSE: scan one lead
POST /signal/scan/pipeline         — SSE: scan all eligible leads in parallel
POST /signal/brief/stream          — SSE: generate intelligence brief from scan results
POST /signal/brief                 — one-shot brief from cached/provided signals
GET  /signal/leads                 — return leads formatted for signal UI
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.lead import Lead, LeadStatus
from app.services.signal.scanner import (
    generate_brief_stream,
    scan_lead,
    scan_lead_stream,
    scan_pipeline_stream,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signal", tags=["JARVIS SIGNAL"], dependencies=[Depends(get_current_captain)])


# ── Pydantic ───────────────────────────────────────────────────────────────────

class PipelineScanRequest(BaseModel):
    tenant_id: Optional[UUID] = None
    limit: int = Field(default=20, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    statuses: list[str] = Field(
        default=["NEW", "NURTURE", "CONTACTED", "REPLIED"],
    )


class BriefRequest(BaseModel):
    signals: list[dict] = Field(default_factory=list)
    tenant_id: Optional[UUID] = None


# ── Lead fetcher ───────────────────────────────────────────────────────────────

async def _fetch_leads(
    db: AsyncSession,
    tenant_id: Optional[UUID],
    limit: int,
    min_score: float,
    statuses: list[str],
) -> list[dict]:
    valid_statuses = [s for s in statuses if s in [e.value for e in LeadStatus]]
    q = (
        select(Lead)
        .where(
            and_(
                Lead.score >= min_score,
                Lead.status.in_([LeadStatus(s) for s in valid_statuses]),
            )
        )
        .order_by(Lead.score.desc())
        .limit(limit)
    )
    if tenant_id:
        q = q.where(Lead.tenant_id == tenant_id)

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "industry": r.industry,
            "country": r.country,
            "pain_points": r.pain_points or [],
            "score": float(r.score or 0),
            "status": r.status.value if r.status else "NEW",
            "outreach_count": r.outreach_count or 0,
            "notes": r.notes or "",
        }
        for r in rows
    ]


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/leads")
async def signal_leads(
    tenant_id: Optional[UUID] = None,
    limit: int = Query(default=30, ge=1, le=100),
    min_score: float = Query(default=0.0),
    db: AsyncSession = Depends(get_db),
):
    """Return leads in signal-scan format (lightweight, no AI)."""
    leads = await _fetch_leads(db, tenant_id, limit, min_score, ["NEW", "NURTURE", "CONTACTED", "REPLIED"])
    return {"leads": leads, "total": len(leads)}


@router.post("/scan/lead/{lead_id}")
@limiter.limit("30/minute")
async def scan_one_lead(
    request,
    lead_id: UUID,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """SSE: scan a single lead and stream the signal result."""
    q = select(Lead).where(Lead.id == lead_id)
    if tenant_id:
        q = q.where(Lead.tenant_id == tenant_id)
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = {
        "id": str(row.id),
        "company_name": row.company_name,
        "contact_name": row.contact_name,
        "email": row.email,
        "industry": row.industry,
        "country": row.country,
        "pain_points": row.pain_points or [],
        "score": float(row.score or 0),
        "status": row.status.value if row.status else "NEW",
        "outreach_count": row.outreach_count or 0,
        "notes": row.notes or "",
    }

    return StreamingResponse(
        scan_lead_stream(lead),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/scan/pipeline")
@limiter.limit("5/minute")
async def scan_pipeline(
    request,
    body: PipelineScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE: scan all eligible leads in parallel, emitting each signal as it completes.

    Protocol:
      data: {"type":"pipeline_start","total":N}
      data: {"type":"scan_result","signal":{...},"done":N,"total":N}
      ...
      data: {"type":"pipeline_complete","results":[...sorted by signal_score]}
      data: {"type":"done"}
    """
    leads = await _fetch_leads(db, body.tenant_id, body.limit, body.min_score, body.statuses)
    if not leads:
        async def empty():
            import json
            yield "data: " + json.dumps({"type": "pipeline_start", "total": 0}) + "\n\n"
            yield "data: " + json.dumps({"type": "pipeline_complete", "results": []}) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return StreamingResponse(
        scan_pipeline_stream(leads),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/brief/stream")
@limiter.limit("10/minute")
async def brief_stream(request, body: BriefRequest):
    """
    SSE: stream the AI intelligence brief for provided signals.
    Pass the results from /scan/pipeline as `signals`.

    Protocol:
      data: {"type":"start","leads_analysed":N}
      data: {"type":"token","text":"..."}
      ...
      data: {"type":"complete","full_text":"..."}
      data: {"type":"done"}
    """
    if not body.signals:
        raise HTTPException(status_code=400, detail="Provide signals from a pipeline scan")

    return StreamingResponse(
        generate_brief_stream(body.signals),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/status")
async def signal_status(
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Pipeline health metrics for the SIGNAL dashboard header."""
    from sqlalchemy import func
    from app.core.config import settings as _cfg
    _tid = tenant_id
    if _tid is None and _cfg.JARVIS_DEFAULT_TENANT_ID:
        try:
            _tid = UUID(str(_cfg.JARVIS_DEFAULT_TENANT_ID))
        except (ValueError, AttributeError):
            pass
    _tf = [Lead.tenant_id == _tid] if _tid else []
    total = await db.scalar(select(func.count()).select_from(Lead).where(*_tf)) or 0
    hot = await db.scalar(
        select(func.count()).select_from(Lead).where(*_tf, Lead.score >= 75)
    ) or 0
    warm = await db.scalar(
        select(func.count()).select_from(Lead).where(*_tf, Lead.score.between(45, 74))
    ) or 0
    eligible = await db.scalar(
        select(func.count()).select_from(Lead).where(*_tf, Lead.outreach_eligible == True)
    ) or 0
    return {
        "total_leads": total,
        "hot_leads": hot,
        "warm_leads": warm,
        "eligible_for_outreach": eligible,
        "cool_cold": max(0, total - hot - warm),
    }
