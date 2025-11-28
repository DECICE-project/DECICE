import logging
from pathlib import Path
from typing import Optional

from config.config import get_settings

from ..data_processing import DataTransformer
from ..feature_engineer import FeatureEngineer
from . import (aggregate_feature_registry, discover_features,
               node_feature_registry, task_feature_registry)

logger = logging.getLogger(__name__)

_features_discovered = False


def _run_discovery_once():
    """Runs feature discovery exactly once."""
    global _features_discovered
    if not _features_discovered:
        logger.info("Factory: Running feature discovery...")
        discover_features()
        _features_discovered = True
        logger.info("...discovery complete.")
    else:
        logger.debug("Factory: Feature discovery already completed.")


def create_data_transformer() -> DataTransformer:
    """
    Factory function to create a fully-configured transformer.
    """

    # Ensure discovery has run
    _run_discovery_once()

    # Get all discovered feature names *from* the registries.
    TASK_FEATURE_SET: list[str] = task_feature_registry.get_all_names()
    NODE_FEATURE_SET: list[str] = node_feature_registry.get_all_names()

    logger.info(
        f"Factory: Found {len(TASK_FEATURE_SET)} workflowtask features and {len(NODE_FEATURE_SET)} node features."
    )
    logger.debug(f"Factory: WorkflowTask features list: {TASK_FEATURE_SET}")
    logger.debug(f"Factory: Node features list: {NODE_FEATURE_SET}")

    # Instantiate and return the transformer.
    return DataTransformer(
        task_registry=task_feature_registry,
        task_feature_names=TASK_FEATURE_SET,
        node_registry=node_feature_registry,
        node_feature_names=NODE_FEATURE_SET,
    )


def create_feature_engineer(
    scalers_file_path: Optional[Path] = None,
) -> FeatureEngineer:
    """
    Factory function to create a fully-configured feature engineer.
    """

    # Ensure discovery has run
    _run_discovery_once()

    # Get aggregate feature names
    AGGREGATE_FEATURE_SET: list[str] = aggregate_feature_registry.get_all_names()

    logger.info(f"Factory: Found {len(AGGREGATE_FEATURE_SET)} aggregate features.")
    logger.debug(f"Factory: Aggregate features list: {AGGREGATE_FEATURE_SET}")

    # Determine scaler path
    _scalers_path = scalers_file_path
    if _scalers_path is None:
        try:
            settings = get_settings()
            _scalers_path = settings.ALL_SCALERS_FILE_PATH
            logger.info(
                f"Factory: Using default scalers path from settings: {_scalers_path}"
            )
        except Exception as e:
            logger.error(
                f"Factory: Could not load settings to get default scalers path: {e}. Scalers may fail to load.",
                exc_info=True,
            )
            raise ValueError(
                "Scalers path must be provided or configured in settings."
            ) from e

    # Instantiate and return the engineer
    return FeatureEngineer(
        registry=aggregate_feature_registry,
        feature_names=AGGREGATE_FEATURE_SET,
        scalers_file_path=_scalers_path,
    )
