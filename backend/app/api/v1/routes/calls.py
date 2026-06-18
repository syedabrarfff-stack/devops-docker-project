from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.revenue_activation.calls import call_room_service

router = APIRouter(prefix="/calls", tags=["Call Rooms"])


class PreBriefRequest(BaseModel):
    lead_id: UUID
    tenant_id: Optional[UUID] = None


class DebriefRequest(BaseModel):
    lead_id: UUID
    call_outcome: str = Field(..., pattern="^(won|lost|follow-up|follow_up)$")
    notes: str = Field(..., min_length=1, max_length=20_000)
    next_action: Optional[str] = Field(default=None, max_length=2_000)
    tenant_id: Optional[UUID] = None


@router.post("/pre-brief")
async def pre_brief_call(request: Request, body: PreBriefRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        return await call_room_service.pre_brief(body.lead_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/live-support/{lead_id}")
async def live_call_support(lead_id: UUID, request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await call_room_service.live_support(lead_id, resolved_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/debrief")
async def debrief_call(request: Request, body: DebriefRequest = Body(...)):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    outcome = body.call_outcome.replace("_", "-")
    try:
        return await call_room_service.debrief(
            lead_id=body.lead_id,
            call_outcome=outcome,
            notes=body.notes,
            next_action=body.next_action,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
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

