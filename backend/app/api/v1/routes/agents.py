from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/agents", tags=["agents"])

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
    agent_id: str
    task: str
    priority: str = "normal"
    context: Optional[dict] = None


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
async def dispatch_task(task: TaskDispatch):
    return {
        "success": True,
        "task_id": f"task_{task.agent_id}_{int(__import__('time').time())}",
        "agent_id": task.agent_id,
        "message": f"Task dispatched to agent {task.agent_id}",
        "status": "queued",
    }
