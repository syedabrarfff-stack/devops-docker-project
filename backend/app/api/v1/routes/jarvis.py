"""
JARVIS Self-Awareness API
Morning briefing, idea enhancer, agent teams, self-improvement, memory, evolution
"""
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.intelligence.jarvis_awareness import (
    JARVIS_AWARENESS_PROMPT,
    generate_morning_briefing,
    self_improvement_report,
    enhance_idea,
    spawn_agent_team,
    jarvis_chat,
)
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)
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


@router.get("/greeting")
async def jarvis_greeting(db: AsyncSession = Depends(get_db)):
    """Context-aware greeting — called when Captain opens the app."""
    from datetime import datetime
    from app.services.memory.manager import build_context

    hour = datetime.now().hour
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    try:
        memory_context = await build_context(db, query="recent client activity leads proposals", limit=5)

        response = await ai_router.chat(
            messages=[
                {"role": "system", "content": JARVIS_AWARENESS_PROMPT},
                {"role": "user", "content": (
                    f"Captain just opened the JARVIS dashboard. It's {time_of_day}. "
                    f"Give a natural, warm greeting in 2-3 sentences. Mention what's happening if there's context below. "
                    f"End by asking if they want the full brief or to jump straight to clients. "
                    f"Context: {memory_context or 'No recent activity to report.'}"
                )}
            ],
            task_type="FAST",
            max_tokens=120,
        )
        greeting_text = response.get("content", f"Good {time_of_day}, Captain. JARVIS operational.")
    except Exception:
        greeting_text = f"Good {time_of_day}, Captain. All systems running."

    return {
        "greeting": greeting_text,
        "time_of_day": time_of_day,
        "speak": True,
    }


@router.get("/voice-brief")
async def jarvis_voice_brief(db: AsyncSession = Depends(get_db)):
    """Short spoken brief — 4-5 topics, voice-optimised, no markdown."""
    try:
        briefing = await generate_morning_briefing(db)
        return {
            "brief": briefing.get("briefing", ""),
            "date": briefing.get("date", ""),
            "speak": True,
        }
    except Exception as e:
        logger.error(f"Voice brief failed: {e}")
        return {"brief": "Brief unavailable right now, Captain.", "speak": True}


@router.get("/ai-health")
async def jarvis_ai_health():
    """Test all AI providers and return real-time status."""
    import asyncio
    from app.services.ai.router import ai_router as _router

    results = {}
    providers_to_test = [
        ("anthropic", "claude-3-haiku-20240307"),
        ("openai", "gpt-4o-mini"),
        ("google", "gemini-1.5-flash"),
        ("deepseek", "deepseek-chat"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small"),
    ]

    async def test_provider(name, model):
        import time
        t0 = time.monotonic()
        try:
            resp = await _router.chat(
                messages=[{"role": "user", "content": "Reply with one word: operational"}],
                task_type="FAST",
                max_tokens=5,
                force_provider=name,
            )
            latency = int((time.monotonic() - t0) * 1000)
            return name, {
                "status": "online",
                "latency_ms": latency,
                "model": model,
                "response": resp.get("content", "")[:20],
            }
        except Exception as ex:
            return name, {
                "status": "offline",
                "error": str(ex)[:100],
                "model": model,
            }

    tasks = [test_provider(name, model) for name, model in providers_to_test]
    try:
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in test_results:
            if isinstance(r, tuple):
                name, data = r
                results[name] = data
    except Exception as e:
        logger.error(f"AI health check failed: {e}")

    online = sum(1 for v in results.values() if v.get("status") == "online")
    return {
        "providers": results,
        "online": online,
        "total": len(results),
        "overall": "operational" if online > 0 else "degraded",
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
