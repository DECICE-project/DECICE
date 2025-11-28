import argparse
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from config.config import get_settings
from core.features import aggregate_feature_registry
from core.features.factory import _run_discovery_once

# Set up logging
settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL.value,
    format="%(asctime)s - %(levelname)s - %(name)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main(buffer_path: Path):
    """
    Loads an unscaled replay buffer and prints the statistical analysis
    of its feature vectors.
    """

    if not buffer_path.exists() or not buffer_path.is_file():
        logger.error(f"Replay buffer file not found at: {buffer_path}")
        return

    logger.info(f"Loading replay buffer from {buffer_path}...")
    try:
        with open(buffer_path, "rb") as f:
            # Buffer stores list of tuples: (state, action, reward, next_state, done)
            buffer_data = pickle.load(f)

        # Extract just the state vectors
        unscaled_states = np.array([experience[0] for experience in buffer_data])
        logger.info(f"Loaded {len(unscaled_states)} unscaled state vectors.")

        if unscaled_states.size == 0:
            logger.warning("Replay buffer is empty. No features to analyze.")
            return

    except Exception as e:
        logger.error(f"Failed to load or parse replay buffer: {e}", exc_info=True)
        return

    # Run discovery to get the feature names in the correct order
    try:
        _run_discovery_once()
        feature_names = sorted(aggregate_feature_registry.get_all_names())
    except Exception as e:
        logger.error(f"Failed to run feature discovery: {e}", exc_info=True)
        return

    if not unscaled_states.shape[1] == len(feature_names):
        logger.error(
            f"CRITICAL: Feature count mismatch! Buffer has {unscaled_states.shape[1]} features, "
            f"but registry found {len(feature_names)} features."
        )
        logger.error(f"Registry features: {feature_names}")
        return

    logger.info(f"Successfully matched {len(feature_names)} features.")

    # Create a Pandas DataFrame for easy analysis
    df = pd.DataFrame(unscaled_states, columns=feature_names)

    # Get the statistical summary
    analysis = df.describe()

    logger.info("Feature Range Analysis")
    logger.info(analysis)
    logger.info("End of Analysis")

    logger.info(f"Successfully analyzed {len(df)} samples.")
    logger.info("Set LOG_LEVEL=DEBUG in .env to see full feature lists if needed.")


if __name__ == "__main__":
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Analyze the statistical properties of an unscaled replay buffer."
    )
    parser.add_argument(
        "--replay_buffer_path",
        type=str,
        default=str(settings.DEFAULT_REPLAY_BUFFER_FILE),
        help=f"Path to the replay buffer .pkl file to analyze (default: {settings.DEFAULT_REPLAY_BUFFER_FILE})",
    )
    args = parser.parse_args()

    main(Path(args.replay_buffer_path))
