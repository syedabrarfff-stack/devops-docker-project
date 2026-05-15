"""
JARVIS Self-Awareness & Daily Intelligence Engine
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai.router import ai_router
from app.services.memory import manager as mem
from app.services.intelligence.jarvis_authority import JARVIS_AUTHORITY_PROMPT

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
JARVIS: Supreme Operational Manager — runs all 40 agents across 10 teams.
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

        briefing_text = response.get("content", "JARVIS briefing unavailable — AI providers offline.")

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
        return {
            "report": response.get("content", ""),
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
        analysis = response.get("content", "")

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
            "agent_team": response.get("content", ""),
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
        # Recall relevant memories for this conversation
        memory_context = await mem.build_context(db, session_id=session_id, query=message)

        system_prompt = JARVIS_AWARENESS_PROMPT
        if memory_context:
            system_prompt = f"{JARVIS_AWARENESS_PROMPT}\n\n--- JARVIS MEMORY ---\n{memory_context}\n---"

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend(history[-10:])

        messages.append({"role": "user", "content": message})

        response = await ai_router.chat(
            messages=messages,
            task_type=task_type,
            max_tokens=1500
        )

        jarvis_response = response.get("content", "")

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
            "model": response.get("model", ""),
            "provider": response.get("provider", ""),
            "task_type": task_type,
            "memory_active": bool(memory_context),
        }
    except Exception as e:
        logger.error(f"JARVIS chat failed: {e}")
        return {
            "response": "Captain, JARVIS is experiencing a temporary disruption. Reconnecting to AI systems.",
            "error": str(e)
        }
