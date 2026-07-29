"""Layer 18 — Operational Resilience Engine API routes."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.api.v1.routes.auth import get_current_captain

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.intelligence.resilience_engine import resilience_engine
from app.services.intelligence.incident_playbooks import get_playbook, get_all_playbooks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resilience", tags=["Resilience Engine"], dependencies=[Depends(get_current_captain)])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class IncidentIn(BaseModel):
    incident_type: str = Field(..., max_length=100)
    details: dict = {}


class ResolveIn(BaseModel):
    resolution_notes: str = Field(..., max_length=4000)


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


@router.post("/incident")
@limiter.limit("10/minute")
async def detect_and_respond(body: IncidentIn, request: Request, tenant_id: Optional[UUID] = None):
    """Detect an incident and trigger the appropriate response playbook."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        result = await resilience_engine.detect_and_respond(
            tenant_id=resolved_tenant_id,
            incident_type=body.incident_type,
            details=body.details,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to detect and respond to incident: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process incident") from exc


@router.post("/incident/{event_id}/resolve")
@limiter.limit("20/minute")
async def resolve_incident(event_id: UUID, body: ResolveIn, request: Request, tenant_id: Optional[UUID] = None):
    """Mark an active incident as resolved with resolution notes."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        await resilience_engine.resolve_incident(
            tenant_id=resolved_tenant_id,
            event_id=event_id,
            resolution_notes=body.resolution_notes,
        )
        return {"status": "resolved"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve incident %s: %s", event_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resolve incident") from exc


@router.get("/active")
@limiter.limit("20/minute")
async def get_active_incidents(request: Request, tenant_id: Optional[UUID] = None):
    """Return all currently active (unresolved) incidents."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await resilience_engine.get_active_incidents(tenant_id=resolved_tenant_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get active incidents: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get active incidents") from exc


@router.get("/status")
@limiter.limit("20/minute")
async def get_resilience_status(request: Request, tenant_id: Optional[UUID] = None):
    """Get overall system resilience status and health summary."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    try:
        return await resilience_engine.get_resilience_status(tenant_id=resolved_tenant_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get resilience status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get resilience status") from exc


@router.get("/playbooks")
async def list_playbooks():
    """Return all registered incident response playbooks."""
    try:
        return get_all_playbooks()
    except Exception as exc:
        logger.error("Failed to list playbooks: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list playbooks") from exc


@router.get("/playbooks/{incident_type}")
async def get_incident_playbook(incident_type: str):
    """Return the response playbook for a specific incident type."""
    try:
        playbook = get_playbook(incident_type)
        if not playbook:
            raise HTTPException(status_code=404, detail=f"No playbook found for incident type '{incident_type}'")
        return playbook
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get playbook for '%s': %s", incident_type, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get playbook") from exc
