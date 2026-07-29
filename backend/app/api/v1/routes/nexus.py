"""
JARVIS NEXUS — Supreme Autonomous Intelligence Core API.

GET  /nexus/status        — full operational status
GET  /nexus/constitution  — immutable rule set
GET  /nexus/pulse         — latest heartbeat snapshot
GET  /nexus/decisions     — recent autonomous decision log
GET  /nexus/health        — subsystem health matrix
POST /nexus/heal          — trigger heal on specific subsystem
POST /nexus/cycle         — SSE: run full autonomous cycle
POST /nexus/think         — SSE: brain reasoning only (no action)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.v1.routes.auth import get_current_captain
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.nexus.constitution import get_constitution
from app.services.nexus.heartbeat import (
    get_latest_pulse,
    get_decisions,
    get_heal_log,
    run_pulse,
)
from app.services.nexus.healer import diagnose_all, heal_subsystem
from app.services.nexus.nexus import nexus_status, nexus_cycle_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nexus", tags=["JARVIS NEXUS"], dependencies=[Depends(get_current_captain)])


class HealRequest(BaseModel):
    subsystem: str = Field(..., description="Subsystem to heal")


class ThinkRequest(BaseModel):
    pipeline_state: Optional[dict] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_nexus_status(db: AsyncSession = Depends(get_db)):
    """Full NEXUS operational status — Constitution + Brain + Heartbeat + Healer."""
    return await nexus_status(db)


@router.get("/constitution")
async def get_nexus_constitution():
    """Return the immutable NEXUS Constitution — 12 articles that govern all autonomous action."""
    rules = get_constitution()
    return {
        "articles": len(rules),
        "constitution": rules,
        "immutable": True,
        "version": "1.0.0",
    }


@router.get("/pulse")
async def get_nexus_pulse(db: AsyncSession = Depends(get_db)):
    """Latest heartbeat pulse snapshot. Triggers a fresh pulse if none exists."""
    pulse = await get_latest_pulse()
    if not pulse:
        pulse = await run_pulse(db)
    return pulse


@router.get("/decisions")
async def get_nexus_decisions(limit: int = Query(default=20, ge=1, le=100)):
    """Recent autonomous decision log."""
    decisions = await get_decisions(limit)
    heal_log = await get_heal_log(10)
    return {"decisions": decisions, "heal_log": heal_log, "total": len(decisions)}


@router.get("/health")
async def get_nexus_health(db: AsyncSession = Depends(get_db)):
    """Subsystem health matrix — per-subsystem status and healability."""
    health = await diagnose_all(db)
    healthy = sum(1 for s in health.values() if s.get("status") == "healthy")
    return {
        "subsystems": health,
        "healthy_count": healthy,
        "total_count": len(health),
        "overall": "healthy" if healthy == len(health)
                   else "degraded" if healthy > 0
                   else "critical",
    }


@router.post("/heal")
@limiter.limit("10/minute")
async def heal_nexus_subsystem(
    request,
    body: HealRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger healing protocol for a specific subsystem."""
    valid = {"redis", "scheduler", "autopilot", "ai_provider", "database", "signal", "ghost", "pipeline"}
    if body.subsystem not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown subsystem: {body.subsystem}")
    result = await heal_subsystem(body.subsystem, db)
    return result


@router.post("/cycle")
@limiter.limit("3/minute")
async def run_nexus_cycle(request, db: AsyncSession = Depends(get_db)):
    """
    SSE: Run the full autonomous NEXUS cycle.
    PULSE → THINK → ACT → HEAL → LOG → NOTIFY

    Protocol:
      data: {"type":"phase","phase":"PULSE","message":"..."}
      data: {"type":"pulse","data":{...}}
      data: {"type":"phase","phase":"THINK","message":"..."}
      data: {"type":"thinking","text":"..."}
      data: {"type":"decision","decision":{...}}
      data: {"type":"phase","phase":"HEAL","message":"..."}
      data: {"type":"heal","results":[...]}
      data: {"type":"phase","phase":"COMPLETE","message":"..."}
      data: {"type":"done"}
    """
    return StreamingResponse(
        nexus_cycle_stream(db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/think")
@limiter.limit("5/minute")
async def nexus_think(request, body: ThinkRequest, db: AsyncSession = Depends(get_db)):
    """
    SSE: BRAIN reasoning only — no action dispatched. Use for insight without side effects.
    """
    from app.services.nexus.brain import think_stream

    # If no state provided, read current pulse
    if body.pipeline_state:
        state = body.pipeline_state
    else:
        pulse = await get_latest_pulse()
        if not pulse:
            pulse = await run_pulse(db)
        state = {
            **pulse.get("pipeline", {}),
            "pending_drafts": pulse.get("autopilot_pending", 0),
            "subsystem_health": pulse.get("subsystems", {}),
        }

    return StreamingResponse(
        think_stream(state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/pulse/trigger")
@limiter.limit("10/minute")
async def trigger_pulse(request, db: AsyncSession = Depends(get_db)):
    """Trigger an immediate heartbeat pulse and return the result."""
    pulse = await run_pulse(db)
    return pulse
