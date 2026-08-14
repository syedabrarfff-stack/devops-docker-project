"""
Aliyar Solutions Service Catalog API v2 - Updated to use ServiceRegistry

This is the new catalog API that uses the dynamic ServiceRegistry.
Includes backward compatibility with old ServiceDivision records.

Routes:
- GET    /catalog/services             (list all services)
- GET    /catalog/services/{code}      (get specific service)
- GET    /catalog/groups               (list service groups)
- GET    /catalog/stats                (catalog statistics)
- POST   /catalog/bootstrap            (bootstrap registry)
- POST   /catalog/migrate              (run migration)
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.registry.migration import ServiceRegistryMigration

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/catalog",
    tags=["Service Catalog v2"],
    dependencies=[Depends(get_current_captain)],
)


@router.get(
    "/services",
    summary="List all services",
    description="Get all services from registry (with ServiceDivision fallback for backward compatibility)",
)
@limiter.limit("60/minute")
async def list_services(
    request: Request,
    group: Optional[str] = Query(None, description="Filter by division/group"),
    featured_only: bool = Query(False, description="Show featured services only"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all services from the dynamic registry.

    Backward compatible: falls back to ServiceDivision if registry not initialized.
    """
    try:
        migration = ServiceRegistryMigration(db)

        # Ensure registry is initialized
        await migration.ensure_registry_initialized()

        # Get services (registry + fallback)
        services = await migration.get_all_services_with_fallback(
            group=group, featured_only=featured_only
        )

        return {
            "services": services,
            "total": len(services),
            "group": group,
            "featured_only": featured_only,
        }
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve services")


@router.get(
    "/services/{code}",
    summary="Get service by code",
    description="Retrieve specific service details (with fallback to ServiceDivision)",
)
@limiter.limit("60/minute")
async def get_service(
    request: Request,
    code: str = Query(..., description="Service code (e.g., SCOUT, HERALD)"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific service by its code."""
    try:
        migration = ServiceRegistryMigration(db)

        # Try to get from registry with fallback
        service = await migration.get_service_with_fallback(code)

        if not service:
            raise HTTPException(status_code=404, detail=f"Service '{code}' not found")

        return service
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving service {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve service")


@router.get(
    "/groups",
    summary="List service groups",
    description="Get all service groups/divisions from registry",
)
@limiter.limit("60/minute")
async def list_groups(request: Request, db: AsyncSession = Depends(get_db)):
    """List all service groups/divisions."""
    try:
        migration = ServiceRegistryMigration(db)

        # Ensure registry is initialized
        await migration.ensure_registry_initialized()

        # Get groups (registry + fallback)
        groups = await migration.get_groups_with_fallback()

        return {"groups": groups, "total": len(groups)}
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve groups")


@router.get(
    "/stats",
    summary="Get catalog statistics",
    description="Retrieve statistics about services in registry",
)
@limiter.limit("60/minute")
async def catalog_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Get catalog statistics."""
    try:
        migration = ServiceRegistryMigration(db)

        # Verify migration status
        integrity = await migration.verify_migration_integrity()

        services = await migration.get_all_services_with_fallback()

        # Count by status
        status_counts = {}
        for svc in services:
            status = "active" if svc.get("is_active") else "inactive"
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count by group
        group_counts = {}
        for svc in services:
            group = svc.get("division_group", "Unknown")
            group_counts[group] = group_counts.get(group, 0) + 1

        return {
            "total_services": len(services),
            "by_status": status_counts,
            "by_group": group_counts,
            "migration_integrity": integrity,
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.post(
    "/bootstrap",
    summary="Bootstrap service registry",
    description="Initialize ServiceRegistry with 25 canonical services (idempotent)",
)
@limiter.limit("5/minute")
async def bootstrap_registry(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Bootstrap the ServiceRegistry with 25 canonical services.
    Idempotent: safe to call multiple times.
    """
    try:
        migration = ServiceRegistryMigration(db)
        result = await migration.bootstrap_services_into_registry()

        return {
            "status": "success",
            "message": "Service registry initialized",
            "details": result,
        }
    except Exception as e:
        logger.error(f"Error bootstrapping registry: {e}")
        raise HTTPException(status_code=500, detail="Failed to bootstrap registry")


@router.post(
    "/migrate",
    summary="Run migration from old to new catalog",
    description="Migrate ServiceDivision records to ServiceRegistry",
)
@limiter.limit("3/minute")
async def run_migration(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Run migration to convert old ServiceDivision records to new ServiceRegistry.
    Non-destructive: creates new records without deleting old ones.
    """
    try:
        migration = ServiceRegistryMigration(db)

        # Bootstrap if needed
        await migration.ensure_registry_initialized()

        # Check integrity
        integrity = await migration.verify_migration_integrity()

        return {
            "status": "success",
            "message": "Migration complete",
            "migration_status": integrity,
        }
    except Exception as e:
        logger.error(f"Error running migration: {e}")
        raise HTTPException(status_code=500, detail="Migration failed")


@router.get(
    "/verify",
    summary="Verify migration integrity",
    description="Check if registry is properly initialized and complete",
)
@limiter.limit("30/minute")
async def verify_migration(request: Request, db: AsyncSession = Depends(get_db)):
    """Verify migration integrity and readiness for cutover."""
    try:
        migration = ServiceRegistryMigration(db)
        integrity = await migration.verify_migration_integrity()

        return {
            "status": "healthy" if integrity["ready_for_cutover"] else "incomplete",
            "details": integrity,
        }
    except Exception as e:
        logger.error(f"Error verifying migration: {e}")
        raise HTTPException(status_code=500, detail="Verification failed")
