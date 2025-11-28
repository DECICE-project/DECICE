import logging
from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import TrainingDataset
from core.dependencies.dependencies import get_db_session

logger = logging.getLogger(__name__)


class DatasetRepository:
    def __init__(self, session: AsyncSession):
        self.db = session

    async def create(self, dataset: TrainingDataset) -> TrainingDataset:
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get_by_name(self, name: str) -> Optional[TrainingDataset]:
        stmt = select(TrainingDataset).where(TrainingDataset.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[TrainingDataset]:
        stmt = select(TrainingDataset).where(TrainingDataset.is_active)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update(self, dataset: TrainingDataset) -> TrainingDataset:
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def delete(self, dataset: TrainingDataset) -> None:
        await self.db.delete(dataset)
        await self.db.commit()


# Dependency Provider Function
def get_data_repository(
    session: AsyncSession = Depends(get_db_session),
) -> DatasetRepository:
    """FastAPI dependency provider for DatasetRepository."""
    return DatasetRepository(session=session)
