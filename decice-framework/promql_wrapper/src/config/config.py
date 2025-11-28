import json
import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClusterInfoQueryConfig(BaseModel):
    field_name: str
    promql: str
    label_key: str | None = None


class NodeInfoQueryConfig(BaseModel):
    field_name: str
    promql: str


class AutoUpdateDT(BaseSettings):
    enabled: bool = False
    frequency_seconds: float = 30.0


class ServiceSettings(BaseSettings):
    """
    Consolidated application settings.
    Loads variables from .env files and the environment.
    """

    # Environment Setting
    ENVIRONMENT: Literal["local", "staging", "production"]

    # Service Host/Port
    PROMQL_WRAPPER_HOST: str = "0.0.0.0"
    PROMQL_WRAPPER_PORT: int = 8050

    # Service Log Level
    LOG_LEVEL: str = "INFO"

    # Downstream Service Locations
    DT_SERVICE_HOST: str = "127.0.0.1"
    DT_SERVICE_PORT: int = 8010
    DT_BASE_URL: Optional[str] = None

    PROMETHEUS_HOST: str = "127.0.0.1"
    PROMETHEUS_PORT: int = 9090
    PROMETHEUS_BASE_URL: Optional[str] = None

    # Background Task/Digital Twin Configuration
    AUTO_UPDATE_DT_ENABLED: bool = False
    AUTO_UPDATE_DT_FREQUENCY_SECONDS: float = 30.0

    # Prometheus Queries
    POWER_CONSUMPTION_PROMQL_QUERIES: Optional[list[str]] = None
    CLUSTER_INFO_QUERIES: Optional[list[ClusterInfoQueryConfig]] = None
    NODE_INFO_QUERIES: Optional[list[NodeInfoQueryConfig]] = None

    # API Key
    INTERNAL_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "production" else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _construct_and_validate_urls(self) -> "ServiceSettings":
        """Constructs full base URLs from host and port."""
        self.DT_BASE_URL = f"http://{self.DT_SERVICE_HOST}:{self.DT_SERVICE_PORT}"
        self.PROMETHEUS_BASE_URL = (
            f"http://{self.PROMETHEUS_HOST}:{self.PROMETHEUS_PORT}"
        )

        return self

    @field_validator("NODE_INFO_QUERIES", "CLUSTER_INFO_QUERIES", mode="before")
    @classmethod
    def parse_json_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for NODE_INFO_QUERIES: {e}")
        return v


@lru_cache
def get_settings() -> ServiceSettings:
    """
    Creates and caches a singleton instance of the service settings.
    """
    return ServiceSettings()
