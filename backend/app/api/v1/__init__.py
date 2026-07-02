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
from app.api.v1.routes import truth_engine, resilience, financial_intel, learning, founder, moat
from app.api.v1.routes import omega
from app.api.v1.routes import ghost
from app.api.v1.routes import autopilot
from app.api.v1.routes import signal
from app.api.v1.routes import nexus
from app.api.v1.routes import constitution
from app.api.v1.routes import service_registry

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


api_router.include_router(chat.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(briefing.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(approvals.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(agents.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(ws.router)
api_router.include_router(crm.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(leads.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(outreach.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(memory.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(tasks.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(auth.router)
api_router.include_router(scheduler.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(calendar.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(notifications.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(sync.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(intelligence.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(governance.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(emergency.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(knowledge.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(catalog.router)
api_router.include_router(ai_ops.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(team.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(jarvis.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(agent_ops.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(gmail.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(discovery.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(voice.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(pricing.router)
api_router.include_router(proposals.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(invoices.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(revenue.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(clients.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(council.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(tenancy.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(departments.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(demos.router)
api_router.include_router(pilot.router)
api_router.include_router(captain.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(captain.voice_router, dependencies=[Depends(get_current_captain)])
api_router.include_router(economics.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(innovation.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(civilization.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(calls.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(intel.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(connector_hub.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(consciousness.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(aionx.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(batch1.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(frontier.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(system.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(communication.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(ses_inbound.router)          # public — SES inbound webhook
api_router.include_router(whitelabel.router)           # public — white-label client onboarding
api_router.include_router(payments.router)             # public — checkout / payment links
api_router.include_router(payments.webhook_router)     # public — Stripe webhook callbacks
api_router.include_router(telegram_webhook.router)     # public — Telegram webhook callbacks
api_router.include_router(trust.router, dependencies=[Depends(get_current_captain)])
# Layer 18 — Truth, Validation & Resilience
api_router.include_router(truth_engine.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(resilience.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(financial_intel.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(learning.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(founder.router, dependencies=[Depends(get_current_captain)])
api_router.include_router(moat.router, dependencies=[Depends(get_current_captain)])
# OMEGA — Global Intelligence Swarm (Captain auth required — 16-model AI swarm)
api_router.include_router(omega.router, dependencies=[Depends(get_current_captain)])
# GHOST — AI Outreach Intelligence Engine (Captain auth required — sends emails)
api_router.include_router(ghost.router, dependencies=[Depends(get_current_captain)])
# AUTOPILOT — Autonomous Outreach Pipeline (Captain auth required — approves/sends emails)
api_router.include_router(autopilot.router, dependencies=[Depends(get_current_captain)])
# SIGNAL — AI Pipeline Intelligence Scanner (Captain auth required — triggers AI scans)
api_router.include_router(signal.router, dependencies=[Depends(get_current_captain)])
# NEXUS — Supreme Autonomous Intelligence Core (Captain auth required — autonomous execution)
api_router.include_router(nexus.router, dependencies=[Depends(get_current_captain)])
# Layer 19 — Supreme Intelligence: Constitution, CEO, Revenue, Platform, Sales Autonomy
api_router.include_router(constitution.router, dependencies=[Depends(get_current_captain)])
# Phase 3 — Service Registry API (dynamic service management)
api_router.include_router(service_registry.router, dependencies=[Depends(get_current_captain)])
