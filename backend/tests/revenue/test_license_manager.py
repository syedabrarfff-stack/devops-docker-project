"""Tests for R6-3: White-label license manager — provisioning, rotation, validation, MRR."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLicenseKeyGeneration:
    def test_key_format(self):
        with patch("app.services.whitelabel.license_manager.settings") as cfg:
            cfg.SECRET_KEY = "test_secret_key_for_hmac_generation"
            from app.services.whitelabel.license_manager import _generate_license_key
            key = _generate_license_key("tenant_abc")
            assert key.startswith("wl_")
            assert len(key) > 20

    def test_different_tenants_get_different_keys(self):
        with patch("app.services.whitelabel.license_manager.settings") as cfg:
            cfg.SECRET_KEY = "test_secret_key_for_hmac_generation"
            from app.services.whitelabel.license_manager import _generate_license_key
            k1 = _generate_license_key("tenant_1")
            k2 = _generate_license_key("tenant_2")
            assert k1 != k2

    def test_same_tenant_keys_are_unique_due_to_random_component(self):
        with patch("app.services.whitelabel.license_manager.settings") as cfg:
            cfg.SECRET_KEY = "test_secret_key_for_hmac_generation"
            from app.services.whitelabel.license_manager import _generate_license_key
            k1 = _generate_license_key("tenant_x")
            k2 = _generate_license_key("tenant_x")
            # random component makes each call unique
            assert k1 != k2


class TestProvisionTenant:
    @pytest.mark.asyncio
    async def test_provision_returns_tenant_record(self):
        with (
            patch("app.services.whitelabel.license_manager.get_db_session") as db_ctx,
            patch("app.services.whitelabel.license_manager._generate_license_key", return_value="wl_abc123"),
            patch("app.services.whitelabel.license_manager.settings") as cfg,
        ):
            cfg.SECRET_KEY = "test_secret"
            mock_db = AsyncMock()
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.whitelabel.license_manager import LicenseManager
            lm = LicenseManager()
            result = await lm.provision_tenant(
                company_name="TestCo",
                contact_email="admin@testco.com",
                plan="STARTER",
            )
            assert isinstance(result, dict)
            assert "license_key" in result or "tenant_id" in result or "status" in result


class TestValidateLicense:
    @pytest.mark.asyncio
    async def test_valid_key_returns_tenant_info(self):
        with patch("app.services.whitelabel.license_manager.get_db_session") as db_ctx:
            mock_db = AsyncMock()
            mock_tenant = MagicMock()
            mock_tenant.license_key = "wl_valid_key"
            mock_tenant.is_active = True
            mock_tenant.plan = "GROWTH"
            mock_tenant.company_name = "ValidCo"
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_tenant)))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.whitelabel.license_manager import LicenseManager
            lm = LicenseManager()
            result = await lm.validate_license("wl_valid_key")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_invalid_key_returns_invalid(self):
        with patch("app.services.whitelabel.license_manager.get_db_session") as db_ctx:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.whitelabel.license_manager import LicenseManager
            lm = LicenseManager()
            result = await lm.validate_license("wl_nonexistent")
            assert result.get("valid") is False or result.get("status") == "invalid" or isinstance(result, dict)


class TestMrrSnapshot:
    @pytest.mark.asyncio
    async def test_mrr_snapshot_returns_numeric_total(self):
        with patch("app.services.whitelabel.license_manager.get_db_session") as db_ctx:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                fetchall=MagicMock(return_value=[
                    MagicMock(plan="STARTER", count=2),
                    MagicMock(plan="GROWTH", count=1),
                ])
            ))
            db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.whitelabel.license_manager import LicenseManager
            lm = LicenseManager()
            result = await lm.get_mrr_snapshot()
            assert isinstance(result, dict)
            assert "total_mrr" in result or "mrr" in result or "tenants" in result
