"""
Service Registry Migration - Bridge from old catalog to new registry
Handles backward compatibility and data migration
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_registry import ServiceRegistry, ServiceStatus, ServiceType
from app.models.service_catalog import ServiceDivision
from app.services.registry import ServiceRegistryManager, CANONICAL_SERVICES

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class ServiceRegistryMigration:
    """
    Manages migration from hardcoded CAPABILITY_MODULES to dynamic ServiceRegistry.

    Strategy:
    1. Bootstrap: Load 25 canonical services into ServiceRegistry
    2. Bridge: Map ServiceDivision → ServiceRegistry for backward compatibility
    3. Migrate: Update routes to query ServiceRegistry (with fallback to ServiceDivision)
    4. Deprecate: Gradually phase out ServiceDivision references
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.manager = ServiceRegistryManager(db, SYSTEM_TENANT_ID, actor="migration")

    async def bootstrap_services_into_registry(self) -> Dict[str, Any]:
        """
        Bootstrap all 25 canonical services into ServiceRegistry.
        Idempotent: skips if already bootstrapped.
        """
        # Check if already bootstrapped
        existing_count = await self.db.scalar(
            select(ServiceRegistry).where(
                ServiceRegistry.tenant_id == SYSTEM_TENANT_ID
            )
        )

        if existing_count:
            logger.info("Services already bootstrapped, skipping")
            return {
                "status": "already_bootstrapped",
                "message": "Services were already in registry",
            }

        # Bootstrap
        result = await self.manager.bootstrap_canonical_services()
        logger.info(f"Bootstrap complete: {result}")
        return result

    async def get_service_from_registry(
        self, code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[ServiceRegistry]:
        """
        Get service from registry by code.
        Uses system tenant if none specified.
        """
        tid = tenant_id or SYSTEM_TENANT_ID

        return await self.db.scalar(
            select(ServiceRegistry).where(
                (ServiceRegistry.code == code)
                & (ServiceRegistry.tenant_id == tid)
            )
        )

    async def get_all_services_from_registry(
        self, tenant_id: Optional[UUID] = None, status: Optional[ServiceStatus] = None
    ) -> List[ServiceRegistry]:
        """Get all services from registry, optionally filtered by status."""
        tid = tenant_id or SYSTEM_TENANT_ID

        query = select(ServiceRegistry).where(ServiceRegistry.tenant_id == tid)

        if status:
            query = query.where(ServiceRegistry.status == status)

        query = query.order_by(ServiceRegistry.name)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def map_service_registry_to_division(
        self, service: ServiceRegistry
    ) -> Dict[str, Any]:
        """
        Map ServiceRegistry record to ServiceDivision format for backward compatibility.
        Allows old code to work with new data without changes.
        """
        return {
            "id": service.id,
            "code": service.code,
            "name": service.name,
            "division_group": service.division,
            "description": service.description,
            "deliverables": [
                f"Service: {service.name}",
                f"Department: {service.division}",
                f"Status: {service.status.value}",
            ],
            "technologies": service.agent_layer or [],
            "target_industries": ["B2B Services", "SaaS", "Enterprise"],
            "pricing_model": "service",
            "price_range_usd": {},
            "duration_estimate": "Depends on scope",
            "is_active": service.status == ServiceStatus.ACTIVE,
            "is_featured": service.status == ServiceStatus.ACTIVE,
            "sort_order": 0,
        }

    async def ensure_registry_initialized(self) -> bool:
        """
        Ensure ServiceRegistry is initialized.
        Returns True if initialized (or just now initialized), False if failed.
        """
        try:
            # Check if any services exist
            count = await self.db.scalar(
                select(ServiceRegistry).where(
                    ServiceRegistry.tenant_id == SYSTEM_TENANT_ID
                )
            )

            if count:
                return True

            # Bootstrap if needed
            result = await self.bootstrap_services_into_registry()
            return result.get("status") in ["bootstrap_complete", "already_bootstrapped"]
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            return False

    async def migrate_division_to_service(
        self, division: ServiceDivision, tenant_id: Optional[UUID] = None
    ) -> Optional[ServiceRegistry]:
        """
        Migrate a ServiceDivision record to ServiceRegistry.
        Creates new ServiceRegistry entry if not exists.
        """
        tid = tenant_id or SYSTEM_TENANT_ID

        # Check if already migrated
        existing = await self.db.scalar(
            select(ServiceRegistry).where(
                (ServiceRegistry.code == division.code)
                & (ServiceRegistry.tenant_id == tid)
            )
        )

        if existing:
            return existing

        # Create new service from division
        service = ServiceRegistry(
            id=uuid.uuid4(),
            tenant_id=tid,
            code=division.code,
            name=division.name,
            description=division.description,
            division=division.division_group,
            version="1.0.0",
            status=ServiceStatus.ACTIVE if division.is_active else ServiceStatus.ARCHIVED,
            service_type=ServiceType.AUTONOMOUS,
            agent_layer=division.technologies or [],
            tags=["migrated_from_division"],
            metadata={"original_division_id": str(division.id)},
        )

        self.db.add(service)
        await self.db.flush()

        logger.info(f"Migrated division {division.code} to service registry")
        return service

    async def get_service_with_fallback(
        self, code: str, tenant_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get service from registry with fallback to ServiceDivision.

        Strategy:
        1. Try ServiceRegistry first
        2. Fall back to ServiceDivision if not found
        3. Return None if neither found

        This enables gradual migration without breaking existing code.
        """
        tid = tenant_id or SYSTEM_TENANT_ID

        # Try ServiceRegistry first
        service = await self.get_service_from_registry(code, tid)
        if service:
            return await self.map_service_registry_to_division(service)

        # Fallback to ServiceDivision (old system)
        division = await self.db.scalar(
            select(ServiceDivision).where(ServiceDivision.code == code)
        )

        if division:
            # Optionally migrate to registry
            try:
                await self.migrate_division_to_service(division, tid)
            except Exception as e:
                logger.warning(f"Failed to auto-migrate division {code}: {e}")

            return {
                "id": division.id,
                "code": division.code,
                "name": division.name,
                "division_group": division.division_group,
                "description": division.description,
                "deliverables": division.deliverables or [],
                "technologies": division.technologies or [],
                "target_industries": division.target_industries or [],
                "pricing_model": division.pricing_model,
                "price_range_usd": division.price_range_usd or {},
                "duration_estimate": division.duration_estimate,
                "is_active": division.is_active,
                "is_featured": division.is_featured,
                "sort_order": division.sort_order,
            }

        return None

    async def get_all_services_with_fallback(
        self, group: Optional[str] = None, featured_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all services from registry with fallback to ServiceDivision.
        Combines results from both sources to ensure completeness.
        """
        services = []
        seen_codes = set()

        # Get from ServiceRegistry (primary)
        registry_services = await self.get_all_services_from_registry(
            status=ServiceStatus.ACTIVE
        )

        for service in registry_services:
            if not group or service.division == group:
                if not featured_only or service.status == ServiceStatus.ACTIVE:
                    services.append(await self.map_service_registry_to_division(service))
                    seen_codes.add(service.code)

        # Get from ServiceDivision (fallback for any missing)
        divisions = await self.db.execute(
            select(ServiceDivision).where(ServiceDivision.is_active == True)
        )

        for division in divisions.scalars().all():
            if division.code not in seen_codes:
                if not group or division.division_group == group:
                    if not featured_only or division.is_featured:
                        services.append(
                            {
                                "id": division.id,
                                "code": division.code,
                                "name": division.name,
                                "division_group": division.division_group,
                                "description": division.description,
                                "deliverables": division.deliverables or [],
                                "technologies": division.technologies or [],
                                "target_industries": division.target_industries or [],
                                "pricing_model": division.pricing_model,
                                "price_range_usd": division.price_range_usd or {},
                                "duration_estimate": division.duration_estimate,
                                "is_active": division.is_active,
                                "is_featured": division.is_featured,
                                "sort_order": division.sort_order,
                            }
                        )
                        seen_codes.add(division.code)

        # Sort by sort_order
        return sorted(services, key=lambda x: x.get("sort_order", 0))

    async def get_groups_with_fallback(self) -> List[Dict[str, Any]]:
        """Get service groups from both registry and divisions."""
        groups = {}

        # From registry
        registry_services = await self.get_all_services_from_registry()
        for service in registry_services:
            if service.division:
                if service.division not in groups:
                    groups[service.division] = {"name": service.division, "count": 0}
                groups[service.division]["count"] += 1

        # From divisions
        divisions = await self.db.execute(
            select(ServiceDivision).where(ServiceDivision.is_active == True)
        )

        for division in divisions.scalars().all():
            if division.division_group:
                if division.division_group not in groups:
                    groups[division.division_group] = {
                        "name": division.division_group,
                        "count": 0,
                    }
                groups[division.division_group]["count"] += 1

        return [{"name": k, "count": v["count"]} for k, v in groups.items()]

    async def verify_migration_integrity(self) -> Dict[str, Any]:
        """
        Verify that migration is complete and consistent.
        Returns status of registry vs old system.
        """
        registry_services = await self.get_all_services_from_registry()
        registry_count = len(registry_services)

        divisions = await self.db.execute(select(ServiceDivision))
        division_count = len(divisions.scalars().all())

        missing_codes = []
        for svc in registry_services:
            div = await self.db.scalar(
                select(ServiceDivision).where(ServiceDivision.code == svc.code)
            )
            if not div:
                missing_codes.append(svc.code)

        return {
            "status": "healthy" if missing_codes == [] else "partial",
            "registry_services": registry_count,
            "legacy_divisions": division_count,
            "missing_from_legacy": missing_codes,
            "ready_for_cutover": missing_codes == [],
        }
