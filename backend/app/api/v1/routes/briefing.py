from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.approval import ApprovalRequest
from app.models.lead import Lead
from app.models.outreach import OutreachEmail, OutreachSequence
from app.models.tasks import AgentTask
from app.models.team_member import TeamMember
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


@router.get("/activity")
async def activity_briefing(db: AsyncSession = Depends(get_db)):
    """Return a natural, voice-first operations briefing for Captain."""
    now = datetime.now()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"

    async def count(model, *filters) -> int:
        query = select(func.count()).select_from(model)
        for condition in filters:
            query = query.where(condition)
        return int(await db.scalar(query) or 0)

    active_team = await count(TeamMember, TeamMember.is_active.is_(True))
    total_leads = await count(Lead)
    new_leads = await count(Lead, Lead.status == "new")
    qualified_leads = await count(Lead, Lead.status == "qualified")
    contacted_leads = await count(Lead, Lead.outreach_sent.is_(True))
    active_sequences = await count(OutreachSequence, OutreachSequence.status == "active")
    drafted_or_scheduled = await count(OutreachEmail, OutreachEmail.status.in_(["draft", "scheduled"]))
    sent_emails = await count(OutreachEmail, OutreachEmail.status == "sent")
    replies = await count(OutreachEmail, OutreachEmail.status == "replied")
    pending_approvals = await count(ApprovalRequest, ApprovalRequest.status == "pending")
    running_tasks = await count(AgentTask, AgentTask.status == "running")
    queued_tasks = await count(AgentTask, AgentTask.status == "queued")
    completed_tasks = await count(AgentTask, AgentTask.status == "completed")

    latest_tasks_result = await db.execute(
        select(AgentTask)
        .order_by(AgentTask.created_at.desc())
        .limit(3)
    )
    latest_tasks = [
        {
            "title": task.title,
            "assigned_to": task.assigned_to,
            "status": task.status,
            "task_type": task.task_type,
        }
        for task in latest_tasks_result.scalars().all()
    ]

    highlights = []
    if drafted_or_scheduled:
        highlights.append(f"Outreach has {drafted_or_scheduled} email messages drafted or scheduled for review.")
    if new_leads or qualified_leads:
        highlights.append(f"Lead generation is holding {new_leads} new leads and {qualified_leads} qualified leads.")
    if pending_approvals:
        highlights.append(f"There are {pending_approvals} approval items waiting for your decision.")
    if running_tasks or queued_tasks:
        highlights.append(f"The task queue has {running_tasks} running item and {queued_tasks} queued items.")
    if not highlights:
        highlights.append("No urgent production items are waiting; the system is steady and ready for the next command.")

    spoken = (
        f"{greeting}, Captain. I can brief you now. "
        f"The team registry has {active_team} active specialists online. "
        f"Across growth, we have {total_leads} leads in the system, including {new_leads} new and {qualified_leads} qualified. "
        f"Outreach has {active_sequences} active sequences, {drafted_or_scheduled} messages drafted or scheduled, "
        f"{sent_emails} sent, and {replies} replies recorded. "
        f"Operations shows {running_tasks} running task, {queued_tasks} queued tasks, and {completed_tasks} completed tasks. "
        f"Approvals waiting for you: {pending_approvals}. "
        f"{' '.join(highlights)} "
        "Shall I open the detailed briefing panel or continue with the next command?"
    )

    return {
        "greeting": greeting,
        "generated_at": now.isoformat(),
        "spoken": spoken,
        "summary": {
            "active_team": active_team,
            "leads": {
                "total": total_leads,
                "new": new_leads,
                "qualified": qualified_leads,
                "contacted": contacted_leads,
            },
            "outreach": {
                "active_sequences": active_sequences,
                "drafted_or_scheduled": drafted_or_scheduled,
                "sent": sent_emails,
                "replies": replies,
            },
            "tasks": {
                "running": running_tasks,
                "queued": queued_tasks,
                "completed": completed_tasks,
                "latest": latest_tasks,
            },
            "pending_approvals": pending_approvals,
        },
        "highlights": highlights,
    }


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
