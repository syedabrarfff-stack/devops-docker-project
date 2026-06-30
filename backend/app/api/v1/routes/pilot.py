from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from app.core.config import settings
from app.services.pilot.activation import pilot_activation_service


router = APIRouter(prefix="/pilot", tags=["Pilot"], dependencies=[Depends(get_current_captain)])


@router.get("/status")
async def pilot_status(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await pilot_activation_service.status(resolved_tenant_id)


@router.post("/activate", dependencies=[Depends(get_current_captain)])
@limiter.limit("3/minute")
async def activate_pilot(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await pilot_activation_service.activate(resolved_tenant_id)


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
