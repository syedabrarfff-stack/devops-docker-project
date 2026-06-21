"""Layer 18 — Truth Engine API routes."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.services.intelligence.truth_engine import truth_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/truth", tags=["Truth Engine"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class PredictionIn(BaseModel):
    prediction_type: str
    entity_type: str
    entity_id: Optional[str] = None
    predicted_value: Optional[float] = None
    predicted_label: Optional[str] = None
    predicted_by: str
    confidence_score: Optional[float] = None
    metadata: dict = {}


class OutcomeIn(BaseModel):
    outcome_value: Optional[float] = None
    outcome_label: Optional[str] = None


class RealityCheckIn(BaseModel):
    check_type: str


# ---------------------------------------------------------------------------
# Tenant resolution helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/prediction")
async def record_prediction(body: PredictionIn, request: Request, tenant_id: Optional[UUID] = None):
    """Record a prediction for later accuracy tracking."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        result = await truth_engine.record_prediction(
            tenant_id=resolved_tenant_id,
            prediction_type=body.prediction_type,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            predicted_value=body.predicted_value,
            predicted_label=body.predicted_label,
            predicted_by=body.predicted_by,
            confidence_score=body.confidence_score,
            metadata=body.metadata,
        )
        return {"id": result, "status": "recorded"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to record prediction: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record prediction") from exc


@router.post("/outcome/{truth_event_id}")
async def record_outcome(truth_event_id: UUID, body: OutcomeIn, request: Request, tenant_id: Optional[UUID] = None):
    """Record the actual outcome for a previously tracked prediction."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        result = await truth_engine.record_outcome(
            tenant_id=resolved_tenant_id,
            truth_event_id=truth_event_id,
            outcome_value=body.outcome_value,
            outcome_label=body.outcome_label,
        )
        return {"accuracy_delta": result, "status": "recorded"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to record outcome for event %s: %s", truth_event_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record outcome") from exc


@router.get("/report")
async def get_truth_report(request: Request, tenant_id: Optional[UUID] = None):
    """Get the full truth engine accuracy report."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await truth_engine.get_truth_report(tenant_id=resolved_tenant_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get truth report: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get truth report") from exc


@router.get("/accuracy")
async def get_accuracy_dashboard(request: Request, tenant_id: Optional[UUID] = None):
    """Get the accuracy dashboard across all prediction types."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await truth_engine.get_accuracy_dashboard(tenant_id=resolved_tenant_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get accuracy dashboard: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get accuracy dashboard") from exc


@router.post("/reality-check")
async def run_reality_check(body: RealityCheckIn, request: Request, tenant_id: Optional[UUID] = None):
    """Run a reality check to validate system assumptions against actual data."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await truth_engine.run_reality_check(
            tenant_id=resolved_tenant_id,
            check_type=body.check_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to run reality check: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run reality check") from exc
