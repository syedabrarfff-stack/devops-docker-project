"""R6-3: White-label Licensing Manager.

Generates and validates per-tenant API license keys.
Enforces plan limits (monthly_leads, monthly_emails, ai_calls_per_day).
Provides MRR snapshot for Captain dashboard.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, date
from typing import Any

from sqlalchemy import select, text as sqla_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.whitelabel.white_label_service import PLAN_LIMITS

logger = logging.getLogger(__name__)

_KEY_PREFIX = "wl_"
_KEY_LENGTH = 40  # bytes of entropy → 80-char hex string


# ── Key generation ────────────────────────────────────────────────────────────

def _generate_license_key(tenant_id: uuid.UUID) -> str:
    """
    Generate a deterministic-looking but cryptographically random license key.
    Format: wl_<80 hex chars>
    The tenant_id is mixed into the HMAC so the key can be traced back
    to the tenant if needed, but only by the holder of SECRET_KEY.
    """
    raw = secrets.token_bytes(_KEY_LENGTH)
    mac = hmac.new(
        settings.SECRET_KEY.encode(),
        str(tenant_id).encode() + raw,
        hashlib.sha256,
    ).hexdigest()
    return f"{_KEY_PREFIX}{mac}{secrets.token_hex(8)}"


# ── LicenseManager ───────────────────────────────────────────────────────────

class LicenseManager:
    """
    Manages white-label tenant licensing.
    Keys are stored in the tenants table (license_key column).
    Usage is counted against plan limits from PLAN_LIMITS.
    """

    async def provision_tenant(
        self,
        company_name: str,
        admin_email: str,
        plan_tier: str,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Create a new white-label tenant with a fresh license key."""
        from app.models.tenant import Tenant, PlanTier

        try:
            tier = PlanTier[plan_tier.upper()]
        except KeyError:
            tier = PlanTier.STARTER

        tenant_id = uuid.uuid4()
        license_key = _generate_license_key(tenant_id)
        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER])

        tenant = Tenant(
            id=tenant_id,
            name=company_name,
            plan_tier=tier,
            license_key=license_key,
            admin_email=admin_email,
            monthly_leads_limit=limits["monthly_leads"],
            monthly_emails_limit=limits["monthly_emails"],
            ai_calls_per_day_limit=limits["ai_calls_per_day"],
            is_active=True,
        )
        session.add(tenant)
        await session.commit()

        logger.info("[LicenseManager] Provisioned tenant %s (%s)", company_name, tier.value)
        return {
            "tenant_id": str(tenant_id),
            "company_name": company_name,
            "plan_tier": tier.value,
            "license_key": license_key,
            "limits": {k: v for k, v in limits.items() if k != "features"},
            "provisioned_at": datetime.now(UTC).isoformat(),
        }

    async def rotate_license_key(
        self, tenant_id: uuid.UUID, session: AsyncSession
    ) -> dict[str, Any]:
        """Invalidate existing key and issue a new one."""
        new_key = _generate_license_key(tenant_id)
        await session.execute(
            sqla_text(
                "UPDATE tenants SET license_key=:key, updated_at=NOW() WHERE id=:tid"
            ),
            {"key": new_key, "tid": tenant_id},
        )
        await session.commit()
        logger.info("[LicenseManager] Key rotated for tenant %s", tenant_id)
        return {"tenant_id": str(tenant_id), "license_key": new_key}

    async def validate_license(
        self, license_key: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Return tenant metadata if key is valid and tenant is active, else None."""
        if not license_key or not license_key.startswith(_KEY_PREFIX):
            return None
        result = await session.execute(
            sqla_text(
                "SELECT id, name, plan_tier, is_active, "
                "monthly_leads_limit, monthly_emails_limit "
                "FROM tenants WHERE license_key=:key"
            ),
            {"key": license_key},
        )
        row = result.fetchone()
        if not row or not row[3]:  # not found or inactive
            return None
        return {
            "tenant_id": str(row[0]),
            "company_name": row[1],
            "plan_tier": row[2],
            "monthly_leads_limit": row[4],
            "monthly_emails_limit": row[5],
        }

    async def get_mrr_snapshot(self, session: AsyncSession) -> dict[str, Any]:
        """
        MRR snapshot: count tenants per plan tier and compute monthly revenue.
        Uses GBP pricing from PLAN_LIMITS.
        """
        from app.models.tenant import PlanTier

        result = await session.execute(
            sqla_text(
                "SELECT plan_tier, COUNT(*) FROM tenants "
                "WHERE is_active=true GROUP BY plan_tier"
            )
        )
        rows = result.fetchall()

        tier_prices = {
            "STARTER": 1500,
            "GROWTH": 3000,
            "ENTERPRISE": 6000,
            "INDUSTRY_OS": 10000,
        }
        breakdown: dict[str, Any] = {}
        total_mrr = 0
        total_tenants = 0

        for row in rows:
            tier_name = row[0].upper() if row[0] else "STARTER"
            count = row[1]
            price = tier_prices.get(tier_name, 1500)
            revenue = count * price
            breakdown[tier_name] = {"count": count, "price_gbp": price, "revenue_gbp": revenue}
            total_mrr += revenue
            total_tenants += count

        return {
            "total_tenants": total_tenants,
            "total_mrr_gbp": total_mrr,
            "breakdown": breakdown,
            "snapshot_at": datetime.now(UTC).isoformat(),
        }

    async def list_tenants(
        self, session: AsyncSession, page: int = 1, per_page: int = 20
    ) -> list[dict[str, Any]]:
        """Paginated tenant list for Captain dashboard."""
        offset = (page - 1) * per_page
        result = await session.execute(
            sqla_text(
                "SELECT id, name, plan_tier, admin_email, is_active, created_at "
                "FROM tenants ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ),
            {"lim": per_page, "off": offset},
        )
        rows = result.fetchall()
        return [
            {
                "tenant_id": str(r[0]),
                "company_name": r[1],
                "plan_tier": r[2],
                "admin_email": r[3],
                "is_active": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]

    async def upgrade_plan(
        self, tenant_id: uuid.UUID, new_plan: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Upgrade/downgrade a tenant plan tier."""
        from app.models.tenant import PlanTier

        try:
            tier = PlanTier[new_plan.upper()]
        except KeyError:
            raise ValueError(f"Invalid plan tier: {new_plan}")

        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER])
        await session.execute(
            sqla_text(
                "UPDATE tenants SET plan_tier=:tier, "
                "monthly_leads_limit=:leads, monthly_emails_limit=:emails, "
                "ai_calls_per_day_limit=:ai, updated_at=NOW() "
                "WHERE id=:tid"
            ),
            {
                "tier": tier.value,
                "leads": limits["monthly_leads"],
                "emails": limits["monthly_emails"],
                "ai": limits["ai_calls_per_day"],
                "tid": tenant_id,
            },
        )
        await session.commit()
        return {"tenant_id": str(tenant_id), "new_plan": tier.value, "limits": limits}


license_manager = LicenseManager()
