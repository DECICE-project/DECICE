import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModelMetadata(BaseModel):
    """Metadata stored alongside the model weights."""

    version_id: str
    created_at: str
    metrics: Dict[str, Any]
    description: Optional[str] = None


class ModelRegistry:
    """
    Manages storage, retrieval, and versioning of AI models.
    Structure:
      /models/
        ├── v1_20231124-120000/
        │   ├── actor.pth
        │   ├── critic.pth
        │   └── metadata.json
        └── current -> v1_20231124-120000 (symlink or reference)
    """

    def __init__(self, base_dir: str = "/app/models"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_model(
        self, agent, metrics: Dict[str, Any], description: str = "Training Checkpoint"
    ) -> str:
        """
        Saves the current agent state as a new version.
        Returns the version_id.
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        version_id = f"v_{timestamp}"
        model_dir = self.base_dir / version_id
        model_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save Weights (Delegated to agent)
        # Assuming agent has a save method that takes a directory
        agent.save(str(model_dir))

        # 2. Save Metadata
        metadata = ModelMetadata(
            version_id=version_id,
            created_at=datetime.now().isoformat(),
            metrics=metrics,
            description=description,
        )

        with open(model_dir / "metadata.json", "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.info(f"Model version {version_id} saved to {model_dir}")
        return version_id

    def list_models(self) -> List[ModelMetadata]:
        """Returns a list of all available models, sorted by date (newest first)."""
        models = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                try:
                    with open(item / "metadata.json", "r") as f:
                        data = json.load(f)
                        models.append(ModelMetadata(**data))
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {item}: {e}")

        # Sort by version_id (which has timestamp) descending
        return sorted(models, key=lambda x: x.version_id, reverse=True)

    def get_model_path(self, version_id: str) -> Optional[Path]:
        """Returns the path to a specific model version."""
        path = self.base_dir / version_id
        if path.exists() and path.is_dir():
            return path
        return None

    def delete_model(self, version_id: str) -> bool:
        """Deletes a model version."""
        path = self.base_dir / version_id
        if path.exists():
            shutil.rmtree(path)
            logger.info(f"Deleted model version {version_id}")
            return True
        return False
