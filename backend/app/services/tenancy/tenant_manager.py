from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import AuditLog
from app.models.tenant import PlanTier, Tenant, TenantApiKey, User, UserRole


PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "STARTER": {"max_leads": 500, "max_agents": 10, "max_ai_calls": 1000},
    "GROWTH": {"max_leads": 2000, "max_agents": 25, "max_ai_calls": 5000},
    "ENTERPRISE": {"max_leads": 10000, "max_agents": 64, "max_ai_calls": None},
}

DEFAULT_PERSONAS = [
    {
        "key": "captain_assistant",
        "name": "Captain Assistant",
        "purpose": "Summarize decisions, surface exceptions, and protect Captain's time.",
    },
    {
        "key": "revenue_operator",
        "name": "Revenue Operator",
        "purpose": "Move qualified leads through research, outreach, follow-up, and proposal stages.",
    },
    {
        "key": "delivery_operator",
        "name": "Delivery Operator",
        "purpose": "Track project health, client outcomes, risks, and retention moments.",
    },
]

DEFAULT_AGENT_CONFIGS = [
    {"agent": "lead_researcher", "enabled": True, "approval_required": False},
    {"agent": "outreach_writer", "enabled": True, "approval_required": True},
    {"agent": "proposal_generator", "enabled": True, "approval_required": True},
    {"agent": "reply_classifier", "enabled": True, "approval_required": False},
    {"agent": "invoice_operator", "enabled": True, "approval_required": True},
]

DEFAULT_SERVICE_CATALOG = [
    "AI appointment and front-desk automation",
    "Cloud reliability and DevOps stabilization",
    "Revenue workflow automation",
    "CRM and sales operations automation",
    "Executive analytics and operational dashboards",
]

DEFAULT_GOVERNANCE_RULES = [
    {"rule": "pricing_exception_requires_captain", "enabled": True},
    {"rule": "regulated_sector_requires_approval", "enabled": True},
    {"rule": "live_outreach_requires_captain_clearance", "enabled": True},
    {"rule": "spend_above_500_requires_captain", "enabled": True},
]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TenantManager:
    async def create_tenant(
        self,
        name: str,
        plan_tier: str,
        admin_email: str,
        admin_password: str,
    ) -> tuple[Tenant, User]:
        tenant_id = uuid.uuid4()
        tier = self._normalize_plan(plan_tier)
        slug = self._slugify(name)
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)

        async with AsyncSessionLocal() as db:
            slug = await self._unique_slug(db, slug)
            await self._apply_rls_context(db, tenant_id)

            settings_payload = {
                "limits": self._limits_for_plan(tier.value),
                "personas": DEFAULT_PERSONAS,
                "agent_configs": DEFAULT_AGENT_CONFIGS,
                "service_catalog": DEFAULT_SERVICE_CATALOG,
                "governance_rules": DEFAULT_GOVERNANCE_RULES,
            }
            tenant = Tenant(
                id=tenant_id,
                tenant_id=tenant_id,
                name=name.strip(),
                slug=slug,
                plan_tier=tier,
                api_key_hash=api_key_hash,
                settings=settings_payload,
                is_active=True,
            )
            user = User(
                tenant_id=tenant_id,
                email=admin_email.strip().lower(),
                hashed_password=pwd_context.hash(admin_password),
                role=UserRole.ADMIN,
                is_captain=False,
            )
            tenant_api_key = TenantApiKey(
                tenant_id=tenant_id,
                key_hash=api_key_hash,
                key_prefix=self._key_prefix(api_key),
                name="default",
                is_active=True,
            )

            db.add_all([tenant, user, tenant_api_key])
            await db.flush()
            await self._audit(
                db,
                tenant_id=tenant_id,
                action="tenant_created",
                entity_type="tenant",
                entity_id=tenant.id,
                after_json={"name": tenant.name, "plan_tier": tenant.plan_tier.value, "admin_email": user.email},
            )
            await db.commit()

        await self.provision_tenant(tenant_id)
        setattr(tenant, "_plain_api_key", api_key)
        return tenant, user

    async def provision_tenant(self, tenant_id: uuid.UUID | str) -> None:
        tenant_uuid = self._tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as db:
            await self._apply_rls_context(db, tenant_uuid)
            tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_uuid))
            if tenant is None:
                raise ValueError(f"Tenant not found: {tenant_uuid}")

            current_settings = dict(tenant.settings or {})
            current_settings.setdefault("personas", DEFAULT_PERSONAS)
            current_settings.setdefault("agent_configs", DEFAULT_AGENT_CONFIGS)
            current_settings.setdefault("service_catalog", DEFAULT_SERVICE_CATALOG)
            current_settings.setdefault("governance_rules", DEFAULT_GOVERNANCE_RULES)
            current_settings.setdefault("limits", self._limits_for_plan(tenant.plan_tier.value))
            tenant.settings = current_settings

            await self._audit(
                db,
                tenant_id=tenant_uuid,
                action="tenant_provisioned",
                entity_type="tenant",
                entity_id=tenant.id,
                after_json={
                    "personas": len(current_settings["personas"]),
                    "agent_configs": len(current_settings["agent_configs"]),
                    "service_catalog_entries": len(current_settings["service_catalog"]),
                    "governance_rules": len(current_settings["governance_rules"]),
                },
            )
            await db.commit()

    async def get_tenant_from_api_key(self, api_key: str) -> Tenant | None:
        if not api_key:
            return None

        api_key_hash = self._hash_api_key(api_key)
        async with AsyncSessionLocal() as db:
            key_record = await db.scalar(
                select(TenantApiKey).where(
                    TenantApiKey.key_hash == api_key_hash,
                    TenantApiKey.is_active.is_(True),
                    TenantApiKey.revoked_at.is_(None),
                )
            )
            if key_record:
                tenant = await db.scalar(
                    select(Tenant).where(
                        Tenant.id == key_record.tenant_id,
                        Tenant.is_active.is_(True),
                    )
                )
                if tenant:
                    key_record.last_used_at = datetime.now(timezone.utc)
                    await db.commit()
                return tenant

            tenant = await db.scalar(
                select(Tenant).where(
                    Tenant.api_key_hash == api_key_hash,
                    Tenant.is_active.is_(True),
                )
            )
            return tenant

    async def get_tenant_by_id(self, tenant_id: uuid.UUID | str) -> Tenant | None:
        tenant_uuid = self._tenant_uuid(tenant_id)
        async with AsyncSessionLocal() as db:
            return await db.scalar(
                select(Tenant).where(
                    Tenant.id == tenant_uuid,
                    Tenant.is_active.is_(True),
                )
            )

    async def list_tenants(self) -> list[Tenant]:
        async with AsyncSessionLocal() as db:
            rows = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
            return list(rows.scalars().all())

    async def update_plan_limits(self, tenant_id: uuid.UUID | str, limits: dict[str, Any]) -> Tenant:
        tenant_uuid = self._tenant_uuid(tenant_id)
        sanitized = {
            key: value
            for key, value in limits.items()
            if key in {"max_leads", "max_agents", "max_ai_calls"} and (value is None or int(value) >= 0)
        }
        if not sanitized:
            raise ValueError("No valid plan limits provided")

        async with AsyncSessionLocal() as db:
            await self._apply_rls_context(db, tenant_uuid)
            tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_uuid))
            if tenant is None:
                raise ValueError(f"Tenant not found: {tenant_uuid}")
            settings_payload = dict(tenant.settings or {})
            current_limits = dict(settings_payload.get("limits") or self._limits_for_plan(tenant.plan_tier.value))
            current_limits.update(sanitized)
            settings_payload["limits"] = current_limits
            tenant.settings = settings_payload
            await self._audit(
                db,
                tenant_id=tenant_uuid,
                action="tenant_limits_updated",
                entity_type="tenant",
                entity_id=tenant.id,
                after_json={"limits": current_limits},
            )
            await db.commit()
            return tenant

    async def rotate_api_key(self, tenant_id: uuid.UUID | str, name: str = "rotated") -> tuple[TenantApiKey, str]:
        tenant_uuid = self._tenant_uuid(tenant_id)
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            await self._apply_rls_context(db, tenant_uuid)
            tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_uuid))
            if tenant is None:
                raise ValueError(f"Tenant not found: {tenant_uuid}")

            existing_rows = await db.execute(
                select(TenantApiKey).where(
                    TenantApiKey.tenant_id == tenant_uuid,
                    TenantApiKey.is_active.is_(True),
                )
            )
            for existing in existing_rows.scalars().all():
                existing.is_active = False
                existing.revoked_at = now

            tenant.api_key_hash = api_key_hash
            key_record = TenantApiKey(
                tenant_id=tenant_uuid,
                key_hash=api_key_hash,
                key_prefix=self._key_prefix(api_key),
                name=name,
                is_active=True,
            )
            db.add(key_record)
            await db.flush()
            await self._audit(
                db,
                tenant_id=tenant_uuid,
                action="tenant_api_key_rotated",
                entity_type="tenant",
                entity_id=tenant.id,
                after_json={"key_prefix": key_record.key_prefix, "name": key_record.name},
            )
            await db.commit()
            return key_record, api_key

    def limits_for_tenant(self, tenant: Tenant) -> dict[str, int | None]:
        settings_payload = tenant.settings or {}
        return dict(settings_payload.get("limits") or self._limits_for_plan(tenant.plan_tier.value))

    def _limits_for_plan(self, plan_tier: str) -> dict[str, int | None]:
        tier = (plan_tier or PlanTier.STARTER.value).upper()
        if tier == "INDUSTRY_OS":
            tier = PlanTier.ENTERPRISE.value
        return PLAN_LIMITS.get(tier, PLAN_LIMITS[PlanTier.STARTER.value])

    def _normalize_plan(self, plan_tier: str) -> PlanTier:
        tier = (plan_tier or PlanTier.STARTER.value).strip().upper()
        if tier == "INDUSTRY_OS":
            tier = PlanTier.ENTERPRISE.value
        if tier not in PLAN_LIMITS:
            raise ValueError(f"Unsupported tenant plan tier: {plan_tier}")
        return PlanTier(tier)

    async def _unique_slug(self, db, slug: str) -> str:
        base = slug or "tenant"
        candidate = base
        suffix = 2
        while await db.scalar(select(Tenant.id).where(Tenant.slug == candidate)):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _apply_rls_context(self, db, tenant_id: uuid.UUID) -> None:
        if settings.DATABASE_URL.startswith("sqlite"):
            return
        await set_tenant_context(db, str(tenant_id))

    async def _audit(
        self,
        db,
        *,
        tenant_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        after_json: dict,
    ) -> None:
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor="tenant_manager",
                details=after_json,
                after_json=after_json,
            )
        )

    def _tenant_uuid(self, tenant_id: uuid.UUID | str) -> uuid.UUID:
        return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))

    def _generate_api_key(self) -> str:
        return f"jv_{secrets.token_urlsafe(32)}"

    def _hash_api_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def _key_prefix(self, api_key: str) -> str:
        return api_key[:16]

    def _slugify(self, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return slug[:100] or "tenant"
