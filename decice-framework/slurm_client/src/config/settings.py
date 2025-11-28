from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlurmClientSettings(BaseSettings):
    """Application Configuration"""

    CLIENT_HOST: str = "127.0.0.1"
    CLIENT_PORT: int = 8060
    RELOAD: bool = True
    SLURM_API_BASE: str = "http://localhost:6820/slurm/v0.0.43"
    SLURMDB_API_BASE: str = "http://localhost:6820/slurmdb/v0.0.43"

    PSGC_SERVICE_HOST: str
    PSGC_SERVICE_PORT: int
    PSGC_SERVICE_BASE_URL: Optional[str] = None

    # Path to the private key used by slurmctld/slurmrestd for JWTs.
    # e.g., /etc/slurm/slurm.key
    # TODO: discuss implementation
    SLURM_JWT_KEY_PATH: str
    SLURM_JWT_ALGO: str = "HS256"

    INTERNAL_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def assemble_urls(self) -> "SlurmClientSettings":
        """Constructs full URLs from their component parts."""
        self.PSGC_SERVICE_BASE_URL = (
            f"http://{self.PSGC_SERVICE_HOST}:{self.PSGC_SERVICE_PORT}"
        )

        return self


@lru_cache
def get_settings() -> SlurmClientSettings:
    return SlurmClientSettings()
