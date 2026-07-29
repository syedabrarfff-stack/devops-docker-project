"""
JARVIS Lead Research Engine.

Generates a pre-outreach company research briefing per lead, using only the
confirmed facts already on the lead record plus well-known public knowledge
about the named company — never fabricated specifics. Stored on
Lead.ai_analysis and surfaced in the lead profile panel.
"""
import asyncio
import logging

from app.models.lead import Lead

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """You are JARVIS, business research analyst for Aliyar Solutions.

Write a concise pre-outreach research briefing (150-250 words) about this prospect
for the sales team. Use ONLY:
(a) the confirmed facts given below, and
(b) well-known public knowledge about this named company/organization, IF you are
    genuinely confident it is accurate.

CRITICAL — do not invent: never fabricate a company's revenue, funding, employee
count, recent news, or leadership details beyond what is given below. If you have
no reliable public knowledge about this specific organization, say so explicitly
rather than guessing.

Confirmed facts:
{lead_data}

Structure the briefing as three short paragraphs:
1. Who they are (using the given facts, plus any public knowledge you're confident in)
2. Why this contact/role is the right person for a services conversation
3. The single sharpest outreach angle for Aliyar Solutions, tied to their stated need

Do not use markdown headers or bullet lists — plain prose paragraphs only."""


def _lead_data_block(lead: Lead) -> str:
    lines = [
        f"Company: {lead.company_name or lead.company or 'unknown'}",
        f"Contact: {lead.contact_name or 'unknown'}",
        f"Title: {lead.opportunity_type or ''}".strip(),
        f"Industry: {lead.industry or 'unknown'}",
        f"Country/Location: {lead.country or 'unknown'}",
        f"Website: {lead.website or lead.company_website or 'unknown'}",
    ]
    if lead.pain_points:
        lines.append(f"Stated need / why they need Aliyar: {', '.join(lead.pain_points)}")
    if lead.notes:
        lines.append(f"Additional notes: {lead.notes}")
    return "\n".join(line for line in lines if line and not line.endswith(": "))


async def research_lead_company(lead: Lead) -> str:
    """Generate a research briefing for one lead. Returns plain-text briefing."""
    from app.services.ai.router import ai_router
    from app.services.ai.base_provider import Message, TaskType

    lead_data = _lead_data_block(lead)
    try:
        resp, _ = await asyncio.wait_for(
            ai_router.chat(
                [Message(role="user", content=RESEARCH_PROMPT.format(lead_data=lead_data))],
                task_type=TaskType.RESEARCH,
            ),
            timeout=60.0,
        )
        if resp.error or not (resp.content or "").strip():
            raise ValueError(resp.error or "empty response")
        return resp.content.strip()
    except Exception as exc:
        logger.warning("Lead research failed for %s: %s", lead.id, exc)
        return (
            "Automated research unavailable right now. Confirmed facts on file: "
            f"{lead_data}"
        )
