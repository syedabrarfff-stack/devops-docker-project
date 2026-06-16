"""System-level HUD routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.aionx.omni_mission_control import system_hud

router = APIRouter(prefix="/system", tags=["System HUD"])


@router.get("/hud")
async def get_system_hud(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await system_hud(db, persist=False)


@router.post("/self-heal")
async def trigger_self_heal() -> dict[str, Any]:
    """Manually trigger JARVIS autonomous self-healing cycle.
    Resets failed AI circuit breakers, refills empty lead pipelines,
    resumes paused scheduler jobs, and reports Redis health."""
    from app.services.monitoring.self_healer import run_self_healing_cycle
    return await run_self_healing_cycle()
