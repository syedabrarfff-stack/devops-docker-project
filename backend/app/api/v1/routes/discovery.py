"""
JARVIS Local Market Discovery — Google Maps Places API
Finds businesses with weak digital presence as qualified leads.
"""
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovery", tags=["discovery"])


# ── Pain signal scoring ───────────────────────────────────────────────────────

def _pain_score(place: dict) -> dict:
    """
    Score a business by its digital weakness signals.
    Higher score = better lead candidate (more gaps we can fill).
    """
    score = 0
    signals = []

    website = place.get("website") or place.get("websiteUri", "")
    if not website:
        score += 18
        signals.append("no website")

    rating = place.get("rating") or place.get("averageRating", 0)
    review_count = place.get("userRatingsTotal") or place.get("userRatingCount", 0)

    if rating and float(rating) < 3.8:
        score += 14
        signals.append(f"low rating ({rating})")

    if review_count < 20:
        score += 8
        signals.append(f"low reviews ({review_count})")

    if not place.get("formatted_phone_number") and not place.get("nationalPhoneNumber"):
        score += 5
        signals.append("no phone listed")

    opening_hours = place.get("opening_hours") or place.get("regularOpeningHours")
    if not opening_hours:
        score += 4
        signals.append("no hours listed")

    photos = place.get("photos") or []
    if len(photos) < 2:
        score += 3
        signals.append("no photos")

    return {"score": score, "signals": signals}


def _opportunity_type(place: dict, industry: str) -> list[str]:
    """Suggest which Aliyar services would help this business."""
    opportunities = []
    types = [t.lower() for t in (place.get("types") or [])]
    name = (place.get("name") or "").lower()

    if "clinic" in types or "doctor" in name or "dentist" in name or "hospital" in types:
        opportunities += ["Patient Booking System", "Reputation Management", "WhatsApp Appointment Bot"]
    if "restaurant" in types or "food" in types or "cafe" in name:
        opportunities += ["Online Ordering System", "Review Response Automation", "Loyalty Program"]
    if "hotel" in types or "lodging" in types:
        opportunities += ["Booking Automation", "Guest Communication System", "Review Management"]
    if "real_estate" in types or "real estate" in industry.lower():
        opportunities += ["Lead Capture Portal", "CRM Automation", "Property Listing System"]

    if not opportunities:
        opportunities = ["Website & Digital Presence", "CRM & Lead Management", "AI Automation"]

    return opportunities[:3]


# ── Models ────────────────────────────────────────────────────────────────────

class LocalMarketRequest(BaseModel):
    industry: str = Field(..., description="e.g. 'dental clinic', 'hotel', 'restaurant'")
    location: str = Field(..., description="e.g. 'Dubai', 'London', 'New York'")
    service_angle: Optional[str] = Field(None, description="e.g. 'website', 'automation'")
    limit: int = Field(10, ge=1, le=25)
    min_score: int = Field(0, ge=0, description="Minimum pain score (0=all, 10=weaker only)")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/local-market")
async def discover_local_market(body: LocalMarketRequest, db: AsyncSession = Depends(get_db)):
    """
    Discover businesses with digital gaps in any city/industry.
    Uses Google Maps Places API. Returns scored leads ready for outreach.
    """
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_MAPS_API_KEY not configured. Add it to your .env file.",
        )

    query = f"{body.industry} in {body.location}"
    leads = []

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Google Maps Places Text Search (New API)
            resp = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": (
                        "places.id,places.displayName,places.formattedAddress,"
                        "places.rating,places.userRatingCount,places.websiteUri,"
                        "places.nationalPhoneNumber,places.types,places.regularOpeningHours,"
                        "places.photos,places.googleMapsUri"
                    ),
                    "Content-Type": "application/json",
                },
                json={
                    "textQuery": query,
                    "maxResultCount": min(body.limit * 2, 20),
                    "languageCode": "en",
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Google Maps API error {resp.status_code}: {resp.text[:200]}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Google Maps API returned {resp.status_code}. Check API key and billing.",
                )

            data = resp.json()
            places = data.get("places", [])

            for place in places:
                pain = _pain_score(place)
                if pain["score"] < body.min_score:
                    continue

                name = place.get("displayName", {}).get("text", "Unknown")
                leads.append({
                    "name": name,
                    "address": place.get("formattedAddress", ""),
                    "phone": place.get("nationalPhoneNumber", ""),
                    "website": place.get("websiteUri", ""),
                    "rating": place.get("rating", 0),
                    "review_count": place.get("userRatingCount", 0),
                    "google_maps_url": place.get("googleMapsUri", ""),
                    "pain_score": pain["score"],
                    "pain_signals": pain["signals"],
                    "opportunities": _opportunity_type(place, body.industry),
                    "lead_quality": "hot" if pain["score"] >= 20 else "warm" if pain["score"] >= 10 else "cold",
                    "has_website": bool(place.get("websiteUri")),
                    "types": place.get("types", []),
                })

            # Sort by pain score — biggest opportunity first
            leads.sort(key=lambda x: x["pain_score"], reverse=True)
            leads = leads[:body.limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

    hot = sum(1 for l in leads if l["lead_quality"] == "hot")
    warm = sum(1 for l in leads if l["lead_quality"] == "warm")

    return {
        "query": query,
        "location": body.location,
        "industry": body.industry,
        "total_found": len(leads),
        "hot_leads": hot,
        "warm_leads": warm,
        "leads": leads,
        "next_action": (
            f"JARVIS found {hot} hot leads and {warm} warm leads in {body.location}. "
            f"Recommend running overnight_cold_outreach for businesses with no website."
        ),
    }


@router.get("/industries")
async def list_target_industries():
    """Industries with highest digital gaps — best prospecting targets."""
    return {
        "industries": [
            {"name": "dental_clinic",       "label": "Dental Clinics",       "avg_pain_score": 24},
            {"name": "hotel",               "label": "Hotels & Guesthouses",  "avg_pain_score": 21},
            {"name": "restaurant",          "label": "Restaurants",           "avg_pain_score": 19},
            {"name": "real_estate_agency",  "label": "Real Estate Agencies",  "avg_pain_score": 22},
            {"name": "law_firm",            "label": "Law Firms",             "avg_pain_score": 26},
            {"name": "accounting_firm",     "label": "Accounting Firms",      "avg_pain_score": 25},
            {"name": "physiotherapy",       "label": "Physiotherapy Clinics", "avg_pain_score": 23},
            {"name": "beauty_salon",        "label": "Beauty Salons & Spas",  "avg_pain_score": 18},
            {"name": "car_dealer",          "label": "Car Dealerships",       "avg_pain_score": 17},
            {"name": "construction_company","label": "Construction & Trades",  "avg_pain_score": 28},
        ],
        "recommendation": "Law firms, construction, and accounting firms have the highest digital gaps globally.",
    }
