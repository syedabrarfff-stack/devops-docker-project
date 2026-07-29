"""Tests for R6-3: White-label license manager — provisioning, rotation, validation, MRR.

LicenseManager operates on the same canonical Tenant/User/TenantApiKey models
as app.services.tenancy.tenant_manager (see that module's docstring for why).
These tests use real (unpersisted) ORM instances for query results — that
model's actual attributes matter here, not just "a dict came back" — and mock
only the AsyncSession itself.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.tenant import PlanTier, Tenant, TenantApiKey, User, UserRole


def _make_session(**overrides) -> AsyncMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=overrides.get("scalar_return"))
    session.get = AsyncMock(return_value=overrides.get("get_return"))
    session.execute = AsyncMock(return_value=overrides.get("execute_return", MagicMock()))
    session.add_all = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


class TestLicenseKeyGeneration:
    def test_key_format(self):
        from app.services.whitelabel.license_manager import _generate_license_key
        key = _generate_license_key()
        assert key.startswith("wl_")
        assert len(key) > 20

    def test_keys_are_unique(self):
        from app.services.whitelabel.license_manager import _generate_license_key
        k1 = _generate_license_key()
        k2 = _generate_license_key()
        assert k1 != k2

    def test_hash_is_deterministic_and_sha256(self):
        from app.services.whitelabel.license_manager import _hash_key
        h1 = _hash_key("wl_sometoken")
        h2 = _hash_key("wl_sometoken")
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex digest


class TestProvisionTenant:
    @pytest.mark.asyncio
    async def test_provision_returns_tenant_record(self):
        # session.scalar is used by _unique_slug's collision check — None means no collision
        session = _make_session(scalar_return=None)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.provision_tenant(
            company_name="TestCo",
            admin_email="admin@testco.com",
            plan_tier="STARTER",
            session=session,
        )
        assert isinstance(result, dict)
        assert result["license_key"].startswith("wl_")
        assert result["admin_email"] == "admin@testco.com"
        assert result["plan_tier"] == "STARTER"
        assert "admin_temp_password" in result
        assert "limits" in result
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_plan_tier_defaults_to_starter(self):
        session = _make_session(scalar_return=None)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.provision_tenant(
            company_name="TestCo",
            admin_email="admin@testco.com",
            plan_tier="NOT_A_REAL_TIER",
            session=session,
        )
        assert result["plan_tier"] == "STARTER"


class TestValidateLicense:
    @pytest.mark.asyncio
    async def test_valid_key_returns_tenant_info(self):
        from app.services.whitelabel.license_manager import _hash_key

        tenant_id = uuid.uuid4()
        key_record = TenantApiKey(
            tenant_id=tenant_id, key_hash=_hash_key("wl_valid_key"),
            key_prefix="wl_valid_key"[:16], name="default", is_active=True,
        )
        tenant = Tenant(
            id=tenant_id, tenant_id=tenant_id, name="ValidCo", slug="validco",
            plan_tier=PlanTier.GROWTH, is_active=True,
            settings={"limits": {"monthly_leads": 2000, "monthly_emails": 6000}},
        )
        session = _make_session(scalar_return=key_record, get_return=tenant)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.validate_license("wl_valid_key", session)
        assert isinstance(result, dict)
        assert result["company_name"] == "ValidCo"
        assert result["plan_tier"] == "GROWTH"

    @pytest.mark.asyncio
    async def test_invalid_key_returns_none(self):
        session = _make_session(scalar_return=None)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.validate_license("wl_nonexistent", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_key_returns_none_without_query(self):
        session = _make_session()

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.validate_license("not-a-license-key", session)
        assert result is None
        session.scalar.assert_not_awaited()


class TestRotateLicenseKey:
    @pytest.mark.asyncio
    async def test_rotate_returns_new_key(self):
        tenant_id = uuid.uuid4()
        tenant = Tenant(id=tenant_id, tenant_id=tenant_id, name="RotateCo", slug="rotateco", plan_tier=PlanTier.STARTER)
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = []
        session = _make_session(get_return=tenant, execute_return=execute_result)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.rotate_license_key(tenant_id, session)
        assert result["license_key"].startswith("wl_")
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rotate_unknown_tenant_returns_error(self):
        session = _make_session(get_return=None)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.rotate_license_key(uuid.uuid4(), session)
        assert "error" in result


class TestMrrSnapshot:
    @pytest.mark.asyncio
    async def test_mrr_snapshot_returns_numeric_total(self):
        execute_result = MagicMock()
        execute_result.all.return_value = [
            (PlanTier.STARTER, uuid.uuid4()),
            (PlanTier.STARTER, uuid.uuid4()),
            (PlanTier.GROWTH, uuid.uuid4()),
        ]
        session = _make_session(execute_return=execute_result)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.get_mrr_snapshot(session)
        assert isinstance(result, dict)
        assert result["total_tenants"] == 3
        assert result["total_mrr_gbp"] == 2 * 1500 + 1 * 3000


class TestUpgradePlan:
    @pytest.mark.asyncio
    async def test_upgrade_updates_plan_and_limits(self):
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id, tenant_id=tenant_id, name="UpgradeCo", slug="upgradeco",
            plan_tier=PlanTier.STARTER, settings={"limits": {"monthly_leads": 500}},
        )
        session = _make_session(get_return=tenant)

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.upgrade_plan(tenant_id, "GROWTH", session)
        assert result["new_plan"] == "GROWTH"
        assert tenant.plan_tier == PlanTier.GROWTH
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upgrade_invalid_plan_raises(self):
        session = _make_session()
        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        with pytest.raises(ValueError):
            await lm.upgrade_plan(uuid.uuid4(), "NOT_A_PLAN", session)
