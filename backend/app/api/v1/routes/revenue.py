from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.services.governance.invoice_engine import invoice_engine

router = APIRouter(prefix="/revenue", tags=["revenue"])


@router.get("/snapshot")
async def revenue_snapshot(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await invoice_engine.revenue_snapshot(resolved_tenant_id)


@router.get("/mrr-chart")
async def revenue_mrr_chart(
    request: Request,
    tenant_id: Optional[UUID] = None,
    days: int = Query(default=90, ge=1, le=365),
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return {"points": await invoice_engine.mrr_chart(resolved_tenant_id, days=days)}


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
