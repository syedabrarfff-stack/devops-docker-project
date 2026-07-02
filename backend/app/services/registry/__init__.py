"""Service Registry - dynamic service management system."""

from app.services.registry.service_registry_manager import (
    ServiceRegistryManager,
    CANONICAL_SERVICES,
)

__all__ = ["ServiceRegistryManager", "CANONICAL_SERVICES"]
