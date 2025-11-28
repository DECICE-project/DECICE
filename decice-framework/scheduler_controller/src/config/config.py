import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Configuration"""

    # Environment Setting
    ENVIRONMENT: Literal["local", "staging", "production"]

    # Service's own host/port
    # 0.0.0.0 for container-friendliness
    SC_HOST: str = "0.0.0.0"
    SC_PORT: int = 8020

    # Downstream Service Locations
    DT_SERVICE_HOST: str = "127.0.0.1"
    DT_SERVICE_PORT: int = 8010
    DT_SERVICE_BASE_URL: Optional[str] = None

    SCHEDULER_SERVICE_HOST: str = "127.0.0.1"
    SCHEDULER_SERVICE_PORT: int = 8030
    SCHEDULER_SERVICE_BASE_URL: Optional[str] = None

    # API Key
    INTERNAL_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "production" else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _construct_and_validate_urls(self) -> "Settings":
        self.DT_SERVICE_BASE_URL = (
            f"http://{self.DT_SERVICE_HOST}:{self.DT_SERVICE_PORT}"
        )
        self.SCHEDULER_SERVICE_BASE_URL = (
            f"http://{self.SCHEDULER_SERVICE_HOST}:{self.SCHEDULER_SERVICE_PORT}"
        )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
