from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/innovation", tags=["innovation"])


class InnovationProposalIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10)
    impact_score: float = Field(ge=0, le=100)
    feasibility_score: float = Field(ge=0, le=100)
    proposed_by: str = "JARVIS"
    tenant_id: Optional[UUID] = None


class InnovationActionIn(BaseModel):
    tenant_id: Optional[UUID] = None


@router.get("/queue")
async def innovation_queue(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.innovation import innovation_queue_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await innovation_queue_service.list_queue(resolved_tenant_id)


@router.post("/propose")
async def propose_innovation(request: Request, body: InnovationProposalIn):
    from app.services.innovation import innovation_queue_service

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    return await innovation_queue_service.propose(
        resolved_tenant_id,
        title=body.title,
        description=body.description,
        impact_score=body.impact_score,
        feasibility_score=body.feasibility_score,
        proposed_by=body.proposed_by,
    )


@router.post("/seed")
async def seed_innovation_queue(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.innovation import innovation_queue_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await innovation_queue_service.seed(resolved_tenant_id)


@router.post("/weekly-review")
async def weekly_innovation_review(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.innovation import innovation_queue_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await innovation_queue_service.weekly_council_review(resolved_tenant_id)


@router.post("/{item_id}/deployed")
async def mark_innovation_deployed(
    item_id: UUID,
    request: Request,
    body: InnovationActionIn = Body(default_factory=InnovationActionIn),
):
    from app.services.innovation import innovation_queue_service

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        return await innovation_queue_service.mark_deployed(resolved_tenant_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
