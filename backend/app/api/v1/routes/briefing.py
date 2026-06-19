from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.services.intelligence.morning_briefing import MorningBriefingEngine
from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

router = APIRouter(prefix="/briefing", tags=["briefing"])

BRIEFING_PROMPT = """You are JARVIS, the operational intelligence core of Aliyar Solutions.
Generate a sharp, strategic morning briefing for Captain Syed Abrar.

Format:
1. Greeting (time-aware: morning/afternoon/evening)
2. Pipeline snapshot (MRR, pipeline value, hot leads count)
3. Priority actions — use the live data provided to surface EXACTLY what needs attention today
4. Overdue proposals — name the clients, days overdue, recommend action
5. Pending contracts — who needs to sign, next step
6. Trust engine status — how many briefs sent this week, conversion momentum
7. One strategic recommendation for today
8. Close: "Ready for your commands, Captain."

Tone: direct, confident, premium intelligence. No fluff. CEO-level signal only.
Use the live JARVIS data provided in the user message as ground truth."""


@router.get("/morning")
async def morning_briefing(request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _resolve_tenant_id(request)
    await set_tenant_context(db, str(tenant_id))
    engine = MorningBriefingEngine()
    metrics = await engine._collect_metrics(db, tenant_id)
    content = engine._render(metrics)
    now = datetime.now()
    hour = now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return {
        "briefing": content,
        "metrics": metrics,
        "model": "grounded_metrics",
        "provider": "jarvis",
        "demo": False,
        "generated_at": now.isoformat(),
        "greeting": greeting,
    }


@router.get("/morning-ai")
async def morning_briefing_ai(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_captain),
):
    now = datetime.now()
    hour = now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    date_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

    # Pull live metrics to ground the AI in reality
    tenant_id = settings.JARVIS_DEFAULT_TENANT_ID
    from app.services.intelligence.morning_briefing import MorningBriefingEngine
    engine = MorningBriefingEngine()
    try:
        await set_tenant_context(db, str(tenant_id))
        metrics = await engine._collect_metrics(db, _resolve_tenant_id_from_str(str(tenant_id)))
    except Exception:
        metrics = {}

    hot_lead_names = ", ".join(l["company"] for l in metrics.get("hot_leads", [])) or "none identified"
    overdue_list = "; ".join(
        f"{p['client']} ({p['days_overdue']}d overdue)" for p in metrics.get("overdue_proposals", [])
    ) or "none"
    contract_list = ", ".join(
        f"{c['client']} [{c['status']}]" for c in metrics.get("pending_contracts", [])
    ) or "none"

    live_data = f"""
LIVE JARVIS DATA — {date_str}

REVENUE:
- MRR: ${metrics.get('mrr', 0):,.0f}
- Pipeline: ${metrics.get('pipeline', 0):,.0f}
- New leads today: {metrics.get('new_leads', 0)}

PIPELINE INTELLIGENCE:
- Hot leads (score ≥ 60, ready for proposal): {metrics.get('hot_lead_count', 0)} — {hot_lead_names}
- Overdue proposals (sent > 3 days, no response): {metrics.get('overdue_proposal_count', 0)} — {overdue_list}
- Accepted proposals awaiting contract: {metrics.get('accepted_proposals_awaiting_contract', 0)}
- Pending contracts (unsigned): {metrics.get('pending_contract_count', 0)} — {contract_list}
- Executive briefs generated this week: {metrics.get('briefs_this_week', 0)}

OUTREACH:
- Scheduled today: {metrics.get('outreach_count', 0)}
- Replies this week: {metrics.get('reply_count', 0)}
- Top lead: {metrics.get('top_lead_name', 'none')} ({int(metrics.get('top_lead_score', 0))}/100)

ACTIONS PENDING: {metrics.get('pending_approvals', 0)}
""".strip()

    response, _ = await ai_router.chat(
        messages=[Message(role="user", content=f"{greeting} JARVIS. Today is {date_str}.\n\n{live_data}\n\nGenerate the morning briefing.")],
        task_type=TaskType.REASONING,
        system_prompt=BRIEFING_PROMPT,
        max_tokens=1500,
    )

    return {
        "briefing": response.content,
        "metrics": metrics,
        "model": response.model,
        "provider": response.provider,
        "demo": response.demo,
        "generated_at": now.isoformat(),
        "greeting": greeting,
    }


def _resolve_tenant_id_from_str(tenant_str: str) -> UUID:
    try:
        return UUID(str(tenant_str))
    except (ValueError, AttributeError):
        return UUID("794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1")


@router.post("/generate")
async def generate_briefing(request: Request, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_captain)):
    return await morning_briefing(request, db)


@router.get("/status")
async def system_status():
    providers = ai_router.get_provider_status()
    available = [k for k, v in providers.items() if v["available"]]
    return {
        "system": "JARVIS",
        "company": "Aliyar Solutions",
        "status": "operational",
        "ai_providers": {
            "total": len(providers),
            "available": len(available),
            "active": available,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/opportunity-radar")
async def trigger_opportunity_radar(
    bg: BackgroundTasks = None,
    _: dict = Depends(get_current_captain),
) -> dict:
    """Manually trigger the Opportunity Radar — returns idle hot leads immediately."""
    tenant_id = _resolve_tenant_id_from_str(str(settings.JARVIS_DEFAULT_TENANT_ID))
    from app.services.intelligence.opportunity_radar import run_opportunity_radar
    report = await run_opportunity_radar(tenant_id)
    return report


def _resolve_tenant_id(request: Request) -> UUID:
    tenant_id = (
        getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
