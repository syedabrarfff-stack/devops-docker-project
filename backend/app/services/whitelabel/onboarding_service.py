"""
White-Label Onboarding Service.

Takes a new agency client from "just signed up" to "JARVIS is live and sending"
in 7 steps. Every step is an API call. The React wizard calls each step in order.

After Step 7, the tenant's JARVIS instance is fully configured and operational.
Their leads are isolated. Their outreach goes from their email. Their dashboard
shows their branding. JARVIS runs under their name.
"""
from __future__ import annotations

import logging
import secrets
import string
from datetime import UTC, datetime
from uuid import UUID

from app.services.tenancy import TenantManager
from app.services.whitelabel.white_label_service import white_label, PLAN_LIMITS
from app.models.tenant import PlanTier

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Orchestrates the full 7-step white-label onboarding flow.
    Each step is idempotent — can be called again if the agency updates details.
    """

    async def create_agency_tenant(
        self,
        company_name: str,
        admin_email: str,
        plan_tier: str = "STARTER",
    ) -> dict:
        """
        Pre-step: Create the tenant record and return credentials.
        Called when agency submits signup form and Stripe confirms payment.
        """
        manager = TenantManager()

        # Generate a secure temporary password
        temp_password = self._generate_temp_password()

        try:
            tenant, user = await manager.create_tenant(
                name=company_name,
                plan_tier=plan_tier,
                admin_email=admin_email,
                admin_password=temp_password,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        logger.info("New agency tenant created: %s (%s)", company_name, str(tenant.tenant_id))

        return {
            "tenant_id": str(tenant.tenant_id),
            "company_name": company_name,
            "plan_tier": plan_tier,
            "admin_email": admin_email,
            "temp_password": temp_password,
            "api_key": getattr(tenant, "_plain_api_key", None),
            "next_step": "Step 1: Configure branding",
            "onboarding_url": f"/onboarding/{tenant.tenant_id}",
            "created_at": datetime.now(UTC).isoformat(),
            "message": (
                f"Welcome to JARVIS. Your agency instance is being configured. "
                f"Login with {admin_email} / {temp_password} — change password on first login."
            ),
        }

    async def step1_branding(
        self,
        tenant_id: UUID,
        company_name: str,
        tagline: str = "",
        logo_url: str = "",
        primary_color: str = "#3b82f6",
        company_website: str = "",
        founder_name: str = "",
    ) -> dict:
        """Step 1 — Company identity and branding."""
        result = await white_label.apply_branding(
            tenant_id, company_name, tagline, logo_url,
            primary_color, company_website, founder_name
        )
        result["step"] = 1
        result["next_step"] = "Step 2: Configure team personas"
        return result

    async def step2_personas(
        self,
        tenant_id: UUID,
        personas: list[dict],
        email_domain: str,
    ) -> dict:
        """
        Step 2 — Team identity.
        Agency provides names for each role. JARVIS uses these in all outreach.
        Minimum: 1 persona (sales/outreach). Maximum: 9.

        Example persona:
        {
            "name": "James Harper",
            "role": "sales",
            "title": "Client Acquisition Specialist",
            "is_primary_outreach": true
        }
        """
        result = await white_label.configure_personas(tenant_id, personas, email_domain)
        result["step"] = 2
        result["next_step"] = "Step 3: Add email credentials"
        return result

    async def step3_email(
        self,
        tenant_id: UUID,
        gmail_address: str,
        gmail_app_password: str,
        reply_to_name: str = "",
    ) -> dict:
        """
        Step 3 — Email sending credentials.
        JARVIS will send outreach FROM this address, displayed as the primary persona name.

        For Google Workspace: use App Password (16 chars, no spaces).
        Gmail must have IMAP enabled and 2FA active.
        """
        result = await white_label.configure_email(
            tenant_id, gmail_address, gmail_app_password, reply_to_name
        )
        result["step"] = 3
        result["next_step"] = "Step 4: Connect integrations (optional)"
        return result

    async def step4_integrations(
        self,
        tenant_id: UUID,
        apollo_api_key: str = "",
        hubspot_api_key: str = "",
        notion_api_key: str = "",
        slack_webhook_url: str = "",
    ) -> dict:
        """
        Step 4 — Third-party integrations.
        All optional — JARVIS works without them but works better with them.
        """
        result = await white_label.configure_integrations(
            tenant_id, apollo_api_key, hubspot_api_key, notion_api_key, slack_webhook_url
        )
        result["step"] = 4
        result["next_step"] = "Step 5: Define target markets"
        return result

    async def step5_market_focus(
        self,
        tenant_id: UUID,
        target_markets: list[str],
        target_industries: list[str],
        service_offerings: list[str],
        icp_description: str = "",
    ) -> dict:
        """
        Step 5 — Who JARVIS hunts.
        Sets the ICP (Ideal Client Profile) that guides lead discovery and outreach.
        """
        result = await white_label.configure_market_focus(
            tenant_id, target_markets, target_industries,
            service_offerings, icp_description
        )
        result["step"] = 5
        result["next_step"] = "Step 6: Review and go live"
        return result

    async def step6_review(self, tenant_id: UUID) -> dict:
        """Step 6 — Show the full checklist before going live."""
        checklist = await white_label.get_onboarding_checklist(tenant_id)
        config = await white_label.get_config(tenant_id)

        all_done = checklist.get("steps", {})
        required_done = all([
            all_done.get("branding"),
            all_done.get("personas"),
            all_done.get("email_config"),
        ])

        return {
            "step": 6,
            "checklist": checklist,
            "ready_to_launch": required_done,
            "config_preview": config.to_dict() if config else {},
            "warning": (
                None if required_done
                else "Complete steps 1–3 before going live. Steps 4–5 are optional."
            ),
            "next_step": "Step 7: Confirm and launch" if required_done else checklist.get("next_step"),
        }

    async def step7_go_live(self, tenant_id: UUID) -> dict:
        """
        Step 7 — Final confirmation. Flips the live switch.
        After this, JARVIS begins operating for this tenant:
        - Lead discovery starts at next scheduled run
        - Outreach queue activates
        - Morning briefing scheduled
        - Dashboard is live
        """
        checklist = await white_label.get_onboarding_checklist(tenant_id)
        steps = checklist.get("steps", {})

        if not steps.get("branding") or not steps.get("personas") or not steps.get("email_config"):
            return {
                "error": "Cannot go live — required steps incomplete.",
                "missing": checklist.get("next_step"),
            }

        result = await white_label.mark_onboarding_complete(tenant_id)

        logger.info("🚀 Tenant %s went live!", tenant_id)

        return {
            "step": 7,
            "status": "LIVE",
            "tenant_id": str(tenant_id),
            "message": (
                "JARVIS is now operational for your agency. "
                "Lead discovery begins at next scheduled run. "
                "Outreach will start within 24 hours. "
                "Your dashboard is live."
            ),
            "dashboard_url": "/dashboard",
            "support": "support@aliyarsolutions.com",
            "went_live_at": datetime.now(UTC).isoformat(),
        }

    async def get_all_plan_options(self) -> dict:
        """Return all plan tiers with pricing for the signup page."""
        return {
            "plans": [
                {
                    "tier": tier.value,
                    "limits": limits,
                    "recommended": tier == PlanTier.GROWTH,
                    "label": "Most Popular" if tier == PlanTier.GROWTH else (
                        "Best Value" if tier == PlanTier.ENTERPRISE else ""
                    ),
                }
                for tier, limits in PLAN_LIMITS.items()
            ]
        }

    def _generate_temp_password(self) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$"
        return "".join(secrets.choice(alphabet) for _ in range(16))


onboarding = OnboardingService()
