from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter

router = APIRouter(prefix="/civilization", tags=["civilization"], dependencies=[Depends(get_current_captain)])


@router.get("/ledger")
async def civilization_ledger(request: Request, tenant_id: Optional[UUID] = None, limit: int = Query(200, ge=1, le=1000)):
    from app.services.civilization import civilization_ledger as ledger_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await ledger_service.list_events(resolved_tenant_id, milestones_only=False, limit=limit)


@router.get("/milestones")
async def civilization_milestones(request: Request, tenant_id: Optional[UUID] = None, limit: int = Query(200, ge=1, le=1000)):
    from app.services.civilization import civilization_ledger as ledger_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await ledger_service.list_events(resolved_tenant_id, milestones_only=True, limit=limit)


@router.post("/initialize")
@limiter.limit("3/minute")
async def initialize_civilization_ledger(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.civilization import civilization_ledger as ledger_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await ledger_service.initialize(resolved_tenant_id)


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
