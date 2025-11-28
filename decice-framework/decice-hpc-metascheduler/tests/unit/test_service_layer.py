# file: tests/unit/test_service_layer.py

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime

# Import components from the Service Layer
from services.scheduler_service import SchedulerService
from services.exceptions import JobNotFoundError

def test_submit_job_to_volcano():
    """
    Unit test for the SchedulerService's submit_job method.
    Dependencies (repository, clients) are mocked to isolate the business logic.
    """
    # 1. Arrange: Create mock objects for all dependencies
    mock_repo = MagicMock()
    mock_k8s_client = MagicMock()
    mock_slurm_client = MagicMock()

    # Configure the mock repository's return value
    job_id = uuid4()
    mock_repo.add.return_value = {
        "jobId": job_id,
        "name": "test-job",
        "status": "PENDING",
        "targetCluster": "VOLCANO",
        "creationTimestamp": datetime.utcnow(),
        "userId": "test-user"
    }
    mock_repo.update.return_value = {
        "jobId": job_id,
        "name": "test-job",
        "status": "PENDING",
        "targetCluster": "VOLCANO",
        "creationTimestamp": datetime.utcnow(),
        "userId": "test-user"
    }
    
    # Configure the mock k8s client's return value
    mock_k8s_client.create_manager_pod.return_value = "test-job-manager-pod"

    # 2. Act: Instantiate the service with the mocked dependencies and call the method
    service = SchedulerService(
        job_repository=mock_repo,
        kubernetes_client=mock_k8s_client,
        slurm_client=mock_slurm_client
    )
    
    submission_data = {
        "name": "test-job",
        "image": "test-image",
        "schedulerTarget": "VOLCANO"
    }
    
    result = service.submit_job(submission_data=submission_data, user_id="test-user")

    # 3. Assert: Verify the business logic behaved as expected
    # a) Check that the repository was called to add the initial record
    mock_repo.add.assert_called_once_with(
        name="test-job",
        image="test-image",
        scheduler_target="VOLCANO",
        user_id="test-user"
    )
    
    # b) Check that the *correct* downstream client was called
    mock_k8s_client.create_manager_pod.assert_called_once()
    mock_slurm_client.submit_job_via_interlink.assert_not_called()

    # c) Check that the repository was called to update the record with the pod name
    mock_repo.update.assert_called_once_with(
        job_id=job_id,
        user_id="test-user",
        update_data={"manager_pod_name": "test-job-manager-pod"}
    )
    
    assert result.jobId == job_id

def test_get_job_raises_not_found(
):
    """Tests that the service layer correctly translates a repository's None result into a business exception."""
    mock_repo = MagicMock()
    mock_repo.get.return_value = None # Simulate the job not being found in the DB

    service = SchedulerService(mock_repo, Mock(), Mock())

    with pytest.raises(JobNotFoundError):
        service.get_job(job_id=uuid4(), user_id="any-user")