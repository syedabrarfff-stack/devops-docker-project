"""Unit tests for ServiceRegistryManager - Phase 2 validation."""

import pytest
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_registry import ServiceStatus, ServiceType
from app.services.registry import ServiceRegistryManager


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """Test tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def actor_name() -> str:
    """Test actor name."""
    return "test_user"


class TestServiceRegistryManagerBootstrap:
    """Tests for service bootstrapping."""

    @pytest.mark.asyncio
    async def test_bootstrap_canonical_services(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify all 25 canonical services are bootstrapped."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        result = await manager.bootstrap_canonical_services()

        assert result["status"] == "bootstrap_complete"
        assert result["total_canonical"] == 25
        assert result["created_count"] == 25
        assert len(result["details"]["created"]) == 25
        assert len(result["details"]["errors"]) == 0

    @pytest.mark.asyncio
    async def test_bootstrap_idempotent(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify bootstrap is idempotent (no duplicates on re-run)."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)

        # First bootstrap
        result1 = await manager.bootstrap_canonical_services()
        assert result1["created_count"] == 25

        # Second bootstrap should not create duplicates
        result2 = await manager.bootstrap_canonical_services()
        assert result2["created_count"] == 0  # Already exist

    @pytest.mark.asyncio
    async def test_get_service_by_code(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify service retrieval by code."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")
        assert scout is not None
        assert scout.code == "SCOUT"
        assert scout.name == "Lead Intelligence"
        assert scout.division == "Revenue Operations"
        assert scout.service_type == ServiceType.AUTONOMOUS

    @pytest.mark.asyncio
    async def test_get_all_services(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify retrieving all services."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        services = await manager.get_all_services()
        assert len(services) == 25

        # Verify services are active by default
        for service in services:
            assert service.status == ServiceStatus.ACTIVE
            assert service.tenant_id == tenant_id


class TestServiceInstantiation:
    """Tests for service instantiation."""

    @pytest.mark.asyncio
    async def test_instantiate_service(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify service instance creation."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")
        instance = await manager.instantiate_service(
            service_id=scout.id,
            instance_name="SCOUT-PRIMARY",
            deployment_region="ap-south-2",
        )

        assert instance.instance_name == "SCOUT-PRIMARY"
        assert instance.service_id == scout.id
        assert instance.tenant_id == tenant_id
        assert instance.status == ServiceStatus.BETA
        assert instance.deployment_region == "ap-south-2"

    @pytest.mark.asyncio
    async def test_initialize_instance(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify instance initialization and deployment."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")
        instance = await manager.instantiate_service(
            service_id=scout.id, instance_name="SCOUT-PRIMARY"
        )

        # Initialize the instance
        initialized = await manager.initialize_service_instance(instance.id)

        assert initialized.status == ServiceStatus.ACTIVE
        assert initialized.is_healthy == 1
        assert initialized.deployed_at is not None

    @pytest.mark.asyncio
    async def test_get_service_instances(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify retrieving all instances of a service."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")

        # Create multiple instances
        instance1 = await manager.instantiate_service(
            service_id=scout.id, instance_name="SCOUT-US"
        )
        instance2 = await manager.instantiate_service(
            service_id=scout.id, instance_name="SCOUT-EU"
        )

        instances = await manager.get_service_instances(scout.id)
        assert len(instances) == 2
        assert {i.instance_name for i in instances} == {"SCOUT-US", "SCOUT-EU"}


class TestMetricsTracking:
    """Tests for metrics recording."""

    @pytest.mark.asyncio
    async def test_record_metrics(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify metrics recording."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")

        metrics = await manager.record_metrics(
            service_id=scout.id,
            total_executions=100,
            successful_executions=95,
            failed_executions=5,
            avg_execution_time_ms=250,
            error_rate=5.0,
            active_users=42,
        )

        assert metrics.service_id == scout.id
        assert metrics.total_executions == 100
        assert metrics.successful_executions == 95
        assert metrics.failed_executions == 5
        assert metrics.success_rate == 95.0
        assert metrics.error_rate == 5.0

    @pytest.mark.asyncio
    async def test_get_service_metrics_latest(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify retrieving latest metrics."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")

        # Record multiple metrics
        await manager.record_metrics(scout.id, total_executions=100)
        await manager.record_metrics(scout.id, total_executions=110)
        await manager.record_metrics(scout.id, total_executions=120)

        metrics = await manager.get_service_metrics_latest(scout.id, days=30)
        assert len(metrics) == 3


class TestDependencies:
    """Tests for service dependencies."""

    @pytest.mark.asyncio
    async def test_add_dependency(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify adding service dependencies."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        herald = await manager.get_service_by_code("HERALD")
        scout = await manager.get_service_by_code("SCOUT")

        # HERALD depends on SCOUT for lead scoring
        dependency = await manager.add_dependency(
            service_id=herald.id,
            depends_on_service_id=scout.id,
            dependency_type="data",
            is_critical=True,
        )

        assert dependency.service_id == herald.id
        assert dependency.depends_on_service_id == scout.id
        assert dependency.is_critical == 1

    @pytest.mark.asyncio
    async def test_get_service_dependencies(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify retrieving service dependencies."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        herald = await manager.get_service_by_code("HERALD")
        scout = await manager.get_service_by_code("SCOUT")
        nexus_r = await manager.get_service_by_code("NEXUS-R")

        # Create dependencies
        await manager.add_dependency(herald.id, scout.id, "data")
        await manager.add_dependency(herald.id, nexus_r.id, "data")

        dependencies = await manager.get_service_dependencies(herald.id)
        assert len(dependencies) == 2


class TestDeprecation:
    """Tests for service deprecation."""

    @pytest.mark.asyncio
    async def test_deprecate_service(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify service deprecation workflow."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")
        assert scout.status == ServiceStatus.ACTIVE
        assert scout.deprecated_at is None

        # Deprecate the service
        deprecated = await manager.deprecate_service(
            scout.id, reason="Replaced by SCOUT-v2"
        )

        assert deprecated.status == ServiceStatus.DEPRECATED
        assert deprecated.deprecated_at is not None

    @pytest.mark.asyncio
    async def test_get_only_active_services(
        self, db: AsyncSession, tenant_id: uuid.UUID, actor_name: str
    ):
        """Verify filtering by active status."""
        manager = ServiceRegistryManager(db, tenant_id, actor_name)
        await manager.bootstrap_canonical_services()

        scout = await manager.get_service_by_code("SCOUT")
        await manager.deprecate_service(scout.id)

        active_services = await manager.get_all_services(status=ServiceStatus.ACTIVE)
        assert len(active_services) == 24  # One deprecated

        deprecated_services = await manager.get_all_services(status=ServiceStatus.DEPRECATED)
        assert len(deprecated_services) == 1
