import logging
import uuid
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from fastapi import Depends

from config.config import get_settings
from core.db.models import EvaluationJob
from repositories.evaluation_repository import (
    EvaluationJobRepository,
    get_evaluation_repository,
)
from repositories.dataset_repository import DatasetRepository, get_data_repository
from core.evaluation.worker import run_evaluation_task

logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self, job_repo: EvaluationJobRepository, data_repo: DatasetRepository):
        self.job_repo = job_repo
        self.data_repo = data_repo
        self.settings = get_settings()

        # Use Spawn context for TensorFlow safety
        ctx = multiprocessing.get_context("spawn")
        self.executor = ProcessPoolExecutor(max_workers=1, mp_context=ctx)

    async def start_evaluation(
        self, scheduler_name: str, dataset_name: str
    ) -> EvaluationJob:
        # Validate Dataset
        if not await self.data_repo.get_by_name(dataset_name):
            raise ValueError(f"Dataset '{dataset_name}' not found.")

        # Validate Model existence on disk
        model_path = self.settings.MODELS_BASE_DIR / scheduler_name
        if not model_path.exists():
            raise ValueError(f"Model '{scheduler_name}' not found at {model_path}.")

        job_id = str(uuid.uuid4())

        job = EvaluationJob(
            id=job_id,
            scheduler_name=scheduler_name,
            dataset_name=dataset_name,
            status="queued",
        )
        await self.job_repo.create(job)

        self.executor.submit(run_evaluation_task, job_id, scheduler_name, dataset_name)

        job.status = "submitted"
        await self.job_repo.update_results(job_id, "submitted")

        return job

    async def list_jobs(self):
        return await self.job_repo.list_all()

    async def get_job(self, job_id: str):
        return await self.job_repo.get(job_id)


def get_evaluation_service(
    job_repo: EvaluationJobRepository = Depends(get_evaluation_repository),
    data_repo: DatasetRepository = Depends(get_data_repository),
) -> EvaluationService:
    return EvaluationService(job_repo, data_repo)
