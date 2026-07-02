"""Service Registry - dynamic service management system."""

from app.services.registry.service_registry_manager import (
    ServiceRegistryManager,
    CANONICAL_SERVICES,
)
from app.services.registry.migration import (
    ServiceRegistryMigration,
)

__all__ = ["ServiceRegistryManager", "CANONICAL_SERVICES", "ServiceRegistryMigration"]
