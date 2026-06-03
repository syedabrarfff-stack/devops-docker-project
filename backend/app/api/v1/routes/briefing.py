from fastapi import APIRouter
from datetime import datetime
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
async def morning_briefing():
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
async def generate_briefing():
    return await morning_briefing()


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
