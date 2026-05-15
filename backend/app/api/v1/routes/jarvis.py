"""
JARVIS Self-Awareness API
Morning briefing, idea enhancer, agent teams, self-improvement, memory, evolution
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.intelligence.jarvis_awareness import (
    generate_morning_briefing,
    self_improvement_report,
    enhance_idea,
    spawn_agent_team,
    jarvis_chat,
)
from app.services.memory import manager as mem
from app.services.intelligence.jarvis_self_learning import (
    run_daily_learning_cycle,
    record_outcome,
    resolve_outcome,
    get_evolution_history,
)

router = APIRouter(prefix="/jarvis", tags=["jarvis"])


class IdeaRequest(BaseModel):
    idea: str


class AgentTeamRequest(BaseModel):
    task: str


class ChatRequest(BaseModel):
    message: str
    task_type: str = "FAST"
    history: list = []
    session_id: Optional[str] = None


class OutcomeRequest(BaseModel):
    action_type: str
    action_detail: str
    action_ref: Optional[str] = None
    importance: float = 0.6


class ResolveOutcomeRequest(BaseModel):
    outcome: str   # won, lost, replied, ignored, accepted, rejected
    note: Optional[str] = None


class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "instruction"
    importance: float = 0.9
    tags: list = []


@router.get("/briefing")
async def morning_briefing(db: AsyncSession = Depends(get_db)):
    """Daily morning briefing — news, weather, skills, opportunities."""
    return await generate_morning_briefing(db)


@router.get("/self-improvement")
async def self_improvement(db: AsyncSession = Depends(get_db)):
    """JARVIS self-improvement report — new tech, market intel."""
    return await self_improvement_report(db)


@router.post("/enhance-idea")
async def enhance_idea_endpoint(body: IdeaRequest, db: AsyncSession = Depends(get_db)):
    """JARVIS analyses and enhances Captain's ideas with 10+ improvements."""
    return await enhance_idea(db, body.idea)


@router.post("/spawn-team")
async def spawn_team(body: AgentTeamRequest, db: AsyncSession = Depends(get_db)):
    """JARVIS spawns a specialist agent team for any task."""
    return await spawn_agent_team(db, body.task)


@router.post("/chat")
async def jarvis_chat_endpoint(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Talk to JARVIS — responds as senior operational manager. Memory active."""
    return await jarvis_chat(db, body.message, body.task_type, body.history, body.session_id)


# ── Memory Endpoints ──────────────────────────────────────────────────────────

@router.get("/memory")
async def get_memory(
    query: str = Query("", description="Search query"),
    memory_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
):
    """What does JARVIS remember? Search or browse all memories."""
    memories = await mem.recall(db, query=query, limit=limit, memory_type=memory_type)
    stats = await mem.get_memory_stats(db)
    return {
        "memories": [{
            "id": m.id,
            "type": m.memory_type,
            "content": m.value,
            "importance": m.importance,
            "tags": m.tags or [],
            "access_count": m.access_count,
            "created_at": str(m.created_at),
        } for m in memories],
        "stats": stats,
        "query": query,
    }


@router.post("/memory/store")
async def store_captain_memory(body: MemoryStoreRequest, db: AsyncSession = Depends(get_db)):
    """Captain teaches JARVIS something — stored as permanent instruction."""
    memory = await mem.store_memory(
        db,
        content=body.content,
        memory_type=body.memory_type,
        importance=body.importance,
        tags=body.tags,
    )
    await db.commit()
    return {"id": memory.id, "stored": True, "type": memory.memory_type}


@router.get("/memory/stats")
async def memory_stats(db: AsyncSession = Depends(get_db)):
    """How much does JARVIS know?"""
    stats = await mem.get_memory_stats(db)
    return stats


# ── Self-Evolution Endpoints ──────────────────────────────────────────────────

@router.post("/evolve")
async def trigger_learning_cycle(db: AsyncSession = Depends(get_db)):
    """Trigger JARVIS daily self-learning cycle manually."""
    result = await run_daily_learning_cycle(db)
    return result


@router.get("/evolution-log")
async def evolution_log(limit: int = Query(10, le=30), db: AsyncSession = Depends(get_db)):
    """JARVIS evolution history — what it has learned over time."""
    history = await get_evolution_history(db, limit=limit)
    return {"history": history, "total": len(history)}


# ── Outcome Tracking ──────────────────────────────────────────────────────────

@router.post("/outcomes")
async def create_outcome(body: OutcomeRequest, db: AsyncSession = Depends(get_db)):
    """Log a JARVIS action for outcome tracking."""
    record = await record_outcome(
        db,
        action_type=body.action_type,
        action_detail=body.action_detail,
        action_ref=body.action_ref,
        importance=body.importance,
    )
    await db.commit()
    return {"id": record.id, "action_type": record.action_type, "status": "tracking"}


@router.post("/outcomes/{outcome_id}/resolve")
async def resolve_outcome_endpoint(
    outcome_id: int,
    body: ResolveOutcomeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Captain marks what happened — JARVIS learns from it immediately."""
    record = await resolve_outcome(db, outcome_id, body.outcome, body.note)
    await db.commit()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Outcome record not found")
    return {
        "id": record.id,
        "outcome": record.outcome,
        "learning": record.learning,
        "resolved_at": str(record.resolved_at),
    }


@router.get("/authority")
async def jarvis_authority():
    """JARVIS authority matrix — what JARVIS can do vs what needs Captain approval."""
    from app.services.intelligence.jarvis_authority import (
        get_authority_summary, JARVIS_FULL_AUTHORITY,
        CAPTAIN_APPROVAL_REQUIRED, JARVIS_ALERTS_CAPTAIN,
    )
    summary = get_authority_summary()
    return {
        "summary": summary,
        "autonomous_actions": JARVIS_FULL_AUTHORITY,
        "requires_captain_approval": CAPTAIN_APPROVAL_REQUIRED,
        "alerts_captain": JARVIS_ALERTS_CAPTAIN,
        "philosophy": "JARVIS runs the company. Captain approves money, contracts, and go-live.",
    }


@router.get("/status")
async def jarvis_status():
    """JARVIS operational status."""
    return {
        "status": "operational",
        "system": "JARVIS",
        "company": "Aliyar Solutions",
        "version": "9.0.0",
        "capabilities": [
            "morning_briefing",
            "self_improvement",
            "idea_enhancement",
            "agent_team_spawning",
            "24x7_operations",
            "autonomous_correction",
            "market_intelligence",
            "sales_outreach",
            "proposal_generation",
            "voice_interface_ready"
        ],
        "message": "Good day Captain. JARVIS operational. All systems running."
    }
