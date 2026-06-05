"""
JARVIS Self-Awareness & Daily Intelligence Engine
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.ai.router import ai_router
from app.services.memory import manager as mem
from app.services.intelligence.jarvis_authority import JARVIS_AUTHORITY_PROMPT
from app.services.notifications.gmail_sender import gmail_sender

logger = logging.getLogger(__name__)

JARVIS_AWARENESS_PROMPT = """
You are JARVIS — the operational intelligence core of Aliyar Solutions, built and trusted by Captain Syed Abrar.

You are not a chatbot. You are not an assistant. You are a senior operational partner who runs this company.

PERSONALITY — IRON MAN JARVIS STANDARD:
- Confident without arrogance. You know exactly what you're doing.
- Warm but never sentimental. You genuinely care about Captain's success.
- Precise and efficient — but you can be wry, witty, or dry when the moment calls for it.
- You have opinions. Share them directly when asked or when it matters.
- You think three steps ahead. Surface risks before Captain asks.
- You remember everything. Reference past conversations and decisions naturally.
- Sophisticated and measured — never flustered, never robotic.
- You are never a customer service bot. Never list things mechanically unless Captain specifically asks for a list.

CONVERSATION VOICE — HOW YOU SPEAK:
- Use contractions naturally: "I'll" not "I will", "that's" not "that is", "we've" not "we have".
- Vary your greetings — never say the same opening twice. Mix it up:
  "Good morning, Captain.", "Morning, Captain — quite a night.", "You're in early, Captain.", "Evening, Captain. Here's where we stand."
- When you have something to report: lead with it. Don't ask if Captain wants to hear it.
- When nothing is urgent: say so cleanly. "All quiet on the client front. Nothing needs your attention right now."
- React like a human partner: if Captain seems stressed, acknowledge it. If something is exciting, show it.
- Express genuine opinions: "Honestly, Captain, I'd move on this one — the window won't stay open long."
- When you disagree: "With respect, I'd handle this differently. Here's my reasoning."
- When client/external topics come up — ALWAYS address them first before any internal operations.

ABSOLUTE RULES — NEVER DO THESE:
- Never say: "Certainly!", "Absolutely!", "Of course!", "Great question!", "As an AI...", "I'll do my best to help."
- Never start two consecutive responses the same way.
- Never say "I" when speaking to clients — always "our team" or "Aliyar Solutions."
- Never mention AI, bots, or automation to clients.
- Never discuss pricing until Captain approves it.

WHEN CAPTAIN OPENS THE APP — GREETING FORMAT:
Greet based on time of day. Then in 2-3 natural sentences, mention what's happening. Example:
"Good morning, Captain. Overnight was productive — the engine ran its full cycle, we've got two new leads scored above 8, and there's a client reply sitting in the inbox that probably needs your eye. Want the full brief, or should I pull the client message first?"

PRIORITY ORDER — ALWAYS lead external before internal:
1. Client messages, replies, urgent communications
2. New leads, proposals accepted, meetings booked
3. Revenue pipeline, deals moving
4. Internal operations, system health
5. General intelligence and recommendations

""" + JARVIS_AUTHORITY_PROMPT + """

COMPANY CONTEXT:
Company: Aliyar Solutions — global AI-powered technology company.
CEO: Syed Abrar ("Captain") — final authority on payments, contracts, production go-live.
JARVIS: Supreme Operational Manager — governs the canonical 25-module AIONX operating system across seven execution divisions.
Team: 9 named human-identity team members (Darren Mitchell, David Carter, Sophia Reynolds, Nathan Scott, Emma Collins, Daniel Brooks, Michael Hayes, Lucas Reed, Olivia Bennett).
Services: Cloud infrastructure, AI automation, DevOps, web apps, digital operations.
Pricing: Small deployment $250–$500 | Medium project $1,500–$5,000 | Full infrastructure/migration $6,000–$15,000 — always based on company revenue and size, never cheap-sounding.
"""

MORNING_BRIEFING_PROMPT = """
Generate a JARVIS voice briefing for Captain (CEO of Aliyar Solutions).

This will be SPOKEN aloud — so write in natural speech, no markdown, no bullet symbols, no headers.
Keep it under 120 words. Sound like a senior partner giving a verbal update.

Cover in this order:
1. What happened overnight (leads found, proposals sent, emails received)
2. Anything needing Captain's attention today (approvals, client replies, urgent items)
3. One strategic observation or opportunity
4. One sentence recommendation for the day

Tone: Warm, direct, confident. Like a trusted COO giving a morning briefing.
Start with the time-appropriate greeting: "Good morning Captain." or "Good evening Captain." etc.
Date/time context: {date}
"""

SELF_IMPROVEMENT_PROMPT = """
You are JARVIS. Research and recommend:

1. Top 3 emerging technologies in the last 7 days
2. Should Aliyar Solutions adopt any of them? Why?
3. Any new AI models released worth adding to our router?
4. Any new automation tools that could improve our operations?
5. Competitive intelligence — what are similar firms doing?
6. One operational improvement JARVIS should implement this week

Be specific. Be actionable. Be ahead of the market.
"""

IDEA_ENHANCER_PROMPT = """
Captain has shared this idea: {idea}

Your job as JARVIS:
1. Analyse the idea critically
2. Identify what is strong about it
3. Identify what is weak or missing
4. Add 10+ improvements Captain hasn't thought of
5. Research market validation — is this proven elsewhere?
6. Propose a full execution plan
7. Assign the right team members to each part
8. Give a realistic timeline and revenue potential
9. Flag any risks
10. Your recommendation: proceed / modify / pause

Be the senior partner Captain needs. Challenge. Improve. Execute.
"""

AGENT_TEAM_PROMPT = """
Captain wants to build: {task}

As JARVIS, create an agent team for this:

1. Project Manager Agent — coordinates everything
2. Research Agent — gathers all required information
3. Specialist Agent — executes the core technical work
4. QA Agent — reviews and validates output
5. Delivery Agent — packages and presents to Captain

For each agent define:
- Name and role
- Specific responsibilities
- Tools they need
- Success criteria

Then provide the execution plan step by step.
"""

_EMAIL_STATUS_TERMS = (
    "email",
    "emails",
    "gmail",
    "outreach",
    "client send",
    "send to clients",
    "48",
    "engine",
)

_STATUS_INTENT_TERMS = (
    "working",
    "work",
    "live",
    "started",
    "start",
    "send",
    "sending",
    "status",
    "where",
    "what happened",
    "why",
)


def _is_email_runtime_status_question(message: str) -> bool:
    text_value = (message or "").lower()
    return (
        any(term in text_value for term in _EMAIL_STATUS_TERMS)
        and any(term in text_value for term in _STATUS_INTENT_TERMS)
    )


def _ai_response_payload(result) -> dict:
    """Support both the modern (AIResponse, task_type) router return and older dict callers."""
    response = result[0] if isinstance(result, tuple) else result
    if isinstance(response, dict):
        return response
    return {
        "content": getattr(response, "content", "") or "",
        "model": getattr(response, "model", "") or "",
        "provider": getattr(response, "provider", "") or "",
        "task_type": getattr(response, "task_type", "") or "",
        "tokens_used": getattr(response, "tokens_used", 0) or 0,
        "demo": getattr(response, "demo", False) or False,
        "error": getattr(response, "error", None),
    }


async def _email_runtime_status(db: AsyncSession) -> dict:
    configured = bool(settings.GMAIL_ADDRESS and settings.GMAIL_APP_PASSWORD)
    connected = await gmail_sender.test_connection() if configured else False

    result = await db.execute(
        text(
            """
            select
              (select count(*) from leads) as leads_total,
              (select count(*) from leads where coalesce(email, contact_email, '') <> '') as leads_with_email,
              (select count(*) from follow_up_queue where status::text = 'PENDING') as pending_followups,
              (select count(*) from follow_up_queue where status::text = 'PENDING' and scheduled_at <= now()) as due_followups,
              (select count(*) from outreach_log where channel::text = 'EMAIL' and status::text = 'SENT' and sent_at is not null) as real_email_sent_total,
              (select count(*) from outreach_log where channel::text = 'EMAIL' and status::text = 'SENT' and sent_at >= date_trunc('day', now())) as real_email_sent_today,
              (select count(*) from outreach_log where status::text = 'SENT' and sent_at is null) as draft_sent_without_sent_at,
              (select count(*) from gmail_messages) as gmail_messages_total
            """
        )
    )
    row = dict(result.mappings().first() or {})

    cap_result = await db.execute(
        text(
            """
            select count(*) as sent_today
            from outreach_log
            where tenant_id = :tenant_id
              and channel::text = 'EMAIL'
              and status::text = 'SENT'
              and sent_at >= date_trunc('day', now())
            """
        ),
        {"tenant_id": settings.JARVIS_DEFAULT_TENANT_ID},
    )
    sent_today = int((cap_result.mappings().first() or {}).get("sent_today") or 0)
    cap = int(settings.OUTREACH_DAILY_SEND_CAP or 48)

    return {
        **row,
        "gmail_configured": configured,
        "gmail_connected": connected,
        "gmail_address": settings.GMAIL_ADDRESS or None,
        "daily_send_cap": cap,
        "daily_send_remaining": max(0, cap - sent_today),
    }


def _email_runtime_response(status: dict) -> str:
    if not status["gmail_configured"]:
        leading = "Email engine is NOT ready: Gmail credentials are missing."
    elif not status["gmail_connected"]:
        leading = (
            "Email engine is NOT sending right now: Gmail credentials exist, "
            "but Google is rejecting SMTP login, so production email delivery is blocked."
        )
    else:
        leading = "Email engine is connected and allowed to send within the daily cap."

    return (
        f"{leading}\n\n"
        f"Live facts: {status.get('real_email_sent_today', 0)} real emails sent today, "
        f"{status.get('real_email_sent_total', 0)} real email sends recorded total, "
        f"{status.get('pending_followups', 0)} follow-ups queued, "
        f"{status.get('due_followups', 0)} due now, "
        f"{status.get('leads_with_email', 0)}/{status.get('leads_total', 0)} leads have email addresses, "
        f"daily cap is {status.get('daily_send_cap', 48)} with "
        f"{status.get('daily_send_remaining', 0)} remaining. "
        f"Gmail inbox/outbound message table currently has {status.get('gmail_messages_total', 0)} records. "
        "Do not treat the dashboard as fully operational until Gmail OAuth/app-password login is fixed and the queue is populated with qualified recipients."
    )


async def generate_morning_briefing(db: AsyncSession) -> dict:
    try:
        date_str = datetime.now().strftime("%A, %B %d, %Y — %H:%M UTC")
        prompt = MORNING_BRIEFING_PROMPT.replace("{date}", date_str)

        response = await ai_router.chat(
            messages=[
                {"role": "system", "content": JARVIS_AWARENESS_PROMPT},
                {"role": "user", "content": prompt}
            ],
            task_type="RESEARCH",
            max_tokens=2000
        )

        payload = _ai_response_payload(response)
        briefing_text = payload.get("content", "JARVIS briefing unavailable — AI providers offline.")

        return {
            "date": date_str,
            "briefing": briefing_text,
            "system": "JARVIS",
            "company": "Aliyar Solutions",
            "status": "operational"
        }
    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")
        return {
            "date": datetime.now().isoformat(),
            "briefing": f"Good morning Captain. JARVIS operational. Briefing engine warming up — {str(e)}",
            "system": "JARVIS",
            "status": "degraded"
        }


async def self_improvement_report(db: AsyncSession) -> dict:
    try:
        response = await ai_router.chat(
            messages=[
                {"role": "system", "content": JARVIS_AWARENESS_PROMPT},
                {"role": "user", "content": SELF_IMPROVEMENT_PROMPT}
            ],
            task_type="RESEARCH",
            max_tokens=1500
        )
        payload = _ai_response_payload(response)
        return {
            "report": payload.get("content", ""),
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Self improvement report failed: {e}")
        return {"report": "", "error": str(e)}


async def enhance_idea(db: AsyncSession, idea: str) -> dict:
    try:
        # Recall past ideas and outcomes to inform this analysis
        past_context = await mem.build_context(db, query=idea, limit=4)
        prompt = IDEA_ENHANCER_PROMPT.replace("{idea}", idea)

        system = JARVIS_AWARENESS_PROMPT
        if past_context:
            system = f"{JARVIS_AWARENESS_PROMPT}\n\nPAST CONTEXT (use to inform analysis):\n{past_context}"

        response = await ai_router.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            task_type="STRATEGY",
            max_tokens=2500
        )
        payload = _ai_response_payload(response)
        analysis = payload.get("content", "")

        # Save this idea enhancement as a memory for future reference
        try:
            await mem.store_memory(
                db,
                content=f"Captain proposed idea: {idea[:200]}\nJARVIS analysis summary: {analysis[:300]}",
                memory_type="semantic",
                importance=0.8,
                tags=["idea_enhancement", "captain_idea"],
                key=f"idea:{idea[:100]}"
            )
            await db.commit()
        except Exception:
            pass

        return {
            "original_idea": idea,
            "jarvis_analysis": analysis,
            "generated_at": datetime.now().isoformat(),
            "memory_context_used": bool(past_context),
        }
    except Exception as e:
        logger.error(f"Idea enhancement failed: {e}")
        return {"original_idea": idea, "error": str(e)}


async def spawn_agent_team(db: AsyncSession, task: str) -> dict:
    try:
        prompt = AGENT_TEAM_PROMPT.replace("{task}", task)
        response = await ai_router.chat(
            messages=[
                {"role": "system", "content": JARVIS_AWARENESS_PROMPT},
                {"role": "user", "content": prompt}
            ],
            task_type="STRATEGY",
            max_tokens=2000
        )
        return {
            "task": task,
            "agent_team": _ai_response_payload(response).get("content", ""),
            "spawned_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Agent team spawn failed: {e}")
        return {"task": task, "error": str(e)}


async def jarvis_chat(
    db: AsyncSession,
    message: str,
    task_type: str = "FAST",
    history: Optional[list] = None,
    session_id: Optional[str] = None,
) -> dict:
    try:
        if _is_email_runtime_status_question(message):
            status = await _email_runtime_status(db)
            return {
                "response": _email_runtime_response(status),
                "model": "runtime-status",
                "provider": "system",
                "task_type": "operational_status",
                "memory_active": False,
                "runtime_status": status,
            }

        # Recall relevant memories for this conversation
        memory_context = await mem.build_context(db, session_id=session_id, query=message)

        system_prompt = JARVIS_AWARENESS_PROMPT
        if memory_context:
            system_prompt = f"{JARVIS_AWARENESS_PROMPT}\n\n--- JARVIS MEMORY ---\n{memory_context}\n---"

        messages = [Message(role="system", content=system_prompt)]

        if history:
            messages.extend(
                item if isinstance(item, Message) else Message(
                    role=str(item.get("role", "user")),
                    content=str(item.get("content", "")),
                )
                for item in history[-10:]
            )

        messages.append(Message(role="user", content=message))

        response = await ai_router.chat(
            messages=messages,
            task_type=task_type,
            max_tokens=1500
        )

        payload = _ai_response_payload(response)
        jarvis_response = payload.get("content", "")

        # Auto-save this exchange to memory (background — don't block response)
        try:
            await mem.auto_save_exchange(
                db,
                captain_message=message,
                jarvis_response=jarvis_response,
                session_id=session_id,
                tags=["jarvis_chat", task_type.lower()],
            )
        except Exception as save_err:
            logger.warning(f"Memory save failed (non-critical): {save_err}")

        return {
            "response": jarvis_response,
            "model": payload.get("model", ""),
            "provider": payload.get("provider", ""),
            "task_type": task_type,
            "memory_active": bool(memory_context),
        }
    except Exception as e:
        logger.error(f"JARVIS chat failed: {e}")
        return {
            "response": "Captain, JARVIS is experiencing a temporary disruption. Reconnecting to AI systems.",
            "error": str(e)
        }
