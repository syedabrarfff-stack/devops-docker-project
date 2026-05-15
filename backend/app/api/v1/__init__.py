from fastapi import APIRouter
from app.api.v1.routes import chat, briefing, approvals, agents, ws
from app.api.v1.routes import crm, leads, outreach, memory, tasks
from app.api.v1.routes import auth, scheduler, calendar, notifications, sync
from app.api.v1.routes import intelligence
from app.api.v1.routes import governance, emergency, knowledge, catalog, ai_ops
from app.api.v1.routes import team, voice
from app.api.v1.routes import credentials, capabilities, discovery, automation
from app.api.v1.routes import dashboard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat.router)
api_router.include_router(briefing.router)
api_router.include_router(approvals.router)
api_router.include_router(agents.router)
api_router.include_router(ws.router)
api_router.include_router(crm.router)
api_router.include_router(leads.router)
api_router.include_router(outreach.router)
api_router.include_router(memory.router)
api_router.include_router(tasks.router)
api_router.include_router(auth.router)
api_router.include_router(scheduler.router)
api_router.include_router(calendar.router)
api_router.include_router(notifications.router)
api_router.include_router(sync.router)
api_router.include_router(intelligence.router)
api_router.include_router(governance.router)
api_router.include_router(emergency.router)
api_router.include_router(knowledge.router)
api_router.include_router(catalog.router)
api_router.include_router(ai_ops.router)
api_router.include_router(team.router)
api_router.include_router(voice.router)
api_router.include_router(credentials.router)
api_router.include_router(capabilities.router)
api_router.include_router(discovery.router)
api_router.include_router(automation.router)
api_router.include_router(dashboard.router)
