"""Request/response schemas for Service Registry API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# Request schemas

class ServiceCreateRequest(BaseModel):
    """POST /services/create request."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique service code (e.g., SCOUT)")
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable service name")
    division: str = Field(..., min_length=1, max_length=100, description="Division/department")
    description: Optional[str] = Field(None, max_length=2000)
    service_type: str = Field(..., description="autonomous | human_supervised | hybrid")
    human_interface_executive: Optional[str] = Field(None, max_length=200)
    agent_layer: Optional[List[str]] = Field(default_factory=list)
    kpi_targets: Optional[List[str]] = Field(default_factory=list)
    capability_flags: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        example = {
            "code": "HERALD-V2",
            "name": "Outreach Engine",
            "division": "Revenue Operations",
            "service_type": "hybrid",
            "human_interface_executive": "Darren Mitchell",
            "agent_layer": ["Email sequencing", "Reply handling"],
            "kpi_targets": ["48 emails/day", "Reply rate"],
        }


class ServiceUpdateRequest(BaseModel):
    """PATCH /services/{service_id} request."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, description="active | beta | deprecated | archived")
    human_interface_executive: Optional[str] = Field(None, max_length=200)
    kpi_targets: Optional[List[str]] = None
    capability_flags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        example = {
            "name": "Outreach Engine v2",
            "status": "beta",
            "kpi_targets": ["50 emails/day", "45% reply rate"],
        }


class ServiceTestRequest(BaseModel):
    """POST /services/{service_id}/test request."""
    test_mode: str = Field(default="dry_run", description="dry_run | validation | integration")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Sample data for testing")
    timeout_seconds: int = Field(default=30, ge=5, le=300)


class ServiceRolloutRequest(BaseModel):
    """POST /services/{service_id}/rollout request."""
    target_instances: List[str] = Field(..., description="Instance names to deploy to (e.g., [SCOUT-US, SCOUT-EU])")
    deployment_region: Optional[str] = Field(None, description="Override deployment region")
    rollback_on_error: bool = Field(default=True)
    max_parallel_deployments: int = Field(default=2, ge=1, le=10)


# Response schemas

class ServiceResponse(BaseModel):
    """Service registry entry response."""
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    division: str
    description: Optional[str]
    version: str
    status: str
    service_type: str
    human_interface_executive: Optional[str]
    agent_layer: Optional[List[str]]
    kpi_targets: Optional[List[str]]
    capability_flags: Optional[Dict[str, Any]]
    dependencies: Optional[Dict[str, Any]]
    success_rate: Optional[float]
    avg_execution_time_ms: Optional[int]
    monthly_cost: Optional[float]
    created_at: datetime
    updated_at: datetime
    deprecated_at: Optional[datetime]
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ServiceInstanceResponse(BaseModel):
    """Service instance response."""
    id: UUID
    tenant_id: UUID
    service_id: UUID
    instance_name: str
    status: str
    deployment_region: Optional[str]
    is_healthy: int
    deployed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceMetricsResponse(BaseModel):
    """Service metrics response."""
    id: UUID
    service_id: UUID
    metric_date: datetime
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: Optional[float]
    avg_execution_time_ms: Optional[int]
    error_rate: Optional[float]
    daily_cost: Optional[float]
    active_users: Optional[int]

    class Config:
        from_attributes = True


class ServiceRegistryListResponse(BaseModel):
    """List all services response."""
    total: int
    services: List[ServiceResponse]
    divisions: Dict[str, int]


class ServiceTestResponse(BaseModel):
    """Service test result response."""
    service_id: UUID
    test_mode: str
    status: str
    duration_ms: int
    success: bool
    message: str
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class ServiceRolloutResponse(BaseModel):
    """Service rollout status response."""
    service_id: UUID
    target_instances: List[str]
    deployment_id: UUID
    status: str  # pending | in_progress | success | partial | failed
    started_at: datetime
    completed_at: Optional[datetime]
    progress_percent: int
    successful_deployments: int
    failed_deployments: int
    errors: Optional[List[str]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        example = {
            "error": "Service not found",
            "code": "SERVICE_NOT_FOUND",
            "timestamp": "2026-07-02T12:00:00Z",
        }
