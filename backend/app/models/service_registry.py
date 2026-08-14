"""
Dynamic Service Registry - Plugin Architecture for JARVIS Catalog.

Replaces hardcoded 25-module catalog with pluggable, dynamic service system.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
    Numeric,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServiceStatus(str, Enum):
    """Service lifecycle status."""
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ServiceType(str, Enum):
    """Service execution model."""
    AUTONOMOUS = "autonomous"  # Fully AI-driven
    HUMAN_SUPERVISED = "human_supervised"  # AI with human approval
    HYBRID = "hybrid"  # Mixed execution


class ServiceRegistry(Base):
    """
    Dynamic service registry - replaces hardcoded CAPABILITY_MODULES.

    Each service is:
    - Independently versioned
    - Per-tenant customizable
    - Dynamically instantiable
    - Metrics-tracked
    - Deprecation-managed
    """
    __tablename__ = "service_registry"
    __table_args__ = (
        Index("idx_service_registry_status", "status"),
        Index("idx_service_registry_division", "division"),
        Index("idx_service_registry_tenant", "tenant_id"),
        Index("idx_service_registry_code", "code"),
        UniqueConstraint("code", name="uq_service_registry_code"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Service Identity
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    version = Column(String(20), default="1.0.0")
    status = Column(SQLEnum(ServiceStatus), default=ServiceStatus.ACTIVE, nullable=False)

    # Organization
    division = Column(String(100))
    human_interface_executive = Column(String(200))

    # Execution Model
    service_type = Column(
        SQLEnum(ServiceType),
        default=ServiceType.AUTONOMOUS,
        nullable=False
    )

    # Capabilities
    capability_flags = Column(JSON, default=dict)  # e.g., {"email": true, "whatsapp": false}

    # Intelligence Integration
    agent_layer = Column(JSON)  # List of capable agents
    kpi_targets = Column(JSON)  # Monitored KPIs
    dependencies = Column(JSON)  # Service dependencies

    # Performance Metrics
    success_rate = Column(Numeric(5, 2))  # 0-100%
    avg_execution_time_ms = Column(Integer)  # Average execution time
    monthly_cost = Column(Numeric(10, 2))  # Estimated monthly cost

    # Lifecycle Tracking
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deprecated_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    tags = Column(JSON, default=list)  # For searching, filtering
    metadata = Column(JSON, default=dict)  # Custom data

    # Relationships
    tenant = relationship("Tenant", back_populates="services")
    instances = relationship("ServiceInstance", back_populates="service", cascade="all, delete-orphan")
    metrics = relationship("ServiceMetrics", back_populates="service", cascade="all, delete-orphan")


class ServiceTemplate(Base):
    """
    Reusable service template for creating new service instances.

    Templates define:
    - Default configuration
    - Required/optional capabilities
    - Intelligence requirements
    - Deployment specifications
    """
    __tablename__ = "service_templates"
    __table_args__ = (
        Index("idx_service_templates_name", "template_name"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))

    # Template Identity
    template_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    base_service_code = Column(String(50))  # e.g., "HERALD" template base

    # Configuration
    configuration = Column(JSON)  # Default config for new instances
    required_capabilities = Column(JSON)  # Required features
    optional_capabilities = Column(JSON)  # Optional features

    # Deployment
    docker_image = Column(String(200))  # Optional container image
    environment_template = Column(JSON)  # Env vars needed

    # Intelligence
    agent_requirements = Column(JSON)  # Required agent types
    model_preferences = Column(JSON)  # Preferred AI models

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    instances = relationship("ServiceInstance", back_populates="template")


class ServiceInstance(Base):
    """
    Running instance of a service (instantiated from template).

    One template can have multiple instances (e.g., HERALD-US, HERALD-EU).
    """
    __tablename__ = "service_instances"
    __table_args__ = (
        Index("idx_service_instances_tenant", "tenant_id"),
        Index("idx_service_instances_service", "service_id"),
        Index("idx_service_instances_status", "status"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    service_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_registry.id"), nullable=False)
    template_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_templates.id"))

    # Instance Identity
    instance_name = Column(String(200), nullable=False)  # e.g., "HERALD-US"
    status = Column(SQLEnum(ServiceStatus), default=ServiceStatus.BETA, nullable=False)

    # Configuration (instance-specific customizations)
    configuration = Column(JSON)  # Overrides template config
    environment = Column(JSON)  # Instance-specific env vars

    # Deployment
    deployed_at = Column(TIMESTAMP(timezone=True))
    deployment_region = Column(String(50))  # e.g., "ap-south-2"
    deployment_container_id = Column(String(200))  # Docker/ECS task ID

    # Health
    is_healthy = Column(Integer, default=1)  # 0 = unhealthy, 1 = healthy
    last_health_check = Column(TIMESTAMP(timezone=True))

    # Lifecycle
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deprecated_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    service = relationship("ServiceRegistry", back_populates="instances")
    template = relationship("ServiceTemplate", back_populates="instances")
    tenant = relationship("Tenant")


class ServiceMetrics(Base):
    """
    Metrics tracking for services (success rate, cost, performance).

    Updated daily from scheduler job.
    """
    __tablename__ = "service_metrics"
    __table_args__ = (
        Index("idx_service_metrics_service", "service_id"),
        Index("idx_service_metrics_date", "metric_date"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))
    service_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_registry.id"), nullable=False)

    # Metrics (daily snapshot)
    metric_date = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Performance
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    success_rate = Column(Numeric(5, 2))  # Calculated from above

    # Performance
    avg_execution_time_ms = Column(Integer)  # Average latency
    min_execution_time_ms = Column(Integer)  # Minimum latency
    max_execution_time_ms = Column(Integer)  # Maximum latency

    # Cost
    daily_cost = Column(Numeric(10, 2))
    monthly_cost_estimate = Column(Numeric(10, 2))

    # Usage
    active_users = Column(Integer)  # Number of users using this service
    calls_per_user = Column(Numeric(10, 2))  # Average calls per user

    # Quality
    error_rate = Column(Numeric(5, 2))  # Percentage of errors
    avg_response_time_ms = Column(Integer)  # Average response time

    # Relationships
    service = relationship("ServiceRegistry", back_populates="metrics")


class ServiceDependency(Base):
    """
    Track service-to-service dependencies.

    Used for:
    - Understanding impact of service deprecation
    - Planning service migrations
    - Dependency graph visualization
    """
    __tablename__ = "service_dependencies"
    __table_args__ = (
        Index("idx_service_dependencies_service", "service_id"),
        Index("idx_service_dependencies_depends_on", "depends_on_service_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))
    service_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_registry.id"), nullable=False)
    depends_on_service_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_registry.id"), nullable=False)

    # Dependency type
    dependency_type = Column(String(50))  # e.g., "data", "execution", "scheduling"

    # Importance
    is_critical = Column(Integer, default=0)  # 0 = optional, 1 = critical

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class ServiceAudit(Base):
    """
    Audit trail for all service changes.

    Tracks:
    - Service creation/updates/deprecation
    - Configuration changes
    - Deployment events
    """
    __tablename__ = "service_audit"
    __table_args__ = (
        Index("idx_service_audit_service", "service_id"),
        Index("idx_service_audit_timestamp", "timestamp"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=lambda: str(UUID(int=0)))
    service_id = Column(PG_UUID(as_uuid=True), ForeignKey("service_registry.id"))

    # Event tracking
    action = Column(String(50))  # e.g., "created", "updated", "deployed", "deprecated"
    actor = Column(String(200))  # Who made the change (user or system)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Change details
    change_description = Column(Text)
    before_state = Column(JSON)  # Previous values
    after_state = Column(JSON)  # New values

    # Metadata
    metadata = Column(JSON)  # Additional context
