from fastapi import APIRouter
from app.api.v1.routes import chat, briefing, approvals, agents, ws
from app.api.v1.routes import crm, leads, outreach, memory, tasks
from app.api.v1.routes import auth, scheduler, calendar, notifications, sync
from app.api.v1.routes import intelligence

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
