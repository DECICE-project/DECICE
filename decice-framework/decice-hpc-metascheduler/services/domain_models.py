# file: services/domain_models.py

from uuid import UUID
from datetime import datetime
from schemas import JobState, ClusterType

class Job:
    """
    The business domain model for a Job.
    It represents a job's state and identity within our application's core logic,
    decoupled from both the database and the API schemas.
    """
    def __init__(
        self,
        jobId: UUID,
        name: str,
        status: JobState,
        targetCluster: ClusterType,
        creationTimestamp: datetime,
        userId: str
    ):
        self.jobId = jobId
        self.name = name
        self.status = status
        self.targetCluster = targetCluster
        self.creationTimestamp = creationTimestamp
        self.userId = userId

    # In the future, business logic methods could be added here, e.g.:
    # def can_be_cancelled(self) -> bool:
    #     return self.status in [JobState.PENDING, JobState.RUNNING]