"""R6-3: White-label Licensing Manager.

Thin, Captain-facing layer over the same canonical tenant model used by
app/services/tenancy/tenant_manager.py (Tenant + User + TenantApiKey).

Originally this module maintained its own parallel idea of a tenant record
(dedicated license_key / admin_email / monthly_*_limit columns) that never
matched the actual Tenant schema and crashed on first use. Rather than adding
a second, competing representation of "tenant + credentials + limits" to the
database, this module now reads and writes the exact same tables tenant_manager
already uses correctly:
  - Tenant.api_key_hash / TenantApiKey  → license key issuance + validation
  - Tenant.settings["limits"]           → plan limits (derived from PLAN_LIMITS,
                                           overridable per-tenant)
  - User (role=ADMIN)                   → the tenant's admin contact
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.whitelabel.white_label_service import PLAN_LIMITS

logger = logging.getLogger(__name__)

_KEY_PREFIX = "wl_"


# ── Key generation ────────────────────────────────────────────────────────────

def _generate_license_key() -> str:
    """
    Generate a fresh license key. Stored only as a SHA-256 hash (in
    TenantApiKey.key_hash / Tenant.api_key_hash) — the plaintext value
    is returned to the caller exactly once, at issuance/rotation time.
    """
    return f"{_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100] or "tenant"


# ── LicenseManager ───────────────────────────────────────────────────────────

class LicenseManager:
    """Captain-facing white-label tenant provisioning, licensing, and MRR reporting."""

    async def provision_tenant(
        self,
        company_name: str,
        admin_email: str,
        plan_tier: str,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Create a new white-label tenant with a fresh license key + admin user."""
        from app.models.tenant import PlanTier, Tenant, TenantApiKey, User, UserRole
        from passlib.context import CryptContext

        try:
            tier = PlanTier[plan_tier.upper()]
        except KeyError:
            tier = PlanTier.STARTER

        tenant_id = uuid.uuid4()
        license_key = _generate_license_key()
        key_hash = _hash_key(license_key)
        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER])
        limits_payload = {k: v for k, v in limits.items() if k != "features"}

        slug = await self._unique_slug(session, _slugify(company_name))
        admin_password = secrets.token_urlsafe(16)

        tenant = Tenant(
            id=tenant_id,
            tenant_id=tenant_id,
            name=company_name,
            slug=slug,
            plan_tier=tier,
            api_key_hash=key_hash,
            settings={"limits": limits_payload},
            is_active=True,
        )
        user = User(
            tenant_id=tenant_id,
            email=admin_email.strip().lower(),
            hashed_password=CryptContext(schemes=["bcrypt"], deprecated="auto").hash(admin_password),
            role=UserRole.ADMIN,
            is_captain=False,
        )
        api_key_record = TenantApiKey(
            tenant_id=tenant_id,
            key_hash=key_hash,
            key_prefix=license_key[:16],
            name="default",
            is_active=True,
        )
        session.add_all([tenant, user, api_key_record])
        await session.commit()

        logger.info("[LicenseManager] Provisioned tenant %s (%s)", company_name, tier.value)
        return {
            "tenant_id": str(tenant_id),
            "company_name": company_name,
            "plan_tier": tier.value,
            "license_key": license_key,
            "admin_email": user.email,
            "admin_temp_password": admin_password,
            "limits": limits_payload,
            "provisioned_at": datetime.now(UTC).isoformat(),
        }

    async def rotate_license_key(
        self, tenant_id: uuid.UUID, session: AsyncSession
    ) -> dict[str, Any]:
        """Revoke the tenant's active key(s) and issue a new one."""
        from app.models.tenant import Tenant, TenantApiKey

        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            return {"error": "tenant_not_found", "tenant_id": str(tenant_id)}

        now = datetime.now(UTC)
        existing = await session.execute(
            select(TenantApiKey).where(
                TenantApiKey.tenant_id == tenant_id,
                TenantApiKey.is_active.is_(True),
            )
        )
        for key_record in existing.scalars().all():
            key_record.is_active = False
            key_record.revoked_at = now

        license_key = _generate_license_key()
        key_hash = _hash_key(license_key)
        tenant.api_key_hash = key_hash
        session.add(
            TenantApiKey(
                tenant_id=tenant_id,
                key_hash=key_hash,
                key_prefix=license_key[:16],
                name="rotated",
                is_active=True,
            )
        )
        await session.commit()
        logger.info("[LicenseManager] Key rotated for tenant %s", tenant_id)
        return {"tenant_id": str(tenant_id), "license_key": license_key}

    async def validate_license(
        self, license_key: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Return tenant metadata if key is valid, active, and tenant is active."""
        from app.models.tenant import Tenant, TenantApiKey

        if not license_key or not license_key.startswith(_KEY_PREFIX):
            return None

        key_hash = _hash_key(license_key)
        key_record = await session.scalar(
            select(TenantApiKey).where(
                TenantApiKey.key_hash == key_hash,
                TenantApiKey.is_active.is_(True),
                TenantApiKey.revoked_at.is_(None),
            )
        )
        if not key_record:
            return None

        tenant = await session.get(Tenant, key_record.tenant_id)
        if not tenant or not tenant.is_active:
            return None

        limits = (tenant.settings or {}).get("limits", {})
        return {
            "tenant_id": str(tenant.id),
            "company_name": tenant.name,
            "plan_tier": tenant.plan_tier.value,
            "monthly_leads_limit": limits.get("monthly_leads"),
            "monthly_emails_limit": limits.get("monthly_emails"),
        }

    async def get_mrr_snapshot(self, session: AsyncSession) -> dict[str, Any]:
        """MRR snapshot: count active tenants per plan tier and compute monthly revenue."""
        from app.models.tenant import PlanTier, Tenant

        result = await session.execute(
            select(Tenant.plan_tier, Tenant.id).where(Tenant.is_active.is_(True))
        )
        rows = result.all()

        tier_prices = {
            PlanTier.STARTER: 1500,
            PlanTier.GROWTH: 3000,
            PlanTier.ENTERPRISE: 6000,
            PlanTier.INDUSTRY_OS: 10000,
        }
        breakdown: dict[str, Any] = {}
        total_mrr = 0
        total_tenants = 0

        counts: dict[Any, int] = {}
        for plan_tier, _tenant_id in rows:
            counts[plan_tier] = counts.get(plan_tier, 0) + 1

        for tier, count in counts.items():
            price = tier_prices.get(tier, 1500)
            revenue = count * price
            breakdown[tier.value] = {"count": count, "price_gbp": price, "revenue_gbp": revenue}
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
        """Paginated tenant list for Captain dashboard, with each tenant's admin email."""
        from app.models.tenant import Tenant, User, UserRole

        offset = (page - 1) * per_page
        result = await session.execute(
            select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(per_page)
        )
        tenants = result.scalars().all()
        if not tenants:
            return []

        tenant_ids = [t.id for t in tenants]
        admin_rows = await session.execute(
            select(User.tenant_id, User.email).where(
                User.tenant_id.in_(tenant_ids),
                User.role == UserRole.ADMIN,
            )
        )
        admin_email_by_tenant = dict(admin_rows.all())

        return [
            {
                "tenant_id": str(t.id),
                "company_name": t.name,
                "plan_tier": t.plan_tier.value,
                "admin_email": admin_email_by_tenant.get(t.id),
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tenants
        ]

    async def upgrade_plan(
        self, tenant_id: uuid.UUID, new_plan: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Upgrade/downgrade a tenant plan tier and refresh its stored limits."""
        from app.models.tenant import PlanTier, Tenant

        try:
            tier = PlanTier[new_plan.upper()]
        except KeyError:
            raise ValueError(f"Invalid plan tier: {new_plan}")

        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER])
        limits_payload = {k: v for k, v in limits.items() if k != "features"}

        tenant.plan_tier = tier
        settings_payload = dict(tenant.settings or {})
        settings_payload["limits"] = limits_payload
        tenant.settings = settings_payload
        await session.commit()

        return {"tenant_id": str(tenant_id), "new_plan": tier.value, "limits": limits_payload}

    async def _unique_slug(self, session: AsyncSession, base_slug: str) -> str:
        from app.models.tenant import Tenant

        candidate = base_slug
        suffix = 2
        while await session.scalar(select(Tenant.id).where(Tenant.slug == candidate)):
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate


license_manager = LicenseManager()
