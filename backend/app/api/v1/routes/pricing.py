"""
JARVIS Pricing Engine — intelligent scope-aware pricing for Aliyar Solutions.
Never quotes cheap. Prices based on company size, service scope, and complexity.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai.router import ai_router
from app.services.intelligence.jarvis_awareness import JARVIS_AWARENESS_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pricing", tags=["pricing"])

# ── Pricing brackets ──────────────────────────────────────────────────────────

PRICING_MATRIX = {
    "small": {
        "label": "Small Business / Startup",
        "monthly_revenue_range": "under $20k/month",
        "packages": {
            "starter_website": {"price": 1200, "label": "Professional Website", "delivery": "5 days"},
            "crm_setup": {"price": 1800, "label": "CRM + Lead Pipeline", "delivery": "7 days"},
            "ai_automation_basic": {"price": 2500, "label": "AI Workflow Automation (Basic)", "delivery": "10 days"},
            "social_content": {"price": 800, "label": "Social Media Content System", "delivery": "3 days"},
        },
        "retainer": {"min": 1500, "max": 3500, "label": "Monthly Operations Retainer"},
    },
    "medium": {
        "label": "Mid-Size Business",
        "monthly_revenue_range": "$20k–$200k/month",
        "packages": {
            "full_digital": {"price": 4500, "label": "Complete Digital Transformation", "delivery": "14 days"},
            "sales_engine": {"price": 5500, "label": "AI Sales Engine + CRM", "delivery": "14 days"},
            "automation_suite": {"price": 6500, "label": "Full Automation Suite", "delivery": "21 days"},
            "cloud_migration": {"price": 8000, "label": "Cloud Infrastructure Migration", "delivery": "30 days"},
        },
        "retainer": {"min": 3500, "max": 6500, "label": "Monthly Managed Operations"},
    },
    "enterprise": {
        "label": "Enterprise / Large Business",
        "monthly_revenue_range": "$200k+/month",
        "packages": {
            "enterprise_platform": {"price": 12000, "label": "Enterprise Platform Build", "delivery": "45 days"},
            "ai_infrastructure": {"price": 15000, "label": "Full AI Infrastructure", "delivery": "60 days"},
            "aws_deployment": {"price": 9000, "label": "AWS Production Deployment", "delivery": "30 days"},
            "white_label": {"price": 18000, "label": "White-Label Technology Platform", "delivery": "90 days"},
        },
        "retainer": {"min": 6000, "max": 12000, "label": "Executive Technology Retainer"},
    },
}

SERVICE_MULTIPLIERS = {
    "e-commerce": 1.3,
    "healthcare": 1.4,
    "finance": 1.5,
    "legal": 1.35,
    "real_estate": 1.2,
    "saas": 1.4,
    "manufacturing": 1.25,
    "standard": 1.0,
}


# ── Models ────────────────────────────────────────────────────────────────────

class PricingRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=300)
    industry: Optional[str] = Field(default="standard", max_length=100)
    employee_count: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    estimated_revenue: Optional[str] = Field(default=None, max_length=100)
    services_needed: list[str] = Field(default_factory=list)
    urgency: Optional[str] = Field(default="normal", max_length=50)
    notes: Optional[str] = Field(default=None, max_length=5_000)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/estimate")
async def generate_pricing_estimate(body: PricingRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a pricing estimate for a prospect. JARVIS analyses requirements
    and returns a Captain-ready proposal package with pricing.
    """
    # Determine size tier
    tier = "small"
    if body.estimated_revenue:
        rev = body.estimated_revenue.lower()
        if "200k" in rev or "enterprise" in rev:
            tier = "enterprise"
        elif "20k" in rev or "medium" in rev or "mid" in rev:
            tier = "medium"

    if body.employee_count:
        if body.employee_count > 200:
            tier = "enterprise"
        elif body.employee_count > 25:
            tier = "medium"

    matrix = PRICING_MATRIX[tier]
    multiplier = SERVICE_MULTIPLIERS.get(body.industry.lower(), 1.0)

    # Build package recommendations
    packages = []
    for pkg_key, pkg in matrix["packages"].items():
        adjusted_price = int(pkg["price"] * multiplier)

        # Mark urgent surcharge
        if body.urgency == "urgent":
            adjusted_price = int(adjusted_price * 1.25)

        packages.append({
            "key": pkg_key,
            "label": pkg["label"],
            "price": adjusted_price,
            "original_price": pkg["price"],
            "delivery": pkg["delivery"],
            "industry_adjusted": multiplier != 1.0,
        })

    retainer = matrix["retainer"]
    retainer_min = int(retainer["min"] * multiplier)
    retainer_max = int(retainer["max"] * multiplier)

    # AI-generated positioning statement
    positioning = ""
    try:
        prompt = (
            f"Write a 2-sentence value statement for a proposal to {body.company_name} "
            f"({body.industry or 'general'} industry, {tier} size). "
            f"Services requested: {', '.join(body.services_needed) if body.services_needed else 'digital transformation'}. "
            f"Sound premium, confident, outcome-focused. No fluff. First person as 'Aliyar Solutions'."
        )
        resp, _ = await ai_router.chat(
            messages=[
                {"role": "system", "content": JARVIS_AWARENESS_PROMPT},
                {"role": "user", "content": prompt},
            ],
            task_type="FAST",
            max_tokens=100,
        )
        positioning = resp.content or ""
    except Exception:
        positioning = (
            f"Aliyar Solutions is ready to deploy a complete {tier}-tier solution for {body.company_name}. "
            f"Our team will handle end-to-end delivery with a guaranteed timeline."
        )

    return {
        "company": body.company_name,
        "tier": tier,
        "tier_label": matrix["label"],
        "industry": body.industry,
        "packages": packages,
        "retainer": {
            "label": retainer["label"],
            "monthly_min": retainer_min,
            "monthly_max": retainer_max,
            "range": f"${retainer_min:,}–${retainer_max:,}/month",
        },
        "positioning": positioning,
        "payment_terms": "50% upfront, 50% on delivery (projects) | Monthly advance (retainers)",
        "urgency_surcharge": body.urgency == "urgent",
        "requires_captain_approval": True,
        "note": "All pricing requires Captain approval before sharing with client.",
    }


@router.get("/matrix")
async def pricing_matrix():
    """Full pricing matrix — for Captain reference."""
    return {
        "pricing_philosophy": (
            "Aliyar Solutions prices based on value delivered, not time spent. "
            "We never say cheap or affordable — we say efficient and enterprise-grade."
        ),
        "tiers": PRICING_MATRIX,
        "industry_multipliers": SERVICE_MULTIPLIERS,
        "payment_terms": "50% upfront, 50% on delivery (projects) | Monthly advance (retainers)",
    }
