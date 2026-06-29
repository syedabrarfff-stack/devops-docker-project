"""Layer 18 — Competitive Moat Engine API routes."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.intelligence.moat_engine import moat_engine, _defensibility_label

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/moat", tags=["Competitive Moat"], dependencies=[Depends(get_current_captain)])


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


@router.post("/scan")
@limiter.limit("5/minute")
async def run_moat_scan(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await moat_engine.compute_moat_score(tid)
    except Exception as exc:
        logger.error("run_moat_scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/report")
@limiter.limit("10/minute")
async def get_moat_report(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await moat_engine.get_moat_report(tid)
    except Exception as exc:
        logger.error("get_moat_report failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/score")
@limiter.limit("20/minute")
async def get_moat_score(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        from app.models.truth_resilience import MoatMetrics
        from app.core.database import AsyncSessionLocal, set_tenant_context
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(MoatMetrics).where(MoatMetrics.tenant_id == tid).order_by(MoatMetrics.snapshot_date.desc()).limit(1)
            )
            latest = result.scalar_one_or_none()
        if not latest:
            scanned = await moat_engine.compute_moat_score(tid)
            moat_score = scanned["moat_score"]
            threat_score = scanned["competitive_threat_score"]
        else:
            moat_score = latest.moat_score or 0.0
            threat_score = latest.competitive_threat_score or 100.0
        return {
            "moat_score": moat_score,
            "competitive_threat_score": threat_score,
            "defensibility": _defensibility_label(moat_score),
        }
    except Exception as exc:
        logger.error("get_moat_score failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/dimensions")
@limiter.limit("20/minute")
async def get_dimensions(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        from app.models.truth_resilience import MoatMetrics
        from app.core.database import AsyncSessionLocal, set_tenant_context
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(MoatMetrics).where(MoatMetrics.tenant_id == tid).order_by(MoatMetrics.snapshot_date.desc()).limit(1)
            )
            latest = result.scalar_one_or_none()
        if not latest:
            return await moat_engine.compute_moat_score(tid)
        return {
            "dimensions": {
                "proprietary_data": latest.proprietary_data_score,
                "case_studies": min(100.0, (latest.case_study_count or 0) * 20),
                "delivery_intelligence": latest.delivery_intelligence_score,
                "relationship_graph": latest.relationship_graph_score,
                "institutional_wisdom": latest.institutional_wisdom_score,
                "automation_advantage": latest.automation_advantage_score,
                "operational_speed": latest.operational_speed_score,
            },
            "moat_score": latest.moat_score,
            "snapshot_date": latest.snapshot_date.isoformat() if latest.snapshot_date else None,
        }
    except Exception as exc:
        logger.error("get_dimensions failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/threats")
@limiter.limit("20/minute")
async def get_threats(request: Request, tenant_id: Optional[UUID] = None):
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        from app.models.truth_resilience import MoatMetrics
        from app.core.database import AsyncSessionLocal, set_tenant_context
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(MoatMetrics).where(MoatMetrics.tenant_id == tid).order_by(MoatMetrics.snapshot_date.desc()).limit(1)
            )
            latest = result.scalar_one_or_none()
        if not latest:
            scanned = await moat_engine.compute_moat_score(tid)
            return {"threats": scanned["threats_identified"], "strategic_actions": scanned["strategic_actions"]}
        return {
            "threats": latest.threats_identified or [],
            "strengths": latest.strengths_identified or [],
            "strategic_actions": latest.strategic_actions or [],
        }
    except Exception as exc:
        logger.error("get_threats failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
