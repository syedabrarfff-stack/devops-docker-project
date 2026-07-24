"""
Scout Network — 9 autonomous AI agents that discover leads globally.
Each agent specialises in an industry vertical and region.
Runs daily at 01:30 UTC via APScheduler.

Each scout's raw LLM output is parsed and inserted as real, ICP-scored leads
into the `leads` table (deduped against existing companies) — previously the
raw JSON text was generated, discarded, and never persisted anywhere.
"""
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)

SCOUT_PROFILES: dict[str, dict[str, Any]] = {
    "alpha": {
        "name": "Alpha Scout",
        "specialty": "SaaS & Tech Startups",
        "target_countries": ["US", "UK", "CA", "AU"],
        "recommended_service": "AI Automation Systems",
        "query_templates": [
            "SaaS startup looking for automation",
            "tech company seeking AI integration",
            "software startup operations scaling",
        ],
    },
    "beta": {
        "name": "Beta Scout",
        "specialty": "E-commerce & Retail",
        "target_countries": ["US", "UK", "DE", "AU"],
        "recommended_service": "CRM & Pipeline Automation",
        "query_templates": [
            "ecommerce store automation tools",
            "online retail operational efficiency",
            "shopify store lead generation",
        ],
    },
    "gamma": {
        "name": "Gamma Scout",
        "specialty": "Healthcare & MedTech",
        "target_countries": ["US", "UK", "CA", "IN"],
        "recommended_service": "Cloud Infrastructure",
        "query_templates": [
            "healthcare startup digital transformation",
            "medtech company cloud migration",
            "health platform infrastructure",
        ],
    },
    "delta": {
        "name": "Delta Scout",
        "specialty": "Finance & Fintech",
        "target_countries": ["US", "UK", "SG", "AE"],
        "recommended_service": "DevOps & Monitoring",
        "query_templates": [
            "fintech startup infrastructure",
            "financial services cloud architecture",
            "payment platform reliability",
        ],
    },
    "epsilon": {
        "name": "Epsilon Scout",
        "specialty": "Logistics & Supply Chain",
        "target_countries": ["US", "DE", "IN", "AE"],
        "recommended_service": "AI Automation Systems",
        "query_templates": [
            "logistics company automation",
            "supply chain optimisation AI",
            "warehouse management system",
        ],
    },
    "zeta": {
        "name": "Zeta Scout",
        "specialty": "Real Estate & PropTech",
        "target_countries": ["US", "UK", "AE", "AU"],
        "recommended_service": "Lead Generation Operations",
        "query_templates": [
            "real estate CRM automation",
            "proptech lead generation system",
            "property management software",
        ],
    },
    "eta": {
        "name": "Eta Scout",
        "specialty": "Education & EdTech",
        "target_countries": ["US", "IN", "UK", "AU"],
        "recommended_service": "Digital Platforms",
        "query_templates": [
            "edtech platform growth",
            "education startup marketing automation",
            "online learning lead generation",
        ],
    },
    "theta": {
        "name": "Theta Scout",
        "specialty": "Professional Services",
        "target_countries": ["US", "UK", "CA", "AE"],
        "recommended_service": "Business Dashboards",
        "query_templates": [
            "consulting firm automation",
            "professional services CRM",
            "law firm digital operations",
        ],
    },
    "iota": {
        "name": "Iota Scout",
        "specialty": "Manufacturing & Industry",
        "target_countries": ["DE", "US", "IN", "CN"],
        "recommended_service": "Cloud Infrastructure",
        "query_templates": [
            "manufacturing digital transformation",
            "industrial IoT cloud platform",
            "factory automation AI",
        ],
    },
}


class ScoutNetwork:
    """Orchestrates all 9 scout agents for autonomous lead discovery."""

    async def run_scout(self, scout_id: str, profile: dict) -> dict:
        """Run a single scout agent — uses AI to generate leads from web intelligence."""
        from app.services.ai.router import ai_router
        from app.services.ai.base_provider import Message, TaskType

        logger.info("Scout %s (%s) running...", scout_id, profile["name"])
        try:
            prompt = (
                f"You are {profile['name']}, a lead discovery agent specialising in "
                f"{profile['specialty']} companies in {', '.join(profile['target_countries'])}.\n\n"
                f"Using public web intelligence, identify 3 high-value prospect companies that:\n"
                f"- Are in the {profile['specialty']} sector\n"
                f"- Are actively growing and would benefit from {profile['recommended_service']}\n"
                f"- Have budget for technology investment ($2K–$25K range)\n\n"
                f"Return a JSON array with this exact structure:\n"
                f'[{{"company": "...", "website": "...", "country": "...", "industry": "...", '
                f'"contact_role": "...", "pain_point": "...", "recommended_service": "{profile["recommended_service"]}"}}]\n\n'
                f"Only return valid JSON. No explanation."
            )
            resp, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.RESEARCH,
                ),
                timeout=60.0,
            )
            if resp.error:
                raise ValueError(resp.error)
            return {
                "scout_id": scout_id,
                "scout_name": profile["name"],
                "specialty": profile["specialty"],
                "status": "success",
                "raw_output": resp.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("Scout %s failed: %s", scout_id, e)
            return {
                "scout_id": scout_id,
                "scout_name": profile["name"],
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def run_all_scouts(self, tenant_id=None) -> dict:
        """Run all 9 scouts concurrently, parse each one's raw output into
        real leads, insert them (deduped), and return consolidated results."""
        tasks = [self.run_scout(sid, profile) for sid, profile in SCOUT_PROFILES.items()]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for _v in raw:
            if isinstance(_v, BaseException):
                logger.warning("Scout task raised: %s", _v)
        results = [v for v in raw if isinstance(v, dict)]

        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]

        tenant_uuid = _tenant_uuid(tenant_id)
        companies_found = 0
        inserted = 0
        for result in successful:
            companies = _parse_scout_output(result.get("raw_output", ""))
            companies_found += len(companies)
            inserted += await self._insert_scout_leads(tenant_uuid, result, companies)

        logger.info(
            "Scout network complete: %d success, %d failed, %d companies found, %d leads inserted",
            len(successful), len(failed), companies_found, inserted,
        )
        return {
            "status": "complete",
            "tenant_id": str(tenant_uuid),
            "scouts_run": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "companies_found": companies_found,
            "leads_inserted": inserted,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _insert_scout_leads(self, tenant_uuid: uuid.UUID, scout_result: dict, companies: list[dict]) -> int:
        from app.services.leads.scoring import lead_scoring_engine

        inserted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for company in companies:
                    name = (company.get("company") or "").strip()
                    if not name:
                        continue
                    if await _scout_lead_exists(session, tenant_uuid, name, company.get("website")):
                        continue

                    lead_data = {
                        "company_name": name,
                        "country": company.get("country"),
                        "industry": company.get("industry"),
                        "pain_points": [company.get("pain_point")] if company.get("pain_point") else [],
                        "notes": (
                            f"Scout network signal ({scout_result.get('scout_name')}, "
                            f"{scout_result.get('specialty')}): {company.get('recommended_service') or ''}"
                        ),
                    }
                    score, reasoning = await lead_scoring_engine.score_against_icp(lead_data)
                    lead = Lead(
                        tenant_id=tenant_uuid,
                        company_name=name,
                        company=name,
                        country=company.get("country"),
                        industry=company.get("industry"),
                        score=score,
                        status=LeadStatus.NEW,
                        source="scout_network",
                        pain_points=lead_data["pain_points"],
                        enrichment_data={
                            "scout_id": scout_result.get("scout_id"),
                            "scout_name": scout_result.get("scout_name"),
                            "recommended_service": company.get("recommended_service"),
                            "contact_role": company.get("contact_role"),
                            "icp_scoring": reasoning,
                        },
                        website=company.get("website"),
                        company_website=company.get("website"),
                        notes=lead_data["notes"],
                    )
                    session.add(lead)
                    await session.flush()
                    session.add(
                        AuditLog(
                            tenant_id=tenant_uuid,
                            action="scout_lead_discovered",
                            entity_type="lead",
                            entity_id=lead.id,
                            actor=scout_result.get("scout_name") or "ScoutNetwork",
                            details={"source": "scout_network", "score": score, "company": name},
                            after_json={"company": company, "score": score, "reasoning": reasoning},
                        )
                    )
                    inserted += 1
        return inserted


async def _scout_lead_exists(session, tenant_uuid: uuid.UUID, name: str, website: str | None) -> bool:
    conditions = [Lead.company_name.ilike(name), Lead.company.ilike(name)]
    if website:
        conditions.append(Lead.website.ilike(f"%{website.strip()}%"))
    existing = await session.scalar(
        select(Lead.id).where(Lead.tenant_id == tenant_uuid, or_(*conditions)).limit(1)
    )
    return bool(existing)


def _parse_scout_output(raw: str) -> list[dict[str, Any]]:
    """Extract a JSON array of company dicts from a scout's raw LLM output —
    tolerant of surrounding prose, matching the pattern used elsewhere for
    parsing LLM-generated JSON (see mission_planner._parse_decomposition)."""
    if not raw:
        return []
    raw = raw.strip()
    parsed = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict) and item.get("company")]


def _tenant_uuid(value=None) -> uuid.UUID:
    raw = value or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        raise ValueError("tenant_id is required")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


scout_network = ScoutNetwork()
