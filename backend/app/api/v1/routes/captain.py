from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/captain", tags=["captain"])


@router.get("/state")
async def captain_state(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.captain_state import captain_awareness_engine

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await captain_awareness_engine.current_state(resolved_tenant_id)


@router.get("/decision-load")
async def captain_decision_load(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.captain_state import decision_load_manager

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await decision_load_manager.current_load(resolved_tenant_id)


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
