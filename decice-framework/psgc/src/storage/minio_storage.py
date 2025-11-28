import logging
from datetime import timedelta

from minio import Minio, S3Error
from minio.notificationconfig import NotificationConfig, QueueConfig

from .abstract_storage import (BucketCreationError, ObjectStorage,
                               PresignedUrlError)

logger = logging.getLogger(__name__)


class MinioStorage(ObjectStorage):
    """A concrete implementation of the ObjectStorage interface using MinIO."""

    def __init__(self, client: Minio) -> None:
        """Initializes the storage adapter with a pre-configured Minio client."""
        self.minio_client = client

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
        except S3Error as err:
            raise BucketCreationError(
                f"Error ensuring bucket '{bucket_name}' exists"
            ) from err

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Checks for an object's existence using stat_object."""
        try:
            # stat_object is a lightweight call to get object metadata.
            # if it succeeds, the object exists.
            self.minio_client.stat_object(bucket_name, object_name)
            logger.debug(f"Object '{object_name}' found in bucket '{bucket_name}'.")
            return True
        except S3Error as err:
            # if the error code is NoSuchKey, the object doesn't exist.
            if err.code == "NoSuchKey":
                logger.debug(
                    f"Object '{object_name}' not found in bucket '{bucket_name}'."
                )
                return False
            # other errors
            logger.error(f"S3Error checking for object {object_name}: {err}")
            raise

    def generate_presigned_url(
        self, bucket_name: str, object_name: str, expires_in_seconds: int = 3600
    ) -> str:
        self.ensure_bucket_exists(bucket_name)
        try:
            presigned_url = self.minio_client.presigned_put_object(
                bucket_name, object_name, expires=timedelta(seconds=expires_in_seconds)
            )
            return presigned_url
        except S3Error as err:
            raise PresignedUrlError("Failed to generate presigned URL") from err

    def configure_bucket_notification(self, bucket_name: str) -> None:
        """
        Configure bucket notifications for webhook notifications on PUT (upload) events.
        """
        queue_config = QueueConfig(
            queue="arn:minio:sqs::1:webhook",
            # queue="arn:minio:sqs::webhook",
            events=["s3:ObjectCreated:Put"],
        )
        notification_config = NotificationConfig(queue_config_list=[queue_config])
        self.minio_client.set_bucket_notification(bucket_name, notification_config)
        logger.info("Configured notifications for bucket: {bucket_name}")
