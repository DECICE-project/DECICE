import logging
from typing import Any, Dict, Optional, Sequence

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import TrainingJob
from core.dependencies.dependencies import get_db_session

logger = logging.getLogger(__name__)


class TrainingJobRepository:
    """
    Data Access Layer for Training Jobs.
    Handles creation, status updates, and retrieval of job records.
    """

    def __init__(self, session: AsyncSession):
        self.db = session

    async def create(self, job: TrainingJob) -> TrainingJob:
        """Creates a new training job record."""
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get(self, job_id: str) -> Optional[TrainingJob]:
        """Retrieves a job by its UUID."""
        stmt = select(TrainingJob).where(TrainingJob.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[TrainingJob]:
        """Retrieves all training jobs, ordered by creation time (newest first)."""
        stmt = select(TrainingJob).order_by(TrainingJob.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        job_id: str,
        status: str,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[TrainingJob]:
        """
        Updates the status, error message, and metrics of a job.
        Used by both the Service (initial submission) and the Worker (completion/failure).
        """
        job = await self.get(job_id)
        if not job:
            return None

        job.status = status

        if message:
            job.error_message = message

        if metrics:
            # Update metrics JSON.
            # Note: This usually replaces the dict. If you want to merge, logic is needed here.
            job.metrics = metrics

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job


# Dependency Provider Function
async def get_training_job_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TrainingJobRepository:
    """
    FastAPI Dependency to get a TrainingJobRepository instance
    with an active AsyncSession.
    """
    return TrainingJobRepository(session=session)
