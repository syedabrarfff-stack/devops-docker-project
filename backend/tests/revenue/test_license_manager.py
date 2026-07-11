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
            patch("app.services.whitelabel.license_manager._generate_license_key", return_value="wl_abc123"),
            patch("app.services.whitelabel.license_manager.settings") as cfg,
        ):
            cfg.SECRET_KEY = "test_secret"
            mock_session = AsyncMock()

            from app.services.whitelabel.license_manager import LicenseManager
            lm = LicenseManager()
            result = await lm.provision_tenant(
                company_name="TestCo",
                admin_email="admin@testco.com",
                plan_tier="STARTER",
                session=mock_session,
            )
            assert isinstance(result, dict)
            assert "license_key" in result or "tenant_id" in result or "status" in result


class TestValidateLicense:
    @pytest.mark.asyncio
    async def test_valid_key_returns_tenant_info(self):
        mock_session = AsyncMock()
        mock_row = ("tenant-id-1", "ValidCo", "GROWTH", True, 500, 5000)
        mock_session.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=mock_row)))

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.validate_license("wl_valid_key", mock_session)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_invalid_key_returns_invalid(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(fetchone=MagicMock(return_value=None)))

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.validate_license("wl_nonexistent", mock_session)
        assert result is None


class TestMrrSnapshot:
    @pytest.mark.asyncio
    async def test_mrr_snapshot_returns_numeric_total(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            fetchall=MagicMock(return_value=[
                ("STARTER", 2),
                ("GROWTH", 1),
            ])
        ))

        from app.services.whitelabel.license_manager import LicenseManager
        lm = LicenseManager()
        result = await lm.get_mrr_snapshot(mock_session)
        assert isinstance(result, dict)
        assert "total_mrr_gbp" in result
