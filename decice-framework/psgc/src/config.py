import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Application Configuration"""

    # Environment Setting
    ENVIRONMENT: Literal["local", "staging", "production"]

    # PSGC's own settings
    PSGC_HOST: str = "0.0.0.0"
    PSGC_PORT: int = 8040
    SCHED_WEBHOOK: bool = False

    # Downstream service host/port pairs
    CM_SERVICE_HOST: str = "control-manager"
    CM_SERVICE_PORT: int = 8000
    CM_SERVICE_BASE_URL: Optional[str] = None

    # MinIO configuration
    MINIO_ENDPOINT: str
    MINIO_PORT: int
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool

    # SLURM config
    SLURM_CLIENT_HOST: str
    SLURM_CLIENT_PORT: int
    SLURM_CLIENT_BASE_URL: Optional[str] = None

    # Redis Settings
    REDIS_URL: str
    SESSION_EXPIRE_SECONDS: int

    # Scheduler batching settings
    SCHEDULER_BATCHING_ENABLED: bool = False
    SCHEDULER_BATCH_MAX_SIZE: int = 32
    SCHEDULER_BATCH_MAX_WAIT_MS: int = 1000

    # API Key
    INTERNAL_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "production" else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="_",
    )

    @model_validator(mode="after")
    def assemble_urls(self) -> "ServiceSettings":
        """Constructs full URLs from their component parts."""
        self.CM_SERVICE_BASE_URL = (
            f"http://{self.CM_SERVICE_HOST}:{self.CM_SERVICE_PORT}/v1"
        )
        self.SLURM_CLIENT_BASE_URL = (
            f"http://{self.SLURM_CLIENT_HOST}:{self.SLURM_CLIENT_PORT}"
        )
        return self


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()
