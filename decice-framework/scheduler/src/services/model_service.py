import json
import logging
from typing import Optional

from config.config import get_settings
from core.schemas import SchedulerDefinition

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self.models_dir = self.settings.MODELS_BASE_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def create_scheduler_definition(self, definition: SchedulerDefinition) -> dict:
        """Saves a new scheduler configuration to disk."""
        model_path = self.models_dir / definition.name
        if model_path.exists():
            raise FileExistsError(f"Scheduler '{definition.name}' already exists.")

        model_path.mkdir(parents=True)

        config_path = model_path / "config.json"
        with open(config_path, "w") as f:
            f.write(definition.model_dump_json(indent=2))

        logger.info(f"Created new scheduler definition: {definition.name}")
        return {"status": "created", "path": str(config_path)}

    def get_scheduler_definition(self, name: str) -> Optional[SchedulerDefinition]:
        config_path = self.models_dir / name / "config.json"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            return SchedulerDefinition(**data)
        except Exception as e:
            logger.error(f"Failed to load config for {name}: {e}")
            return None

    def list_models(self) -> list[str]:
        return [d.name for d in self.models_dir.iterdir() if d.is_dir()]


def get_model_service() -> ModelService:
    return ModelService()
