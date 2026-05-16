from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.lead import Lead
from app.services.storage.secure import get_credential


router = APIRouter(prefix="/discovery", tags=["Discovery"])

PLACES_TEXT_SEARCH = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
OVERPASS_API = "https://overpass-api.de/api/interpreter"

HTTP_HEADERS = {
    "User-Agent": "AliyarSolutionsJarvis/1.0 (operations@aliyarsolutions.com)",
}


class LocalMarketRequest(BaseModel):
    industry: str = Field(..., min_length=2, max_length=120)
    location: str = Field(..., min_length=2, max_length=160)
    service_angle: str = Field("workflow automation", max_length=160)
    limit: int = Field(20, ge=1, le=60)


def _pain_signals(place: dict) -> tuple[list[str], str, int]:
    pain: list[str] = []
    score = 45

    rating = place.get("rating")
    reviews = place.get("user_ratings_total") or 0
    website = place.get("website")

    if not website:
        pain.append("No website visible on Google profile")
        score += 18
    if rating and rating < 4.0 and reviews >= 10:
        pain.append("Review rating suggests service experience friction")
        score += 14
    if reviews < 15:
        pain.append("Low review volume indicates weak local trust signals")
        score += 8
    if not place.get("formatted_phone_number"):
        pain.append("No phone number visible on profile")
        score += 5
    if place.get("business_status") and place.get("business_status") != "OPERATIONAL":
        pain.append(f"Business status is {place.get('business_status')}")
        score -= 15

    types = " ".join(str(item) for item in (place.get("types") or []) if item)
    if any(t in types for t in ("doctor", "dentist", "hospital", "health", "clinic")):
        opportunity = "AI receptionist, appointment booking, review response workflow"
        score += 8
    elif any(t in types for t in ("lodging", "restaurant", "food")):
        opportunity = "guest messaging, booking workflow, review operations"
        score += 7
    else:
        opportunity = "CRM workflow, website conversion, lead follow-up automation"

    if not pain:
        pain.append("Profile is visible; needs website and workflow review to confirm operational gaps")

    return pain, opportunity, max(0, min(100, score))


async def _place_details(client: httpx.AsyncClient, key: str, place_id: str) -> dict:
    params = {
        "key": key,
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,business_status,types,url,reviews,opening_hours",
    }
    response = await client.get(PLACES_DETAILS, params=params)
    data = response.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return {}
    return data.get("result") or {}


@router.post("/local-market")
async def local_market_discovery(req: LocalMarketRequest, db: AsyncSession = Depends(get_db)):
    key = await get_credential(db, "GOOGLE_MAPS_API_KEY")

    query = f"{req.industry} in {req.location}"
    fallback_reason = None
    async with httpx.AsyncClient(timeout=25, headers=HTTP_HEADERS) as client:
        candidates: list[dict] = []
        source = "google_maps"
        if key:
            try:
                response = await client.get(PLACES_TEXT_SEARCH, params={"key": key, "query": query})
                data = response.json()
                if data.get("status") in ("OK", "ZERO_RESULTS"):
                    candidates = data.get("results", [])[: req.limit]
                else:
                    fallback_reason = data.get("error_message") or data.get("status")
            except Exception as exc:
                fallback_reason = str(exc)
        else:
            fallback_reason = "GOOGLE_MAPS_API_KEY missing"

        if not candidates:
            source = "open_public_directory"
            candidates = await _public_directory_candidates(client, req)
            if not candidates and fallback_reason:
                raise HTTPException(
                    502,
                    {
                        "blocker": "Live discovery unavailable",
                        "details": fallback_reason,
                        "fallback": "Open public directory fallback returned no candidates.",
                    },
                )

        created = 0
        updated = 0
        leads = []

        for item in candidates:
            details = await _place_details(client, key, item.get("place_id")) if key and item.get("place_id") else {}
            place = {**item, **details}
            name = place.get("name") or "Unknown business"
            website = place.get("website")
            inferred_email = _infer_public_contact_email(place)
            phone = place.get("formatted_phone_number")
            maps_url = place.get("url")
            pain, opportunity, score = _pain_signals(place)

            existing = None
            filters = [Lead.company == name]
            if website:
                filters.append(Lead.website == website)
            result = await db.execute(select(Lead).where(or_(*filters)))
            existing = result.scalar_one_or_none()

            metadata = {
                "place_id": place.get("place_id"),
                "maps_url": maps_url,
                "phone": phone,
                "rating": place.get("rating"),
                "review_count": place.get("user_ratings_total"),
                "business_status": place.get("business_status"),
                "google_types": place.get("types") or [],
                "service_angle": req.service_angle,
                "opening_hours": place.get("opening_hours", {}).get("weekday_text") if place.get("opening_hours") else None,
                "discovery_source": source,
                "fallback_reason": fallback_reason,
                "contact_email_inferred": bool(inferred_email and not place.get("email")),
            }

            if existing:
                existing.website = existing.website or website
                existing.company_website = existing.company_website or website
                existing.email = existing.email or inferred_email
                existing.contact_email = existing.contact_email or inferred_email
                existing.pain_points = pain
                existing.opportunity_type = opportunity
                existing.score = max(existing.score or 0, score)
                existing.tier = "A" if score >= 75 else "B" if score >= 60 else "C"
                existing.metadata_ = {**(existing.metadata_ or {}), **metadata}
                updated += 1
                lead = existing
            else:
                lead = Lead(
                    company=name,
                    company_name=name,
                    website=website,
                    company_website=website,
                    email=inferred_email,
                    contact_email=inferred_email,
                    industry=req.industry,
                    country=req.location,
                    pain_points=pain,
                    opportunity_type=opportunity,
                    status="qualified" if score >= 60 else "new",
                    score=score,
                    tier="A" if score >= 75 else "B" if score >= 60 else "C",
                    source=source,
                    notes=(
                        f"Discovered from {source} for '{query}'. "
                        "Generic contact email was inferred from public website domain; review before outreach."
                        if inferred_email and not place.get("email")
                        else f"Discovered from {source} for '{query}'."
                    ),
                    metadata_=metadata,
                )
                db.add(lead)
                await db.flush()
                created += 1

            leads.append({
                "id": lead.id,
                "company": name,
                "website": website,
                "email": inferred_email,
                "phone": phone,
                "score": score,
                "tier": lead.tier,
                "pain_points": pain,
                "opportunity_type": opportunity,
                "maps_url": maps_url,
            })

        await db.commit()

    return {
        "query": query,
        "source": source,
        "fallback_reason": fallback_reason,
        "created": created,
        "updated": updated,
        "total_candidates": len(candidates),
        "leads": leads,
        "next_action": "Review A/B tier leads in Sales War Room and generate outreach drafts for approval.",
    }


async def _public_directory_candidates(client: httpx.AsyncClient, req: LocalMarketRequest) -> list[dict]:
    geo_response = await client.get(
        NOMINATIM_SEARCH,
        params={"q": req.location, "format": "jsonv2", "limit": 1},
    )
    geo_data = geo_response.json()
    if not geo_data:
        return []

    lat = float(geo_data[0]["lat"])
    lon = float(geo_data[0]["lon"])
    radius = 18000
    selector = _overpass_selector(req.industry)
    query = f"""
    [out:json][timeout:20];
    (
      node(around:{radius},{lat},{lon}){selector};
      way(around:{radius},{lat},{lon}){selector};
      relation(around:{radius},{lat},{lon}){selector};
    );
    out center tags {min(req.limit * 3, 90)};
    """
    response = await client.post(OVERPASS_API, data={"data": query})
    data = response.json()
    candidates = []
    seen: set[str] = set()
    for element in data.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        website = _first_value(tags, "website", "contact:website", "url")
        email = _first_value(tags, "email", "contact:email")
        phone = _first_value(tags, "phone", "contact:phone")
        address = _format_osm_address(tags, req.location)
        candidates.append({
            "name": name,
            "formatted_address": address,
            "formatted_phone_number": phone,
            "website": website,
            "email": email,
            "rating": None,
            "user_ratings_total": 0,
            "business_status": "OPERATIONAL",
            "types": [tags.get("amenity"), tags.get("shop"), tags.get("office"), tags.get("tourism")],
            "url": f"https://www.openstreetmap.org/{element.get('type')}/{element.get('id')}",
            "place_id": f"osm:{element.get('type')}:{element.get('id')}",
        })
        if len(candidates) >= req.limit:
            break
    return candidates


def _overpass_selector(industry: str) -> str:
    text = industry.lower()
    if any(word in text for word in ("clinic", "health", "doctor", "dentist", "medical")):
        return '["amenity"~"clinic|doctors|dentist|hospital|pharmacy"]'
    if any(word in text for word in ("hotel", "hospitality", "lodging")):
        return '["tourism"~"hotel|guest_house|motel|hostel"]'
    if "restaurant" in text or "food" in text:
        return '["amenity"~"restaurant|cafe|fast_food"]'
    if "agency" in text:
        return '["office"~"company|consulting|advertising|it"]'
    return '["name"]["office"]'


def _first_value(tags: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return None


def _format_osm_address(tags: dict, fallback: str) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city") or tags.get("addr:suburb"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    clean = [str(part) for part in parts if part]
    return ", ".join(clean) if clean else fallback


def _infer_public_contact_email(place: dict) -> Optional[str]:
    explicit = place.get("email")
    if explicit and "@" in explicit:
        return explicit.strip().lower()
    website = place.get("website")
    if not website:
        return None
    parsed = urlparse(website if "://" in website else f"https://{website}")
    domain = parsed.netloc.lower().removeprefix("www.")
    if not domain or "." not in domain:
        return None
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain):
        return None
    return f"info@{domain}"
