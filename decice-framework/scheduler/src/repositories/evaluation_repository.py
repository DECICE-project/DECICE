import logging
from typing import Sequence, Optional
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.db.models import EvaluationJob
from core.dependencies.dependencies import get_db_session

logger = logging.getLogger(__name__)


class EvaluationJobRepository:
    def __init__(self, session: AsyncSession):
        self.db = session

    async def create(self, job: EvaluationJob) -> EvaluationJob:
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get(self, job_id: str) -> Optional[EvaluationJob]:
        result = await self.db.execute(
            select(EvaluationJob).where(EvaluationJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[EvaluationJob]:
        stmt = select(EvaluationJob).order_by(EvaluationJob.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_results(
        self, job_id: str, status: str, metrics: dict = None, error: str = None
    ):
        job = await self.get(job_id)
        if not job:
            return

        job.status = status
        if error:
            job.error_message = error

        if metrics:
            job.details = metrics.get("details")
            job.optimality_rate = metrics.get("optimality_rate")
            job.avg_regret = metrics.get("avg_regret")
            job.avg_ai_reward = metrics.get("avg_ai_reward")

        self.db.add(job)
        await self.db.commit()


async def get_evaluation_repository(session: AsyncSession = Depends(get_db_session)):
    return EvaluationJobRepository(session)
