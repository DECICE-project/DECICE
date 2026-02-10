# file: tests/unit/test_schemas.py

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from schemas import (
    JobSubmissionSchema,
    JobStatusSchema,
    JobListSchema,
    JobState,
    ClusterType,
)


class TestJobSubmissionSchema:
    """Unit tests for JobSubmissionSchema validation."""

    def test_valid_job_submission(self):
        """Test creating a valid job submission."""
        data = {
            "name": "test-job",
            "image": "test-image:latest",
            "schedulerTarget": "VOLCANO",
        }

        submission = JobSubmissionSchema(**data)

        assert submission.name == "test-job"
        assert submission.image == "test-image:latest"
        assert submission.schedulerTarget == ClusterType.VOLCANO

    def test_job_submission_with_interlink_slurm(self):
        """Test job submission with INTERLINK_SLURM target."""
        data = {
            "name": "slurm-job",
            "image": "slurm-image:v1",
            "schedulerTarget": "INTERLINK_SLURM",
        }

        submission = JobSubmissionSchema(**data)
        assert submission.schedulerTarget == ClusterType.INTERLINK_SLURM

    def test_job_submission_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError):
            JobSubmissionSchema(name="test-job")  # Missing image and schedulerTarget

        with pytest.raises(ValidationError):
            JobSubmissionSchema(
                image="test-image:latest"
            )  # Missing name and schedulerTarget

    def test_job_submission_invalid_scheduler_target(self):
        """Test that invalid scheduler target raises validation error."""
        data = {
            "name": "test-job",
            "image": "test-image:latest",
            "schedulerTarget": "INVALID_TARGET",
        }

        with pytest.raises(ValidationError):
            JobSubmissionSchema(**data)

    def test_job_submission_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        data = {
            "name": "test-job",
            "image": "test-image:latest",
            "schedulerTarget": "VOLCANO",
            "extraField": "not-allowed",
        }

        with pytest.raises(ValidationError):
            JobSubmissionSchema(**data)


class TestJobStatusSchema:
    """Unit tests for JobStatusSchema validation."""

    def test_valid_job_status(self):
        """Test creating a valid job status."""
        job_id = uuid4()
        timestamp = datetime.utcnow()

        data = {
            "jobId": job_id,
            "name": "test-job",
            "status": "PENDING",
            "targetCluster": "VOLCANO",
            "creationTimestamp": timestamp,
            "userId": "user-123",
        }

        status = JobStatusSchema(**data)

        assert status.jobId == job_id
        assert status.name == "test-job"
        assert status.status == JobState.PENDING
        assert status.targetCluster == ClusterType.VOLCANO
        assert status.creationTimestamp == timestamp
        assert status.userId == "user-123"

    def test_job_status_with_all_states(self):
        """Test job status with all possible states."""
        base_data = {
            "jobId": uuid4(),
            "name": "test-job",
            "targetCluster": "VOLCANO",
            "creationTimestamp": datetime.utcnow(),
            "userId": "user-123",
        }

        for state in ["PENDING", "RUNNING", "COMPLETED", "FAILED", "UNKNOWN"]:
            data = {**base_data, "status": state}
            status = JobStatusSchema(**data)
            assert status.status.value == state

    def test_user_id_excluded_from_serialization(self):
        """Test that userId is excluded from JSON serialization."""
        data = {
            "jobId": uuid4(),
            "name": "test-job",
            "status": "PENDING",
            "targetCluster": "VOLCANO",
            "creationTimestamp": datetime.utcnow(),
            "userId": "user-123",
        }

        status = JobStatusSchema(**data)
        json_data = status.model_dump()

        assert "userId" not in json_data
        assert "jobId" in json_data


class TestJobListSchema:
    """Unit tests for JobListSchema validation."""

    def test_valid_job_list(self):
        """Test creating a valid job list."""
        job_data = {
            "jobId": uuid4(),
            "name": "test-job",
            "status": "PENDING",
            "targetCluster": "VOLCANO",
            "creationTimestamp": datetime.utcnow(),
            "userId": "user-123",
        }

        job_status = JobStatusSchema(**job_data)

        data = {"total": 1, "jobs": [job_status]}

        job_list = JobListSchema(**data)

        assert job_list.total == 1
        assert len(job_list.jobs) == 1
        assert job_list.jobs[0].name == "test-job"

    def test_empty_job_list(self):
        """Test creating an empty job list."""
        data = {"total": 0, "jobs": []}

        job_list = JobListSchema(**data)

        assert job_list.total == 0
        assert len(job_list.jobs) == 0
