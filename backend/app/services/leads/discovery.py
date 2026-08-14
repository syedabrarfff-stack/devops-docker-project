from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any

import httpx
from sqlalchemy import func, or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.lead import Lead, LeadStatus
from app.middleware import record_lead_discovered
from app.services.ai.base_provider import Message, TaskType
from app.services.ai.router import ai_router
from app.services.leads.scoring import lead_scoring_engine

logger = logging.getLogger(__name__)

APOLLO_BASE_URL = "https://api.apollo.io/v1"
GOOGLE_PLACES_BASE_URL = "https://maps.googleapis.com/maps/api/place"
DEFAULT_TITLES = ["CEO", "Founder", "Director", "VP"]


class LeadDiscoveryEngine:
    async def search_apollo(self, query: str, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        api_key = settings.APOLLO_API_KEY
        if not api_key:
            logger.info("APOLLO_API_KEY not configured; Apollo discovery skipped")
            return []

        payload = {
            "q_keywords": query,
            "person_titles": filters.get("person_titles") or DEFAULT_TITLES,
            "person_locations": _as_list(filters.get("locations") or filters.get("countries")),
            "organization_industries": _as_list(filters.get("industries")),
            "organization_num_employees_ranges": filters.get("employee_ranges") or ["1,10", "11,50", "51,100"],
            "page": int(filters.get("page") or 1),
            "per_page": min(int(filters.get("per_page") or filters.get("limit") or 25), 100),
            "api_key": api_key,
        }
        payload = {key: value for key, value in payload.items() if value not in (None, [], "")}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{APOLLO_BASE_URL}/people/search",
                    headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.warning("Apollo people search failed with %s", response.status_code)
                    return []
                data = response.json()
        except Exception as exc:
            logger.warning("Apollo people search failed: %s", exc)
            return []

        return [_normalize_apollo_person(person) for person in data.get("people", [])]

    async def enrich_company(self, domain: str) -> dict:
        api_key = settings.APOLLO_API_KEY
        if not api_key or not domain:
            return {}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{APOLLO_BASE_URL}/organizations/enrich",
                    headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                    json={"domain": domain, "api_key": api_key},
                )
                if response.status_code >= 400:
                    logger.warning("Apollo organization enrichment failed with %s", response.status_code)
                    return {}
                data = response.json()
        except Exception as exc:
            logger.warning("Apollo organization enrichment failed for %s: %s", domain, exc)
            return {}

        org = data.get("organization") or data
        return {
            "size": org.get("estimated_num_employees") or org.get("num_employees"),
            "revenue": org.get("annual_revenue"),
            "tech_stack": org.get("technologies") or org.get("technology_names") or [],
            "social_urls": {
                "linkedin": org.get("linkedin_url"),
                "twitter": org.get("twitter_url"),
                "facebook": org.get("facebook_url"),
            },
            "raw": org,
        }

    async def score_lead(self, lead_data: dict) -> float:
        score, reasoning = await lead_scoring_engine.score_against_icp(lead_data)
        if reasoning.get("decision") == "promote":
            return score

        prompt = (
            "Score this lead 0-100 for Aliyar Solutions. ICP: SMB companies "
            "($500K-$10M revenue, 5-100 employees), English-speaking, in "
            "UK/UAE/USA/AUS/Canada, with pain: manual processes, no AI systems, "
            f"no tech team. Lead: {lead_data}. Return only a number 0-100."
        )
        try:
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.RESEARCH,
                    force_provider="google",
                    max_tokens=32,
                ),
                timeout=30.0,
            )
            if not response.demo and not response.error:
                parsed = _parse_score(response.content or "")
                if parsed is not None:
                    return parsed
        except Exception as exc:
            logger.warning("AI lead score failed; using heuristic score: %s", exc)

        return _heuristic_score(lead_data)

    async def run_daily_discovery(self, tenant_id: str | uuid.UUID, targets: list) -> int:
        import asyncio as _asyncio
        tenant_uuid = uuid.UUID(str(tenant_id))

        # Phase 1: concurrent I/O — fetch all targets in parallel
        normalized_targets = [(_normalize_target(t), t) for t in targets]

        async def _fetch_one(norm_target, original_target):
            try:
                records = await self._discover_target(norm_target)
                return [(r, norm_target) for r in records]
            except Exception as exc:
                logger.warning("Discovery target failed %s: %s", norm_target.get("query"), exc)
                return []

        fetch_tasks = [_fetch_one(nt, ot) for nt, ot in normalized_targets]
        raw_target_results = await _asyncio.gather(*fetch_tasks, return_exceptions=True)
        for _v in raw_target_results:
            if isinstance(_v, BaseException):
                logger.warning("Discovery fetch task raised: %s", _v)
        results_by_target = [v if isinstance(v, list) else [] for v in raw_target_results]

        # Phase 2: flatten and dedupe before DB writes
        all_records: list[tuple[dict, dict]] = []
        seen_keys: set[str] = set()
        for records_with_target in results_by_target:
            for lead_data, norm_target in records_with_target:
                key = _dedupe_key(lead_data)
                if key and key in seen_keys:
                    continue
                if key:
                    seen_keys.add(key)
                all_records.append((lead_data, norm_target))

        if not all_records:
            return 0

        # Phase 3: score + persist in single DB session
        inserted = 0
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(tenant_uuid))
                for lead_data, norm_target in all_records:
                    if await self._lead_exists(session, tenant_uuid, lead_data):
                        continue
                    score, reasoning = await lead_scoring_engine.score_against_icp(lead_data)
                    phone = lead_data.get("phone")
                    lead = Lead(
                        tenant_id=tenant_uuid,
                        company_name=lead_data.get("company_name"),
                        company=lead_data.get("company_name"),
                        contact_name=lead_data.get("contact_name"),
                        email=lead_data.get("email"),
                        contact_email=lead_data.get("email"),
                        phone=phone,
                        whatsapp_number=_extract_whatsapp(phone, lead_data),
                        country=lead_data.get("country") or norm_target.get("country"),
                        industry=lead_data.get("industry") or norm_target.get("industry"),
                        score=score,
                        status=LeadStatus.NEW,
                        source=lead_data.get("source") or "lead_discovery",
                        pain_points=lead_data.get("pain_points") or [],
                        enrichment_data={
                            **(lead_data.get("enrichment_data") or lead_data),
                            "icp_scoring": reasoning,
                        },
                        apollo_id=lead_data.get("apollo_id"),
                        website=lead_data.get("website"),
                        company_website=lead_data.get("website"),
                        linkedin_url=lead_data.get("linkedin_url"),
                        opportunity_type=lead_data.get("opportunity_type"),
                        notes=lead_data.get("notes"),
                    )
                    session.add(lead)
                    await session.flush()
                    session.add(
                        AuditLog(
                            tenant_id=tenant_uuid,
                            action="lead_discovered",
                            entity_type="lead",
                            entity_id=lead.id,
                            actor="LeadDiscoveryEngine",
                            after_json={
                                "company_name": lead.company_name,
                                "source": lead.source,
                                "score": score,
                                "icp_scoring": reasoning,
                                "target": norm_target,
                            },
                            details={"discovery_source": lead.source},
                        )
                    )
                    inserted += 1
                    record_lead_discovered(lead.source, lead.country)

        logger.info("Lead discovery complete: %s leads inserted from %s targets", inserted, len(targets))
        return inserted

    async def discover_from_google_maps(self, query: str, location: str) -> list[dict]:
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            logger.info("GOOGLE_MAPS_API_KEY not configured; Google Maps discovery skipped")
            return []

        text_query = f"{query} in {location}".strip()
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.get(
                    f"{GOOGLE_PLACES_BASE_URL}/textsearch/json",
                    params={"query": text_query, "key": api_key, "language": "en"},
                )
                if response.status_code >= 400:
                    logger.warning("Google Maps text search failed with %s", response.status_code)
                    return []
                data = response.json()
                places = data.get("results", [])

                results = []
                for place in places:
                    details = await self._google_place_details(client, api_key, place.get("place_id"))
                    results.append(_normalize_google_place(place, details, query, location))
                return results
        except Exception as exc:
            logger.warning("Google Maps discovery failed: %s", exc)
            return []

    async def _discover_target(self, target: dict) -> list[dict]:
        query = target.get("query") or target.get("industry") or "business operations"
        country = target.get("country")
        location = target.get("location") or country or ""
        limit = int(target.get("limit") or 25)

        apollo_filters = {
            "countries": [country] if country else None,
            "industries": [target.get("industry")] if target.get("industry") else None,
            "limit": limit,
        }
        apollo_records = await self.search_apollo(query, apollo_filters)
        maps_records = await self.discover_from_google_maps(query, location) if location else []
        return (apollo_records + maps_records)[: max(limit, 1)]

    async def _google_place_details(self, client: httpx.AsyncClient, api_key: str, place_id: str | None) -> dict:
        if not place_id:
            return {}
        response = await client.get(
            f"{GOOGLE_PLACES_BASE_URL}/details/json",
            params={
                "place_id": place_id,
                "fields": "formatted_phone_number,international_phone_number,website,url",
                "key": api_key,
                "language": "en",
            },
        )
        if response.status_code >= 400:
            return {}
        return response.json().get("result") or {}

    async def _lead_exists(self, session, tenant_id: uuid.UUID, lead_data: dict) -> bool:
        conditions = []
        email = _clean_lower(lead_data.get("email"))
        website = _clean_lower(lead_data.get("website"))
        company_name = _clean_lower(lead_data.get("company_name"))

        if email:
            conditions.append(func.lower(Lead.email) == email)
        if website:
            conditions.append(func.lower(Lead.website) == website)
            conditions.append(func.lower(Lead.company_website) == website)
        if company_name:
            conditions.append(func.lower(Lead.company_name) == company_name)
            conditions.append(func.lower(Lead.company) == company_name)
        if not conditions:
            return False

        existing_id = await session.scalar(
            select(Lead.id).where(Lead.tenant_id == tenant_id, or_(*conditions)).limit(1)
        )
        return existing_id is not None


def _normalize_apollo_person(person: dict) -> dict:
    org = person.get("organization") or {}
    company_name = org.get("name") or person.get("organization_name")
    website = org.get("website_url") or org.get("primary_domain") or org.get("domain")
    return {
        "source": "apollo",
        "apollo_id": person.get("id"),
        "company_name": company_name,
        "contact_name": person.get("name") or " ".join(
            part for part in [person.get("first_name"), person.get("last_name")] if part
        ).strip(),
        "title": person.get("title"),
        "email": person.get("email"),
        "phone": person.get("phone") or person.get("sanitized_phone"),
        "country": person.get("country"),
        "industry": _first(org.get("industries")),
        "website": website,
        "linkedin_url": person.get("linkedin_url"),
        "employee_count": org.get("estimated_num_employees") or org.get("num_employees"),
        "estimated_revenue": org.get("annual_revenue"),
        "pain_points": [],
        "opportunity_type": "AI automation and operations modernization",
        "enrichment_data": {"person": person, "organization": org},
    }


def _normalize_google_place(place: dict, details: dict, query: str, location: str) -> dict:
    website = details.get("website")
    phone = details.get("formatted_phone_number") or details.get("international_phone_number")
    rating = place.get("rating")
    reviews = place.get("user_ratings_total")
    pain_points = []
    if not website:
        pain_points.append("No website visible in Google Maps profile")
    if reviews is not None and reviews < 20:
        pain_points.append("Low review volume")
    if rating is not None and rating < 3.8:
        pain_points.append("Weak public rating")

    return {
        "source": "google_maps",
        "company_name": place.get("name"),
        "contact_name": None,
        "email": None,
        "phone": phone,
        "country": location,
        "industry": query,
        "website": website,
        "address": place.get("formatted_address"),
        "google_maps_url": details.get("url"),
        "pain_points": pain_points,
        "opportunity_type": "Website, CRM, appointment automation, and customer communication",
        "enrichment_data": {"place": place, "details": details},
    }


def _normalize_target(target: Any) -> dict:
    if isinstance(target, str):
        return {"query": target, "industry": target, "limit": 25}
    if not isinstance(target, dict):
        return {"query": "business operations", "limit": 25}
    data = dict(target)
    data["query"] = data.get("query") or data.get("industry") or data.get("service") or "business operations"
    data["location"] = data.get("location") or data.get("country")
    data["limit"] = int(data.get("limit") or 25)
    return data


def _heuristic_score(lead_data: dict) -> float:
    score = 35.0
    country = (lead_data.get("country") or "").lower()
    industry = (lead_data.get("industry") or "").lower()
    employees = _to_int(lead_data.get("employee_count"))
    revenue = str(lead_data.get("estimated_revenue") or "").lower()
    pain_points = lead_data.get("pain_points") or []

    if any(market in country for market in ["uk", "united kingdom", "usa", "united states", "uae", "australia", "canada"]):
        score += 18
    if any(word in industry for word in ["saas", "software", "clinic", "hotel", "agency", "ecommerce", "restaurant"]):
        score += 16
    if employees and 5 <= employees <= 100:
        score += 14
    if any(token in revenue for token in ["500", "1m", "2m", "5m", "10m"]):
        score += 8
    score += min(len(pain_points) * 7, 21)
    if lead_data.get("email"):
        score += 6
    if lead_data.get("website"):
        score += 3

    return max(0.0, min(100.0, round(score, 1)))


def _parse_score(text: str) -> float | None:
    for match in re.finditer(r"\b(?:100|[1-9]?\d)(?:\.\d+)?\b", text):
        value = float(match.group(0))
        if 0 <= value <= 100:
            return value
    return None


def _as_list(value: Any) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    return [value]


def _first(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_lower(value: Any) -> str | None:
    if not value:
        return None
    return str(value).strip().lower()


def _dedupe_key(lead_data: dict) -> str | None:
    return (
        _clean_lower(lead_data.get("email"))
        or _clean_lower(lead_data.get("website"))
        or _clean_lower(lead_data.get("company_name"))
    )


def _extract_whatsapp(phone: str | None, lead_data: dict) -> str | None:
    """Return E.164-normalized phone if it looks like a mobile number, else None."""
    raw = phone or lead_data.get("whatsapp_number") or lead_data.get("mobile")
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", str(raw))
    if len(digits) < 7:
        return None
    if digits.startswith("+"):
        return digits
    if len(digits) >= 10:
        return "+" + digits
    return None


lead_discovery_engine = LeadDiscoveryEngine()
