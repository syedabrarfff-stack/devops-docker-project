"""
JARVIS Emergency Control System — incident management, system health, and Captain alerts.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emergency", tags=["emergency"])


class IncidentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    severity: str = Field(default="medium", max_length=20)
    category: str = Field(default="infrastructure", max_length=50)
    description: str = Field(..., min_length=1, max_length=10_000)
    affected_systems: List[str] = []


class ResolveRequest(BaseModel):
    actions_taken: List[str] = []


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=2_000)


@router.get("/health")
async def system_health():
    """Real-time health check across all JARVIS subsystems."""
    from app.services.monitoring.emergency import check_system_health
    return await check_system_health()


@router.get("/incidents")
async def list_incidents(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from app.services.monitoring.emergency import get_incidents
    return {"incidents": await get_incidents(db, status=status, limit=limit)}


@router.post("/incidents")
@limiter.limit("5/minute")
async def declare_incident(request: Request, req: IncidentRequest, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_captain)):
    from app.services.monitoring.emergency import declare_emergency
    async with db.begin():
        incident = await declare_emergency(
            db,
            title=req.title,
            severity=req.severity,
            category=req.category,
            description=req.description,
            affected_systems=req.affected_systems,
            auto_detected=False,
        )
    return {"incident": incident, "captain_notified": True}


@router.post("/incidents/{incident_id}/resolve")
@limiter.limit("10/minute")
async def resolve_incident(request: Request, incident_id: int, req: ResolveRequest, db: AsyncSession = Depends(get_db)):
    from app.services.monitoring.emergency import resolve_incident as _resolve
    async with db.begin():
        ok = await _resolve(db, incident_id, req.actions_taken)
    if not ok:
        raise HTTPException(404, "Incident not found")
    return {"id": incident_id, "status": "resolved"}


@router.post("/incidents/{incident_id}/action")
@limiter.limit("20/minute")
async def add_action(request: Request, incident_id: int, req: ActionRequest, db: AsyncSession = Depends(get_db)):
    from app.services.monitoring.emergency import add_action as _add
    async with db.begin():
        ok = await _add(db, incident_id, req.action)
    if not ok:
        raise HTTPException(404, "Incident not found")
    return {"id": incident_id, "action_logged": True}


@router.post("/alert")
@limiter.limit("5/minute")
async def send_captain_alert(request: Request, req: IncidentRequest, _: dict = Depends(get_current_captain)):
    """Send an immediate alert to Captain without creating a DB incident."""
    from app.services.notifications.slack import notify_system_event
    from app.core.config import settings
    try:
        await notify_system_event(
            title=f"⚠️ CAPTAIN ALERT [{req.severity.upper()}]: {req.title}",
            body=req.description,
            level=req.severity,
        )
    except Exception as exc:
        logger.error("Captain alert notification failed [%s]: %s", req.severity, exc)
    return {"alerted": True, "channels": ["slack", "telegram", "dashboard"]}
