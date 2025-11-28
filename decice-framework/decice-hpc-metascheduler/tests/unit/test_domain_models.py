# file: tests/unit/test_domain_models.py

import pytest
from uuid import uuid4
from datetime import datetime

from services.domain_models import Job
from schemas import JobState, ClusterType


class TestJobDomainModel:
    """Unit tests for the Job domain model."""
    
    def test_job_creation_with_all_fields(self):
        """Test creating a Job domain model with all required fields."""
        job_id = uuid4()
        creation_time = datetime.utcnow()
        
        job = Job(
            jobId=job_id,
            name="test-job",
            status=JobState.PENDING,
            targetCluster=ClusterType.VOLCANO,
            creationTimestamp=creation_time,
            userId="test-user-123"
        )
        
        assert job.jobId == job_id
        assert job.name == "test-job"
        assert job.status == JobState.PENDING
        assert job.targetCluster == ClusterType.VOLCANO
        assert job.creationTimestamp == creation_time
        assert job.userId == "test-user-123"
    
    def test_job_with_different_statuses(self):
        """Test Job model with different job states."""
        job_id = uuid4()
        
        for status in [JobState.PENDING, JobState.RUNNING, JobState.COMPLETED, JobState.FAILED]:
            job = Job(
                jobId=job_id,
                name=f"job-{status.value.lower()}",
                status=status,
                targetCluster=ClusterType.INTERLINK_SLURM,
                creationTimestamp=datetime.utcnow(),
                userId="user-123"
            )
            assert job.status == status
    
    def test_job_with_different_clusters(self):
        """Test Job model with different cluster types."""
        job_id = uuid4()
        
        for cluster in [ClusterType.VOLCANO, ClusterType.INTERLINK_SLURM]:
            job = Job(
                jobId=job_id,
                name=f"job-{cluster.value.lower()}",
                status=JobState.PENDING,
                targetCluster=cluster,
                creationTimestamp=datetime.utcnow(),
                userId="user-123"
            )
            assert job.targetCluster == cluster
    
    # Future: Add tests for business logic methods when they're implemented
    # def test_can_be_cancelled_when_pending(self):
    #     """Test that pending jobs can be cancelled."""
    #     job = Job(...)
    #     assert job.can_be_cancelled() == True
    #
    # def test_cannot_be_cancelled_when_completed(self):
    #     """Test that completed jobs cannot be cancelled."""
    #     job = Job(status=JobState.COMPLETED, ...)
    #     assert job.can_be_cancelled() == False
