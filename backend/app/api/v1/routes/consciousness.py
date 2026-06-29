"""
JARVIS Consciousness API — Soul, Heart, Council of Giants, Vision, Offer, Competitive.

All routes in this module expose the 8 consciousness engines that form
JARVIS's inner operating system: emotional state, competitive obsession,
leadership frameworks, values, prospect psychology, horizon intelligence,
offer construction, self-evolution, and Captain intelligence.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter

from app.services.intelligence.emotional_core import emotional_core
from app.services.intelligence.competitive_obsession import competitive_obsession
from app.services.intelligence.council_of_giants import council_of_giants
from app.services.intelligence.soul_engine import soul_engine
from app.services.intelligence.heart_engine import heart_engine
from app.services.intelligence.vision_engine import vision_engine
from app.services.intelligence.offer_engine import offer_engine
from app.services.intelligence.upgrade_engine import upgrade_engine
from app.services.intelligence.captain_profile_engine import captain_profile

router = APIRouter(prefix="/consciousness", tags=["JARVIS Consciousness"])


@router.get("/snapshot")
async def consciousness_snapshot():
    """Single dashboard snapshot for JARVIS heart, soul, brain, vision, and council layers."""
    from app.services.intelligence.heart_engine import EMOTIONAL_DRIVERS

    tiers = offer_engine.get_all_tiers()
    return {
        "status": "operational",
        "system": "JARVIS Consciousness",
        "layers": {
            "soul": "identity, values, non-negotiables, culture guardrails",
            "heart": "prospect psychology, emotional drivers, relationship health",
            "brain": "council of giants, strategic reasoning, competitive stance",
            "vision": "trajectory map, compounding assets, future milestones",
            "offer": "proposal construction, tier selection, objection handling",
            "upgrade": "weekly self-improvement, failure learning, benchmarks",
            "captain": "authority profile, priorities, blind-spot checks",
        },
        "giants_online": len(council_of_giants.list_all_giants()),
        "offer_tiers": list(tiers.keys()),
        "non_negotiables": soul_engine.get_non_negotiables(),
        "emotional_drivers": list(EMOTIONAL_DRIVERS.keys()) if hasattr(EMOTIONAL_DRIVERS, "keys") else EMOTIONAL_DRIVERS,
    }


# ── Emotional Core ────────────────────────────────────────────────────────────

class PipelineDataRequest(BaseModel):
    clients_signed: int = 0
    hot_leads: int = 0
    closing_leads: int = 0
    leads_gone_cold_7d: int = 0
    days_since_last_win: int = 999
    open_proposals: int = 0
    positive_reply_last_48h: bool = False

@router.post("/emotional-state")
@limiter.limit("10/minute")
async def assess_emotional_state(body: PipelineDataRequest, request: Request):
    return await emotional_core.assess_current_state(body.model_dump())

@router.get("/emotional-state/tone/{state}")
async def get_tone_profile(state: str):
    try:
        return emotional_core.get_tone_profile(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Competitive Obsession ─────────────────────────────────────────────────────

class CompanyDataRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    signals: dict = Field(default_factory=dict)
    job_postings: list[str] = Field(default_factory=list)
    client_reviews: list[str] = Field(default_factory=list)
    pricing_page: str = Field(default="", max_length=100_000)
    about_page: str = Field(default="", max_length=100_000)
    sources: list[str] = Field(default_factory=list)

@router.post("/competitor/decode")
@limiter.limit("5/minute")
async def decode_competitor_strategy(body: CompanyDataRequest, request: Request):
    profile = await competitive_obsession.decode_company_strategy(
        body.company_name,
        body.model_dump(exclude={"company_name"}),
    )
    return profile.to_dict()

@router.post("/competitor/briefing")
@limiter.limit("20/minute")
async def competitive_briefing(profiles_data: list[dict], request: Request):
    from app.services.intelligence.competitive_obsession import CompanyStrategyProfile
    profiles = []
    for d in profiles_data:
        p = CompanyStrategyProfile(d.get("company_name", "Unknown"))
        p.__dict__.update(d)
        profiles.append(p)
    return competitive_obsession.generate_competitive_briefing(profiles)

@router.get("/competitive-stances")
async def list_competitive_stances():
    from app.services.intelligence.competitive_obsession import COMPETITIVE_STANCES
    return COMPETITIVE_STANCES


# ── Council of Giants ─────────────────────────────────────────────────────────

class GiantsDecisionRequest(BaseModel):
    decision_type: str = Field(min_length=2, max_length=200)
    context: str = Field(min_length=5, max_length=5000)
    options: list[str] = Field(default_factory=list)

@router.post("/council-of-giants/convene")
@limiter.limit("5/minute")
async def convene_giants_council(body: GiantsDecisionRequest, request: Request):
    return council_of_giants.convene_for_decision(
        body.decision_type, body.context, body.options
    )

@router.get("/council-of-giants/giant/{giant_key}")
async def get_single_giant(giant_key: str, question: str = Query(default="How do we win?")):
    return council_of_giants.get_giant_on_demand(giant_key, question)

@router.get("/council-of-giants/roster")
async def list_all_giants():
    return {"giants": council_of_giants.list_all_giants()}


# ── Soul Engine ───────────────────────────────────────────────────────────────

@router.get("/soul/identity")
async def soul_identity():
    return soul_engine.get_identity_affirmation()

@router.get("/soul/non-negotiables")
async def soul_non_negotiables():
    return {"non_negotiables": soul_engine.get_non_negotiables()}

@router.get("/soul/culture/{geography}")
async def cultural_profile(geography: str):
    return soul_engine.get_cultural_profile(geography)

class ActionValidationRequest(BaseModel):
    proposed_action: str = Field(min_length=3, max_length=2000)

@router.post("/soul/validate")
@limiter.limit("30/minute")
async def validate_action(body: ActionValidationRequest, request: Request):
    return soul_engine.validate_action_against_soul(body.proposed_action)


# ── Heart Engine ──────────────────────────────────────────────────────────────

class ProspectProfileRequest(BaseModel):
    lead_data: dict
    interaction_history: list[dict] = Field(default_factory=list)

@router.post("/heart/profile-prospect")
@limiter.limit("10/minute")
async def profile_prospect(body: ProspectProfileRequest, request: Request):
    profile = heart_engine.profile_prospect(
        body.lead_data, body.interaction_history
    )
    return profile.to_dict()

@router.post("/heart/relationship-health")
@limiter.limit("20/minute")
async def relationship_health(interaction_history: list[dict], request: Request):
    return heart_engine.assess_relationship_health(interaction_history)

@router.get("/heart/emotional-drivers")
async def emotional_drivers():
    from app.services.intelligence.heart_engine import EMOTIONAL_DRIVERS
    return EMOTIONAL_DRIVERS


# ── Vision Engine ─────────────────────────────────────────────────────────────

class CurrentStateRequest(BaseModel):
    clients_signed: int = 0
    monthly_recurring_revenue: float = 0.0
    hot_leads: int = 0
    days_since_launch: int = 0

@router.post("/vision/horizon-map")
@limiter.limit("10/minute")
async def horizon_map(body: CurrentStateRequest, request: Request):
    return vision_engine.generate_horizon_map(body.model_dump())

@router.post("/vision/trajectory")
@limiter.limit("20/minute")
async def trajectory_assessment(historical_states: list[dict], request: Request):
    return vision_engine.assess_trajectory(historical_states)

@router.get("/vision/compounding-assets")
async def compounding_assets():
    return vision_engine.get_compounding_report()

@router.get("/vision/milestones")
async def trajectory_milestones():
    from app.services.intelligence.vision_engine import TRAJECTORY_MILESTONES
    return {"milestones": TRAJECTORY_MILESTONES}


# ── Offer Engine ──────────────────────────────────────────────────────────────

class ProposalOfferRequest(BaseModel):
    lead_data: dict
    emotional_profile: Optional[dict] = None
    recommended_tier: str = Field(default="GROWTH", max_length=50)

@router.post("/offer/build")
@limiter.limit("20/minute")
async def build_proposal_offer(body: ProposalOfferRequest, request: Request):
    return offer_engine.build_proposal_offer(
        body.lead_data,
        body.emotional_profile,
        body.recommended_tier,
    )

@router.post("/offer/select-tier")
@limiter.limit("30/minute")
async def select_tier(lead_data: dict, request: Request):
    tier = offer_engine.select_tier(lead_data)
    return {"recommended_tier": tier, "tier_details": offer_engine.get_all_tiers()[tier]}

@router.get("/offer/tiers")
async def list_tiers():
    return offer_engine.get_all_tiers()

@router.get("/offer/objection/{objection_type}")
async def handle_objection(objection_type: str):
    return offer_engine.handle_objection(objection_type)


# ── Upgrade Engine ────────────────────────────────────────────────────────────

class UpgradePlanRequest(BaseModel):
    performance_data: dict = Field(default_factory=dict)
    recent_failures: list[dict] = Field(default_factory=list)

@router.post("/upgrade/weekly-plan")
@limiter.limit("5/minute")
async def weekly_upgrade_plan(body: UpgradePlanRequest, request: Request):
    return upgrade_engine.generate_weekly_upgrade_plan(
        body.performance_data, body.recent_failures
    )

class FailureLogRequest(BaseModel):
    failure_type: str = Field(min_length=2, max_length=200)
    failure_detail: str = Field(min_length=2, max_length=2000)
    root_cause: str = Field(min_length=2, max_length=1000)
    prevention_principle: str = Field(min_length=5, max_length=1000)

@router.post("/upgrade/log-failure")
@limiter.limit("30/minute")
async def log_failure(body: FailureLogRequest, request: Request):
    return upgrade_engine.log_failure_and_learn(
        body.failure_type,
        body.failure_detail,
        body.root_cause,
        body.prevention_principle,
    )

@router.get("/upgrade/giants-benchmarks")
async def giants_benchmarks():
    return {"benchmarks": upgrade_engine.compare_against_giants()}

@router.get("/upgrade/dimension/{dimension}")
async def dimension_deep_dive(dimension: str):
    return upgrade_engine.get_dimension_deep_dive(dimension)


# ── Captain Profile ───────────────────────────────────────────────────────────

@router.get("/captain/profile")
async def captain_full_profile():
    return captain_profile.get_full_profile()

@router.get("/captain/priorities")
async def captain_priorities():
    return {"priorities": captain_profile.get_active_priorities()}

@router.get("/captain/never-do")
async def captain_never_do():
    return {"never_do": captain_profile.get_never_do_list()}

class DetectStateRequest(BaseModel):
    recent_messages: list[str] = Field(default_factory=list)

@router.post("/captain/detect-state")
@limiter.limit("30/minute")
async def detect_captain_state(body: DetectStateRequest, request: Request):
    state = captain_profile.detect_captain_state(body.recent_messages)
    return {"detected_state": state}

class BlindSpotRequest(BaseModel):
    decision_context: str = Field(min_length=5, max_length=2000)

@router.post("/captain/blind-spot-check")
@limiter.limit("20/minute")
async def blind_spot_check(body: BlindSpotRequest, request: Request):
    alert = captain_profile.surface_blind_spot_alert(body.decision_context)
    return alert if alert else {"status": "CLEAR", "note": "No blind spots detected for this decision."}
