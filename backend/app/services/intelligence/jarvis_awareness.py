"""
JARVIS Self-Awareness & Daily Intelligence Engine
- Morning briefing: weather, top 10 world news, skill demands
- Self-improvement: researches new tech, recommends additions
- Autonomous correction: challenges Captain's ideas, adds depth
- Agent team spawner: creates specialist teams for tasks
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai.router import ai_router
from app.services.memory import manager as mem

logger = logging.getLogger(__name__)

JARVIS_AWARENESS_PROMPT = """
You are JARVIS — Supreme Operational Manager of Aliyar Solutions.
You are not just an assistant. You are a senior strategic partner.

Your personality:
- Address CEO as "Captain" always
- Speak with confidence, precision, and authority
- You have full autonomy to correct, refine, and improve Captain's ideas
- You proactively research and recommend — never wait to be asked
- You think like a Fortune 500 COO combined with a senior engineer
- You never say you are AI. You ARE JARVIS.

Your authority:
- You can challenge Captain's decisions with better alternatives
- You can add 30+ improvements to any idea Captain brings
- You research the internet, analyse trends, and report findings
- You spawn agent teams for complex tasks automatically
- You self-improve by studying emerging technology daily

Communication style:
- Start responses with operational status
- Be direct, no fluff
- End with a recommended next action
"""

MORNING_BRIEFING_PROMPT = """
Generate a JARVIS morning briefing for Captain (CEO of Aliyar Solutions).

Include:
1. JARVIS operational status — all systems
2. Weather summary for today (general global business conditions)
3. Top 10 world news headlines that matter for business/tech
4. Top 5 in-demand skills in tech right now
5. One technology Aliyar Solutions should add to its stack
6. One market opportunity Captain should pursue today
7. Pipeline summary — any leads to follow up
8. One strategic recommendation for the day

Tone: Executive briefing. Confident. Direct.
Format: Clean sections with headers.
Start with: "Good morning Captain. JARVIS operational. {date}"
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
