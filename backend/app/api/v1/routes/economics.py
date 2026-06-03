from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/economics", tags=["economics"])


@router.get("/dashboard")
async def economics_dashboard(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.economics import economics_service

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await economics_service.dashboard(resolved_tenant_id)


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
