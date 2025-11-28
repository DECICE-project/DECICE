import argparse
import logging
import pickle
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

from config.config import get_settings
from core.features import aggregate_feature_registry
from core.features.factory import _run_discovery_once

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(buffer_path: Path, output_path: Path):
    logger.info(f"Loading replay buffer from {buffer_path}...")
    try:
        with open(buffer_path, "rb") as f:
            # Buffer stores list of tuples: (state, action, reward, next_state, done)
            buffer_data = pickle.load(f)
        # Extract just the state vectors
        unscaled_states = np.array([experience[0] for experience in buffer_data])
        logger.info(f"Loaded {len(unscaled_states)} unscaled state vectors.")
    except Exception as e:
        logger.error(f"Failed to load replay buffer: {e}", exc_info=True)
        return

    # Run discovery to get the feature names in the correct order
    _run_discovery_once()
    feature_names = sorted(aggregate_feature_registry.get_all_names())

    if not unscaled_states.shape[1] == len(feature_names):
        logger.error(
            f"Feature count mismatch! Buffer has {unscaled_states.shape[1]} features, but registry found {len(feature_names)}."
        )
        return

    logger.info(f"Fitting scalers for {len(feature_names)} features: {feature_names}")
    scalers = {}
    for i, feature_name in enumerate(feature_names):
        # Extract the 1D array for this feature
        feature_data = unscaled_states[:, i].reshape(-1, 1)
        # Fit a new scaler instance
        scaler = StandardScaler()
        scaler.fit(feature_data)
        scalers[feature_name] = scaler
        logger.debug(
            f"  Fitted scaler for '{feature_name}': mean={scaler.mean_[0]:.2f}, std={scaler.scale_[0]:.2f}"
        )

    # Get the default filename from settings
    default_filename = get_settings().SCALERS_DICT_FILENAME

    # Check if the provided path has a file extension.
    # If not, we assume it's a directory.
    if not output_path.suffix:
        logger.info(
            f"Output path '{output_path}' has no extension, assuming it's a directory. "
            f"Appending default filename: '{default_filename}'"
        )
        # Create the directory
        output_path.mkdir(parents=True, exist_ok=True)
        # Set the full file path
        output_path = output_path / default_filename
    else:
        # User provided a full file path. Create its parent directory.
        output_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(scalers, output_path)
    logger.info(
        f"Successfully fitted and saved {len(scalers)} scalers to {output_path}"
    )


if __name__ == "__main__":
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Fit scalers from an unscaled replay buffer."
    )
    parser.add_argument(
        "--replay_buffer_path",
        type=str,
        default=str(settings.DEFAULT_REPLAY_BUFFER_FILE),
    )
    parser.add_argument(
        "--scalers_output_path", type=str, default=str(settings.ALL_SCALERS_FILE_PATH)
    )
    args = parser.parse_args()
    main(Path(args.replay_buffer_path), Path(args.scalers_output_path))
