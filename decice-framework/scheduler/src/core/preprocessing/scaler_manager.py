import json
import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

from core.features.factory import create_data_transformer, create_feature_engineer
from core.schemas import ScheduleRequest

logger = logging.getLogger(__name__)


class ScalerManager:
    """
    Handles fitting and saving feature scalers from raw dataset files.
    """

    @staticmethod
    def fit_and_save_scalers(dataset_path: Path, output_path: Path):
        logger.info(
            f"Auto-Calibration: Fitting scalers using dataset at {dataset_path}..."
        )

        # Setup minimal pipeline to extract raw features
        # Pass None for scalers_file_path to force raw output
        transformer = create_data_transformer()
        raw_engineer = create_feature_engineer(scalers_file_path=None)

        feature_names = raw_engineer.feature_names
        collected_vectors = []

        files = list(dataset_path.glob("*.json"))
        if not files:
            raise ValueError(f"No JSON files found in {dataset_path} to fit scalers.")

        # Extract features from every file in the dataset
        # Limit to e.g., 500 files to save time if dataset is huge
        files_to_process = files[:500]

        for file_path in files_to_process:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                request = ScheduleRequest(**data)

                # Transform to DF
                jobs_df, nodes_df, latency = transformer.transform(request)

                # Extract Raw Vector (1D numpy array)
                vector = raw_engineer.build_features(jobs_df, nodes_df, latency)
                collected_vectors.append(vector)
            except Exception as e:
                logger.warning(
                    f"Skipping file {file_path.name} during calibration: {e}"
                )

        if not collected_vectors:
            raise RuntimeError(
                "Could not extract any valid feature vectors for calibration."
            )

        # Fit Scikit-Learn Scalers
        # Shape: (N_samples, N_features)
        X = np.array(collected_vectors)

        scalers_dict = {}
        logger.info(f"Fitting scalers on matrix shape {X.shape}...")

        for i, name in enumerate(feature_names):
            feature_column = X[:, i].reshape(-1, 1)
            scaler = StandardScaler()
            scaler.fit(feature_column)
            scalers_dict[name] = scaler

        # Save to Disk
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scalers_dict, output_path)
        logger.info(f"Scalers saved to {output_path}")
