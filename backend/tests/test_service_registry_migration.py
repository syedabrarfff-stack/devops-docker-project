"""Tests for Service Registry migration and backward compatibility - Phase 5."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.registry.migration import ServiceRegistryMigration, SYSTEM_TENANT_ID
from app.models.service_registry import ServiceStatus


class TestServiceRegistryMigration:
    """Tests for migration layer."""

    @pytest.mark.asyncio
    async def test_bootstrap_services_into_registry(
        self, db: AsyncSession
    ):
        """Verify services are bootstrapped into registry."""
        migration = ServiceRegistryMigration(db)
        result = await migration.bootstrap_services_into_registry()

        assert result["status"] == "bootstrap_complete"
        assert result["created_count"] == 25
        assert len(result["details"]["created"]) == 25

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(self, db: AsyncSession):
        """Verify bootstrap is idempotent."""
        migration = ServiceRegistryMigration(db)

        # First run
        result1 = await migration.bootstrap_services_into_registry()
        assert result1["status"] == "bootstrap_complete"

        # Second run should skip
        result2 = await migration.bootstrap_services_into_registry()
        assert result2["status"] == "already_bootstrapped"

    @pytest.mark.asyncio
    async def test_get_service_from_registry(self, db: AsyncSession):
        """Verify getting service from registry."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        service = await migration.get_service_from_registry("SCOUT")
        assert service is not None
        assert service.code == "SCOUT"
        assert service.name == "Lead Intelligence"

    @pytest.mark.asyncio
    async def test_get_all_services_from_registry(self, db: AsyncSession):
        """Verify getting all services from registry."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        services = await migration.get_all_services_from_registry()
        assert len(services) == 25
        assert all(s.tenant_id == SYSTEM_TENANT_ID for s in services)

    @pytest.mark.asyncio
    async def test_map_service_registry_to_division(self, db: AsyncSession):
        """Verify mapping ServiceRegistry to ServiceDivision format."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        service = await migration.get_service_from_registry("SCOUT")
        mapped = await migration.map_service_registry_to_division(service)

        assert mapped["code"] == "SCOUT"
        assert mapped["name"] == "Lead Intelligence"
        assert mapped["division_group"] == "Revenue Operations"
        assert mapped["is_active"] is True

    @pytest.mark.asyncio
    async def test_ensure_registry_initialized(self, db: AsyncSession):
        """Verify registry initialization check."""
        migration = ServiceRegistryMigration(db)

        result = await migration.ensure_registry_initialized()
        assert result is True

        # Should be idempotent
        result2 = await migration.ensure_registry_initialized()
        assert result2 is True

    @pytest.mark.asyncio
    async def test_get_service_with_fallback_from_registry(
        self, db: AsyncSession
    ):
        """Verify getting service with fallback prioritizes registry."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        service = await migration.get_service_with_fallback("SCOUT")
        assert service is not None
        assert service["code"] == "SCOUT"

    @pytest.mark.asyncio
    async def test_get_all_services_with_fallback(self, db: AsyncSession):
        """Verify getting all services with fallback."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        services = await migration.get_all_services_with_fallback()
        assert len(services) >= 25  # At least the bootstrapped services
        assert all("code" in s for s in services)

    @pytest.mark.asyncio
    async def test_get_all_services_with_filter(self, db: AsyncSession):
        """Verify filtering services by group."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        services = await migration.get_all_services_with_fallback(
            group="Revenue Operations"
        )
        assert len(services) > 0
        assert all(s["division_group"] == "Revenue Operations" for s in services)

    @pytest.mark.asyncio
    async def test_get_groups_with_fallback(self, db: AsyncSession):
        """Verify getting groups/divisions."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        groups = await migration.get_groups_with_fallback()
        assert len(groups) > 0

        # Check for known divisions
        group_names = {g["name"] for g in groups}
        assert "Revenue Operations" in group_names
        assert "AI Automation" in group_names

    @pytest.mark.asyncio
    async def test_verify_migration_integrity(self, db: AsyncSession):
        """Verify migration integrity check."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        integrity = await migration.verify_migration_integrity()
        assert integrity["status"] in ["healthy", "partial"]
        assert "registry_services" in integrity
        assert "legacy_divisions" in integrity


class TestBackwardCompatibility:
    """Tests for backward compatibility with old ServiceDivision."""

    @pytest.mark.asyncio
    async def test_old_routes_still_work(self, client, db: AsyncSession):
        """Verify old catalog routes still work (backward compatibility)."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        # Old route should still work
        response = client.get("/api/v1/catalog/divisions")
        assert response.status_code == 200
        data = response.json()
        assert "divisions" in data

    @pytest.mark.asyncio
    async def test_new_routes_work(self, client, db: AsyncSession):
        """Verify new v2 catalog routes work."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        # New route should work
        response = client.get("/api/v1/catalog/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert len(data["services"]) >= 25

    @pytest.mark.asyncio
    async def test_get_service_new_route(self, client, db: AsyncSession):
        """Verify getting service via new v2 route."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        response = client.get("/api/v1/catalog/services/SCOUT")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "SCOUT"
        assert data["name"] == "Lead Intelligence"

    @pytest.mark.asyncio
    async def test_bootstrap_endpoint(self, client, db: AsyncSession):
        """Verify bootstrap endpoint."""
        response = client.post("/api/v1/catalog/bootstrap")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_verify_endpoint(self, client, db: AsyncSession):
        """Verify verify endpoint."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        response = client.get("/api/v1/catalog/verify")
        assert response.status_code == 200
        data = response.json()
        assert "details" in data
        assert "migration_status" in data["details"]

    @pytest.mark.asyncio
    async def test_groups_endpoint(self, client, db: AsyncSession):
        """Verify groups endpoint."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        response = client.get("/api/v1/catalog/groups")
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert len(data["groups"]) > 0

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, client, db: AsyncSession):
        """Verify stats endpoint."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        response = client.get("/api/v1/catalog/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_services" in data
        assert "by_status" in data
        assert "by_group" in data
        assert "migration_integrity" in data

    @pytest.mark.asyncio
    async def test_no_breaking_changes(self, client, db: AsyncSession):
        """Verify no breaking changes to existing catalog routes."""
        migration = ServiceRegistryMigration(db)
        await migration.bootstrap_services_into_registry()

        # Old endpoint: /api/v1/catalog/divisions
        response1 = client.get("/api/v1/catalog/divisions")
        assert response1.status_code == 200
        assert "divisions" in response1.json()

        # Old endpoint: /api/v1/catalog/groups
        response2 = client.get("/api/v1/catalog/groups")
        assert response2.status_code == 200
        assert "groups" in response2.json()

        # Old endpoint: /api/v1/catalog/capability-modules
        response3 = client.get("/api/v1/catalog/capability-modules")
        assert response3.status_code == 200
        assert "modules" in response3.json()

        # New endpoint: /api/v1/catalog/services
        response4 = client.get("/api/v1/catalog/services")
        assert response4.status_code == 200
        assert "services" in response4.json()
