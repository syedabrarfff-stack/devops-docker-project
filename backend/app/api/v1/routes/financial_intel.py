"""Layer 18 — Financial Intelligence Engine API routes (Virtual CFO)."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/financial", tags=["Financial Intelligence"], dependencies=[Depends(get_current_captain)])


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


@router.post("/snapshot")
@limiter.limit("5/minute")
async def compute_snapshot(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.financial_intelligence import financial_intelligence
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await financial_intelligence.compute_financial_snapshot(tid)
    except Exception as exc:
        logger.error("compute_snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/cfo-briefing")
@limiter.limit("10/minute")
async def get_cfo_briefing(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.financial_intelligence import financial_intelligence
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await financial_intelligence.get_cfo_briefing(tid)
    except Exception as exc:
        logger.error("get_cfo_briefing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/cashflow-forecast")
@limiter.limit("5/minute")
async def generate_cashflow_forecast(
    request: Request,
    tenant_id: Optional[UUID] = None,
    horizon_days: int = Query(default=90, ge=7, le=365),
):
    from app.services.intelligence.financial_intelligence import financial_intelligence
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await financial_intelligence.generate_cashflow_forecast(tid, horizon_days=horizon_days)
    except Exception as exc:
        logger.error("generate_cashflow_forecast failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health-score")
@limiter.limit("10/minute")
async def get_health_score(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.financial_intelligence import financial_intelligence, _grade
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        briefing = await financial_intelligence.get_cfo_briefing(tid)
        if "status" in briefing and briefing["status"] == "no_snapshot":
            snapshot = await financial_intelligence.compute_financial_snapshot(tid)
            score = snapshot["financial_health_score"]
            alerts = snapshot["risk_alerts"]
        else:
            snap = briefing.get("snapshot", {})
            score = snap.get("financial_health_score", 0.0)
            alerts = snap.get("risk_alerts", [])
        return {"score": score, "grade": _grade(score or 0), "alerts": alerts}
    except Exception as exc:
        logger.error("get_health_score failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
