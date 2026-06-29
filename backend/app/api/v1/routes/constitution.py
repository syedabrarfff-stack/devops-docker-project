"""
JARVIS Supreme Intelligence API — Constitution, CEO, Revenue, Platform, Sales.

Layer 19: The 10x Autonomous Intelligence Expansion.

These routes expose JARVIS's highest-order intelligence systems:
 - Constitutional framework (authority matrix, laws, escalation)
 - Autonomous CEO cognition (opportunity scoring, expansion roadmap)
 - Revenue consciousness (LTV, churn, upsell, pipeline health)
 - Platform intelligence (cost posture, scaling, security, deployments)
 - Sales autonomy (lead scoring, outreach sequences, objection playbook)

All endpoints require Captain authentication.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from app.api.v1.routes.auth import get_current_captain

from app.core.rate_limit import limiter
from app.services.intelligence.jarvis_constitution import jarvis_constitution
from app.services.intelligence.autonomous_ceo import autonomous_ceo
from app.services.intelligence.revenue_consciousness import revenue_consciousness
from app.services.intelligence.platform_intelligence import platform_intelligence
from app.services.intelligence.sales_autonomy import sales_autonomy

router = APIRouter(prefix="/supreme", tags=["JARVIS Supreme Intelligence"], dependencies=[Depends(get_current_captain)])


# ══════════════════════════════════════════════════════════════════════════════
# CONSTITUTION
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/constitution/summary")
async def get_constitution_summary() -> dict[str, Any]:
    return jarvis_constitution.get_constitution_summary()


@router.get("/constitution/laws")
async def get_constitution_laws() -> dict[str, Any]:
    return {"laws": jarvis_constitution.get_laws()}


@router.get("/constitution/laws/{law_number}")
async def get_constitution_law(law_number: int) -> dict[str, Any]:
    return jarvis_constitution.get_law(law_number)


@router.get("/constitution/authority-matrix")
async def get_authority_matrix() -> dict[str, Any]:
    return jarvis_constitution.get_authority_matrix()


@router.get("/constitution/escalation-triggers")
async def get_escalation_triggers() -> dict[str, Any]:
    return {"triggers": jarvis_constitution.get_escalation_triggers()}


@router.get("/constitution/revenue-protocol")
async def get_revenue_protocol() -> dict[str, Any]:
    return jarvis_constitution.get_revenue_protocol()


@router.get("/constitution/platform-standards")
async def get_platform_standards() -> dict[str, Any]:
    return jarvis_constitution.get_platform_standards()


class EvaluateActionRequest(BaseModel):
    action: str = Field(min_length=5, max_length=2000)
    category: str = Field(default="OPERATIONAL", max_length=100)
    financial_value: float = Field(default=0.0, ge=0.0, le=10_000_000.0)
    reversible: bool = Field(default=True)
    affects_clients: bool = Field(default=False)
    affects_revenue: bool = Field(default=False)


@router.post("/constitution/evaluate")
@limiter.limit("30/minute")
async def evaluate_action(body: EvaluateActionRequest, request: Request) -> dict[str, Any]:
    return jarvis_constitution.evaluate_action(body.model_dump())


class ScoreDecisionRequest(BaseModel):
    decision: str = Field(min_length=5, max_length=2000)
    context: str = Field(default="", max_length=5000)


@router.post("/constitution/score-decision")
@limiter.limit("20/minute")
async def score_decision(body: ScoreDecisionRequest, request: Request) -> dict[str, Any]:
    return jarvis_constitution.score_decision_against_constitution(body.decision, body.context)


# ══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS CEO
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/ceo/dashboard")
async def get_ceo_dashboard(
    mrr: float = Query(default=0.0, ge=0.0, le=100_000_000.0),
) -> dict[str, Any]:
    return autonomous_ceo.get_ceo_dashboard({"mrr": mrr})


@router.get("/ceo/strategic-pillars")
async def get_strategic_pillars() -> dict[str, Any]:
    from app.services.intelligence.autonomous_ceo import STRATEGIC_PILLARS
    return {"strategic_pillars": STRATEGIC_PILLARS}


@router.get("/ceo/expansion-roadmap")
async def get_expansion_roadmap(
    mrr: float = Query(default=0.0, ge=0.0, le=100_000_000.0),
) -> dict[str, Any]:
    return autonomous_ceo.get_expansion_roadmap(mrr)


@router.get("/ceo/competitive-intelligence")
async def get_competitive_intelligence() -> dict[str, Any]:
    return autonomous_ceo.get_competitive_intelligence()


class OpportunityRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    revenue_potential: str = Field(default="10k_to_25k", max_length=50)
    time_to_revenue: str = Field(default="under_30_days", max_length=50)
    capability_match: str = Field(default="strong_fit", max_length=50)
    strategic_alignment: str = Field(default="core_pillar", max_length=50)
    competitive_moat: str = Field(default="strong_differentiation", max_length=50)


@router.post("/ceo/score-opportunity")
@limiter.limit("20/minute")
async def score_opportunity(body: OpportunityRequest, request: Request) -> dict[str, Any]:
    return autonomous_ceo.score_opportunity(body.model_dump())


class PartnershipRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    revenue_access: float = Field(default=5.0, ge=0.0, le=10.0)
    client_overlap: float = Field(default=5.0, ge=0.0, le=10.0)
    complementary_capability: float = Field(default=5.0, ge=0.0, le=10.0)
    operational_alignment: float = Field(default=5.0, ge=0.0, le=10.0)
    exit_optionality: float = Field(default=5.0, ge=0.0, le=10.0)


@router.post("/ceo/evaluate-partnership")
@limiter.limit("10/minute")
async def evaluate_partnership(body: PartnershipRequest, request: Request) -> dict[str, Any]:
    return autonomous_ceo.evaluate_partnership(body.model_dump())


class PipelineStateRequest(BaseModel):
    mrr: float = Field(default=0.0, ge=0.0, le=100_000_000.0)
    client_count: int = Field(default=0, ge=0, le=10000)
    hot_leads: int = Field(default=0, ge=0, le=10000)
    top_client_revenue_pct: float = Field(default=0.0, ge=0.0, le=1.0)


@router.post("/ceo/strategic-priorities")
@limiter.limit("20/minute")
async def get_strategic_priorities(body: PipelineStateRequest, request: Request) -> dict[str, Any]:
    return autonomous_ceo.get_strategic_priorities(body.model_dump())


# ══════════════════════════════════════════════════════════════════════════════
# REVENUE CONSCIOUSNESS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/revenue/dashboard")
async def get_revenue_dashboard() -> dict[str, Any]:
    return revenue_consciousness.get_revenue_dashboard()


@router.get("/revenue/pricing-tiers")
async def get_pricing_tiers() -> dict[str, Any]:
    from app.services.intelligence.revenue_consciousness import PRICING_TIERS
    return {"pricing_tiers": PRICING_TIERS}


class ClientLTVRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    tier: str = Field(default="GROWTH", max_length=50)
    months_active: int = Field(default=1, ge=0, le=120)
    monthly_value: float = Field(default=0.0, ge=0.0, le=1_000_000.0)
    churn_risk_score: float = Field(default=0.05, ge=0.0, le=1.0)


@router.post("/revenue/compute-ltv")
@limiter.limit("30/minute")
async def compute_ltv(body: ClientLTVRequest, request: Request) -> dict[str, Any]:
    return revenue_consciousness.compute_ltv(body.model_dump())


class ChurnRiskRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    observed_signals: list[str] = Field(default_factory=list, max_length=50)


@router.post("/revenue/churn-risk")
@limiter.limit("30/minute")
async def score_churn_risk(body: ChurnRiskRequest, request: Request) -> dict[str, Any]:
    return revenue_consciousness.score_churn_risk(body.model_dump())


class UpsellRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    tier: str = Field(default="GROWTH", max_length=50)
    signals: list[str] = Field(default_factory=list, max_length=50)


@router.post("/revenue/upsell-opportunities")
@limiter.limit("20/minute")
async def identify_upsell_opportunities(body: UpsellRequest, request: Request) -> dict[str, Any]:
    return revenue_consciousness.identify_upsell_opportunities(body.model_dump())


class PipelineHealthRequest(BaseModel):
    mrr: float = Field(default=0.0, ge=0.0, le=100_000_000.0)
    monthly_growth_pct: float = Field(default=0.0, ge=-100.0, le=1000.0)
    hot_leads: int = Field(default=0, ge=0, le=10000)
    proposals_sent: int = Field(default=0, ge=0, le=10000)
    proposals_won: int = Field(default=0, ge=0, le=10000)
    avg_deal_value: float = Field(default=4000.0, ge=0.0, le=10_000_000.0)
    churn_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)


@router.post("/revenue/pipeline-health")
@limiter.limit("20/minute")
async def compute_pipeline_health(body: PipelineHealthRequest, request: Request) -> dict[str, Any]:
    return revenue_consciousness.compute_pipeline_health(body.model_dump())


class ProspectPricingRequest(BaseModel):
    company_size: int = Field(default=10, ge=1, le=100000)
    budget: float = Field(default=0.0, ge=0.0, le=10_000_000.0)
    complexity: str = Field(default="medium", max_length=50)
    urgency: str = Field(default="normal", max_length=50)


@router.post("/revenue/pricing-recommendation")
@limiter.limit("20/minute")
async def get_pricing_recommendation(body: ProspectPricingRequest, request: Request) -> dict[str, Any]:
    return revenue_consciousness.get_pricing_recommendation(body.model_dump())


# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/platform/dashboard")
async def get_platform_dashboard() -> dict[str, Any]:
    return platform_intelligence.get_platform_dashboard()


@router.get("/platform/tech-debt")
async def get_tech_debt() -> dict[str, Any]:
    return platform_intelligence.get_tech_debt_registry()


class CostPostureRequest(BaseModel):
    monthly_infra_usd: float = Field(default=0.0, ge=0.0, le=1_000_000.0)
    monthly_ai_api_usd: float = Field(default=0.0, ge=0.0, le=1_000_000.0)
    mrr: float = Field(default=0.0, ge=0.0, le=100_000_000.0)
    client_count: int = Field(default=1, ge=1, le=10000)


@router.post("/platform/cost-posture")
@limiter.limit("20/minute")
async def assess_cost_posture(body: CostPostureRequest, request: Request) -> dict[str, Any]:
    return platform_intelligence.assess_cost_posture(body.model_dump())


class ScalingMetricsRequest(BaseModel):
    cpu_pct: float = Field(default=30.0, ge=0.0, le=100.0)
    memory_pct: float = Field(default=40.0, ge=0.0, le=100.0)
    p99_latency_ms: float = Field(default=200.0, ge=0.0, le=60000.0)
    error_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ecs_task_count: int = Field(default=2, ge=1, le=100)


@router.post("/platform/scaling-readiness")
@limiter.limit("20/minute")
async def assess_scaling_readiness(body: ScalingMetricsRequest, request: Request) -> dict[str, Any]:
    return platform_intelligence.assess_scaling_readiness(body.model_dump())


class SecurityScanRequest(BaseModel):
    violations: list[str] = Field(default_factory=list, max_length=100)


@router.post("/platform/security-posture")
@limiter.limit("10/minute")
async def assess_security_posture(body: SecurityScanRequest, request: Request) -> dict[str, Any]:
    return platform_intelligence.assess_security_posture(body.model_dump())


class DeploymentRiskRequest(BaseModel):
    changed_files: list[str] = Field(default_factory=list, max_length=1000)
    has_db_migration: bool = Field(default=False)
    has_schema_change: bool = Field(default=False)
    breaking_api_changes: bool = Field(default=False)
    rollback_tested: bool = Field(default=False)


@router.post("/platform/deployment-risk")
@limiter.limit("20/minute")
async def assess_deployment_risk(body: DeploymentRiskRequest, request: Request) -> dict[str, Any]:
    return platform_intelligence.assess_deployment_risk(body.model_dump())


# ══════════════════════════════════════════════════════════════════════════════
# SALES AUTONOMY
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/sales/dashboard")
async def get_sales_dashboard() -> dict[str, Any]:
    return sales_autonomy.get_sales_dashboard()


@router.get("/sales/objection/{objection_type}")
async def get_objection_playbook(objection_type: str) -> dict[str, Any]:
    return sales_autonomy.handle_objection(objection_type)


@router.get("/sales/sequence/{tier}")
async def get_outreach_sequence(tier: str) -> dict[str, Any]:
    return sales_autonomy.get_outreach_sequence(tier.upper())


class LeadScoringRequest(BaseModel):
    lead_id: str = Field(default="", max_length=100)
    company_fit: Any = Field(default="company_size_10_to_200")
    buying_intent: Any = Field(default={})
    decision_authority: Any = Field(default="unknown")
    budget_signals: Any = Field(default="no_budget_signals")
    timing: Any = Field(default="within_90_days")


@router.post("/sales/score-lead")
@limiter.limit("30/minute")
async def score_lead(body: LeadScoringRequest, request: Request) -> dict[str, Any]:
    return sales_autonomy.score_lead(body.model_dump())


class WinLossRequest(BaseModel):
    deal_id: str = Field(default="", max_length=100)
    outcome: str = Field(min_length=2, max_length=10)
    factors_observed: list[str] = Field(default_factory=list, max_length=50)


@router.post("/sales/analyze-win-loss")
@limiter.limit("20/minute")
async def analyze_win_loss(body: WinLossRequest, request: Request) -> dict[str, Any]:
    return sales_autonomy.analyze_win_loss(body.model_dump())


class ProposalReadinessRequest(BaseModel):
    lead_id: str = Field(default="", max_length=100)
    discovery_call_completed: bool = Field(default=False)
    budget_confirmed: bool = Field(default=False)
    decision_maker_identified: bool = Field(default=False)
    timeline_stated: bool = Field(default=False)
    pain_points_mapped: bool = Field(default=False)
    tier: str = Field(default="WARM", max_length=20)


@router.post("/sales/proposal-readiness")
@limiter.limit("20/minute")
async def assess_proposal_readiness(body: ProposalReadinessRequest, request: Request) -> dict[str, Any]:
    return sales_autonomy.assess_proposal_readiness(body.model_dump())


# ══════════════════════════════════════════════════════════════════════════════
# SUPREME SNAPSHOT — full 10x intelligence overview
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/snapshot")
async def supreme_snapshot(
    mrr: float = Query(default=0.0, ge=0.0, le=100_000_000.0),
) -> dict[str, Any]:
    return {
        "system": "JARVIS Supreme Intelligence Layer",
        "status": "FULLY_OPERATIONAL",
        "subsystems": {
            "constitution": "12 constitutional laws, authority matrix, escalation framework",
            "autonomous_ceo": "Strategic pillars, opportunity scoring, expansion roadmap",
            "revenue_consciousness": "LTV computation, churn prevention, upsell intelligence",
            "platform_intelligence": "Cost posture, scaling triggers, security posture, deployment risk",
            "sales_autonomy": "Lead scoring, outreach sequences, objection playbook, win/loss analysis",
        },
        "constitution_summary": jarvis_constitution.get_constitution_summary(),
        "ceo_phase": autonomous_ceo.get_expansion_roadmap(mrr)["phase_title"],
        "revenue_milestones": revenue_consciousness.get_revenue_dashboard()["milestones"],
        "platform_sla": platform_intelligence.get_platform_dashboard()["sla_standards"],
        "sales_tiers": list(sales_autonomy.get_sales_dashboard()["lead_tiers"]),
        "evaluated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
