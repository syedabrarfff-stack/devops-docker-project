"""System-level HUD routes."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from app.core.database import get_db
from app.services.aionx.omni_mission_control import system_hud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System HUD"])


@router.get("/hud")
async def get_system_hud(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
) -> dict[str, Any]:
    try:
        return await system_hud(db, persist=False)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("system_hud failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="System HUD unavailable")


@router.post("/self-heal")
@limiter.limit("3/minute")
async def trigger_self_heal(request: Request, _: dict = Depends(get_current_captain)) -> dict[str, Any]:
    """Manually trigger JARVIS autonomous self-healing cycle.
    Resets failed AI circuit breakers, refills empty lead pipelines,
    resumes paused scheduler jobs, and reports Redis health."""
    try:
        from app.services.monitoring.self_healer import run_self_healing_cycle
        return await run_self_healing_cycle()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("self_heal trigger failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Self-heal cycle failed")
