from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.revenue_activation.market_awareness import market_awareness_engine

router = APIRouter(prefix="/intel", tags=["Market Intelligence"], dependencies=[Depends(get_current_captain)])


@router.get("/market-pulse")
@limiter.limit("10/minute")
async def market_pulse(
    request: Request,
    tenant_id: Optional[UUID] = None,
    limit: int = Query(default=25, ge=1, le=100),
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await market_awareness_engine.market_pulse(resolved_tenant_id, limit=limit)


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
