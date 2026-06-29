"""Layer 18 — Learning & Evolution Engine API routes."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning", tags=["Learning Engine"], dependencies=[Depends(get_current_captain)])


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


class LessonExtractionIn(BaseModel):
    project_type: str = Field(..., max_length=100)
    client_industry: Optional[str] = Field(default=None, max_length=100)
    delivery_data: dict = {}
    tenant_id: Optional[UUID] = None


class ApplyIn(BaseModel):
    applied_by: str = Field(default="JARVIS", max_length=100)
    tenant_id: Optional[UUID] = None


class SOPIn(BaseModel):
    lesson_ids: list[int] = Field(default_factory=list, max_length=50)
    tenant_id: Optional[UUID] = None


@router.post("/extract-lessons")
@limiter.limit("10/minute")
async def extract_lessons(req: LessonExtractionIn, request: Request):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, req.tenant_id)
    try:
        return await learning_engine.extract_delivery_lessons(
            tenant_id=tid,
            project_type=req.project_type,
            client_industry=req.client_industry,
            delivery_data=req.delivery_data,
        )
    except Exception as exc:
        logger.error("extract_lessons failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/dashboard")
@limiter.limit("10/minute")
async def get_dashboard(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await learning_engine.get_learning_dashboard(tid)
    except Exception as exc:
        logger.error("get_dashboard failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/recommendations")
@limiter.limit("20/minute")
async def get_recommendations(
    request: Request,
    tenant_id: Optional[UUID] = None,
    recommendation_type: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
):
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from sqlalchemy import select
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        from app.models.truth_resilience import ImprovementRecommendation
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            q = select(ImprovementRecommendation).where(
                ImprovementRecommendation.tenant_id == tid,
                ImprovementRecommendation.implementation_status == "pending",
            )
            if recommendation_type:
                q = q.where(ImprovementRecommendation.recommendation_type == recommendation_type)
            q = q.order_by(ImprovementRecommendation.created_at.desc()).limit(limit)
            result = await db.execute(q)
            rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "recommendation_type": r.recommendation_type,
                "source_type": r.source_type,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "implementation_status": r.implementation_status,
                "estimated_impact": r.estimated_impact,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("get_recommendations failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/recommendations/{recommendation_id}/apply")
@limiter.limit("20/minute")
async def apply_recommendation(recommendation_id: int, req: ApplyIn, request: Request):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, req.tenant_id)
    try:
        result = await learning_engine.apply_recommendation(tid, recommendation_id, req.applied_by)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("apply_recommendation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate-sop")
@limiter.limit("5/minute")
async def generate_sop(req: SOPIn, request: Request):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, req.tenant_id)
    try:
        return await learning_engine.generate_sop_recommendation(tid, req.lesson_ids)
    except Exception as exc:
        logger.error("generate_sop failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/optimize-proposal")
@limiter.limit("5/minute")
async def optimize_proposal(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await learning_engine.generate_proposal_optimization(tid)
    except Exception as exc:
        logger.error("optimize_proposal failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/optimize-outreach")
@limiter.limit("5/minute")
async def optimize_outreach(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.learning_engine import learning_engine
    tid = _resolve_tenant_id(request, tenant_id)
    try:
        return await learning_engine.generate_outreach_optimization(tid)
    except Exception as exc:
        logger.error("optimize_outreach failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
