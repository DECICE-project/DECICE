import argparse
import logging
from pathlib import Path

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.features.factory import (create_data_transformer,
                                   create_feature_engineer)
from core.kairos import Kairos
from strategy_loader import StrategyFactory

settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL.value,
    format="%(asctime)s - %(levelname)s - %(name)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    logger.info("Starting AI Scheduler training process...")
    logger.info(
        f"Using settings: LOG_LEVEL={settings.LOG_LEVEL.value}, STRATEGIES_PKG_PATH='{settings.STRATEGIES_PACKAGE_PATH}', etc."
    )
    logger.info(f"Command line arguments provided: {args}")

    try:
        strategy_factory_instance = StrategyFactory(
            strategies_pkg_path=settings.STRATEGIES_PACKAGE_PATH
        )
        kairos_instance = Kairos(strategy_factory_instance=strategy_factory_instance)

        # AIScheduler __init__ will call the factories.
        # pass the scaler path if provided via args, otherwise factory uses default.
        scalers_path_arg = Path(args.scalers_path) if args.scalers_path else None
        data_transformer = create_data_transformer()
        feature_engineer = create_feature_engineer(scalers_file_path=scalers_path_arg)

        ai_scheduler_instance = AIScheduler(
            kairos_instance=kairos_instance,
            feature_engineer=feature_engineer,
            data_transformer=data_transformer,
            actor_lr=settings.AI_ACTOR_LR,
            critic_lr=settings.AI_CRITIC_LR,
            gamma=settings.AI_GAMMA,
            gae_lambda=settings.AI_GAE_LAMBDA,
            policy_clip=settings.AI_POLICY_CLIP,
            entropy_coefficient=settings.AI_ENTROPY_COEFFICIENT,
            epochs_per_update=settings.AI_EPOCHS_PER_UPDATE,
            ppo_batch_size=settings.AI_PPO_BATCH_SIZE,
            replay_buffer_capacity=settings.AI_REPLAY_BUFFER_CAPACITY,
        )
    except Exception as e:
        logger.critical(
            f"Failed to initialize Kairos or AIScheduler: {e}", exc_info=True
        )
        return

    logger.info("Kairos and AIScheduler initialized.")

    replay_buffer_file_path_str = (
        args.replay_buffer_path
        if args.replay_buffer_path
        else str(settings.DEFAULT_REPLAY_BUFFER_FILE)
    )
    replay_buffer_file = Path(replay_buffer_file_path_str)
    logger.info(f"Attempting to load Replay Buffer from: {replay_buffer_file}")

    # load_buffer exists on the ReplayBuffer instance
    ai_scheduler_instance.replay_buffer.load_buffer(replay_buffer_file)

    if len(ai_scheduler_instance.replay_buffer) < ai_scheduler_instance.ppo_batch_size:
        logger.error(
            f"Replay buffer has {len(ai_scheduler_instance.replay_buffer)} samples, "
            f"which is less than PPO batch size ({ai_scheduler_instance.ppo_batch_size}). "
            f"Cannot train. Please populate the buffer first using 'scripts/populate_replay_buffer.py'."
        )
        return

    logger.info(
        f"Replay buffer ready with {len(ai_scheduler_instance.replay_buffer)} experiences."
    )

    num_training_cycles_to_run = (
        args.num_training_cycles
        if args.num_training_cycles is not None
        else settings.TRAINING_CYCLES
    )
    save_interval_to_use = (
        args.save_interval
        if args.save_interval is not None
        else settings.MODEL_SAVE_INTERVAL
    )

    logger.info(f"Starting training for {num_training_cycles_to_run} cycles...")
    logger.info(
        "IMPORTANT: Ensure scalers are correctly loaded by FeatureEngineer for training."
    )

    for cycle in range(1, num_training_cycles_to_run + 1):
        logger.info(f"--- Training Cycle {cycle}/{num_training_cycles_to_run} ---")
        try:
            ai_scheduler_instance.train_agent()
        except Exception as e:
            logger.error(f"Error during training cycle {cycle}: {e}", exc_info=True)
            logger.info("Attempting to save models before exiting due to error...")
            ai_scheduler_instance.save_models()
            break

        if cycle % save_interval_to_use == 0 or cycle == num_training_cycles_to_run:
            logger.info(f"Saving models at training cycle {cycle}...")
            try:
                ai_scheduler_instance.save_models()
            except Exception as e:
                logger.error(
                    f"Failed to save AI model weights during cycle {cycle}: {e}",
                    exc_info=True,
                )

    logger.info("AI Scheduler training process finished.")
    logger.info(
        f"Final model weights saved to '{ai_scheduler_instance.model_base_dir}'."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the AI Scheduler's PPO agent.")
    parser.add_argument(
        "--replay_buffer_path",
        type=str,
        default=str(settings.DEFAULT_REPLAY_BUFFER_FILE),
        help=f"Path to the pre-populated replay buffer .pkl file (default: {settings.DEFAULT_REPLAY_BUFFER_FILE})",
    )
    parser.add_argument(
        "--num_training_cycles",
        type=int,
        default=None,
        help=f"Number of times to call train_agent() (default from settings: {settings.TRAINING_CYCLES})",
    )
    parser.add_argument(
        "--save_interval",
        type=int,
        default=None,
        help=f"Save model weights every N training cycles (default from settings: {settings.MODEL_SAVE_INTERVAL})",
    )
    parser.add_argument(
        "--scalers_path",
        type=str,
        default=None,
        help=f"Optional path to scalers .joblib file (default from settings: {settings.ALL_SCALERS_FILE_PATH})",
    )

    script_args = parser.parse_args()
    main(script_args)
