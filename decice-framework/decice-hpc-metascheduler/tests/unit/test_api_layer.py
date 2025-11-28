# file: tests/unit/test_api_layer.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

# Import the FastAPI app instance
from app import app
from schemas import JobState

@pytest.fixture
def client():
    """Fixture to create a TestClient for the FastAPI app."""
    return TestClient(app)

def test_submit_job_api_success(client: TestClient):
    """
    Unit test for the POST /jobs endpoint.
    The entire service and UoW layer is mocked to isolate the API layer.
    """
    # 1. Arrange: We use `patch` to intercept calls to the UnitOfWork and service layer.
    mock_job_domain_model = MagicMock()
    mock_job_domain_model.jobId = uuid4()
    mock_job_domain_model.name = "mocked-job"
    mock_job_domain_model.status = JobState.PENDING
    mock_job_domain_model.targetCluster = "VOLCANO"
    mock_job_domain_model.creationTimestamp = datetime.utcnow()
    mock_job_domain_model.userId = "mocked-user"  # Add missing userId field
    
    with patch("app.SchedulerService") as mock_scheduler_service:
        # Configure the mock service instance to return our mock domain model
        mock_scheduler_service.return_value.submit_job.return_value = mock_job_domain_model
        
        # We also need to mock the UnitOfWork so it doesn't try to connect to a DB
        with patch("app.UnitOfWork") as mock_uow:
            # 2. Act: Make the API call
            response = client.post(
                "/jobs",
                headers={"Authorization": "Bearer fake-token"},
                json={
                    "name": "mocked-job",
                    "image": "mocked-image",
                    "schedulerTarget": "VOLCANO"
                }
            )

            # 3. Assert: Verify the API layer's behavior
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["name"] == "mocked-job"
            assert response_data["status"] == "PENDING"

            # Check that the service layer was called correctly
            mock_scheduler_service.return_value.submit_job.assert_called_once()


def test_get_job_api_handles_not_found(client: TestClient):
    """
    Tests that the API layer correctly translates a JobNotFoundError from the
    service layer into a 404 HTTP response.
    """
    with patch("app.SchedulerService") as mock_scheduler_service:
        # Configure the mock service to raise the business exception
        from services.exceptions import JobNotFoundError
        mock_scheduler_service.return_value.get_job.side_effect = JobNotFoundError

        with patch("app.UnitOfWork"):
            job_id_to_test = uuid4()
            response = client.get(f"/jobs/{job_id_to_test}", headers={"Authorization": "Bearer fake-token"})
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Job not found"