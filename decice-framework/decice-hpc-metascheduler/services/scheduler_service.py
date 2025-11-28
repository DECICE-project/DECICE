# file: services/scheduler_service.py

from typing import List, Optional, Dict, Any
from uuid import UUID

from repository.job_repository import JobRepository
from .domain_models import Job
from .exceptions import JobNotFoundError
from clients.kubernetes_client import KubernetesClient
from clients.slurm_client import SlurmClient
from clients.prometheus_metrics_client import PrometheusMetricsClient, IntelligentSchedulerService

class SchedulerService:
    """
    The core business logic layer (Service Layer).
    It orchestrates the process of job submission, status checking, and listing.
    """
    def __init__(
        self,
        job_repository: JobRepository,
        kubernetes_client: KubernetesClient, # Dependency Injection
        slurm_client: SlurmClient,           # Dependency Injection
        intelligent_scheduler: IntelligentSchedulerService = None  # Optional for intelligent scheduling
    ):
        self.job_repository = job_repository
        self.kubernetes_client = kubernetes_client
        self.slurm_client = slurm_client
        self.intelligent_scheduler = intelligent_scheduler

    def _map_dict_to_domain(self, job_dict: dict) -> Job:
        """Helper to convert a dictionary from the repository into a Job domain model."""
        return Job(**job_dict)

    async def submit_job(self, submission_data: dict, user_id: str) -> Job:
        """
        Orchestrates the job submission process with intelligent scheduling.
        1. Creates a record in our own database.
        2. Decides the target based on the submission and current load metrics.
        3. Creates a "manager pod" in Kubernetes to handle the actual execution.
        4. Updates the job record with the manager pod's name.
        """
        # Step 1: Intelligent scheduler selection
        scheduler_target = submission_data["schedulerTarget"]
        if self.intelligent_scheduler and scheduler_target == "AUTO":
            # Use load-aware scheduling for AUTO mode
            scheduler_target = await self.intelligent_scheduler.get_scheduling_recommendation(submission_data)
        
        # Step 2: Create the initial job record in our DB.
        job_data = self.job_repository.add(
            name=submission_data["name"],
            image=submission_data["image"],
            scheduler_target=scheduler_target,
            user_id=user_id
        )
        
        # This is where Strategy #2's logic happens.
        # For the MVP, we assume the manager pod always runs on Kubernetes.
        # The manager pod itself will then decide whether to talk to Volcano or Slurm.
        
        # Step 2: Create the manager pod in Kubernetes.
        manager_pod_name = self.kubernetes_client.create_manager_pod(
            job_name=job_data["name"],
            image="my-manager-pod-image:latest", # This would be a predefined image
            command=["python", "job_runner.py"], # The script inside the manager pod
            job_details=submission_data # Pass the original job details to the pod
        )
        
        # Step 3: Update our job record with the manager pod's name for tracking.
        updated_job_data = self.job_repository.update(
            job_id=job_data["jobId"], 
            user_id=user_id, 
            update_data={"manager_pod_name": manager_pod_name}
        )

        return self._map_dict_to_domain(updated_job_data)

    def get_job(self, job_id: UUID, user_id: str) -> Job:
        """
        Retrieves a job, raising a business-specific exception if not found.
        """
        job_data = self.job_repository.get(job_id=job_id, user_id=user_id)
        if job_data is None:
            raise JobNotFoundError(f"Job with id {job_id} not found for this user.")
        
        # Here, you could add logic to query the manager pod's status from Kubernetes
        # and update the job's status in the DB before returning it.
        # For now, we just return the stored status.
        
        return self._map_dict_to_domain(job_data)

    def list_jobs(self, user_id: str, limit: int, offset: int, status: Optional[str], name: Optional[str]) -> tuple[List[Job], int]:
        """
        Lists jobs for a user with filtering and gets the total count.
        """
        job_dicts = self.job_repository.list(
            user_id=user_id, 
            limit=limit, 
            offset=offset, 
            status=status, 
            name=name
        )
        total_count = self.job_repository.count(user_id=user_id, status=status, name=name)
        
        jobs = [self._map_dict_to_domain(d) for d in job_dicts]
        
        return jobs, total_count