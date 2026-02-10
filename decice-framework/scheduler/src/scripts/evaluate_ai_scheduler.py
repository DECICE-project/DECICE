import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.features.factory import create_data_transformer, create_feature_engineer
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
    logger.debug(f"Loading test scenario from: {file_path}")
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
    start_evaluation_time = time.perf_counter()

    logger.info("Starting AI Scheduler evaluation process...")
    logger.info(f"Using settings: LOG_LEVEL={settings.LOG_LEVEL.value}")
    logger.info(f"Command line args: {args}")

    try:
        strategy_factory_instance = StrategyFactory(
            strategies_pkg_path=settings.STRATEGIES_PACKAGE_PATH
        )
        kairos_instance = Kairos(strategy_factory_instance=strategy_factory_instance)

        scalers_path_arg = Path(args.scalers_path)

        data_transformer = create_data_transformer()
        feature_engineer = create_feature_engineer(scalers_file_path=scalers_path_arg)

        ai_scheduler_instance = AIScheduler(
            kairos_instance=kairos_instance,
            data_transformer=data_transformer,
            feature_engineer=feature_engineer,
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

        actor_weights_path_arg = (
            Path(args.actor_weights) if args.actor_weights else None
        )
        critic_weights_path_arg = (
            Path(args.critic_weights) if args.critic_weights else None
        )

        if actor_weights_path_arg or critic_weights_path_arg:
            logger.info("Attempting to load specified model weights for evaluation...")
            ai_scheduler_instance.load_models(
                actor_weights_path=actor_weights_path_arg,
                critic_weights_path=critic_weights_path_arg,
            )
        else:
            logger.info("Using default model weights loaded by AIScheduler init.")

    except Exception as e:
        logger.critical(f"Failed to initialize core components: {e}", exc_info=True)
        return

    logger.info("Core components initialized for evaluation.")

    fuzzy_gate = FuzzyStorageResourcesAccessGate(
        cpu_weight=settings.FUZZY_CPU_WEIGHT,
        memory_weight=settings.FUZZY_MEMORY_WEIGHT,
        storage_weight=settings.FUZZY_STORAGE_WEIGHT,
        network_weight=settings.FUZZY_NETWORK_WEIGHT,
        suitability_threshold=settings.FUZZY_THRESHOLD,
    )
    logger.info("FuzzyStorageResourcesAccessGate initialized.")

    test_scenario_dir = Path(args.test_scenario_dir)
    test_scenario_files = sorted(list(test_scenario_dir.glob("*.json")))

    if not test_scenario_files:
        logger.warning(f"No test scenario files (*.json) found in {test_scenario_dir}.")
        return
    logger.info(
        f"Found {len(test_scenario_files)} test scenario files from {test_scenario_dir}."
    )

    all_results: list[dict[str, Any]] = []

    for scenario_file_path in test_scenario_files:
        logger.info(f"--- Evaluating scenario: {scenario_file_path.name} ---")
        schedule_request_obj = load_scenario_from_file(scenario_file_path)
        if not schedule_request_obj or not schedule_request_obj.tasks:
            logger.warning(
                f"Test scenario {scenario_file_path.name} empty or failed. Skipping."
            )
            continue

        overhead_start_time = time.perf_counter()

        # AI Predicts Strategy
        ai_strategy_name = ai_scheduler_instance.predict_best_strategy_name(
            schedule_request_obj, deterministic=True
        )
        if not ai_strategy_name:
            logger.warning(
                f"AI failed predict for {scenario_file_path.name}. Using default."
            )
            ai_strategy_name = (
                ai_scheduler_instance.strategy_names[0]
                if ai_scheduler_instance.strategy_names
                else "default"
            )
        logger.info(
            f"Scenario '{scenario_file_path.name}', AI-chosen strategy: {ai_strategy_name}"
        )

        try:
            # Transform data
            workloads_df, nodes_df, _ = (
                ai_scheduler_instance.data_transformer.transform(schedule_request_obj)
            )
            jobs_for_strategy: list[dict[str, Any]] = workloads_df.to_dict(
                orient="records"
            )
            nodes_for_strategy: list[dict[str, Any]] = nodes_df.to_dict(
                orient="records"
            )

            # Apply Fuzzy Gate
            suitable_nodes_map = fuzzy_gate.determine_suitable_nodes(
                jobs_for_strategy, nodes_for_strategy
            )
            for job_dict in jobs_for_strategy:
                job_id_str = str(job_dict.get("workload_id"))
                job_dict["suitable_node_ids"] = suitable_nodes_map.get(job_id_str, [])

            overhead_end_time = time.perf_counter()
            overhead_ms = (overhead_end_time - overhead_start_time) * 1000.0

            # Run *ALL* strategies to find the "Oracle" (best) choice
            all_performances = kairos_instance.evaluate_all_strategies(
                jobs_for_strategy, nodes_for_strategy
            )

            if not all_performances:
                logger.warning(
                    f"Kairos returned no performances for {scenario_file_path.name}. Skipping."
                )
                continue

            # Calculate rewards and find the best
            best_reward = -float("inf")
            best_strategy_name = "None"
            ai_strategy_results = {}

            perf_log = "  Strategy Performance:\n"

            for strategy_name, runtime_ms, throughput in all_performances:
                runtime = (
                    runtime_ms if runtime_ms is not None and runtime_ms >= 0 else -1.0
                )
                thru = throughput if throughput is not None else 0.0
                reward = ai_scheduler_instance.calculate_reward(runtime, thru)

                perf_log += f"    - {strategy_name:<25}: Reward={reward:8.2f} (T={thru:5.1f}, R={runtime:7.2f}ms)\n"

                if reward > best_reward:
                    best_reward = reward
                    best_strategy_name = strategy_name

                if strategy_name == ai_strategy_name:
                    ai_strategy_results = {
                        "ai_runtime_ms": runtime,
                        "ai_throughput": thru,
                        "ai_reward": reward,
                    }

            logger.info(perf_log.strip())
            logger.info(
                f"  Oracle's Best Strategy: '{best_strategy_name}' (Reward: {best_reward:.2f})"
            )

            if not ai_strategy_results:
                logger.error(
                    f"AI strategy '{ai_strategy_name}' was not found in Kairos results!"
                )
                ai_strategy_results = {
                    "ai_runtime_ms": -1.0,
                    "ai_throughput": 0.0,
                    "ai_reward": -float("inf"),
                }

            # Store all metrics for final analysis
            all_results.append(
                {
                    "scenario": scenario_file_path.name,
                    "ai_strategy": ai_strategy_name,
                    "best_strategy": best_strategy_name,
                    "ai_reward": ai_strategy_results["ai_reward"],
                    "best_reward": best_reward,
                    "ai_runtime_ms": ai_strategy_results["ai_runtime_ms"],
                    "ai_throughput": ai_strategy_results["ai_throughput"],
                    "overhead_ms": overhead_ms,
                }
            )

        except Exception as e:
            logger.error(
                f"Error processing scenario {scenario_file_path.name}: {e}",
                exc_info=True,
            )
            all_results.append(
                {
                    "scenario": "ERROR",
                    "ai_strategy": "ERROR",
                    "best_strategy": "ERROR",
                    "ai_reward": -float("inf"),
                    "best_reward": -float("inf"),
                    "ai_runtime_ms": -1.0,
                    "ai_throughput": 0.0,
                    "overhead_ms": -1.0,
                }
            )

    if not all_results:
        logger.info("No scenarios were successfully evaluated.")
        return

    results_df = pd.DataFrame(all_results)

    # Filter out any scenarios where all strategies failed
    valid_results_df = results_df[results_df["best_reward"] > -float("inf")].copy()
    num_scenarios_processed = len(results_df)

    if valid_results_df.empty:
        logger.error(
            "All scenarios failed to produce valid rewards. Cannot evaluate performance."
        )
        return

    # Optimality Rate (Our "Precision")
    optimal_selections = (
        valid_results_df["ai_strategy"] == valid_results_df["best_strategy"]
    ).sum()
    optimality_rate = optimal_selections / len(valid_results_df)

    # Average Regret
    valid_results_df["regret"] = (
        valid_results_df["best_reward"] - valid_results_df["ai_reward"]
    )
    avg_regret = valid_results_df["regret"].mean()

    # Average Performance (as % of Max)
    valid_results_df["performance_percent"] = valid_results_df[
        "ai_reward"
    ] / valid_results_df["best_reward"].replace(0, 1e-6)
    valid_results_df["performance_percent"] = valid_results_df[
        "performance_percent"
    ].clip(0, 1)
    avg_performance_percent = valid_results_df["performance_percent"].mean() * 100.0

    # Standard Metrics
    avg_ai_runtime_ms = valid_results_df[valid_results_df["ai_runtime_ms"] >= 0][
        "ai_runtime_ms"
    ].mean()
    avg_ai_throughput = valid_results_df["ai_throughput"].mean()
    avg_ai_reward = valid_results_df["ai_reward"].mean()
    strategy_counts = valid_results_df["ai_strategy"].value_counts().to_dict()

    # New Metrics
    avg_time_per_job_ms = 0.0
    avg_jobs_per_second = 0.0
    if avg_ai_throughput > 0:
        avg_time_per_job_ms = avg_ai_runtime_ms / avg_ai_throughput
    if avg_ai_runtime_ms > 0:
        avg_jobs_per_second = avg_ai_throughput / (avg_ai_runtime_ms / 1000.0)

    # Calculate Real API Pipeline Time
    avg_overhead_ms = valid_results_df[valid_results_df["overhead_ms"] >= 0][
        "overhead_ms"
    ].mean()
    avg_real_api_pipeline_time_ms = avg_overhead_ms + avg_ai_runtime_ms

    total_evaluation_time_s = time.perf_counter() - start_evaluation_time

    logger.info("\n--- AI Scheduler Evaluation Summary ---")
    logger.info(
        f"Evaluated {num_scenarios_processed} test scenarios in {total_evaluation_time_s:.2f} seconds."
    )
    logger.info(f"Average AI Reward: {avg_ai_reward:.2f}")
    logger.info(f"Average AI Throughput: {avg_ai_throughput:.2f} jobs")
    logger.info("---")
    logger.info(f"Average AI Strategy Runtime: {avg_ai_runtime_ms:.2f} ms")
    logger.info(
        f"Average Pipeline Overhead (Transform, Predict, Gate): {avg_overhead_ms:.2f} ms"
    )
    logger.info(
        f"Average Real API Pipeline Time (Overhead + Strategy): {avg_real_api_pipeline_time_ms:.2f} ms"
    )
    logger.info("---")
    logger.info(f"Avg. Strategy Time per Job: {avg_time_per_job_ms:.2f} ms/job")
    logger.info(f"Avg. Strategy Throughput: {avg_jobs_per_second:.1f} jobs/sec")
    logger.info("---")
    logger.info(
        f"Optimality Rate (AI picked Oracle's choice): {optimality_rate * 100.0:.1f}%"
    )
    logger.info(
        f"Average Performance (as % of max reward): {avg_performance_percent:.1f}%"
    )
    logger.info(f"Average Regret (Reward 'left on the table'): {avg_regret:.2f}")
    logger.info(f"AI Strategy Selection Counts: {strategy_counts}")
    logger.info("--- Evaluation Complete ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate a trained AI Scheduler model."
    )
    parser.add_argument(
        "--test_scenario_dir",
        type=str,
        default=str(settings.SCENARIO_DIR_TEST),
        help=f"Directory containing test scenarios (default: {settings.SCENARIO_DIR_TEST})",
    )
    parser.add_argument(
        "--actor_weights",
        type=str,
        default=None,
        help="Optional path to actor weights (.weights.h5). Defaults to settings.",
    )
    parser.add_argument(
        "--critic_weights",
        type=str,
        default=None,
        help="Optional path to critic weights (.weights.h5). Defaults to settings.",
    )
    parser.add_argument(
        "--scalers_path",
        type=str,
        default=str(settings.ALL_SCALERS_FILE_PATH),
        help=f"Path to scalers .joblib file (default: {settings.ALL_SCALERS_FILE_PATH})",
    )

    script_args = parser.parse_args()
    main(script_args)
