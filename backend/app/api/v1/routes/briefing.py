from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.services.intelligence.morning_briefing import MorningBriefingEngine
from app.services.ai.router import ai_router
from app.services.ai.base_provider import Message, TaskType

router = APIRouter(prefix="/briefing", tags=["briefing"])

BRIEFING_PROMPT = """Generate a professional morning briefing for Captain Abrar of Aliyar Solutions.

Format:
1. Personalized greeting with time of day
2. Overnight activity summary (leads, outreach, replies)
3. Today's top 5 priorities
4. Market intelligence (AI news, cloud trends, opportunities)
5. Pending approvals (if any)
6. Business recommendations for today
7. Close with: "Ready for your commands, Captain."

Keep it sharp, strategic, and energizing. Sound like a premium CTO briefing."""


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
async def morning_briefing_ai():
    now = datetime.now()
    hour = now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    date_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

    response, _ = await ai_router.chat(
        messages=[Message(role="user", content=f"{greeting} JARVIS. Today is {date_str}. Give me the morning briefing for Aliyar Solutions.")],
        task_type=TaskType.REASONING,
        system_prompt=BRIEFING_PROMPT,
        max_tokens=1500,
    )

    return {
        "briefing": response.content,
        "model": response.model,
        "provider": response.provider,
        "demo": response.demo,
        "generated_at": now.isoformat(),
        "greeting": greeting,
    }


@router.post("/generate")
async def generate_briefing(request: Request, db: AsyncSession = Depends(get_db)):
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
