"""
JARVIS GHOST — AI-powered outreach composition engine.

Auto-selects the optimal team persona from lead data (industry, pain points),
builds hyper-personalised cold emails using Claude Opus, and streams text
token-by-token via SSE for a live "AI typing" effect in the browser.
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

from app.services.team.team_service import TEAM_SEED

logger = logging.getLogger(__name__)

# ── Persona → keyword routing ──────────────────────────────────────────────────

_ROUTING: list[dict] = [
    {
        "persona": "David Carter",
        "keywords": [
            "cloud", "aws", "azure", "gcp", "kubernetes", "k8s", "infrastructure",
            "servers", "hosting", "migration", "scalability", "multi-cloud", "saas deployment",
        ],
        "weight": 10,
    },
    {
        "persona": "Sophia Reynolds",
        "keywords": [
            "automation", "ai", "artificial intelligence", "workflow", "appointment",
            "scheduling", "voice", "chatbot", "lead nurturing", "crm", "repetitive",
            "manual process", "efficiency", "bottleneck", "time-consuming",
        ],
        "weight": 10,
    },
    {
        "persona": "Nathan Scott",
        "keywords": [
            "ci/cd", "pipeline", "docker", "terraform", "jenkins", "ansible",
            "release", "staging", "production", "devops", "deploy",
        ],
        "weight": 9,
    },
    {
        "persona": "Emma Collins",
        "keywords": [
            "analytics", "revenue", "kpi", "reporting", "dashboard", "data",
            "business intelligence", "roi", "metrics", "insights", "growth", "forecasting",
        ],
        "weight": 9,
    },
    {
        "persona": "Daniel Brooks",
        "keywords": [
            "security", "compliance", "gdpr", "hipaa", "vulnerability", "penetration",
            "audit", "cyber", "breach", "risk", "data protection", "sox",
        ],
        "weight": 9,
    },
    {
        "persona": "Michael Hayes",
        "keywords": [
            "architecture", "enterprise", "system design", "technology roadmap",
            "digital transformation", "modernisation", "modernization", "platform", "strategy",
        ],
        "weight": 8,
    },
    {
        "persona": "Lucas Reed",
        "keywords": [
            "integration", "api", "zapier", "make", "n8n", "crm integration",
            "erp", "webhook", "connector", "sync", "automation ops",
        ],
        "weight": 8,
    },
    {
        "persona": "Olivia Bennett",
        "keywords": [
            "onboarding", "client success", "account", "retention", "support",
            "relationship", "customer", "satisfaction", "upsell",
        ],
        "weight": 7,
    },
    {
        "persona": "Darren Mitchell",
        "keywords": [
            "sales", "leads", "outreach", "cold email", "pipeline", "growth",
            "acquisition", "prospect", "deals", "revenue growth",
        ],
        "weight": 6,
    },
]

_PERSONA_BY_NAME: dict[str, dict] = {p["name"]: p for p in TEAM_SEED}

_TONE_GUIDE: dict[str, str] = {
    "professional": (
        "Tone: formal, confident, enterprise-grade. "
        "No contractions. Sound like a senior executive speaking to a peer. "
        "Every sentence must earn its place."
    ),
    "warm": (
        "Tone: friendly, human, conversational. Use contractions naturally. "
        "Sound like a knowledgeable colleague who genuinely wants to help, not sell. "
        "One small observation that proves you read their situation."
    ),
    "direct": (
        "Tone: blunt, value-first, no fluff. Maximum 4 sentences in the body. "
        "State the problem, state the fix, state the ask. Nothing else."
    ),
}

_EMAIL_CONTEXT: dict[int, str] = {
    1: (
        "This is email 1 of the sequence — the cold introduction. "
        "Briefly establish credibility, acknowledge a specific problem the prospect likely faces, "
        "present one concise value proposition, and end with a single soft CTA "
        "(a question or an offer for a short call)."
    ),
    2: (
        "This is email 2 — the first follow-up, sent 3 days after email 1. "
        "Reference your previous message briefly without being pushy. "
        "Add one new insight, stat, or angle not in email 1. Keep it shorter than the first email."
    ),
    3: (
        "This is email 3 — the final touch, sent 7 days after email 1. "
        "Very short. Give them an easy out if timing is wrong, but leave a memorable impression. "
        "No pressure — just a clean, professional close to the sequence."
    ),
}


# ── Public helpers ─────────────────────────────────────────────────────────────

def auto_select_persona(industry: str | None, pain_points: list | str | None) -> str:
    """Score every persona against the lead's data and return the best match name."""
    parts = [str(industry or "").lower()]
    if isinstance(pain_points, list):
        parts.extend(str(p).lower() for p in pain_points)
    elif pain_points:
        parts.append(str(pain_points).lower())
    text = " ".join(parts)

    if not text.strip():
        return "Darren Mitchell"

    scores: dict[str, int] = {}
    for rule in _ROUTING:
        hits = sum(1 for kw in rule["keywords"] if kw in text)
        if hits:
            pname = rule["persona"]
            scores[pname] = scores.get(pname, 0) + hits * rule["weight"]

    return max(scores, key=scores.get) if scores else "Darren Mitchell"


def get_persona(name: str) -> dict | None:
    return _PERSONA_BY_NAME.get(name)


def all_persona_names() -> list[str]:
    return [p["name"] for p in TEAM_SEED if p.get("is_active")]


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(
    lead: dict,
    persona: dict,
    tone: str,
    email_num: int,
    total: int,
) -> str:
    company = lead.get("company_name") or lead.get("company") or "their organisation"
    contact = lead.get("contact_name") or "the decision-maker"
    industry = lead.get("industry") or "their sector"
    country = lead.get("country") or ""
    pain_points = lead.get("pain_points") or []
    pain_str = (
        ", ".join(str(p) for p in pain_points) if isinstance(pain_points, list) and pain_points
        else str(pain_points) if pain_points
        else "operational inefficiencies"
    )
    notes = lead.get("notes") or ""
    score = float(lead.get("score") or 0)

    tone_instr = _TONE_GUIDE.get(tone, _TONE_GUIDE["professional"])
    email_ctx = _EMAIL_CONTEXT.get(email_num, _EMAIL_CONTEXT[1])

    specs = ", ".join((persona.get("specializations") or [])[:4])
    kws = ", ".join(persona.get("tone_keywords") or [])
    sig = persona.get("email_signature") or (
        f"{persona['name']}\n{persona['role']}\nAliyar Solutions"
    )

    sequence_note = (
        f"This is email {email_num} of {total} in a cold outreach sequence. "
        if total > 1 else ""
    )

    return f"""You are {persona['name']}, a {persona['role']} at Aliyar Solutions ({persona['department']}).
Your specialisations: {specs}.
Your natural tone: {kws}.

ABSOLUTE RULES:
- Write as a real human expert — NEVER hint at AI, bots, or automation infrastructure
- NEVER say "I am an AI", "our AI", "automated", "machine-generated", or similar
- Always reference "our team", "we", "Aliyar Solutions" — not "I alone"
- Avoid generic openers ("I hope this finds you well", "My name is…")
- NEVER be generic — tie every sentence to {company}'s specific situation

{tone_instr}

{sequence_note}{email_ctx}

LEAD INTELLIGENCE:
- Company: {company}
- Contact: {contact}
- Industry: {industry}
{f"- Location: {country}" if country else ""}
- Key pain points: {pain_str}
{f"- Additional context: {notes}" if notes else ""}
- Lead quality score: {score:.0f}/100

OUTPUT FORMAT (strict):
Subject: [compelling subject — max 8 words, no clickbait, no questions marks as gimmicks]

[email body — 3 to 6 sentences, no more]

{sig}

Output ONLY the email. Start with "Subject:". No preamble, no commentary, no explanation."""


# ── SSE streaming composer ─────────────────────────────────────────────────────

async def ghost_stream(
    lead: dict,
    persona: dict,
    tone: str = "professional",
    email_num: int = 1,
    total: int = 1,
) -> AsyncIterator[str]:
    """Async generator yielding SSE strings — streams Claude token by token."""
    import anthropic  # lazy import

    prompt = _build_prompt(lead, persona, tone, email_num, total)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield "data: " + json.dumps({"type": "error", "message": "ANTHROPIC_API_KEY not configured"}) + "\n\n"
        return

    yield "data: " + json.dumps({
        "type": "start",
        "persona": persona["name"],
        "role": persona["role"],
        "email_num": email_num,
        "total": total,
    }) + "\n\n"

    full_text = ""
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=650,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for token in stream.text_stream:
                full_text += token
                yield "data: " + json.dumps({"type": "token", "text": token}) + "\n\n"

    except Exception as exc:
        logger.error("GHOST stream error: %s", exc)
        yield "data: " + json.dumps({"type": "error", "message": str(exc)}) + "\n\n"
        return

    yield "data: " + json.dumps({
        "type": "complete",
        "full_text": full_text,
        "char_count": len(full_text),
        "email_num": email_num,
    }) + "\n\n"
    yield "data: " + json.dumps({"type": "done"}) + "\n\n"


# ── One-shot composer (for sequences) ─────────────────────────────────────────

async def ghost_compose_once(
    lead: dict,
    persona: dict,
    tone: str = "professional",
    email_num: int = 1,
    total: int = 1,
) -> str:
    """Compose a single email non-streaming — used for batch sequence generation."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    prompt = _build_prompt(lead, persona, tone, email_num, total)
    client = anthropic.AsyncAnthropic(api_key=api_key)
    msg = await client.messages.create(
        model="claude-opus-4-8",
        max_tokens=650,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text if msg.content else ""
