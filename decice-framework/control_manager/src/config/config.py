import os
import warnings
from functools import lru_cache
from typing import Literal, Optional, Union

from pydantic import AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Configuration"""

    # Environment Setting
    ENVIRONMENT: Literal["local", "staging", "production"]

    # DB Settings
    DATABASE_URL: str

    # Redis Settings
    REDIS_URL: str
    SESSION_EXPIRE_SECONDS: int

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # CORS Settings
    CORS_ALLOWED_ORIGINS: Union[list[str], str]
    CORS_ALLOWED_METHODS: Union[list[str], str]
    CORS_ALLOWED_HEADERS: Union[list[str], str]
    CORS_ALLOW_CREDENTIALS: bool

    # Service Host/Port
    CM_HOST: str = "0.0.0.0"
    CM_PORT: int = 8000

    # Downstream Service Locations
    DT_HOST: str = "127.0.0.1"
    DT_PORT: int = 8010
    DT_BASE_URL: Optional[AnyHttpUrl] = None

    PROMETHEUS_URL: str = "http://127.0.0.1:9090"

    PROMQL_WRAPPER_HOST: str = "127.0.0.1"
    PROMQL_WRAPPER_PORT: int = 8050
    PROMQL_WRAPPER_BASE_URL: Optional[str] = None

    PSGC_HOST: str = "127.0.0.1"
    PSGC_PORT: int = 8040
    PSGC_BASE_URL: Optional[str] = None

    SCHEDULER_HOST: str = "127.0.0.1"
    SCHEDULER_PORT: int = 8030
    SCHEDULER_BASE_URL: Optional[str] = None

    SC_HOST: str = "127.0.0.1"
    SC_PORT: int = 8020
    SC_BASE_URL: Optional[str] = None

    # OpenTelemetry Configuration
    OTEL_SERVICE_NAME: Optional[str] = None
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: Optional[str] = None
    OTEL_EXPORTER_OTLP_LOGS_HEADERS: Optional[str] = None

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
        self.DT_BASE_URL = f"http://{self.DT_HOST}:{self.DT_PORT}"
        self.PROMQL_WRAPPER_BASE_URL = (
            f"http://{self.PROMQL_WRAPPER_HOST}:{self.PROMQL_WRAPPER_PORT}"
        )
        self.PSGC_BASE_URL = f"http://{self.PSGC_HOST}:{self.PSGC_PORT}"
        self.SCHEDULER_BASE_URL = f"http://{self.SCHEDULER_HOST}:{self.SCHEDULER_PORT}"
        self.SC_BASE_URL = f"http://{self.SC_HOST}:{self.SC_PORT}"

        if len(self.JWT_SECRET_KEY) < 64:
            warnings.warn(
                f"SECURITY WARNING: JWT_SECRET_KEY is potentially too short ({len(self.JWT_SECRET_KEY)} chars)..."
            )

        self.CORS_ALLOWED_ORIGINS = self._assemble_cors_list_helper(
            self.CORS_ALLOWED_ORIGINS
        )
        self.CORS_ALLOWED_METHODS = self._assemble_cors_list_helper(
            self.CORS_ALLOWED_METHODS
        )
        self.CORS_ALLOWED_HEADERS = self._assemble_cors_list_helper(
            self.CORS_ALLOWED_HEADERS
        )

        if self.ENVIRONMENT == "production" and self.CORS_ALLOWED_ORIGINS == ["*"]:
            warnings.warn(
                "SECURITY WARNING: Running in 'production' with CORS_ALLOWED_ORIGINS='*'."
            )

        return self

    def _assemble_cors_list_helper(self, value: Union[list[str], str]) -> list[str]:
        if isinstance(value, str) and value != "*":
            return [item.strip() for item in value.split(",")]
        if isinstance(value, list):
            return value
        if value == "*":
            return ["*"]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
