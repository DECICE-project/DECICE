from abc import ABC, abstractmethod


class StorageError(Exception):
    """Base exception for storage errors."""


class BucketCreationError(StorageError):
    """Raised when bucket creation fails."""


class PresignedUrlError(StorageError):
    """Raised when generating a presigned URL fails."""


class ObjectStorage(ABC):
    @abstractmethod
    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """Ensure that a bucket exists, creating it if necessary."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def generate_presigned_url(
        self, bucket_name: str, object_name: str, expires_in_seconds: int = 3600
    ) -> str:
        """Generate a presigned URL for the given bucket and object."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def configure_bucket_notification(self, bucket_name: str) -> None:
        """
        Optionally configure bucket notifications.
        Subclasses that support notifications should override this method.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Checks if a specific object exists in a bucket."""
        raise NotImplementedError("Subclasses must implement this method")
