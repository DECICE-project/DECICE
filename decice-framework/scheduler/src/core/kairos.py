import logging
import time
from typing import Any, Optional

from strategy_loader import IStrategy, StrategyFactory

logger = logging.getLogger(__name__)


class Kairos:
    """
    Handles scheduling strategies using a StrategyFactory.
    Measures performance (runtime, throughput) and evaluates strategies.
    """

    def __init__(self, strategy_factory_instance: StrategyFactory) -> None:
        """
        Initializes Kairos with a StrategyFactory instance.

        Args:
            strategy_factory_instance (StrategyFactory): An instance of StrategyFactory.
        """
        if not isinstance(strategy_factory_instance, StrategyFactory):
            raise TypeError(
                "Kairos must be initialized with a StrategyFactory instance."
            )
        self.strategy_factory: StrategyFactory = strategy_factory_instance
        self.current_strategy_duration_ns: Optional[int] = None
        logger.info("Kairos initialized with provided strategy factory.")

    def list_strategies(self) -> list[str]:
        """Lists all available strategies via the factory."""
        return self.strategy_factory.list_strategies()

    def run_strategy(
        self,
        strategy_name: str,
        jobs: list[dict[str, Any]],
        nodes: list[dict[str, Any]],
    ) -> tuple[Optional[dict[str, Optional[str]]], Optional[float]]:
        """
        Runs the specified strategy, measures runtime, and calculates throughput.
        """
        self.current_strategy_duration_ns = None
        allocations: Optional[dict[str, Optional[str]]] = None
        throughput: Optional[float] = 0.0  # Default to 0.0

        strategy_instance: Optional[IStrategy] = self.strategy_factory.get_strategy(
            strategy_name
        )

        if not strategy_instance:
            logger.error(f"Strategy '{strategy_name}' not found in factory.")
            return None, None

        logger.info(f"Running strategy: '{strategy_name}'")
        try:
            timer_start_ns = time.time_ns()
            allocations = strategy_instance.schedule(jobs, nodes)
            timer_stop_ns = time.time_ns()
            self.current_strategy_duration_ns = timer_stop_ns - timer_start_ns

            # Optimized throughput calculation
            if hasattr(strategy_instance, "calculate_throughput_from_allocations"):
                throughput = strategy_instance.calculate_throughput_from_allocations(
                    allocations, jobs, nodes
                )
            elif hasattr(strategy_instance, "calculate_throughput"):
                # Fallback to original method if the optimized one isn't available
                throughput = strategy_instance.calculate_throughput(jobs, nodes)
            else:
                logger.warning(
                    f"Strategy '{strategy_name}' does not have a recognized throughput calculation method. Throughput set to 0."
                )

            throughput = throughput if throughput is not None else 0.0
            logger.info(
                f"Strategy '{strategy_name}' completed. Runtime: {self.get_runtime():.4f} ms, Throughput: {throughput:.2f}"
            )

        except Exception as e:
            logger.exception(f"Exception running strategy '{strategy_name}': {e}")
            # allocations might be None or partially filled if error occurred mid-schedule

        return allocations, throughput

    def get_runtime_mcs(self) -> Optional[float]:
        if self.current_strategy_duration_ns is None:
            return None
        return self.current_strategy_duration_ns / 1000.0

    def get_runtime(self) -> Optional[float]:
        if self.current_strategy_duration_ns is None:
            return None
        return self.current_strategy_duration_ns / 1_000_000.0

    def evaluate_all_strategies(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> list[tuple[str, Optional[float], float]]:
        """
        Evaluates all strategies, collecting their name, runtime (ms), and throughput.
        Returns:
            List[Tuple[str, Optional[float], float]]:
                List of (strategy_name, runtime_ms, throughput) tuples.
        """
        strategy_performance_data: list[tuple[str, Optional[float], float]] = []
        available_strategies = self.list_strategies()

        if not available_strategies:
            logger.warning("No strategies found to evaluate.")
            return strategy_performance_data

        for strategy_name in available_strategies:
            _, throughput_val = self.run_strategy(strategy_name, jobs, nodes)
            runtime_ms = self.get_runtime()

            current_throughput = throughput_val if throughput_val is not None else 0.0

            if runtime_ms is None:
                strategy_performance_data.append((strategy_name, float("inf"), 0.0))
            else:
                strategy_performance_data.append(
                    (strategy_name, runtime_ms, current_throughput)
                )

        return strategy_performance_data

    # def _calculate_reward_for_evaluation(
    #     self, runtime_ms: Optional[float], throughput: float
    # ) -> float:
    #     """
    #     Helper to calculate reward consistently for strategy evaluation.
    #     Mirrors the logic in AIScheduler.calculate_reward.
    #     """
    #     if runtime_ms is None or runtime_ms < 0:  # Strategy failed or invalid runtime
    #         return -float("inf")  # Heavily penalize failed strategies

    #     runtime_s = runtime_ms / 1000.0
    #     reward = throughput * 1.0  # Weight for throughput

    #     if runtime_s > 0.001:  # Using 1ms as a threshold for "very fast"
    #         reward -= runtime_s * 0.1  # Penalty for runtime
    #     elif throughput > 0:  # runtime_s is <= 1MS and throughput is positive
    #         reward += 0.5  # Bonus for very fast and effective execution
    #     # If throughput is 0 and runtime is also ~0, reward is 0.
    #     return float(reward)

    def _calculate_reward_for_evaluation(
        self, runtime_ms: Optional[float], throughput: float
    ) -> float:
        """
        Helper to calculate reward consistently for strategy evaluation.
        Mirrors the logic in AIScheduler.calculate_reward.
        """
        THROUGHPUT_WEIGHT: float = 1.0
        RUNTIME_PENALTY_WEIGHT: float = 10.0
        # Handle cases where the strategy failed or returned an invalid time
        if runtime_ms is None or runtime_ms < 0:
            logger.warning(
                f"Invalid runtime ({runtime_ms}ms) for Oracle. Returning -inf reward."
            )
            return -float("inf")  # Heavily penalize failed strategies

        # Convert runtime from milliseconds to seconds
        runtime_s = runtime_ms / 1000.0

        # Calculate the two components
        throughput_benefit = throughput * THROUGHPUT_WEIGHT
        runtime_cost = runtime_s * RUNTIME_PENALTY_WEIGHT

        # Final reward is benefit minus cost
        reward = throughput_benefit - runtime_cost

        return float(reward)

    def choose_best_strategy(
        self, jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> Optional[str]:
        """
        Evaluates all strategies and chooses the best one based on the
        AI's reward function logic (higher reward is better).

        Args:
            jobs (list[dict[str, Any]]): List of job dictionaries.
            nodes (list[dict[str, Any]]): List of node dictionaries.
        Returns:
            Optional[str]: The name of the best strategy, or None if no strategies could be evaluated.
        """
        all_performances = self.evaluate_all_strategies(jobs, nodes)

        if not all_performances:
            # TODO: Maybe raise Exception instead of returning None
            logger.warning(
                "KAIROS Oracle: Cannot choose best strategy; no strategy performances were evaluated."
            )
            return None

        best_calculated_reward = -float("inf")
        best_strategy_name: Optional[str] = None

        logger.debug("KAIROS Oracle: Evaluating strategies based on calculated reward:")
        for name, runtime_ms, current_throughput in all_performances:
            # Use the consistent reward calculation
            reward = self._calculate_reward_for_evaluation(
                runtime_ms, current_throughput
            )

            logger.debug(
                f"  Strategy: {name}, Runtime(ms): {runtime_ms if runtime_ms is not None else 'Fail':.2f}, "
                f"Throughput: {current_throughput:.2f}, Calculated Reward: {reward:.2f}"
            )
            if reward > best_calculated_reward:
                best_calculated_reward = reward
                best_strategy_name = name

        if best_strategy_name:
            logger.info(
                f"KAIROS Oracle chose best strategy: '{best_strategy_name}' with reward {best_calculated_reward:.2f}"
            )
        else:
            # This might happen if all strategies failed and got -inf reward
            logger.warning(
                "KAIROS Oracle could not determine a best strategy from evaluations (all failed or had -inf reward)."
            )
            # Optionally, fall back to a default simple strategy name if truly nothing is selectable
            if all_performances:  # if there were strategies but all scored -inf
                return self.list_strategies()[0] if self.list_strategies() else None

        return best_strategy_name
