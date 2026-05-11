"""
JARVIS Self-Awareness API
Morning briefing, idea enhancer, agent teams, self-improvement
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.intelligence.jarvis_awareness import (
    generate_morning_briefing,
    self_improvement_report,
    enhance_idea,
    spawn_agent_team,
    jarvis_chat,
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
    """Talk to JARVIS — responds as senior operational manager."""
    return await jarvis_chat(db, body.message, body.task_type, body.history)


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
