from fastapi import APIRouter
from app.api.v1.routes import chat, briefing, approvals, agents, ws
from app.api.v1.routes import crm, leads, outreach, memory, tasks
from app.api.v1.routes import auth, scheduler, calendar, notifications, sync
from app.api.v1.routes import intelligence
from app.api.v1.routes import governance, emergency, knowledge, catalog, ai_ops
from app.api.v1.routes import team
from app.api.v1.routes import jarvis
from app.api.v1.routes import agent_ops
from app.api.v1.routes import gmail
from app.api.v1.routes import discovery
from app.api.v1.routes import voice
from app.api.v1.routes import pricing
from app.api.v1.routes import proposals
from app.api.v1.routes import invoices
from app.api.v1.routes import revenue

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
api_router.include_router(jarvis.router)
api_router.include_router(agent_ops.router)
api_router.include_router(gmail.router)
api_router.include_router(discovery.router)
api_router.include_router(voice.router)
api_router.include_router(pricing.router)
api_router.include_router(proposals.router)
api_router.include_router(invoices.router)
api_router.include_router(revenue.router)
