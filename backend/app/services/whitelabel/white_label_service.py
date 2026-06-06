"""
White-Label Configuration Engine.

Every tenant (agency client) gets their own fully configured JARVIS instance.
This service manages everything that makes their JARVIS uniquely theirs:
branding, team personas, email credentials, target markets, service offerings,
and usage limits — all isolated from every other tenant.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tenant import Tenant, PlanTier

logger = logging.getLogger(__name__)


# Plan tier limits — what each tier gets
PLAN_LIMITS = {
    PlanTier.STARTER: {
        "monthly_leads": 500,
        "monthly_emails": 1500,
        "max_users": 1,
        "max_personas": 3,
        "ai_calls_per_day": 100,
        "features": ["outreach", "leads", "crm", "briefing"],
        "price_gbp": 1500,
        "support": "email",
    },
    PlanTier.GROWTH: {
        "monthly_leads": 2000,
        "monthly_emails": 6000,
        "max_users": 3,
        "max_personas": 9,
        "ai_calls_per_day": 500,
        "features": ["outreach", "leads", "crm", "briefing", "council", "proposals", "intelligence"],
        "price_gbp": 3000,
        "support": "priority_email",
    },
    PlanTier.ENTERPRISE: {
        "monthly_leads": -1,       # unlimited
        "monthly_emails": -1,      # unlimited
        "max_users": 10,
        "max_personas": -1,        # unlimited
        "ai_calls_per_day": -1,    # unlimited
        "features": ["all"],
        "price_gbp": 6000,
        "support": "dedicated_slack",
    },
    PlanTier.INDUSTRY_OS: {
        "monthly_leads": -1,
        "monthly_emails": -1,
        "max_users": -1,
        "max_personas": -1,
        "ai_calls_per_day": -1,
        "features": ["all", "white_label_resell", "custom_models"],
        "price_gbp": 10000,
        "support": "dedicated_manager",
    },
}

# Default persona templates — agency fills in the names/emails
DEFAULT_PERSONA_ROLES = [
    {"role": "sales",      "title": "Client Acquisition Specialist",    "domain": "Sales, lead qualification"},
    {"role": "cloud",      "title": "Solutions Architect",              "domain": "Cloud infrastructure, AWS"},
    {"role": "ai",         "title": "Workflow Consultant",              "domain": "AI automation, process integration"},
    {"role": "devops",     "title": "Deployment Engineer",              "domain": "DevOps, CI/CD"},
    {"role": "crm",        "title": "Business Optimisation Specialist", "domain": "Analytics, CRM, revenue ops"},
    {"role": "security",   "title": "Security Consultant",              "domain": "Cybersecurity, compliance"},
    {"role": "infra",      "title": "Infrastructure Strategist",        "domain": "Architecture, scaling"},
    {"role": "process",    "title": "Process Integration Specialist",   "domain": "Automation, API integration"},
    {"role": "account",    "title": "Account Coordinator",              "domain": "Client success, reporting"},
]


class WhiteLabelConfig:
    """Full white-label configuration for one tenant."""

    def __init__(self, tenant_id: UUID, settings: dict):
        self.tenant_id = tenant_id
        self._settings = settings

    @property
    def branding(self) -> dict:
        return self._settings.get("branding", {})

    @property
    def personas(self) -> list[dict]:
        return self._settings.get("personas", [])

    @property
    def email_config(self) -> dict:
        return self._settings.get("email_config", {})

    @property
    def integrations(self) -> dict:
        return self._settings.get("integrations", {})

    @property
    def target_markets(self) -> list[str]:
        return self._settings.get("target_markets", [])

    @property
    def service_offerings(self) -> list[str]:
        return self._settings.get("service_offerings", [])

    @property
    def onboarding_complete(self) -> bool:
        required = ["branding", "personas", "email_config"]
        return all(
            self._settings.get(k) for k in required
        )

    def to_dict(self) -> dict:
        return {
            "tenant_id": str(self.tenant_id),
            "branding": self.branding,
            "personas": self.personas,
            "email_config": {
                k: ("***" if "password" in k.lower() or "secret" in k.lower() else v)
                for k, v in self.email_config.items()
            },
            "integrations": {
                k: ("***configured***" if v else "not_set")
                for k, v in self.integrations.items()
            },
            "target_markets": self.target_markets,
            "service_offerings": self.service_offerings,
            "onboarding_complete": self.onboarding_complete,
        }


class WhiteLabelService:
    """
    Manages the white-label configuration for every tenant.
    Called during onboarding and whenever a tenant updates their settings.
    """

    async def get_config(self, tenant_id: UUID) -> WhiteLabelConfig | None:
        async for db in get_db():
            result = await db.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return None
            return WhiteLabelConfig(tenant_id, tenant.settings or {})

    async def apply_branding(
        self,
        tenant_id: UUID,
        company_name: str,
        tagline: str = "",
        logo_url: str = "",
        primary_color: str = "#3b82f6",
        company_website: str = "",
        founder_name: str = "",
    ) -> dict:
        """Step 1 of onboarding — company identity."""
        return await self._patch_settings(tenant_id, {
            "branding": {
                "company_name": company_name,
                "tagline": tagline,
                "logo_url": logo_url,
                "primary_color": primary_color,
                "company_website": company_website,
                "founder_name": founder_name,
                "jarvis_internal_name": f"JARVIS — {company_name}",
            }
        })

    async def configure_personas(
        self,
        tenant_id: UUID,
        personas: list[dict],
        email_domain: str,
    ) -> dict:
        """
        Step 2 — set up the human team identity.
        Each persona gets a name, email, and role domain.
        """
        configured = []
        for i, persona_input in enumerate(personas[:9]):
            role_template = DEFAULT_PERSONA_ROLES[i] if i < len(DEFAULT_PERSONA_ROLES) else DEFAULT_PERSONA_ROLES[0]
            configured.append({
                "role": persona_input.get("role", role_template["role"]),
                "name": persona_input.get("name", f"Team Member {i+1}"),
                "title": persona_input.get("title", role_template["title"]),
                "email": persona_input.get("email", f"{persona_input.get('name', 'team').lower().replace(' ', '.')}@{email_domain}"),
                "domain": role_template["domain"],
                "is_primary_outreach": persona_input.get("is_primary_outreach", i == 0),
            })

        return await self._patch_settings(tenant_id, {
            "personas": configured,
            "email_domain": email_domain,
        })

    async def configure_email(
        self,
        tenant_id: UUID,
        executive_email: str,
        executive_name: str,
        reply_to_name: str = "",
    ) -> dict:
        """Step 3 — SES executive identity for outreach sending."""
        return await self._patch_settings(tenant_id, {
            "email_config": {
                "provider": "ses",
                "ses_from_email": executive_email,
                "ses_from_name": executive_name or "Joseph David",
                "reply_to_name": reply_to_name or executive_name or executive_email.split("@")[0],
                "configured_at": datetime.now(UTC).isoformat(),
            }
        })

    async def configure_integrations(
        self,
        tenant_id: UUID,
        apollo_api_key: str = "",
        hubspot_api_key: str = "",
        notion_api_key: str = "",
        slack_webhook_url: str = "",
    ) -> dict:
        """Step 4 — third-party integrations."""
        return await self._patch_settings(tenant_id, {
            "integrations": {
                "apollo_api_key": apollo_api_key,
                "hubspot_api_key": hubspot_api_key,
                "notion_api_key": notion_api_key,
                "slack_webhook_url": slack_webhook_url,
            }
        })

    async def configure_market_focus(
        self,
        tenant_id: UUID,
        target_markets: list[str],
        target_industries: list[str],
        service_offerings: list[str],
        icp_description: str = "",
    ) -> dict:
        """Step 5 — who JARVIS hunts for this tenant."""
        return await self._patch_settings(tenant_id, {
            "target_markets": target_markets,
            "target_industries": target_industries,
            "service_offerings": service_offerings,
            "icp_description": icp_description,
        })

    async def mark_onboarding_complete(self, tenant_id: UUID) -> dict:
        """Step 7 — flip the live switch."""
        return await self._patch_settings(tenant_id, {
            "onboarding_complete": True,
            "went_live_at": datetime.now(UTC).isoformat(),
        })

    async def get_plan_limits(self, plan_tier: str) -> dict:
        """Return limits for a plan tier."""
        tier = PlanTier(plan_tier) if isinstance(plan_tier, str) else plan_tier
        return PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER])

    async def get_tenant_email_credentials(self, tenant_id: UUID) -> dict:
        """
        Called by the outreach engine to get THIS tenant's executive email identity.
        Returns empty dict if not configured — outreach engine falls back to global.
        """
        config = await self.get_config(tenant_id)
        if not config:
            return {}
        email_cfg = config.email_config
        if not email_cfg.get("ses_from_email"):
            return {}
        return {
            "provider": "ses",
            "ses_from_email": email_cfg["ses_from_email"],
            "ses_from_name": email_cfg.get("ses_from_name") or "Joseph David",
            "reply_to_name": email_cfg.get("reply_to_name") or "Joseph David",
        }

    async def get_tenant_personas(self, tenant_id: UUID) -> list[dict]:
        """Called by outreach engine to get THIS tenant's persona identities."""
        config = await self.get_config(tenant_id)
        if not config or not config.personas:
            return []
        return config.personas

    async def get_onboarding_checklist(self, tenant_id: UUID) -> dict:
        """Shows what's done and what's missing in tenant setup."""
        config = await self.get_config(tenant_id)
        if not config:
            return {"error": "Tenant not found"}

        s = config._settings
        return {
            "tenant_id": str(tenant_id),
            "steps": {
                "branding":         bool(s.get("branding", {}).get("company_name")),
                "personas":         bool(s.get("personas")),
                "email_config":     bool(s.get("email_config", {}).get("ses_from_email")),
                "integrations":     bool(s.get("integrations")),
                "market_focus":     bool(s.get("target_markets")),
                "onboarding_done":  bool(s.get("onboarding_complete")),
            },
            "ready_to_launch": config.onboarding_complete,
            "next_step": self._next_onboarding_step(s),
        }

    def _next_onboarding_step(self, settings: dict) -> str:
        if not settings.get("branding", {}).get("company_name"):
            return "Step 1: Add company branding"
        if not settings.get("personas"):
            return "Step 2: Configure team personas"
        if not settings.get("email_config", {}).get("ses_from_email"):
            return "Step 3: Add executive email identity"
        if not settings.get("target_markets"):
            return "Step 4: Set target markets and ICP"
        if not settings.get("onboarding_complete"):
            return "Step 5: Review and go live"
        return "Complete — JARVIS is live"

    async def _patch_settings(self, tenant_id: UUID, patch: dict) -> dict:
        async for db in get_db():
            result = await db.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return {"error": f"Tenant {tenant_id} not found"}

            current = dict(tenant.settings or {})
            current.update(patch)
            tenant.settings = current
            await db.commit()
            await db.refresh(tenant)

            logger.info("White-label config updated for tenant %s: %s", tenant_id, list(patch.keys()))
            return {
                "tenant_id": str(tenant_id),
                "updated_keys": list(patch.keys()),
                "updated_at": datetime.now(UTC).isoformat(),
            }


white_label = WhiteLabelService()
