from minio import Minio

from service.storage_service import StorageService
from storage.minio_storage import MinioStorage


class TestStorageServiceIntegration:
    def test_ensure_bucket_exists_and_generate_url(
        self,
        minio_client: Minio,
        minio_endpoint: str,
    ):
        """
        GIVEN a live MinIO instance provided by testcontainers
        WHEN we use the StorageService to ensure a bucket exists and generate a URL
        THEN the bucket should actually be created in MinIO and a valid URL should be returned.
        """
        storage_backend = MinioStorage(client=minio_client)

        storage_service = StorageService(storage_backend=storage_backend)

        bucket_name = "test-integration-bucket"
        object_name = "my-test-file.zip"

        storage_service.ensure_bucket_exists(bucket_name)

        presigned_url = storage_service.generate_presigned_url(
            bucket_name=bucket_name, object_name=object_name, expires_in_seconds=60
        )

        assert minio_client.bucket_exists(bucket_name)

        assert isinstance(presigned_url, str)
        assert f"/{bucket_name}/{object_name}" in presigned_url
        assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in presigned_url
        assert "X-Amz-Credential=" in presigned_url
        assert "X-Amz-Expires=60" in presigned_url
