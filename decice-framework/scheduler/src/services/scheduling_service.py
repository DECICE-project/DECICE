import logging
from typing import Any

from fastapi import Depends

from core.ai_scheduler import AIScheduler
from core.fuzzy_storage import FuzzyStorageResourcesAccessGate
from core.kairos import Kairos
from core.schemas import ScheduleRequest, ScheduleResponse, TaskPlacement
from dependencies import get_ai_scheduler, get_fuzzy_gate, get_kairos

logger = logging.getLogger(__name__)


class SchedulingService:
    """Orchestrates the entire AI-driven scheduling process."""

    def __init__(
        self,
        ai_scheduler: AIScheduler,
        kairos: Kairos,
        fuzzy_gate: FuzzyStorageResourcesAccessGate,
    ):
        self.ai_scheduler = ai_scheduler
        self.kairos = kairos
        self.fuzzy_gate = fuzzy_gate

    def process_schedule(self, schedule_request: ScheduleRequest) -> ScheduleResponse:
        """Processes a scheduling request through the full pipeline..."""
        logger.info(
            f"Processing scheduling request for {len(schedule_request.tasks)} tasks "
            f"and {sum(len(vp.nodes) for vp in schedule_request.cluster.vertexpools)} total nodes "
            f"across {len(schedule_request.cluster.vertexpools)} vertexpools."
        )

        try:
            logger.debug("Transforming API models into DataFrames...")
            tasks_df, nodes_df, latency_matrix = (
                self.ai_scheduler.data_transformer.transform(schedule_request)
            )

            logger.debug(f"DataTransformer returned tasks_df shape: {tasks_df.shape}")
            logger.debug(f"DataTransformer returned nodes_df shape: {nodes_df.shape}")
            if not tasks_df.empty:
                logger.debug(f"Tasks DF columns: {tasks_df.columns.tolist()}")
            if not nodes_df.empty:
                logger.debug(f"Nodes DF columns: {nodes_df.columns.tolist()}")

            # Convert DataFrames to lists of dicts
            # INFO: Using fillna(0) might mask issues if columns are missing entirely
            # A more robust approach might check required columns exist first
            tasks_for_processing: list[dict[str, Any]] = tasks_df.fillna(0).to_dict(
                orient="records"
            )
            nodes_for_processing: list[dict[str, Any]] = nodes_df.fillna(0).to_dict(
                orient="records"
            )
            logger.debug(
                f"Prepared {len(tasks_for_processing)} tasks and {len(nodes_for_processing)} nodes for processing (as lists of dicts)."
            )

            if tasks_for_processing:
                logger.debug(
                    f"First task dict passed to FuzzyGate: {tasks_for_processing[0]}"
                )
            else:
                logger.debug(
                    "tasks_for_processing list is empty before passing to FuzzyGate."
                )

        except Exception as e:
            logger.error(
                f"Error during data transformation or prep: {e}", exc_info=True
            )
            raise ValueError(f"Input data transformation failed: {e}")

        # Fuzzy Gate
        logger.info("Running Fuzzy Storage Resources Access Gate for pre-filtering...")
        logger.debug(
            f"Passing {len(tasks_for_processing)} tasks and {len(nodes_for_processing)} nodes to FuzzyGate."
        )
        suitable_nodes_map = self.fuzzy_gate.determine_suitable_nodes(
            tasks_for_processing, nodes_for_processing
        )

        # Augment task dictionaries
        for task_dict in tasks_for_processing:
            task_id_str = str(task_dict.get("task_id"))
            task_dict["suitable_node_ids"] = suitable_nodes_map.get(task_id_str, [])

        logger.debug("Tasks augmented with suitable_node_ids from FuzzyGate.")

        # AI Predicts a Strategy
        logger.info("AI Scheduler predicting optimal strategy...")
        chosen_strategy_name = self.ai_scheduler.predict_best_strategy_name(
            schedule_request, deterministic=True
        )
        if not chosen_strategy_name:
            chosen_strategy_name = (
                self.ai_scheduler.strategy_names[0]
                if self.ai_scheduler.strategy_names
                else "default"
            )
            logger.warning(
                f"AI prediction failed. Falling back to default: {chosen_strategy_name}"
            )
        logger.info(f"AI Chose Strategy: '{chosen_strategy_name}'")

        # Kairos Executes the Chosen Strategy
        logger.info(f"Kairos executing strategy: '{chosen_strategy_name}'...")
        logger.debug(
            f"Passing {len(tasks_for_processing)} tasks and {len(nodes_for_processing)} nodes to Kairos."
        )
        predictions_map, throughput = self.kairos.run_strategy(
            chosen_strategy_name, tasks_for_processing, nodes_for_processing
        )
        runtime_ms = self.kairos.get_runtime() or -1.0
        logger.info(
            f"Strategy '{chosen_strategy_name}' executed. Runtime: {runtime_ms:.2f}ms, Throughput: {throughput or 0.0:.2f}"
        )

        # Collect Experience
        try:
            self.ai_scheduler.collect_experience(
                schedule_request, chosen_strategy_name, runtime_ms, throughput or 0.0
            )
        except Exception as e:
            logger.error(f"Error during experience collection: {e}", exc_info=True)

        # Format Final Response
        final_placements: list[TaskPlacement] = []
        safe_predictions_map = predictions_map if predictions_map is not None else {}

        for task_input in schedule_request.tasks:
            task_id_key = str(task_input.id)
            allocated_node_id_str = safe_predictions_map.get(task_id_key)
            target_node_ids = [allocated_node_id_str] if allocated_node_id_str else []

            final_placements.append(
                TaskPlacement(
                    task_id=task_input.id,
                    target_node_ids=target_node_ids,
                    strategy_used=chosen_strategy_name,
                )
            )

        logger.info(
            f"Scheduling processed. Returning {len(final_placements)} placements."
        )
        return ScheduleResponse(
            placements=final_placements,
            scheduling_duration_ms=runtime_ms if runtime_ms >= 0 else None,
        )


def get_scheduling_service(
    ai_scheduler: AIScheduler = Depends(get_ai_scheduler),
    kairos: Kairos = Depends(get_kairos),
    fuzzy_gate: FuzzyStorageResourcesAccessGate = Depends(get_fuzzy_gate),
) -> SchedulingService:
    return SchedulingService(
        ai_scheduler=ai_scheduler,
        kairos=kairos,
        fuzzy_gate=fuzzy_gate,
    )
