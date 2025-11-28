from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api import app
from auth.auth import verify_internal_traffic
from services.snapshot_service import get_snapshot_service


@pytest.mark.asyncio
async def test_pool_endpoint_success(
    test_client: TestClient,
):
    """
    GIVEN a request to the /pool endpoint
    WHEN the underlying service executes successfully
    THEN the API should return a 202 Accepted status and a success message.
    """
    mock_snapshot_service = AsyncMock()
    mock_snapshot_service.create_and_post_snapshot = AsyncMock()

    app.dependency_overrides[verify_internal_traffic] = lambda: True
    app.dependency_overrides[get_snapshot_service] = lambda: mock_snapshot_service

    response = test_client.post("/pool")

    assert response.status_code == 202
    assert response.json() == {"message": "Digital Twin update completed successfully."}
    mock_snapshot_service.create_and_post_snapshot.assert_awaited_once()

    app.dependency_overrides.clear()
