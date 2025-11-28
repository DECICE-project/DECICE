from fastapi import Depends
from minio import Minio

from core.dependencies import get_minio_client
from storage.abstract_storage import ObjectStorage
from storage.minio_storage import MinioStorage


class StorageService:
    """A service that provides a clean interface for object storage operations."""

    def __init__(self, storage_backend: ObjectStorage):
        self.storage = storage_backend

    def generate_presigned_url(
        self, bucket_name: str, object_name: str, expires_in_seconds: int = 3600
    ) -> str:
        return self.storage.generate_presigned_url(
            bucket_name, object_name, expires_in_seconds
        )

    def ensure_bucket_exists(self, bucket_name: str):
        self.storage.ensure_bucket_exists(bucket_name)

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        return self.storage.object_exists(bucket_name, object_name)


# Dependency Provider Function
def get_storage_service(
    minio_client: Minio = Depends(get_minio_client),
) -> StorageService:
    """
    FastAPI dependency provider for StorageService.
    This function creates the concrete MinioStorage instance using centralized
    configuration and injects it into the StorageService.
    """
    minio_backend = MinioStorage(client=minio_client)

    return StorageService(storage_backend=minio_backend)
