from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.agents.liaison import client_liaison_service

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(get_current_captain)])

AGENT_HIERARCHY = {
    "core": {
        "id": "jarvis-core",
        "name": "JARVIS Core",
        "role": "AI Operating System",
        "icon": "⚡",
        "status": "active",
    },
    "managers": [
        {"id": "sales-mgr", "name": "Sales Manager", "icon": "💼", "status": "active", "workers": 3},
        {"id": "outreach-mgr", "name": "Outreach Manager", "icon": "📣", "status": "active", "workers": 4},
        {"id": "research-mgr", "name": "Research Manager", "icon": "🔭", "status": "active", "workers": 2},
        {"id": "devops-mgr", "name": "DevOps Manager", "icon": "⚙️", "status": "active", "workers": 2},
        {"id": "finance-mgr", "name": "Finance Manager", "icon": "💰", "status": "idle", "workers": 2},
        {"id": "content-mgr", "name": "Content Manager", "icon": "✍️", "status": "active", "workers": 3},
        {"id": "automation-mgr", "name": "Automation Manager", "icon": "🤖", "status": "active", "workers": 3},
        {"id": "security-mgr", "name": "Security Manager", "icon": "🛡️", "status": "active", "workers": 2},
        {"id": "infra-mgr", "name": "Infrastructure Manager", "icon": "☁️", "status": "idle", "workers": 2},
        {"id": "client-mgr", "name": "Client Success Manager", "icon": "🎧", "status": "active", "workers": 2},
    ],
    "workers": [
        {"id": "lead-agent", "name": "Lead Generation Agent", "manager": "outreach-mgr", "status": "active"},
        {"id": "email-agent", "name": "Email Outreach Agent", "manager": "outreach-mgr", "status": "active"},
        {"id": "proposal-agent", "name": "Proposal Agent", "manager": "sales-mgr", "status": "active"},
        {"id": "crm-agent", "name": "CRM Agent", "manager": "sales-mgr", "status": "active"},
        {"id": "analytics-agent", "name": "Analytics Agent", "manager": "research-mgr", "status": "active"},
        {"id": "news-agent", "name": "News Intelligence Agent", "manager": "research-mgr", "status": "active"},
        {"id": "aws-agent", "name": "AWS Infrastructure Agent", "manager": "devops-mgr", "status": "idle"},
        {"id": "monitor-agent", "name": "Monitoring Agent", "manager": "security-mgr", "status": "active"},
        {"id": "content-agent", "name": "Content Generation Agent", "manager": "content-mgr", "status": "active"},
        {"id": "social-agent", "name": "Social Media Agent", "manager": "content-mgr", "status": "active"},
        {"id": "seo-agent", "name": "SEO Agent", "manager": "content-mgr", "status": "idle"},
        {"id": "automation-agent", "name": "Workflow Automation Agent", "manager": "automation-mgr", "status": "active"},
    ],
}


class TaskDispatch(BaseModel):
    agent_id: str = Field(..., max_length=100)
    task: str = Field(..., min_length=1, max_length=8_000)
    priority: str = Field(default="normal", max_length=20)
    context: Optional[dict] = None


class PrepareLiaisonCallRequest(BaseModel):
    lead_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    call_topic: Optional[str] = Field(default=None, max_length=300)
    call_objective: Optional[str] = Field(default=None, max_length=500)


@router.get("/hierarchy")
async def get_hierarchy():
    total = len(AGENT_HIERARCHY["managers"]) + len(AGENT_HIERARCHY["workers"]) + 1
    active = sum(1 for a in [*AGENT_HIERARCHY["managers"], *AGENT_HIERARCHY["workers"]]
                 if a["status"] == "active") + 1
    return {
        **AGENT_HIERARCHY,
        "stats": {"total_agents": total, "active": active, "idle": total - active},
    }


@router.post("/dispatch")
@limiter.limit("30/minute")
async def dispatch_task(request: Request, task: TaskDispatch):
    return {
        "success": True,
        "task_id": f"task_{task.agent_id}_{int(__import__('time').time())}",
        "agent_id": task.agent_id,
        "message": f"Task dispatched to agent {task.agent_id}",
        "status": "queued",
    }


@router.get("/liaison")
async def list_liaison_agents():
    return client_liaison_service.list_agents()


@router.post("/liaison/seed")
@limiter.limit("3/minute")
async def seed_liaison_agents(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await client_liaison_service.seed_agents(resolved_tenant_id)


@router.post("/liaison/{agent_name}/prepare-call")
@limiter.limit("10/minute")
async def prepare_liaison_call(
    agent_name: str,
    request: Request,
    body: PrepareLiaisonCallRequest = Body(default_factory=PrepareLiaisonCallRequest),
):
    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        return await client_liaison_service.prepare_call(
            agent_name,
            resolved_tenant_id,
            lead_id=body.lead_id,
            client_id=body.client_id,
            call_topic=body.call_topic,
            call_objective=body.call_objective,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
