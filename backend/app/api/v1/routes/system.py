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
