import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api import app
from auth.auth import verify_internal_traffic
from services.orchestration import get_orchestration_service


@pytest.fixture
def mock_orchestration_service() -> AsyncMock:
    """Provides a mock OrchestrationService."""
    service = AsyncMock()
    service.process_scheduling.return_value = {
        "placements": [
            {
                "task_id": "mock-task-id",
                "target_node_ids": ["node-1"],
                "strategy_used": "mock-strategy",
            }
        ],
        "scheduling_duration_ms": 5.0,
    }
    return service


@pytest.mark.asyncio
async def test_scheduler_controller_endpoint_success(
    mock_orchestration_service: AsyncMock,
):
    """
    GIVEN a valid Task payload
    WHEN a POST request is made to /scheduler-controller
    THEN it should return a 201 Created with the mocked service response.
    """
    app.dependency_overrides[verify_internal_traffic] = lambda: True
    app.dependency_overrides[get_orchestration_service] = lambda: (
        mock_orchestration_service
    )

    client = TestClient(app)

    payload = {
        "id": str(uuid.uuid4()),
        "requirements": {"required_cpu": 1, "required_memory": "1024Mi"},
    }
    # ----------------------------------------------------------------------

    response = client.post("/scheduler-controller", json=payload)

    if response.status_code == 422:
        print(f"Validation Error: {response.json()}")

    assert response.status_code == 201

    data = response.json()
    assert "placements" in data
    assert data["placements"][0]["target_node_ids"] == ["node-1"]

    mock_orchestration_service.process_scheduling.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scheduler_controller_endpoint_validation_error(
    mock_orchestration_service: AsyncMock,
):
    """
    GIVEN an invalid payload (missing required fields)
    WHEN a POST request is made
    THEN it should return 422 Unprocessable Entity.
    """
    app.dependency_overrides[verify_internal_traffic] = lambda: True
    app.dependency_overrides[get_orchestration_service] = lambda: (
        mock_orchestration_service
    )
    client = TestClient(app)

    payload = {"id": str(uuid.uuid4())}

    response = client.post("/scheduler-controller", json=payload)

    assert response.status_code == 422
    mock_orchestration_service.process_scheduling.assert_not_awaited()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """
    GIVEN the application is running
    WHEN a GET request is made to /health
    THEN it should return 200 OK.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
