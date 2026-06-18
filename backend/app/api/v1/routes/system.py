"""System-level HUD routes."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.aionx.omni_mission_control import system_hud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System HUD"])


@router.get("/hud")
async def get_system_hud(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        return await system_hud(db, persist=False)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("system_hud failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="System HUD unavailable")


@router.post("/self-heal")
async def trigger_self_heal() -> dict[str, Any]:
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
