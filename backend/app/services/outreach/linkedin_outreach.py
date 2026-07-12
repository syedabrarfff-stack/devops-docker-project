"""R6-4: LinkedIn Outreach Activation.

Enriches leads with LinkedIn profile data (via Proxycurl API),
generates AI-crafted first-connection messages, and queues them
for manual or automated sending.

Proxycurl: https://nubela.co/proxycurl — scrapes LinkedIn without ToS violation.
Set PROXYCURL_API_KEY in .env to activate enrichment.

Scheduler job: linkedin_outreach_sweep every 2h — picks HOT leads
without linkedin_enriched=true and enriches + generates outreach message.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROXYCURL_BASE = "https://nubela.co/proxycurl/api"
_LINKEDIN_PROFILE_EP = f"{_PROXYCURL_BASE}/v2/linkedin"
_LINKEDIN_COMPANY_EP = f"{_PROXYCURL_BASE}/linkedin/company"

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


# ── Proxycurl enrichment ──────────────────────────────────────────────────────

async def enrich_person_profile(linkedin_url: str) -> dict[str, Any] | None:
    """Fetch a person's LinkedIn profile via Proxycurl."""
    if not settings.PROXYCURL_API_KEY:
        logger.debug("PROXYCURL_API_KEY not set — LinkedIn enrichment disabled")
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                _LINKEDIN_PROFILE_EP,
                params={"url": linkedin_url, "use_cache": "if-present"},
                headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
            )
        if r.status_code == 200:
            return r.json()
        logger.warning("[LinkedIn] Proxycurl %s → %s", linkedin_url[:60], r.status_code)
        return None
    except Exception as exc:
        logger.warning("[LinkedIn] Proxycurl error: %s", exc)
        return None


async def enrich_company_profile(company_domain: str) -> dict[str, Any] | None:
    """Fetch company LinkedIn data by domain (e.g. 'stripe.com')."""
    if not settings.PROXYCURL_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                _LINKEDIN_COMPANY_EP,
                params={"domain": company_domain, "use_cache": "if-present"},
                headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
            )
        return r.json() if r.status_code == 200 else None
    except Exception as exc:
        logger.warning("[LinkedIn] Company enrich error: %s", exc)
        return None


# ── Message generation ────────────────────────────────────────────────────────

async def generate_linkedin_message(
    lead_company: str,
    contact_name: str,
    profile_data: dict | None,
    service_angle: str = "AI automation",
) -> str:
    """
    Use the AI fabric to craft a LinkedIn first-connection message.
    Falls back to a high-quality template if fabric is unavailable.
    """
    headline = ""
    current_role = ""
    if profile_data:
        headline = profile_data.get("headline") or ""
        experiences = profile_data.get("experiences") or []
        if experiences:
            current_role = experiences[0].get("title") or ""

    try:
        from app.services.ai.router import ai_router
        prompt = (
            f"Write a LinkedIn first-connection message for {contact_name} "
            f"at {lead_company}. "
            f"Their role: {current_role or 'business leader'}. "
            f"Their headline: {headline[:100] if headline else 'N/A'}. "
            f"Our pitch angle: {service_angle}. "
            "Rules: max 300 characters, no emojis, natural and conversational, "
            "don't mention AI or automation explicitly, "
            "end with a soft CTA ('Would love to connect.'). "
            "Return ONLY the message text, nothing else."
        )
        response, _ = await ai_router.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type="SALES",
        )
        if response and not response.error and response.content:
            return response.content[:300].strip()
    except Exception as exc:
        logger.debug("[LinkedIn] AI message gen failed: %s", exc)

    # Fallback template
    first = contact_name.split()[0] if contact_name else "there"
    return (
        f"Hi {first}, I came across {lead_company} and was impressed by your work in "
        f"{service_angle}. Would love to connect and explore if there's any overlap "
        f"with what we're building at Aliyar Solutions."
    )[:300]


# ── Lead enrichment + queue ───────────────────────────────────────────────────

async def enrich_and_queue_lead(lead_id: uuid.UUID) -> dict[str, Any]:
    """
    Enrich a lead with LinkedIn data and generate the outreach message.
    Stores result in lead.raw_data and outreach_log.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            sqla_text(
                "SELECT id, company_name, contact_name, contact_email, "
                "linkedin_url, domain, icp_score FROM leads WHERE id=:lid"
            ),
            {"lid": lead_id},
        )
        row = result.fetchone()

    if not row:
        return {"status": "not_found", "lead_id": str(lead_id)}

    _, company, contact, email, linkedin_url, domain, score = row

    profile_data = None
    if linkedin_url:
        profile_data = await enrich_person_profile(linkedin_url)
    elif domain:
        profile_data = await enrich_company_profile(domain)

    service_angle = _infer_service_angle(score)
    message = await generate_linkedin_message(company, contact or "", profile_data, service_angle)

    async with AsyncSessionLocal() as session:
        await session.execute(
            sqla_text(
                "UPDATE leads SET "
                "linkedin_enriched=true, linkedin_message=:msg, updated_at=NOW() "
                "WHERE id=:lid"
            ),
            {"msg": message, "lid": lead_id},
        )
        await session.commit()

    logger.info("[LinkedIn] Lead %s enriched and queued (%s)", company, lead_id)
    return {
        "lead_id": str(lead_id),
        "company": company,
        "message": message,
        "enriched": profile_data is not None,
        "status": "queued",
    }


def _infer_service_angle(score: float | None) -> str:
    if not score:
        return "AI automation and operational intelligence"
    if score >= 80:
        return "enterprise AI infrastructure"
    if score >= 60:
        return "workflow automation and AI integration"
    return "operational efficiency through AI"


# ── Scheduler sweep ───────────────────────────────────────────────────────────

async def linkedin_outreach_sweep() -> dict[str, Any]:
    """
    Scheduled job: find HOT leads not yet LinkedIn-enriched and process them.
    Runs every 2h. Caps at 25 per sweep to avoid Proxycurl quota exhaustion.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text as sqla_text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            sqla_text(
                "SELECT id FROM leads "
                "WHERE (linkedin_enriched IS NULL OR linkedin_enriched=false) "
                "AND icp_score >= 60 "
                "AND status NOT IN ('closed','disqualified') "
                "ORDER BY icp_score DESC NULLS LAST "
                "LIMIT 25"
            )
        )
        lead_ids = [row[0] for row in result.fetchall()]

    if not lead_ids:
        return {"processed": 0, "skipped": 0}

    processed = 0
    errors = 0
    for lid in lead_ids:
        try:
            await enrich_and_queue_lead(lid)
            processed += 1
        except Exception as exc:
            logger.warning("[LinkedIn] Sweep error for %s: %s", lid, exc)
            errors += 1

    logger.info("[LinkedIn] Sweep complete: %d processed, %d errors", processed, errors)
    return {"processed": processed, "errors": errors, "run_at": datetime.now(UTC).isoformat()}


# Scheduler registration: see app/services/scheduler/scheduler.py's
# `linkedin_outreach_sweep_job()` (registered in _production_job_specs(),
# runs every 2h). That is the only registration path — do not re-add a
# registrar here (Task #23: one scheduler, one job registry). This module's
# previous `register_linkedin_job()` was dead on arrival — it imported a
# `scheduler` attribute that has never existed on engine.py, so this sweep
# never ran in production regardless of the engine.py/scheduler.py split.
