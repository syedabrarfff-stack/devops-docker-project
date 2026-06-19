from fastapi import APIRouter, Depends
from app.core.config import settings
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
from app.api.v1.routes import clients
from app.api.v1.routes import council
from app.api.v1.routes import tenancy
from app.api.v1.routes import departments
from app.api.v1.routes import demos
from app.api.v1.routes import pilot
from app.api.v1.routes import captain
from app.api.v1.routes.auth import get_current_captain
from app.api.v1.routes import economics
from app.api.v1.routes import innovation
from app.api.v1.routes import civilization
from app.api.v1.routes import calls
from app.api.v1.routes import intel
from app.api.v1.routes import connector_hub
from app.api.v1.routes import consciousness
from app.api.v1.routes import aionx
from app.api.v1.routes import batch1
from app.api.v1.routes import frontier
from app.api.v1.routes import system
from app.api.v1.routes import communication
from app.api.v1.routes import ses_inbound
from app.api.v1.routes import whitelabel
from app.api.v1.routes import payments
from app.api.v1.routes import telegram_webhook
from app.api.v1.routes import trust

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["health"])
async def api_health():
    """API-prefixed liveness probe for public checks and deployment scripts."""
    return {
        "status": "ok",
        "system": "JARVIS",
        "company": "Aliyar Solutions",
        "version": settings.APP_VERSION,
    }


@api_router.get("/ai/health", tags=["AI Operations"])
async def ai_health_alias():
    """Compatibility alias for AI provider health."""
    return await ai_ops.provider_health()


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
api_router.include_router(clients.router)
api_router.include_router(council.router)
api_router.include_router(tenancy.router)
api_router.include_router(departments.router)
api_router.include_router(demos.router)
api_router.include_router(pilot.router)
api_router.include_router(captain.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(captain.voice_router, dependencies=[Depends(get_current_captain)])
api_router.include_router(economics.router)
api_router.include_router(innovation.router)
api_router.include_router(civilization.router)
api_router.include_router(calls.router)
api_router.include_router(intel.router)
api_router.include_router(connector_hub.router)
api_router.include_router(consciousness.router)
api_router.include_router(aionx.router)
api_router.include_router(batch1.router)
api_router.include_router(frontier.router)
api_router.include_router(system.router)
api_router.include_router(communication.router)
api_router.include_router(ses_inbound.router)
api_router.include_router(whitelabel.router)
api_router.include_router(payments.router)
api_router.include_router(payments.webhook_router)
api_router.include_router(telegram_webhook.router)
api_router.include_router(trust.router)
