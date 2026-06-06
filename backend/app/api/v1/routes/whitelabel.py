"""
White-Label JARVIS — Onboarding & Agency Management API.

These routes power:
1. The public signup page (create tenant + get plan options)
2. The 7-step onboarding wizard
3. Agency admin panel (config review, usage stats)
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

from app.services.whitelabel.onboarding_service import onboarding
from app.services.whitelabel.white_label_service import white_label

router = APIRouter(prefix="/whitelabel", tags=["White-Label Onboarding"])


# ── Signup / Plan Selection ───────────────────────────────────────────────────

@router.get("/plans")
async def get_plan_options():
    """Public — show all plan tiers on the landing page."""
    return await onboarding.get_all_plan_options()


class SignupRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    admin_email: str = Field(min_length=5, max_length=255)
    plan_tier: str = Field(default="STARTER")

@router.post("/signup")
async def agency_signup(body: SignupRequest):
    """
    Called when an agency completes payment on the landing page.
    Creates tenant, returns login credentials, begins onboarding.
    """
    result = await onboarding.create_agency_tenant(
        body.company_name, body.admin_email, body.plan_tier
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── 7-Step Onboarding Wizard ──────────────────────────────────────────────────

class BrandingRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    tagline: str = ""
    logo_url: str = ""
    primary_color: str = "#3b82f6"
    company_website: str = ""
    founder_name: str = ""

@router.post("/onboarding/{tenant_id}/step1-branding")
async def onboarding_step1(tenant_id: UUID, body: BrandingRequest):
    return await onboarding.step1_branding(
        tenant_id, body.company_name, body.tagline,
        body.logo_url, body.primary_color, body.company_website, body.founder_name
    )


class PersonaItem(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    role: str = Field(default="sales")
    title: str = ""
    email: str = ""
    is_primary_outreach: bool = False

class PersonasRequest(BaseModel):
    personas: list[PersonaItem] = Field(min_length=1, max_length=9)
    email_domain: str = Field(min_length=3, max_length=200)

@router.post("/onboarding/{tenant_id}/step2-personas")
async def onboarding_step2(tenant_id: UUID, body: PersonasRequest):
    return await onboarding.step2_personas(
        tenant_id,
        [p.model_dump() for p in body.personas],
        body.email_domain,
    )


class EmailConfigRequest(BaseModel):
    executive_email: str = Field(min_length=5, max_length=255)
    executive_name: str = Field(default="Joseph David", min_length=2, max_length=120)
    reply_to_name: str = ""

@router.post("/onboarding/{tenant_id}/step3-email")
async def onboarding_step3(tenant_id: UUID, body: EmailConfigRequest):
    return await onboarding.step3_email(
        tenant_id, body.executive_email, body.executive_name, body.reply_to_name
    )


class IntegrationsRequest(BaseModel):
    apollo_api_key: str = ""
    hubspot_api_key: str = ""
    notion_api_key: str = ""
    slack_webhook_url: str = ""

@router.post("/onboarding/{tenant_id}/step4-integrations")
async def onboarding_step4(tenant_id: UUID, body: IntegrationsRequest):
    return await onboarding.step4_integrations(
        tenant_id, body.apollo_api_key, body.hubspot_api_key,
        body.notion_api_key, body.slack_webhook_url,
    )


class MarketFocusRequest(BaseModel):
    target_markets: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    service_offerings: list[str] = Field(default_factory=list)
    icp_description: str = ""

@router.post("/onboarding/{tenant_id}/step5-market")
async def onboarding_step5(tenant_id: UUID, body: MarketFocusRequest):
    return await onboarding.step5_market_focus(
        tenant_id, body.target_markets, body.target_industries,
        body.service_offerings, body.icp_description,
    )


@router.get("/onboarding/{tenant_id}/step6-review")
async def onboarding_step6(tenant_id: UUID):
    return await onboarding.step6_review(tenant_id)


@router.post("/onboarding/{tenant_id}/step7-golive")
async def onboarding_step7(tenant_id: UUID):
    result = await onboarding.step7_go_live(tenant_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Agency Admin Panel ────────────────────────────────────────────────────────

@router.get("/config/{tenant_id}")
async def get_white_label_config(tenant_id: UUID):
    """Agency owner sees their full config (passwords masked)."""
    config = await white_label.get_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return config.to_dict()


@router.get("/config/{tenant_id}/checklist")
async def get_onboarding_checklist(tenant_id: UUID):
    return await white_label.get_onboarding_checklist(tenant_id)


@router.get("/config/{tenant_id}/personas")
async def get_tenant_personas(tenant_id: UUID):
    personas = await white_label.get_tenant_personas(tenant_id)
    return {"personas": personas, "count": len(personas)}


@router.get("/config/{tenant_id}/plan-limits")
async def get_tenant_plan_limits(tenant_id: UUID):
    config = await white_label.get_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Read plan tier from tenant
    from app.core.database import get_db
    from app.models.tenant import Tenant
    from sqlalchemy import select
    async for db in get_db():
        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant:
            limits = await white_label.get_plan_limits(tenant.plan_tier.value)
            return {"plan_tier": tenant.plan_tier.value, "limits": limits}
    raise HTTPException(status_code=404, detail="Tenant not found")
