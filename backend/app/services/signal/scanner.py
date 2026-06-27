"""
JARVIS SIGNAL — AI Pipeline Intelligence Scanner.

For every lead in the CRM, SIGNAL uses Claude to:
  - Infer purchase intent signals from industry, pain points, and company profile
  - Generate a signal score (0-100) representing likelihood to buy now
  - Identify the optimal team persona and outreach timing
  - Produce a one-line "why now" reason

The daily pipeline brief is an AI-generated executive summary:
  - Top opportunities ranked by signal strength
  - Market context relevant to the pipeline
  - Specific recommended action per lead

All analysis is streamed via SSE so the Captain sees intelligence appear in real time.
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# ── Prompt templates ───────────────────────────────────────────────────────────

_SIGNAL_PROMPT = """You are JARVIS — the AI intelligence core of Aliyar Solutions, a global technology company.

Your task: analyse this CRM lead and produce a structured signal assessment.

LEAD DATA:
Company: {company}
Contact: {contact}
Industry: {industry}
Country: {country}
Pain Points: {pain_points}
Lead Score: {score}/100
Status: {status}
Outreach Count: {outreach_count}
Notes: {notes}

ALIYAR SOLUTIONS SERVICES: AI Automation & Workflows · Cloud & AWS Infrastructure · DevOps & CI/CD ·
Cybersecurity · Analytics & Business Intelligence · CRM & Revenue Operations · Web Applications ·
Digital Transformation · API Integrations · Enterprise Architecture · Process Automation

ANALYSIS INSTRUCTIONS:
1. Infer what business pressures this company likely faces right now based on industry and profile.
2. Identify 2-5 specific buying signals (things that suggest they are ready or motivated to buy NOW).
3. Assess purchase intent: how likely is this company to convert to a client in the next 30 days?
4. Recommend which Aliyar team member should contact them and WHY.
5. Generate a ONE-SENTENCE "why now" reason — the key insight that makes this a priority.

Respond ONLY in this exact JSON format (no markdown, no preamble):
{{
  "signal_score": <integer 0-100>,
  "intent_tier": "<HOT|WARM|COOL|COLD>",
  "signals": [
    "<specific buying signal 1>",
    "<specific buying signal 2>",
    "<specific buying signal 3>"
  ],
  "why_now": "<one compelling sentence — the urgency trigger>",
  "recommended_persona": "<exact name from: Darren Mitchell, David Carter, Sophia Reynolds, Nathan Scott, Emma Collins, Daniel Brooks, Michael Hayes, Lucas Reed, Olivia Bennett>",
  "persona_reason": "<one sentence why this persona is best>",
  "recommended_tone": "<professional|warm|direct>",
  "risk_flags": ["<any red flags that reduce confidence>"],
  "confidence": <integer 0-100>
}}"""

_BRIEF_PROMPT = """You are JARVIS, Supreme Operational Manager of Aliyar Solutions.

You have just completed a signal scan of the active lead pipeline. Here are the results:

{pipeline_summary}

Generate an executive pipeline intelligence brief for Captain (Syed Abrar, CEO).

BRIEF REQUIREMENTS:
- Start with a 2-sentence situational overview of today's pipeline
- List the TOP 5 leads to engage TODAY — ranked by signal strength + urgency
  - For each: company name, intent tier, why now, recommended action (which persona + what to do)
- Identify any patterns across the pipeline (e.g. "3 SaaS companies showing cloud migration signals")
- End with one strategic recommendation for the day

TONE: Direct, operational, executive-level. No fluff. This is an internal briefing.
CAPTAIN TITLE: Address CEO as "Captain"
LENGTH: 350-500 words

Start writing immediately. No preamble like "Here is the brief" — just the content."""


# ── Single lead signal scan ────────────────────────────────────────────────────

async def scan_lead(lead: dict) -> dict:
    """Run AI signal analysis on one lead. Returns signal dict."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_signal(lead)

    pain_str = (
        ", ".join(str(p) for p in lead.get("pain_points") or [])
        if isinstance(lead.get("pain_points"), list)
        else str(lead.get("pain_points") or "unknown")
    )

    prompt = _SIGNAL_PROMPT.format(
        company=lead.get("company_name") or lead.get("company") or "Unknown",
        contact=lead.get("contact_name") or "Unknown",
        industry=lead.get("industry") or "Unknown",
        country=lead.get("country") or "Unknown",
        pain_points=pain_str or "not specified",
        score=lead.get("score") or 0,
        status=lead.get("status") or "NEW",
        outreach_count=lead.get("outreach_count") or 0,
        notes=lead.get("notes") or "none",
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip() if msg.content else "{}"
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            raw = raw.rsplit("```", 1)[0].strip()
        signal = json.loads(raw)
        signal["lead_id"] = str(lead.get("id") or "")
        signal["lead_company"] = lead.get("company_name") or lead.get("company") or "—"
        signal["lead_contact"] = lead.get("contact_name") or ""
        signal["lead_email"] = lead.get("email") or ""
        signal["lead_industry"] = lead.get("industry") or ""
        signal["lead_score"] = float(lead.get("score") or 0)
        signal["lead_status"] = lead.get("status") or "NEW"
        signal["lead_country"] = lead.get("country") or ""
        signal["lead_pain_points"] = lead.get("pain_points") or []
        return signal
    except Exception as exc:
        logger.error("Signal scan failed for %s: %s", lead.get("company_name"), exc)
        return {**_fallback_signal(lead), "error": str(exc)}


def _fallback_signal(lead: dict) -> dict:
    score = float(lead.get("score") or 0)
    tier = "HOT" if score >= 75 else "WARM" if score >= 50 else "COOL" if score >= 25 else "COLD"
    return {
        "lead_id": str(lead.get("id") or ""),
        "lead_company": lead.get("company_name") or lead.get("company") or "—",
        "lead_contact": lead.get("contact_name") or "",
        "lead_email": lead.get("email") or "",
        "lead_industry": lead.get("industry") or "",
        "lead_score": score,
        "lead_status": lead.get("status") or "NEW",
        "lead_country": lead.get("country") or "",
        "lead_pain_points": lead.get("pain_points") or [],
        "signal_score": int(score),
        "intent_tier": tier,
        "signals": ["Profile data available", "CRM score indicates potential"],
        "why_now": "Lead meets baseline qualification criteria.",
        "recommended_persona": "Darren Mitchell",
        "persona_reason": "Default assignment — run full scan for optimal routing.",
        "recommended_tone": "professional",
        "risk_flags": [],
        "confidence": 40,
    }


# ── SSE: scan a single lead ───────────────────────────────────────────────────

async def scan_lead_stream(lead: dict) -> AsyncIterator[str]:
    """SSE stream: emits start → result → done for one lead."""
    yield "data: " + json.dumps({
        "type": "scan_start",
        "lead_id": str(lead.get("id") or ""),
        "company": lead.get("company_name") or lead.get("company"),
    }) + "\n\n"

    result = await scan_lead(lead)

    yield "data: " + json.dumps({"type": "scan_result", "signal": result}) + "\n\n"
    yield "data: " + json.dumps({"type": "done"}) + "\n\n"


# ── SSE: scan full pipeline ───────────────────────────────────────────────────

async def scan_pipeline_stream(
    leads: list[dict],
    on_result=None,
) -> AsyncIterator[str]:
    """
    SSE stream: scans every lead and emits each result as it completes.
    Protocol:
      data: {"type":"pipeline_start","total":N}
      data: {"type":"scan_result","signal":{...},"done":N,"total":N}
      ...
      data: {"type":"pipeline_complete","results":[...]}
      data: {"type":"done"}
    """
    import asyncio

    total = len(leads)
    yield "data: " + json.dumps({"type": "pipeline_start", "total": total}) + "\n\n"

    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    results: list[dict] = []
    counter = {"n": 0}

    async def scan_one(lead: dict) -> None:
        result = await scan_lead(lead)
        counter["n"] += 1
        results.append(result)
        await queue.put({"type": "scan_result", "signal": result, "done": counter["n"], "total": total})

    async def run_all() -> None:
        await asyncio.gather(*[scan_one(l) for l in leads])
        await queue.put(None)

    task = asyncio.create_task(run_all())

    while True:
        event = await queue.get()
        if event is None:
            break
        yield "data: " + json.dumps(event, default=str) + "\n\n"

    await task
    # Sort by signal_score descending
    results.sort(key=lambda r: r.get("signal_score", 0), reverse=True)
    yield "data: " + json.dumps({"type": "pipeline_complete", "results": results}) + "\n\n"
    yield "data: " + json.dumps({"type": "done"}) + "\n\n"


# ── SSE: generate intelligence brief ─────────────────────────────────────────

async def generate_brief_stream(signals: list[dict]) -> AsyncIterator[str]:
    """
    Stream the AI-generated pipeline intelligence brief token by token.
    Protocol:
      data: {"type":"start"}
      data: {"type":"token","text":"..."}
      ...
      data: {"type":"complete","full_text":"..."}
      data: {"type":"done"}
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield "data: " + json.dumps({"type": "error", "message": "ANTHROPIC_API_KEY not configured"}) + "\n\n"
        return

    # Build pipeline summary for the prompt
    top = sorted(signals, key=lambda s: s.get("signal_score", 0), reverse=True)[:10]
    lines = []
    for i, s in enumerate(top, 1):
        lines.append(
            f"{i}. {s.get('lead_company', '—')} [{s.get('intent_tier', '?')}] "
            f"Signal: {s.get('signal_score', 0)}/100 · "
            f"Industry: {s.get('lead_industry', '?')} · "
            f"Why now: {s.get('why_now', '?')} · "
            f"Persona: {s.get('recommended_persona', '?')}"
        )
    summary = "\n".join(lines) if lines else "No signals available."

    prompt = _BRIEF_PROMPT.format(pipeline_summary=summary)

    yield "data: " + json.dumps({"type": "start", "leads_analysed": len(signals)}) + "\n\n"

    full_text = ""
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for token in stream.text_stream:
                full_text += token
                yield "data: " + json.dumps({"type": "token", "text": token}) + "\n\n"
    except Exception as exc:
        logger.error("Brief generation error: %s", exc)
        yield "data: " + json.dumps({"type": "error", "message": str(exc)}) + "\n\n"
        return

    yield "data: " + json.dumps({"type": "complete", "full_text": full_text}) + "\n\n"
    yield "data: " + json.dumps({"type": "done"}) + "\n\n"
