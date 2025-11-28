import logging
import multiprocessing
import uuid
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from fastapi import Depends

from config.config import get_settings
from core.db.models import TrainingJob
from core.schemas import TrainingRunRequest
from core.training.worker import run_training_task
from repositories.dataset_repository import (DatasetRepository,
                                             get_data_repository)
from repositories.training_repository import (TrainingJobRepository,
                                              get_training_job_repository)

logger = logging.getLogger(__name__)


class TrainingService:
    """
    Manages background training jobs using a ProcessPoolExecutor.
    """

    def __init__(
        self, job_repo: TrainingJobRepository, dataset_repo: DatasetRepository
    ):
        self.job_repo = job_repo
        self.dataset_repo = dataset_repo
        self.settings = get_settings()
        max_workers = max(1, self.settings.API_WORKERS - 1)

        ctx = multiprocessing.get_context("spawn")
        self.executor = ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)

    async def start_training_job(
        self, run_request: TrainingRunRequest, model_config_dict: dict[str, Any]
    ) -> TrainingJob:
        dataset = await self.dataset_repo.get_by_name(run_request.dataset_name)
        if not dataset:
            raise ValueError(f"Dataset '{run_request.dataset_name}' not found.")

        job_id = str(uuid.uuid4())

        # 1. Create Initial Record in DB
        new_job = TrainingJob(
            id=job_id,
            scheduler_name=run_request.scheduler_name,
            dataset_name=run_request.dataset_name,
            status="queued",
            current_cycle=0,
            total_cycles=run_request.cycles,
            metrics={},
        )
        await self.job_repo.create(new_job)

        # 2. Submit to Process Pool
        self.executor.submit(run_training_task, job_id, run_request, model_config_dict)

        # 3. Update status to submitted
        new_job.status = "submitted"
        await self.job_repo.update_status(job_id, "submitted")

        logger.info(f"Submitted training job {job_id} for {run_request.scheduler_name}")
        return new_job

    async def get_job_status(self, job_id: str) -> TrainingJob | None:
        return await self.job_repo.get(job_id)

    async def list_jobs(self):
        return await self.job_repo.list_all()


# --- Dependency Injection ---


def get_training_service(
    job_repo: TrainingJobRepository = Depends(get_training_job_repository),
    dataset_repo: DatasetRepository = Depends(get_data_repository),  # <--- Inject here
) -> TrainingService:
    return TrainingService(job_repo, dataset_repo)
