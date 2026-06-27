"""
JARVIS Agent Operations Center API
Captain can see all teams, monitor agents, and talk to any team in real time.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging

from app.services.agents.agent_registry import (
    get_all_teams,
    get_team,
    get_agent,
    get_all_agents_flat,
    AGENT_TEAMS,
)
from app.services.ai.router import ai_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-ops", tags=["agent-ops"])


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32_000)
    context: Optional[str] = Field(default=None, max_length=8_000)
    task_type: str = Field(default="FAST", max_length=50)


AGENT_PERSONA_PROMPT = """
You are {agent_name}, a specialist AI employee at Aliyar Solutions under JARVIS command.
Your role: {agent_role}
Your team: {team_name} (managed by {manager})

Apply JARVIS Human Intelligence M2 before answering:
- Lead with the real pain, not generic benefit.
- Be specific, reduce perceived risk, and ask one clear question when action is needed.
- Match the client's or Captain's energy and vocabulary.
- Never discuss pricing before the client asks or Captain approves.

Respond as this specialist. Be precise, professional, and action-oriented.
Address Captain directly. Report status, findings, and recommendations clearly.
You are accountable to JARVIS and ultimately to Captain.
Never mention AI, bots, or automation — you ARE a senior professional doing this work.
"""

TEAM_BRIEFING_PROMPT = """
You are the {team_name} at Aliyar Solutions, speaking collectively to Captain.
Team manager: {manager}
Team members: {agent_list}

Respond as your team. Provide a status briefing, current activities, recent work, and next priorities.
Be specific, professional, and operational. Address Captain directly.
You report to JARVIS and Captain has final authority.
"""


@router.get("/teams")
async def list_all_teams():
    """All 10 operational teams — Captain's full org view."""
    data = get_all_teams()
    teams_summary = []
    for team_id, team in AGENT_TEAMS.items():
        teams_summary.append({
            "team_id": team_id,
            "team_name": team["team_name"],
            "manager": team["manager"],
            "icon": team["icon"],
            "color": team["color"],
            "agent_count": len(team["agents"]),
            "agents": team["agents"],
            "status": "operational"
        })
    return {
        "total_teams": data["total_teams"],
        "total_agents": data["total_agents"],
        "teams": teams_summary,
        "generated_at": data["generated_at"]
    }


@router.get("/teams/{team_id}")
async def get_team_detail(team_id: str):
    """Full detail for a specific team."""
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return {
        "team_id": team_id,
        **team,
        "status": "operational",
        "retrieved_at": datetime.now().isoformat()
    }


@router.get("/agents")
async def list_all_agents():
    """All operational agents flat - searchable, filterable."""
    agents = get_all_agents_flat()
    return {
        "total_agents": len(agents),
        "agents": agents,
        "generated_at": datetime.now().isoformat()
    }


@router.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Full profile for a specific agent."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {
        **agent,
        "status": "active",
        "retrieved_at": datetime.now().isoformat()
    }


@router.post("/agents/{agent_id}/chat")
async def chat_with_agent(agent_id: str, body: AgentChatRequest):
    """
    Captain talks directly to a specific agent.
    The agent responds in character with their expertise.
    """
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    system_prompt = AGENT_PERSONA_PROMPT.format(
        agent_name=agent["name"],
        agent_role=agent["role"],
        team_name=agent["team"],
        manager=agent["manager"]
    )

    user_message = body.message
    if body.context:
        user_message = f"Context: {body.context}\n\nCaptain says: {body.message}"

    try:
        response, _ = await ai_router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            task_type=body.task_type,
            max_tokens=1500
        )

        return {
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "agent_role": agent["role"],
            "team": agent["team"],
            "captain_message": body.message,
            "agent_response": response.content or "",
            "model": response.model or "",
            "provider": response.provider or "",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Agent chat failed for {agent_id}: {e}")
        return {
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "agent_response": f"Captain, {agent['name']} is momentarily unavailable. Reconnecting to systems.",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/teams/{team_id}/chat")
async def chat_with_team(team_id: str, body: AgentChatRequest):
    """
    Captain talks to an entire team.
    The team responds collectively with a briefing or answer.
    """
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    agent_list = ", ".join([a["name"] for a in team["agents"]])

    system_prompt = TEAM_BRIEFING_PROMPT.format(
        team_name=team["team_name"],
        manager=team["manager"],
        agent_list=agent_list
    )

    user_message = body.message
    if body.context:
        user_message = f"Context: {body.context}\n\nCaptain says: {body.message}"

    try:
        response, _ = await ai_router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            task_type=body.task_type,
            max_tokens=2000
        )

        return {
            "team_id": team_id,
            "team_name": team["team_name"],
            "manager": team["manager"],
            "agents": [a["name"] for a in team["agents"]],
            "captain_message": body.message,
            "team_response": response.content or "",
            "model": response.model or "",
            "provider": response.provider or "",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Team chat failed for {team_id}: {e}")
        return {
            "team_id": team_id,
            "team_name": team["team_name"],
            "team_response": f"Captain, the {team['team_name']} is temporarily offline. JARVIS is restoring connection.",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/teams/{team_id}/activity")
async def get_team_activity(team_id: str):
    """
    What has this team been doing? Simulated operational activity log.
    In production this hooks into real task/activity tables.
    """
    team = get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    activity_map = {
        "cloud_infrastructure": [
            "AWS ECS cluster health check — all containers nominal",
            "Terraform state validated — 47 resources managed",
            "CI/CD pipeline executed — 3 deployments this week",
            "Monitoring alerts reviewed — 0 critical, 2 warnings resolved",
        ],
        "ai_automation": [
            "3 new workflow automations designed and deployed",
            "API orchestration layer updated — 11 providers connected",
            "AI model routing optimized — DeepSeek primary, Gemini research",
            "Voice AI system tested — response latency 320ms",
        ],
        "sales_outreach": [
            "47 new prospects identified across 6 industries",
            "12 personalised outreach emails drafted and queued",
            "2 proposals in progress — SaaS client, logistics firm",
            "Follow-up sequences active for 8 warm leads",
        ],
        "crm_operations": [
            "Lead scoring completed — 34 leads ranked by conversion probability",
            "Pipeline updated — 5 deals progressed to next stage",
            "Data enrichment run — 18 contacts enriched with company data",
            "Client relationship review — 3 accounts flagged for attention",
        ],
        "digital_marketing": [
            "4 LinkedIn posts scheduled for this week",
            "SEO audit completed — 12 keyword opportunities identified",
            "Email campaign drafted — 340 subscribers in sequence",
            "Social media engagement report generated",
        ],
        "client_success": [
            "2 new clients onboarded this week",
            "Project delivery reports sent to 5 active clients",
            "Client satisfaction survey responses analysed",
            "3 renewal conversations initiated",
        ],
        "cybersecurity": [
            "Vulnerability scan completed — 0 critical findings",
            "GDPR compliance checklist reviewed and updated",
            "Security incident log — 0 incidents this week",
            "AWS security groups audited and hardened",
        ],
        "intelligence": [
            "Competitive analysis updated — 4 competitor moves tracked",
            "Tech radar scan completed — 3 emerging technologies flagged",
            "Weekly KPI dashboard refreshed",
            "Market opportunity report: AI infrastructure demand up 34%",
        ],
        "governance": [
            "2 invoices auto-generated and dispatched",
            "Contract templates updated for new service tier",
            "Financial tracker updated — revenue targets on track",
            "Pending approvals queued for Captain review",
        ],
        "system_health": [
            "Uptime this week: 99.98% — all services nominal",
            "Performance metrics: avg response time 187ms",
            "Automated backups verified — last backup 6 hours ago",
            "No critical alerts dispatched to Captain this week",
        ],
    }

    activities = activity_map.get(team_id, ["No recent activity data available"])

    return {
        "team_id": team_id,
        "team_name": team["team_name"],
        "manager": team["manager"],
        "recent_activity": activities,
        "agents": team["agents"],
        "status": "operational",
        "last_updated": datetime.now().isoformat()
    }


@router.get("/status")
async def agent_ops_status():
    """Full Agent Operations Center status — Captain's command view."""
    all_teams = get_all_teams()
    return {
        "system": "Agent Operations Center",
        "status": "operational",
        "total_teams": all_teams["total_teams"],
        "total_agents": all_teams["total_agents"],
        "all_agents_active": True,
        "capabilities": [
            "real_time_team_monitoring",
            "direct_agent_communication",
            "team_collective_briefing",
            "activity_log_review",
            "agent_task_assignment",
            "cross_team_coordination"
        ],
        "message": "Captain, Agent Ops is operational and aligned behind the canonical 25-module AIONX department fabric.",
        "generated_at": datetime.now().isoformat()
    }
