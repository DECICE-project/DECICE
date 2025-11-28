import json
import logging
import random
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from core.ai_scheduler import AIScheduler
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from core.schemas import ScheduleRequest
from core.training.generator import ScenarioGenerator

logger = logging.getLogger(__name__)


class TrainingSimulator:
    """
    A Virtual Training Environment (VTE) that simulates the scheduling loop
    to train the AI Agent.
    """

    def __init__(
        self,
        ai_scheduler: AIScheduler,
        kairos: Kairos,
        fuzzy_gate: FuzzyStorageResourcesAccessGate,
    ):
        self.ai_scheduler = ai_scheduler
        self.kairos = kairos
        self.fuzzy_gate = fuzzy_gate
        self.is_training = False

        # New: Path to specific dataset folder.
        # If None, simulator generates random data.
        self.dataset_path: Optional[Path] = None

    async def run_training_session(
        self,
        cycles: int = 10,
        episodes_per_cycle: int = 50,
        should_stop_callback: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Dict[str, Any]:
        """
        Runs a full training session.

        Args:
            cycles: Number of training loops.
            episodes_per_cycle: Number of scenarios to simulate before updating weights.
            should_stop_callback: Async function that returns True if we should abort.
        """
        if self.is_training:
            raise RuntimeError("Training session already in progress.")

        self.is_training = True
        logger.info(
            f"Starting VTE Session: {cycles} cycles x {episodes_per_cycle} episodes."
        )
        if self.dataset_path:
            logger.info(f"VTE: Loading scenarios from dataset: {self.dataset_path}")

        stats = {
            "total_episodes": 0,
            "total_reward": 0.0,
            "cycles_completed": 0,
            "status": "completed",  # Default
        }

        try:
            for cycle in range(cycles):
                # --- 1. Check Cancellation ---
                if should_stop_callback:
                    if await should_stop_callback():
                        logger.warning("VTE: Stop signal received. Aborting training.")
                        stats["status"] = "canceled"
                        break

                logger.info(f"VTE Cycle {cycle + 1}/{cycles} starting...")

                # --- 2. Generate Experience (Episodes) ---
                for _ in range(episodes_per_cycle):
                    await self._run_single_episode()
                    stats["total_episodes"] += 1

                # --- 3. Train Agent ---
                # This performs the gradient updates using the PPO buffer
                self.ai_scheduler.train_agent()
                stats["cycles_completed"] += 1

                # Optional: Save checkpoint every 5 cycles
                if (cycle + 1) % 5 == 0:
                    self.ai_scheduler.save_models()

            # Final save
            self.ai_scheduler.save_models()
            logger.info(f"VTE Session Finished. Status: {stats['status']}")

        except Exception as e:
            logger.error(f"VTE Training crashed: {e}", exc_info=True)
            stats["status"] = "failed"
            raise
        finally:
            self.is_training = False

        return stats

    async def _run_single_episode(self):
        """
        Generates one scenario, asks AI for action, calculates reward, stores experience.
        """
        # 1. Get a Request (Either from Disk or Generator)
        request = self._get_next_scenario()
        if not request:
            logger.warning("VTE: Could not generate/load a scenario. Skipping episode.")
            return

        # 2. Data Prep (Transform + Fuzzy)
        # Transform to DataFrames
        tasks_df, nodes_df, _ = self.ai_scheduler.data_transformer.transform(request)

        # Convert to list of dicts for Kairos/Strategies
        tasks_dicts = tasks_df.fillna(0).to_dict(orient="records")
        nodes_dicts = nodes_df.fillna(0).to_dict(orient="records")

        # Fuzzy Gate (Pre-filtering)
        suitable_map = self.fuzzy_gate.determine_suitable_nodes(
            tasks_dicts, nodes_dicts
        )
        for t in tasks_dicts:
            t_id = str(t.get("task_id"))
            t["suitable_node_ids"] = suitable_map.get(t_id, [])

        # 3. AI Action
        # The AI looks at the request and predicts the best strategy name
        strategy_name = self.ai_scheduler.predict_best_strategy_name(
            request, deterministic=False
        )

        logger.debug(f"VTE: AI selected '{strategy_name}'")

        if not strategy_name:
            strategy_name = "round_robin"  # Fallback

        # 4. Environment Step (Virtual Execution via Kairos)
        # We assume the environment is the "Oracle" execution of that strategy
        _, throughput = self.kairos.run_strategy(
            strategy_name, tasks_dicts, nodes_dicts
        )
        runtime_ms = self.kairos.get_runtime() or 0.0

        # 5. Reward & Store
        self.ai_scheduler.collect_experience(
            request, strategy_name, runtime_ms, throughput or 0.0
        )

    def _get_next_scenario(self) -> Optional[ScheduleRequest]:
        """Helper to get a scenario either from the Dataset folder or Generator."""
        # A. Load from Dataset (if configured)
        if self.dataset_path and self.dataset_path.exists():
            files = list(self.dataset_path.glob("*.json"))
            if files:
                # Randomly sample a file from the dataset to simulate variety
                # (In a strict epoch, you might want to iterate sequentially,
                # but random sampling is fine for RL experience replay)
                random_file = random.choice(files)
                try:
                    with open(random_file, "r") as f:
                        data = json.load(f)
                    return ScheduleRequest(**data)
                except Exception as e:
                    logger.error(f"Failed to load scenario {random_file}: {e}")
                    return None

        # B. Fallback: Generate Synthetic
        return ScenarioGenerator.generate_request(num_tasks=10, num_nodes=20)
