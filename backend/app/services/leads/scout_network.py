"""
Scout Network — 9 autonomous AI agents that discover leads globally.
Each agent specialises in an industry vertical and region.
Runs daily at 01:30 UTC via APScheduler.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

from app.core.config import settings

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

    async def run_all_scouts(self) -> dict:
        """Run all 9 scouts concurrently and return consolidated results."""
        tasks = [self.run_scout(sid, profile) for sid, profile in SCOUT_PROFILES.items()]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for _v in raw:
            if isinstance(_v, BaseException):
                logger.warning("Scout task raised: %s", _v)
        results = [v for v in raw if isinstance(v, dict)]

        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]

        logger.info("Scout network complete: %d success, %d failed", len(successful), len(failed))
        return {
            "status": "complete",
            "scouts_run": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }


scout_network = ScoutNetwork()
