"""
JARVIS AUTOPILOT — Autonomous Outreach Pipeline API.

POST /autopilot/ignite              — trigger a compose cycle
GET  /autopilot/pending             — list pending drafts for review
GET  /autopilot/all                 — all drafts (sent/rejected/pending)
GET  /autopilot/status              — pipeline status + stats
POST /autopilot/approve/{draft_id}  — approve + send one email
POST /autopilot/reject/{draft_id}   — reject a draft
POST /autopilot/approve-all         — bulk approve all pending
PATCH /autopilot/draft/{draft_id}   — edit subject/body before sending
DELETE /autopilot/clear             — clear all non-pending drafts
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.services.autopilot.pipeline import (
    approve_all_pending,
    approve_draft,
    edit_draft,
    get_all_drafts,
    get_autopilot_status,
    get_pending_drafts,
    reject_draft,
    run_autopilot_cycle,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/autopilot", tags=["JARVIS AUTOPILOT"])


# ── Pydantic ───────────────────────────────────────────────────────────────────

class IgniteRequest(BaseModel):
    tenant_id: Optional[UUID] = None
    max_leads: int = Field(default=10, ge=1, le=25)
    min_score: float = Field(default=55.0, ge=0.0, le=100.0)
    tone: str = Field(default="professional", pattern="^(professional|warm|direct)$")


class RejectRequest(BaseModel):
    reason: Optional[str] = Field(default="", max_length=500)


class EditDraftRequest(BaseModel):
    subject: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, max_length=50_000)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tid(request: Request, explicit: Optional[UUID]) -> str:
    if explicit:
        return str(explicit)
    tenant = getattr(request.state, "tenant_id", None)
    if tenant:
        return str(tenant)
    hdr = request.headers.get("X-Tenant-ID")
    if hdr:
        return hdr
    from app.core.config import settings
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return str(settings.JARVIS_DEFAULT_TENANT_ID)
    return "system"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/ignite")
@limiter.limit("5/minute")
async def ignite(request: Request, body: IgniteRequest):
    """
    Trigger an autopilot compose cycle.
    Selects top leads, composes emails via GHOST (Claude Opus), queues for approval.
    """
    tid = _tid(request, body.tenant_id)
    try:
        result = await run_autopilot_cycle(
            tenant_id=body.tenant_id,
            max_leads=body.max_leads,
            min_score=body.min_score,
            tone=body.tone,
        )
    except Exception as exc:
        logger.error("Autopilot ignite error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/pending")
async def pending_drafts(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Return all pending drafts awaiting Captain review."""
    tid = _tid(request, tenant_id)
    return {
        "drafts": await get_pending_drafts(tid),
        "tenant_id": tid,
    }


@router.get("/all")
async def all_drafts(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Return all drafts (pending, sent, rejected, error)."""
    tid = _tid(request, tenant_id)
    return {
        "drafts": await get_all_drafts(tid),
        "tenant_id": tid,
    }


@router.get("/status")
async def autopilot_status(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Pipeline health: counts, last run time, all-time sent count."""
    tid = _tid(request, tenant_id)
    return await get_autopilot_status(tid)


@router.post("/approve/{draft_id}")
@limiter.limit("60/minute")
async def approve(request: Request, draft_id: str, tenant_id: Optional[UUID] = None):
    """Approve a draft — sends the email immediately via the Aliyar Gmail stack."""
    tid = _tid(request, tenant_id)
    try:
        result = await approve_draft(tid, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@router.post("/reject/{draft_id}")
@limiter.limit("30/minute")
async def reject(
    request: Request,
    draft_id: str,
    body: RejectRequest = RejectRequest(),
    tenant_id: Optional[UUID] = None,
):
    """Reject a draft — marks it rejected without sending."""
    tid = _tid(request, tenant_id)
    try:
        await reject_draft(tid, draft_id, body.reason or "")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rejected": True, "draft_id": draft_id}


@router.post("/approve-all")
@limiter.limit("3/minute")
async def bulk_approve(request: Request, tenant_id: Optional[UUID] = None):
    """Bulk-approve all pending drafts. Sends all emails in parallel."""
    tid = _tid(request, tenant_id)
    result = await approve_all_pending(tid)
    return result


@router.patch("/draft/{draft_id}")
@limiter.limit("30/minute")
async def edit(
    request: Request,
    draft_id: str,
    body: EditDraftRequest,
    tenant_id: Optional[UUID] = None,
):
    """Edit a draft's subject or body before approving."""
    tid = _tid(request, tenant_id)
    try:
        draft = await edit_draft(tid, draft_id, subject=body.subject, body=body.body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"updated": True, "draft": draft}


@router.delete("/clear")
@limiter.limit("10/minute")
async def clear_actioned(request: Request, tenant_id: Optional[UUID] = None):
    """Remove sent/rejected/error drafts from the queue. Pending ones are kept."""
    from app.services.autopilot.pipeline import _load_drafts, _save_drafts
    tid = _tid(request, tenant_id)
    drafts = await _load_drafts(tid)
    kept = [d for d in drafts if d["status"] == "pending"]
    removed = len(drafts) - len(kept)
    await _save_drafts(tid, kept)
    return {"cleared": removed, "remaining": len(kept)}
