import logging
import tempfile
from pathlib import Path
from typing import Sequence

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import get_settings
from core.db.models import TrainingDataset
from core.storage.interface import IStorageProvider
from core.storage.local import LocalStorageProvider
from core.training.generator import ScenarioGenerator
from repositories.dataset_repository import (DatasetRepository,
                                             get_data_repository)

logger = logging.getLogger(__name__)


class DataService:
    def __init__(self, repository: DatasetRepository, storage: IStorageProvider):
        self.repo = repository
        self.storage = storage

    async def create_synthetic_dataset(
        self, name: str, num_files: int, job_min: int, job_max: int
    ) -> dict:
        """
        Generates synthetic data and stores it via the storage provider and repository.
        """
        # 1. Logic Check via Repository
        existing = await self.repo.get_by_name(name)
        if existing:
            return {
                "status": "error",
                "message": f"Dataset '{name}' already exists in database.",
            }

        generated_count = 0

        # 2. Generate and Store
        # We use a temporary directory to generate the files first.
        # This decouples the Generator (which writes to disk) from our Storage Provider (which might be S3).
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Instantiate generator pointing to temp folder
                generator = ScenarioGenerator(output_dir=temp_path)
                generated_count = generator.generate_batch(
                    num_files=num_files, job_range=(job_min, job_max)
                )

                # Move files from temp folder to our Storage Provider
                for file_path in temp_path.glob("*.json"):
                    # Define key structure: "{dataset_name}/{filename}"
                    storage_key = f"{name}/{file_path.name}"
                    with open(file_path, "rb") as f:
                        self.storage.save_file(storage_key, f)

        except Exception as e:
            logger.error(f"Failed to generate dataset: {e}", exc_info=True)
            # Cleanup storage if partial upload happened (optional depending on storage provider)
            self.storage.delete_folder(name)
            raise e

        # 3. Metadata Write via Repository
        new_dataset = TrainingDataset(
            name=name,
            file_count=generated_count,
            path=name,  # Storing the relative "key" or "prefix"
            storage_type="local",
            job_min=job_min,
            job_max=job_max,
        )

        await self.repo.create(new_dataset)

        return {
            "status": "created",
            "dataset_name": name,
            "files_generated": generated_count,
            "path": new_dataset.path,
        }

    async def upload_dataset(self, name: str, files: list[UploadFile]) -> dict:
        # 1. Logic Check via Repository
        existing = await self.repo.get_by_name(name)
        if existing:
            return {"status": "error", "message": f"Dataset '{name}' already exists."}

        # 2. Physical Write via Storage Adapter
        saved_count = 0
        try:
            for file in files:
                if not file.filename.endswith(".json"):
                    continue

                # Define structure: "{dataset_name}/{filename}"
                storage_key = f"{name}/{file.filename}"
                self.storage.save_file(storage_key, file.file)
                saved_count += 1
        except Exception as e:
            # Cleanup on failure
            self.storage.delete_folder(name)
            raise e

        # 3. Metadata Write via Repository
        new_dataset = TrainingDataset(
            name=name,
            file_count=saved_count,
            path=name,  # Storing the relative "key" or "prefix"
            storage_type="local",
        )
        await self.repo.create(new_dataset)

        return {"status": "uploaded", "dataset_name": name, "files": saved_count}

    async def list_datasets(self) -> Sequence[TrainingDataset]:
        return await self.repo.list_active()

    async def delete_dataset(self, name: str) -> dict:
        dataset = await self.repo.get_by_name(name)
        if not dataset:
            return {"status": "error", "message": "Dataset not found"}

        # 1. Delete physical files
        self.storage.delete_folder(name)

        # 2. Delete DB record
        await self.repo.delete(dataset)

        return {"status": "deleted", "dataset_name": name}


# # Dependency Provider Functions
def get_storage_provider() -> IStorageProvider:
    # This is where you would toggle between Local and S3 based on env vars
    settings = get_settings()
    # return S3StorageProvider(bucket=settings.S3_BUCKET) if settings.USE_S3 else ...
    return LocalStorageProvider(root_dir=settings.DATA_BASE_DIR / "datasets")


def get_data_service(
    repository: DatasetRepository = Depends(get_data_repository),
    storage: IStorageProvider = Depends(get_storage_provider),
) -> DataService:
    """FastAPI dependency provider for DataService."""
    return DataService(repository=repository, storage=storage)
