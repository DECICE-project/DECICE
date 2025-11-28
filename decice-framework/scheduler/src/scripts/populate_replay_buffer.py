import argparse
import json
import logging
from pathlib import Path
from typing import Any, Optional

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.features.factory import (create_data_transformer,
                                   create_feature_engineer)
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from core.schemas import ScheduleRequest
from strategy_loader import StrategyFactory

settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL.value,
    format="%(asctime)s - %(levelname)s - %(name)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_scenario_from_file(file_path: Path) -> Optional[ScheduleRequest]:
    """Loads a single JSON scenario file directly into a ScheduleRequest object."""
    logger.debug(f"Loading scenario from: {file_path}")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        schedule_request = ScheduleRequest(**data)
        return schedule_request
    except Exception as e:
        logger.error(
            f"Failed to load or parse ScheduleRequest from {file_path.name}: {e}",
            exc_info=True,
        )
        return None


def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    logger.info("Starting replay buffer population process...")
    logger.info(f"Using settings: LOG_LEVEL={settings.LOG_LEVEL.value}")
    logger.info(f"Command line args: {args}")

    try:
        strategy_factory_instance = StrategyFactory(
            strategies_pkg_path=settings.STRATEGIES_PACKAGE_PATH
        )
        kairos_instance = Kairos(strategy_factory_instance=strategy_factory_instance)

        # INFO: We pass a non-existent path to create_feature_engineer.
        # This forces it to initialize with an empty scaler dictionary,
        # which in turn forces it to save the *raw, unscaled* features
        # into the replay buffer
        non_existent_scaler_path = Path("dummy/path/that/does/not/exist.joblib")

        ai_scheduler_instance = AIScheduler(
            kairos_instance=kairos_instance,
            data_transformer=create_data_transformer(),
            feature_engineer=create_feature_engineer(
                scalers_file_path=non_existent_scaler_path
            ),
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

    logger.info(
        f"Components initialized. Buffer size: {len(ai_scheduler_instance.replay_buffer)}"
    )

    fuzzy_gate = FuzzyStorageResourcesAccessGate(
        cpu_weight=settings.FUZZY_CPU_WEIGHT,
        memory_weight=settings.FUZZY_MEMORY_WEIGHT,
        storage_weight=settings.FUZZY_STORAGE_WEIGHT,
        network_weight=settings.FUZZY_NETWORK_WEIGHT,
        suitability_threshold=settings.FUZZY_THRESHOLD,
    )
    logger.info("FuzzyStorageResourcesAccessGate initialized.")

    scenario_input_dir = Path(args.scenario_dir)
    scenario_files = sorted(list(scenario_input_dir.glob("*.json")))

    if not scenario_files:
        logger.warning(f"No scenario files (*.json) found in {scenario_input_dir}.")
        return
    logger.info(
        f"Found {len(scenario_files)} scenario files from {scenario_input_dir}."
    )

    processed_scenarios_count = 0
    for scenario_file_path in scenario_files:
        logger.info(f"Processing scenario: {scenario_file_path.name}")
        schedule_request_obj = load_scenario_from_file(scenario_file_path)
        if not schedule_request_obj or not schedule_request_obj.tasks:
            logger.warning(
                f"Scenario {scenario_file_path.name} empty or failed. Skipping."
            )
            continue

        try:
            # Generate state vector *once* for the scenario
            # This will be UNSCALED because FeatureEngineer has no scalers
            state_vector = ai_scheduler_instance._get_state_vector(schedule_request_obj)
            if state_vector is None:
                logger.warning(
                    f"Could not generate state vector for {scenario_file_path.name}. Skipping."
                )
                continue
            logger.debug(f"State vector generated, shape: {state_vector.shape}")

            # Get DFs for strategy evaluation
            workloads_df, nodes_df, _ = (
                ai_scheduler_instance.data_transformer.transform(schedule_request_obj)
            )
            jobs_for_evaluation: list[dict[str, Any]] = workloads_df.to_dict(
                orient="records"
            )
            nodes_for_evaluation: list[dict[str, Any]] = nodes_df.to_dict(
                orient="records"
            )

        except Exception as e:
            logger.error(
                f"Error processing data for {scenario_file_path.name}: {e}. Skipping.",
                exc_info=True,
            )
            continue

        # Pre-filter using Fuzzy Gate
        suitable_nodes_map = fuzzy_gate.determine_suitable_nodes(
            jobs_for_evaluation, nodes_for_evaluation
        )
        for job_dict in jobs_for_evaluation:
            job_id_str = str(job_dict.get("workload_id"))
            job_dict["suitable_node_ids"] = suitable_nodes_map.get(job_id_str, [])
        logger.debug("Data prepared for Kairos (FuzzyGate applied).")

        logger.info(
            f"Evaluating all strategies with Kairos for {scenario_file_path.name}..."
        )
        all_performances = kairos_instance.evaluate_all_strategies(
            jobs_for_evaluation, nodes_for_evaluation
        )

        if not all_performances:
            logger.warning(
                f"Kairos returned no performances for {scenario_file_path.name}. Skipping."
            )
            continue

        # Add experience for *each* strategy's performance
        for strategy_name, runtime_ms, throughput in all_performances:
            if runtime_ms is None or runtime_ms == float("inf") or runtime_ms < 0:
                logger.warning(
                    f"Strategy '{strategy_name}' had invalid runtime ({runtime_ms}). Skipping."
                )
                continue

            current_throughput = throughput if throughput is not None else 0.0

            try:
                action_index = ai_scheduler_instance.strategy_names.index(strategy_name)
            except ValueError:
                logger.error(
                    f"Strategy '{strategy_name}' not in AIScheduler's list. Skipping."
                )
                continue

            reward = ai_scheduler_instance.calculate_reward(
                runtime_ms, current_throughput
            )

            ai_scheduler_instance.replay_buffer.add(
                state_vector, action_index, reward, next_state=None, done=True
            )
            logger.debug(
                f"  Added to Buffer: Action: {strategy_name}({action_index}), Reward: {reward:.2f}"
            )

        processed_scenarios_count += 1
        logger.info(
            f"Finished scenario: {scenario_file_path.name}. Buffer size: {len(ai_scheduler_instance.replay_buffer)}"
        )

    if processed_scenarios_count == 0:
        logger.error("No scenarios processed. Replay buffer not saved.")
        return

    # Save the buffer and initial models
    replay_buffer_file = Path(args.replay_buffer_output)
    try:
        ai_scheduler_instance.replay_buffer.save_buffer(replay_buffer_file)
    except Exception as e:
        logger.error(f"Failed to save replay buffer: {e}", exc_info=True)

    try:
        # Save initial (untrained) models
        ai_scheduler_instance.save_models()
        logger.info(
            f"AI model weights saved to '{ai_scheduler_instance.model_base_dir}'."
        )
    except Exception as e:
        logger.error(f"Failed to save AI model weights: {e}", exc_info=True)

    logger.info("Replay buffer population process finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Replay Buffer.")
    parser.add_argument(
        "--scenario_dir",
        type=str,
        default=str(settings.SCENARIO_DIR_TRAIN),
        help=f"Directory containing scenario JSON files (default: {settings.SCENARIO_DIR_TRAIN})",
    )
    parser.add_argument(
        "--replay_buffer_output",
        type=str,
        default=str(settings.DEFAULT_REPLAY_BUFFER_FILE),
        help=f"File path to save the populated replay buffer (default: {settings.DEFAULT_REPLAY_BUFFER_FILE})",
    )
    script_args = parser.parse_args()
    main(script_args)
