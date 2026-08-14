"""Layer 18 — Founder Dependency Engine API routes."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.intelligence.founder_dependency import (
    founder_dependency_engine,
    TARGET_DEPENDENCY_SCORE,
    CRITICAL_THRESHOLD,
    HIGH_THRESHOLD,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/founder", tags=["Founder Dependency"], dependencies=[Depends(get_current_captain)])


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


def _status(score: float) -> str:
    if score > CRITICAL_THRESHOLD:
        return "critical"
    if score > HIGH_THRESHOLD:
        return "high"
    if score <= TARGET_DEPENDENCY_SCORE:
        return "target_met"
    return "normal"


@router.post("/assess")
@limiter.limit("5/minute")
async def run_assessment(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await founder_dependency_engine.compute_dependency_score(tid)
    except Exception as exc:
        logger.error("run_assessment failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/report")
@limiter.limit("10/minute")
async def get_report(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await founder_dependency_engine.get_dependency_report(tid)
    except Exception as exc:
        logger.error("get_report failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/score")
@limiter.limit("20/minute")
async def get_score(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        from app.models.truth_resilience import DependencyScore
        from app.core.database import AsyncSessionLocal, set_tenant_context
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(DependencyScore).where(DependencyScore.tenant_id == tid).order_by(DependencyScore.snapshot_date.desc()).limit(1)
            )
            latest = result.scalar_one_or_none()
        if not latest:
            assessed = await founder_dependency_engine.compute_dependency_score(tid)
            score = assessed["overall_dependency_score"]
        else:
            score = latest.overall_dependency_score or 0.0
        return {"score": score, "status": _status(score), "target": TARGET_DEPENDENCY_SCORE}
    except Exception as exc:
        logger.error("get_score failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/opportunities")
@limiter.limit("10/minute")
async def get_opportunities(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        report = await founder_dependency_engine.get_dependency_report(tid)
        if "status" in report:
            assessed = await founder_dependency_engine.compute_dependency_score(tid)
            return {
                "automation": assessed["automation_opportunities"],
                "delegation": assessed["delegation_opportunities"],
                "alerts": assessed["single_point_alerts"],
            }
        latest = report.get("latest", {})
        return {
            "automation": latest.get("automation_opportunities", []),
            "delegation": latest.get("delegation_opportunities", []),
            "alerts": latest.get("single_point_alerts", []),
        }
    except Exception as exc:
        logger.error("get_opportunities failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
