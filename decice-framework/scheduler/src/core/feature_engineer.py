import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .features.interfaces import IAggregateFeatureExtractor
from .features.registry import FeatureRegistry
from .schemas import LatencyMatrix

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Takes prepared DataFrames, builds an aggregate feature vector using a
    registry of extractors, and applies scalers to produce the final
    vector for the AI model.
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        feature_names: list[str],
        scalers_file_path: Path,
    ):
        """
        Initializes the FeatureEngineer using Dependency Injection.

        Args:
            registry: A FeatureRegistry instance containing aggregate extractors.
            feature_names: The list of feature names to build.
            scalers_file_path: Path to the .joblib file containing scalers.
        """
        self.feature_names = sorted(feature_names)  # Ensure consistent order
        self.EXPECTED_FEATURE_DIM = len(self.feature_names)

        # Instantiate the required feature extractors
        self.extractors: list[IAggregateFeatureExtractor] = []
        extractor_map = {}  # Temp map to ensure correct order later
        for name in self.feature_names:
            try:
                extractor_cls = registry.get_extractor_class(name)
                instance = extractor_cls()
                if not isinstance(instance, IAggregateFeatureExtractor):
                    raise TypeError(
                        f"Extractor {name} is not IAggregateFeatureExtractor"
                    )
                extractor_map[name] = instance  # Store by name
            except KeyError:
                raise ValueError(f"Aggregate feature '{name}' not found in registry.")

        # Ensure extractors list is in the same sorted order as feature_names
        self.extractors = [extractor_map[name] for name in self.feature_names]

        logger.info(
            f"FeatureEngineer initialized for {self.EXPECTED_FEATURE_DIM} features: {self.feature_names}"
        )

        # Load scalers
        self.scalers = self._load_scalers(scalers_file_path)

    def _load_scalers(self, _path: Path) -> dict[str, Any]:
        """Loads scalers from the specified file path."""
        try:
            if _path.exists() and _path.is_file():
                loaded_scalers = joblib.load(_path)
                if not isinstance(loaded_scalers, dict):
                    raise TypeError(
                        f"Scaler file at {_path} did not contain a dictionary."
                    )

                missing = [
                    name for name in self.feature_names if name not in loaded_scalers
                ]
                if missing:
                    logger.error(
                        f"Critical: Missing scalers for features: {missing}. Will produce unscaled output."
                    )
                    return {}  # Return empty dict if scalers are missing
                else:
                    logger.info(
                        f"All {len(loaded_scalers)} required scalers loaded successfully from {_path}."
                    )
                    # Only keep scalers for the features we actually use
                    return {
                        name: loaded_scalers[name]
                        for name in self.feature_names
                        if name in loaded_scalers
                    }
            else:
                logger.warning(
                    f"Scaler file not found at '{_path}'. FeatureEngineer will produce raw, unscaled features."
                )
        except Exception as e:
            logger.error(
                f"Error loading scalers from {_path}: {e}. Will produce unscaled features.",
                exc_info=True,
            )
        return {}

    def build_features(
        self,
        jobs_df: pd.DataFrame,
        nodes_df: pd.DataFrame,
        latency_matrix: LatencyMatrix,
    ) -> np.ndarray:
        """
        Builds the final, scaled feature vector.
        """

        # Calculate raw feature values using extractor instances
        # The order is guaranteed by how self.extractors was built in __init__
        raw_features = [
            f.calculate(jobs_df, nodes_df, latency_matrix) for f in self.extractors
        ]

        # Apply scaling
        scaled_features: list[float] = []
        if not self.scalers:
            logger.warning(
                "Scalers not loaded. Outputting raw, unscaled feature vector."
            )
            scaled_features = [float(v) for v in raw_features]
        else:
            for i, feature_name in enumerate(self.feature_names):
                raw_value = raw_features[i]
                if feature_name in self.scalers:
                    scaler = self.scalers[feature_name]
                    # Ensure raw_value is float before scaling
                    try:
                        float_raw_value = float(raw_value)
                    except (ValueError, TypeError):
                        logger.error(
                            f"Could not convert raw value '{raw_value}' for feature '{feature_name}' to float. Using 0.0."
                        )
                        float_raw_value = 0.0

                    scaled_value = scaler.transform(np.array([[float_raw_value]]))[0, 0]
                    scaled_features.append(scaled_value)
                else:
                    logger.warning(
                        f"No scaler found for '{feature_name}'. Using raw value."
                    )
                    scaled_features.append(float(raw_value))

        vector = np.array(scaled_features, dtype=np.float32)

        if vector.shape[0] != self.EXPECTED_FEATURE_DIM:
            raise ValueError(
                f"Final feature vector dim mismatch: expected {self.EXPECTED_FEATURE_DIM}, got {vector.shape[0]}."
            )

        logger.debug(
            f"Successfully built scaled feature vector of size {vector.shape[0]}."
        )
        return vector
