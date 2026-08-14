"""
Service Registry Initialization - auto-bootstrap on app startup
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.registry.migration import ServiceRegistryMigration

logger = logging.getLogger(__name__)


async def initialize_service_registry(db: AsyncSession) -> None:
    """
    Initialize service registry on app startup.
    Safe to call multiple times (idempotent).
    """
    try:
        migration = ServiceRegistryMigration(db)
        result = await migration.ensure_registry_initialized()

        if result:
            logger.info("✓ Service Registry initialized with 25 canonical services")
        else:
            logger.warning("⚠ Service Registry initialization failed")
    except Exception as e:
        logger.error(f"Service Registry initialization error: {e}")
        # Don't block startup - registry can be initialized later
