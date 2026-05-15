from __future__ import annotations

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

    types = " ".join(place.get("types") or [])
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
    if not key:
        raise HTTPException(
            status_code=409,
            detail={
                "blocker": "GOOGLE_MAPS_API_KEY missing",
                "next_step": "Open Access Vault and add a Google Maps Platform API key with Places API enabled.",
            },
        )

    query = f"{req.industry} in {req.location}"
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(PLACES_TEXT_SEARCH, params={"key": key, "query": query})
        data = response.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            raise HTTPException(502, {"blocker": "Google Places API error", "details": data.get("error_message") or data.get("status")})

        candidates = data.get("results", [])[: req.limit]
        created = 0
        updated = 0
        leads = []

        for item in candidates:
            details = await _place_details(client, key, item.get("place_id")) if item.get("place_id") else {}
            place = {**item, **details}
            name = place.get("name") or "Unknown business"
            website = place.get("website")
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
            }

            if existing:
                existing.website = existing.website or website
                existing.company_website = existing.company_website or website
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
                    industry=req.industry,
                    country=req.location,
                    pain_points=pain,
                    opportunity_type=opportunity,
                    status="qualified" if score >= 60 else "new",
                    score=score,
                    tier="A" if score >= 75 else "B" if score >= 60 else "C",
                    source="google_maps",
                    notes=f"Discovered from Google Places for '{query}'.",
                    metadata_=metadata,
                )
                db.add(lead)
                await db.flush()
                created += 1

            leads.append({
                "id": lead.id,
                "company": name,
                "website": website,
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
        "source": "google_maps",
        "created": created,
        "updated": updated,
        "total_candidates": len(candidates),
        "leads": leads,
        "next_action": "Review A/B tier leads in Sales War Room and generate outreach drafts for approval.",
    }
