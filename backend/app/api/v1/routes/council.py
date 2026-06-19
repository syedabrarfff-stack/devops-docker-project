from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field

from app.services.ai.council import intelligence_council

router = APIRouter(prefix="/council", tags=["AI Council"])


class CouncilConveneRequest(BaseModel):
    question: str = Field(min_length=3, max_length=8000)
    context: dict = Field(default_factory=dict)
    council_type: str = Field(default="standard", max_length=80)
    tenant_id: Optional[UUID] = None


@router.post("/convene")
@limiter.limit("20/minute")
async def convene_council(request: Request, body: CouncilConveneRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        result = await intelligence_council.convene(
            question=body.question,
            context=body.context,
            council_type=body.council_type,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump()


@router.get("/sessions")
async def council_sessions(
    request: Request,
    tenant_id: Optional[UUID] = None,
    limit: int = Query(default=25, ge=1, le=100),
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return {"sessions": await intelligence_council.recent_sessions(resolved_tenant_id, limit=limit)}


@router.get("/health")
async def council_health(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id, required=False)
    return await intelligence_council.health(resolved_tenant_id)


@router.get("/status")
async def council_status(request: Request, tenant_id: Optional[UUID] = None):
    """Compatibility status endpoint for dashboard and operating-system health checks."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id, required=False)
    health = await intelligence_council.health(resolved_tenant_id)
    return {
        **health,
        "status": health.get("status", "operational"),
        "endpoint": "council/status",
        "council_live": True,
    }


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID], required: bool = True) -> UUID | None:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        if required:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        return None
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
