"""Integration tests for Service Registry API routes - Phase 3."""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_registry import ServiceStatus, ServiceType


@pytest.fixture
def tenant_id() -> uuid.UUID:
    """Test tenant ID."""
    return uuid.uuid4()


class TestServiceRegistryAPI:
    """Tests for Service Registry API endpoints."""

    @pytest.mark.asyncio
    async def test_create_service_201(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test POST /services/create returns 201 Created."""
        response = client.post(
            "/api/v1/services/create",
            json={
                "code": "TEST-SERVICE",
                "name": "Test Service",
                "division": "Testing",
                "service_type": "autonomous",
                "description": "A test service",
            },
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "TEST-SERVICE"
        assert data["name"] == "Test Service"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_service_duplicate_409(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test POST /services/create returns 409 for duplicate code."""
        # Create first service
        client.post(
            "/api/v1/services/create",
            json={
                "code": "DUPLICATE-TEST",
                "name": "Test",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        # Try to create duplicate
        response = client.post(
            "/api/v1/services/create",
            json={
                "code": "DUPLICATE-TEST",
                "name": "Test 2",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_service_invalid_type_400(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test POST /services/create returns 400 for invalid service_type."""
        response = client.post(
            "/api/v1/services/create",
            json={
                "code": "INVALID-TYPE",
                "name": "Test",
                "division": "Testing",
                "service_type": "invalid_type",
            },
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_services_200(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test GET /services/registry returns 200 with services."""
        # Create a few services
        for i in range(3):
            client.post(
                "/api/v1/services/create",
                json={
                    "code": f"SERVICE-{i}",
                    "name": f"Service {i}",
                    "division": "Testing",
                    "service_type": "autonomous",
                },
                params={"tenant_id": str(tenant_id)},
            )

        response = client.get(
            "/api/v1/services/registry",
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["services"]) == 3

    @pytest.mark.asyncio
    async def test_list_services_with_filter_200(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test GET /services/registry with status filter."""
        # Create services
        client.post(
            "/api/v1/services/create",
            json={
                "code": "ACTIVE-SERVICE",
                "name": "Active",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        response = client.get(
            "/api/v1/services/registry",
            params={
                "tenant_id": str(tenant_id),
                "status_filter": "active",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_service_200(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test GET /services/{service_id} returns 200."""
        # Create service
        create_response = client.post(
            "/api/v1/services/create",
            json={
                "code": "GET-TEST",
                "name": "Get Test",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        service_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/services/{service_id}",
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service_id
        assert data["code"] == "GET-TEST"

    @pytest.mark.asyncio
    async def test_get_service_not_found_404(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test GET /services/{service_id} returns 404 for missing service."""
        fake_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/services/{fake_id}",
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_service_200(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test PATCH /services/{service_id} returns 200."""
        # Create service
        create_response = client.post(
            "/api/v1/services/create",
            json={
                "code": "UPDATE-TEST",
                "name": "Original",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        service_id = create_response.json()["id"]

        # Update service
        response = client.patch(
            f"/api/v1/services/{service_id}",
            json={
                "name": "Updated Name",
                "status": "beta",
            },
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["status"] == "beta"

    @pytest.mark.asyncio
    async def test_delete_service_204(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test DELETE /services/{service_id} returns 204."""
        # Create service
        create_response = client.post(
            "/api/v1/services/create",
            json={
                "code": "DELETE-TEST",
                "name": "Delete Test",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        service_id = create_response.json()["id"]

        # Delete service
        response = client.delete(
            f"/api/v1/services/{service_id}",
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_test_service_200(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test POST /services/{service_id}/test returns 200."""
        # Create service
        create_response = client.post(
            "/api/v1/services/create",
            json={
                "code": "TEST-SERVICE",
                "name": "Test Service",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        service_id = create_response.json()["id"]

        # Test service
        response = client.post(
            f"/api/v1/services/{service_id}/test",
            json={"test_mode": "dry_run"},
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == service_id
        assert data["test_mode"] == "dry_run"
        assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_rollout_service_202(
        self,
        client: TestClient,
        tenant_id: uuid.UUID,
    ):
        """Test POST /services/{service_id}/rollout returns 202."""
        # Create service
        create_response = client.post(
            "/api/v1/services/create",
            json={
                "code": "ROLLOUT-TEST",
                "name": "Rollout Test",
                "division": "Testing",
                "service_type": "autonomous",
            },
            params={"tenant_id": str(tenant_id)},
        )

        service_id = create_response.json()["id"]

        # Rollout service
        response = client.post(
            f"/api/v1/services/{service_id}/rollout",
            json={
                "target_instances": ["ROLLOUT-TEST-PRIMARY"],
            },
            params={"tenant_id": str(tenant_id)},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["service_id"] == service_id
        assert data["status"] == "pending"
        assert "deployment_id" in data
