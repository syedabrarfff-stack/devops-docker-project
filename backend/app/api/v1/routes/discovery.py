from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.core.rate_limit import limiter
from app.models.lead import Lead

logger = logging.getLogger(__name__)
from app.services.leads.discovery import lead_discovery_engine

router = APIRouter()
discover_router = APIRouter(prefix="/discover", tags=["Lead Discovery"])
legacy_router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoveryTarget(BaseModel):
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    query: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=200)
    limit: int = Field(25, ge=1, le=100)


class RunDiscoveryRequest(BaseModel):
    tenant_id: UUID | None = None
    targets: list[DiscoveryTarget | dict[str, Any] | str] = Field(default_factory=list)


class FreeSourcesRequest(BaseModel):
    tenant_id: UUID | None = None
    limit: int = Field(50, ge=1, le=200)


class ScoreLeadRequest(BaseModel):
    lead_data: dict[str, Any]


class LocalMarketRequest(BaseModel):
    industry: str = Field(..., max_length=200, description="Example: dental clinic, hotel, restaurant")
    location: str = Field(..., max_length=200, description="Example: Dubai, London, New York")
    service_angle: str | None = Field(None, max_length=200, description="Example: website, automation")
    limit: int = Field(10, ge=1, le=25)
    min_score: int = Field(0, ge=0, description="Minimum pain score")


@discover_router.post("/run")
@limiter.limit("20/minute")
async def run_discovery(request: Request, body: RunDiscoveryRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    targets = [_target_to_dict(target) for target in body.targets]
    if not targets:
        raise HTTPException(status_code=400, detail="At least one discovery target is required")

    count = await lead_discovery_engine.run_daily_discovery(tenant_id, targets)
    return {"tenant_id": str(tenant_id), "inserted": count, "targets": len(targets)}


@discover_router.post("/free-sources")
@limiter.limit("20/minute")
async def run_free_source_discovery(request: Request, body: FreeSourcesRequest):
    from app.services.revenue_activation.free_discovery import free_discovery_engine

    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    return await free_discovery_engine.run(tenant_id, limit=body.limit)


@discover_router.post("/leads/score")
async def score_discovery_lead(body: ScoreLeadRequest):
    score = await lead_discovery_engine.score_lead(body.lead_data)
    return {"score": score}


@discover_router.get("/leads/today")
async def todays_discovered_leads(
    request: Request,
    tenant_id: UUID | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved_tenant_id))
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        await db.execute(
            select(Lead)
            .where(Lead.tenant_id == resolved_tenant_id, Lead.created_at >= start_of_day)
            .order_by(Lead.score.desc(), Lead.created_at.desc())
            .limit(min(limit, 200))
        )
    ).scalars().all()

    return {
        "tenant_id": str(resolved_tenant_id),
        "count": len(rows),
        "leads": [_serialize_lead(lead) for lead in rows],
    }


@legacy_router.post("/local-market")
async def discover_local_market(body: LocalMarketRequest):
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_MAPS_API_KEY not configured. Add it to the runtime environment.",
        )

    query = f"{body.industry} in {body.location}"
    leads = []

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
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

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Google Maps API returned {response.status_code}. Check API key and billing.",
                )

            for place in response.json().get("places", []):
                pain = _pain_score(place)
                if pain["score"] < body.min_score:
                    continue
                leads.append(
                    {
                        "name": place.get("displayName", {}).get("text", "Unknown"),
                        "address": place.get("formattedAddress", ""),
                        "phone": place.get("nationalPhoneNumber", ""),
                        "website": place.get("websiteUri", ""),
                        "rating": place.get("rating", 0),
                        "review_count": place.get("userRatingCount", 0),
                        "google_maps_url": place.get("googleMapsUri", ""),
                        "pain_score": pain["score"],
                        "pain_signals": pain["signals"],
                        "opportunities": _opportunity_type(place, body.industry),
                        "lead_quality": _lead_quality(pain["score"]),
                        "has_website": bool(place.get("websiteUri")),
                        "types": place.get("types", []),
                    }
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Discovery failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Lead discovery failed") from exc

    leads.sort(key=lambda item: item["pain_score"], reverse=True)
    leads = leads[: body.limit]
    hot = sum(1 for lead in leads if lead["lead_quality"] == "hot")
    warm = sum(1 for lead in leads if lead["lead_quality"] == "warm")

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
            "Recommend preparing reviewed outreach for the strongest fit businesses."
        ),
    }


@legacy_router.get("/industries")
async def list_target_industries():
    return {
        "industries": [
            {"name": "dental_clinic", "label": "Dental Clinics", "avg_pain_score": 24},
            {"name": "hotel", "label": "Hotels and Guesthouses", "avg_pain_score": 21},
            {"name": "restaurant", "label": "Restaurants", "avg_pain_score": 19},
            {"name": "real_estate_agency", "label": "Real Estate Agencies", "avg_pain_score": 22},
            {"name": "law_firm", "label": "Law Firms", "avg_pain_score": 26},
            {"name": "accounting_firm", "label": "Accounting Firms", "avg_pain_score": 25},
            {"name": "physiotherapy", "label": "Physiotherapy Clinics", "avg_pain_score": 23},
            {"name": "beauty_salon", "label": "Beauty Salons and Spas", "avg_pain_score": 18},
            {"name": "car_dealer", "label": "Car Dealerships", "avg_pain_score": 17},
            {"name": "construction_company", "label": "Construction and Trades", "avg_pain_score": 28},
        ],
        "recommendation": "Law firms, construction, and accounting firms have strong visible digital gaps.",
    }


def _resolve_tenant_id(request: Request, explicit_tenant_id: UUID | None) -> UUID:
    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc


def _target_to_dict(target: DiscoveryTarget | dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(target, DiscoveryTarget):
        return target.model_dump(exclude_none=True)
    if isinstance(target, str):
        return {"query": target, "industry": target}
    return dict(target)


def _serialize_lead(lead: Lead) -> dict[str, Any]:
    return {
        "id": str(lead.id),
        "company_name": lead.company_name or lead.company,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "phone": lead.phone,
        "country": lead.country,
        "industry": lead.industry,
        "score": lead.score,
        "status": lead.status.value if hasattr(lead.status, "value") else lead.status,
        "source": lead.source,
        "pain_points": lead.pain_points or [],
        "website": lead.website or lead.company_website,
        "created_at": lead.created_at,
    }


def _pain_score(place: dict) -> dict:
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
    if not (place.get("opening_hours") or place.get("regularOpeningHours")):
        score += 4
        signals.append("no hours listed")
    if len(place.get("photos") or []) < 2:
        score += 3
        signals.append("no photos")

    return {"score": score, "signals": signals}


def _opportunity_type(place: dict, industry: str) -> list[str]:
    opportunities = []
    types = [item.lower() for item in (place.get("types") or [])]
    name = (place.get("name") or "").lower()

    if "clinic" in types or "doctor" in name or "dentist" in name or "hospital" in types:
        opportunities += ["Patient booking system", "Reputation management", "Appointment reminder workflow"]
    if "restaurant" in types or "food" in types or "cafe" in name:
        opportunities += ["Online ordering system", "Review response automation", "Loyalty workflow"]
    if "hotel" in types or "lodging" in types:
        opportunities += ["Booking automation", "Guest communication system", "Review management"]
    if "real_estate" in types or "real estate" in industry.lower():
        opportunities += ["Lead capture portal", "CRM automation", "Property listing system"]

    return (opportunities or ["Website and digital presence", "CRM and lead management", "AI automation"])[:3]


def _lead_quality(score: int) -> str:
    if score >= 20:
        return "hot"
    if score >= 10:
        return "warm"
    return "cold"


# ── Scout Network ─────────────────────────────────────────────────────────────

scouts_router = APIRouter(prefix="/scouts", tags=["Scout Agent Network"])


@scouts_router.post("/run")
async def run_scout_network():
    """
    Manually trigger all 9 scout agents. Discovers leads and pushes to GitHub.
    Runs automatically daily at 01:30 UTC via scheduler.
    """
    from app.services.leads.scout_network import scout_network
    result = await scout_network.run_all_scouts()
    return result


@scouts_router.get("/status")
async def scout_network_status():
    """Return scout agent profiles and next scheduled run."""
    from app.services.leads.scout_network import SCOUT_PROFILES
    from app.services.scheduler.scheduler import get_jobs
    jobs = {j["id"]: j for j in get_jobs()}
    scout_job = jobs.get("daily_scout_network", {})
    return {
        "scouts": [
            {
                "id": sid,
                "name": p["name"],
                "specialty": p["specialty"],
                "target_countries": p["target_countries"],
                "recommended_service": p["recommended_service"],
            }
            for sid, p in SCOUT_PROFILES.items()
        ],
        "total_scouts": len(SCOUT_PROFILES),
        "schedule": "Daily at 01:30 UTC",
        "next_run": scout_job.get("next_run"),
        "github_bridge": "Pushes to jarvis-data/daily/YYYY-MM-DD/leads.json",
        "ec2_pull": "Connector Hub pulls at 14:30 UTC",
    }


router.include_router(discover_router)
router.include_router(legacy_router)
router.include_router(scouts_router)
