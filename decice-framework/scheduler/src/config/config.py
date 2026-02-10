import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(Enum):
    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings for the AI Scheduler.
    """

    # General Config
    ENVIRONMENT: Literal["local", "staging", "production"]
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # Service Host/Port
    SCHEDULER_HOST: str = "0.0.0.0"
    SCHEDULER_PORT: int = 8030
    API_WORKERS: int = 1

    # Internal Auth
    INTERNAL_API_KEY: str

    # ---------------------------------------------------------
    # DATA DIRECTORY STRUCTURE
    # Root for all persistence
    # ---------------------------------------------------------
    DATA_BASE_DIR: Path = Path("data")

    # Models: /data/models
    MODELS_BASE_DIR: Path = DATA_BASE_DIR / "models"

    # Scalers: /data/scalers
    SCALERS_DIR: Path = DATA_BASE_DIR / "scalers"
    SCALERS_DICT_FILENAME: str = "all_feature_scalers.joblib"
    ALL_SCALERS_FILE_PATH: Path = SCALERS_DIR / SCALERS_DICT_FILENAME

    # Datasets: /data/datasets
    # Used by DataService
    DATASETS_DIR: Path = DATA_BASE_DIR / "datasets"

    # Legacy/Script Paths (Mapped to new structure)
    # These are used if you still run old scripts, but we are moving away from them.
    SCENARIO_DIR_TRAIN: Path = DATASETS_DIR / "training"
    SCENARIO_DIR_TEST: Path = DATASETS_DIR / "testing"

    # Replay Buffers: /data/replay_buffers
    REPLAY_BUFFER_DIR: Path = DATA_BASE_DIR / "replay_buffers"
    DEFAULT_REPLAY_BUFFER_FILE: Path = REPLAY_BUFFER_DIR / "replay_buffer.pkl"

    # Tensorboard
    TENSORBOARD_LOG_DIR: Path = DATA_BASE_DIR / "tensorboard"

    # ---------------------------------------------------------
    # STRATEGIES & PARAMETERS
    # ---------------------------------------------------------
    STRATEGIES_PACKAGE_PATH: str = "strategies"

    # FuzzyGate Parameters
    FUZZY_CPU_WEIGHT: float = 0.35
    FUZZY_MEMORY_WEIGHT: float = 0.35
    FUZZY_STORAGE_WEIGHT: float = 0.20
    FUZZY_NETWORK_WEIGHT: float = 0.1
    FUZZY_THRESHOLD: float = 0.25

    # Default AI Hyperparameters (Fallbacks)
    AI_ACTOR_LR: float = 0.0003
    AI_CRITIC_LR: float = 0.001
    AI_GAMMA: float = 0.99
    AI_GAE_LAMBDA: float = 0.95
    AI_POLICY_CLIP: float = 0.2
    AI_ENTROPY_COEFFICIENT: float = 0.01
    AI_EPOCHS_PER_UPDATE: int = 10
    AI_PPO_BATCH_SIZE: int = 64
    AI_REPLAY_BUFFER_CAPACITY: int = 10000

    # Training Defaults
    TRAINING_CYCLES: int = 100
    MODEL_SAVE_INTERVAL: int = 20

    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "production" else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
