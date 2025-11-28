import logging
from typing import Any

logger = logging.getLogger(__name__)


class FuzzyStorageResourcesAccessGate:
    def __init__(
        self,
        cpu_weight: float,
        memory_weight: float,
        storage_weight: float,
        network_weight: float,
        suitability_threshold: float = 0.5,
    ) -> None:
        """Initializes the FuzzyStorageResourcesAccessGate..."""
        # Ensure weights sum close to 1.0 if desired, although not strictly necessary
        total_weight = cpu_weight + memory_weight + storage_weight + network_weight
        if abs(total_weight - 1.0) > 1e-6:
            logger.warning(
                f"FuzzyGate weights (CPU={cpu_weight}, Mem={memory_weight}, Sto={storage_weight}, Net={network_weight}) do not sum to 1.0 (Sum={total_weight})."
            )

        self.weights = {
            "cpu": cpu_weight,
            "memory": memory_weight,
            "storage": storage_weight,
            "network": network_weight,
        }
        self.suitability_threshold = suitability_threshold
        logger.info(
            f"FuzzyGate initialized. Weights: CPU={self.weights['cpu']:.2f}, "
            f"Memory={self.weights['memory']:.2f}, Storage={self.weights['storage']:.2f}, "
            f"Network={self.weights['network']:.2f}. Threshold: {self.suitability_threshold:.2f}"
        )

    def _calculate_component_score(
        self,
        resource_name: str,
        requested: float,
        available: float,
        current_node_utilization_0_1: float,
    ) -> float:
        """Calculates a normalized suitability score (0-1) for a resource component."""
        requested = max(0.0, requested)
        available = max(0.0, available)
        current_node_utilization_0_1 = min(max(0.0, current_node_utilization_0_1), 1.0)

        logger.debug(
            f"Component Score Calc '{resource_name}': Req={requested:.2f}, Avail={available:.2f}, Util(0-1)={current_node_utilization_0_1:.3f}"
        )

        if requested == 0:
            logger.debug(
                f"Component '{resource_name}': Score=1.0 (Task requests none)."
            )
            return 1.0
        if available < requested:
            logger.debug(
                f"Component '{resource_name}': Score=0.0 (Does not fit: avail {available:.2f} < req {requested:.2f})."
            )
            return 0.0

        node_health_score = 1.0 - current_node_utilization_0_1
        fit_quality_score = 1.0 - (
            requested / available
        )  # available > 0 checked by available < requested
        score = node_health_score * fit_quality_score
        logger.debug(
            f"    Comp '{resource_name}': Health={node_health_score:.3f}, Fit={fit_quality_score:.3f} => Score={score:.3f}"
        )
        return score

    def calculate_node_suitability_for_task(
        self, task: dict[str, Any], node: dict[str, Any]
    ) -> float:
        """Calculates the overall weighted suitability score of a node for a task."""

        task_id = task.get("task_id", "N/A_Task_ID")
        node_id = node.get("node_id", "N/A_Node_ID")
        logger.debug(f"Calculating suitability: Task '{task_id}' on Node '{node_id}'")
        logger.debug(f"  Raw Task dict: {task}")

        # Extract task requirements safely
        raw_cpu_req = task.get("required_cpu")
        raw_mem_req = task.get("required_memory")
        # Add placeholder for storage
        raw_storage_req = task.get("required_storage_mb", 0)

        # Log raw values before conversion
        logger.debug(
            f"  Raw Task Reqs - CPU: {raw_cpu_req}, Mem: {raw_mem_req}, Storage: {raw_storage_req}"
        )

        try:
            task_cpu_req = float(raw_cpu_req) if raw_cpu_req is not None else 0.0
            task_mem_req = float(raw_mem_req) if raw_mem_req is not None else 0.0
            task_storage_req = (
                float(raw_storage_req) if raw_storage_req is not None else 0.0
            )
        except (ValueError, TypeError) as e:
            logger.error(
                f"  Error converting task requirements for task '{task_id}' to float: {e}. Using 0.0.",
                exc_info=True,
            )
            task_cpu_req, task_mem_req, task_storage_req = 0.0, 0.0, 0.0

        logger.debug(
            f"  Task '{task_id}' requirements (float): CPU={task_cpu_req:.2f}, Mem={task_mem_req:.2f}MB, Storage={task_storage_req:.2f}MB"
        )

        # Extract relevant node metrics safely
        node_avail_cpu = float(node.get("metrics_available_cpu_cores", 0.0))
        # Convert Util % (0-100) from dict to 0-1 scale needed by score function
        node_cpu_util_0_1 = float(node.get("metrics_cpu_util", 100.0)) / 100.0

        node_avail_mem_mb = float(node.get("metrics_available_mem_mb", 0.0))
        node_mem_util_0_1 = float(node.get("metrics_mem_util", 100.0)) / 100.0

        node_free_disk_mb = float(node.get("metrics_free_disk_mb", 0.0))
        node_total_disk_mb = float(node.get("metrics_total_disk_mb", 0.0))
        disk_utilization_0_1 = (
            (node_total_disk_mb - node_free_disk_mb) / node_total_disk_mb
            if node_total_disk_mb > 1e-6
            else 1.0  # Avoid division by zero
        )
        # Clamp just in case calculation yields slightly out of bounds
        disk_utilization_0_1 = min(max(0.0, disk_utilization_0_1), 1.0)

        node_network_bw_capacity_mbps = float(
            node.get("metrics_network_bandwidth_mbps", 0.0)
        )

        logger.debug(
            f"  Node '{node_id}': AvailCPU={node_avail_cpu:.2f} (Util={node_cpu_util_0_1:.2f}), "
            f"AvailMem={node_avail_mem_mb:.2f}MB (Util={node_mem_util_0_1:.2f}), "
            f"FreeDisk={node_free_disk_mb:.2f}MB (DiskUtil={disk_utilization_0_1:.2f}), "
            f"NetBW={node_network_bw_capacity_mbps:.2f}Mbps"
        )

        # Calculate component scores (Pass 0-1 utilization directly)
        cpu_score = self._calculate_component_score(
            "CPU", task_cpu_req, node_avail_cpu, node_cpu_util_0_1
        )
        memory_score = self._calculate_component_score(
            "Memory", task_mem_req, node_avail_mem_mb, node_mem_util_0_1
        )
        # Calculate storage score (will be 1.0 if task_storage_req is 0)
        storage_score = self._calculate_component_score(
            "Storage", task_storage_req, node_free_disk_mb, disk_utilization_0_1
        )

        typical_max_node_bandwidth = 10000.0  # Example 10 Gbps
        network_score = (
            min(1.0, node_network_bw_capacity_mbps / typical_max_node_bandwidth)
            if typical_max_node_bandwidth > 0
            else 0.0
        )

        # Final weighted sum
        final_suitability_score = (
            cpu_score * self.weights["cpu"]
            + memory_score * self.weights["memory"]
            + storage_score * self.weights["storage"]
            + network_score * self.weights["network"]
        )

        logger.debug(
            f"  Scores Task '{task_id}' on Node '{node_id}': "
            f"CPU={cpu_score:.3f}, Mem={memory_score:.3f}, Sto={storage_score:.3f}, Net={network_score:.3f} "
            f"==> Final: {final_suitability_score:.3f}"
        )
        return final_suitability_score

    def determine_suitable_nodes(
        self, tasks_data: list[dict[str, Any]], nodes_data: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Determines suitable node IDs for each task, sorted by score descending."""
        task_to_suitable_nodes: dict[str, list[str]] = {}
        logger.debug(
            f"FuzzyGate: Determining suitable nodes for {len(tasks_data)} tasks across {len(nodes_data)} nodes."
        )

        if not tasks_data:
            logger.info("FuzzyGate: No tasks provided.")
            return task_to_suitable_nodes
        if not nodes_data:
            logger.warning("FuzzyGate: No nodes provided. No tasks suitable.")
            for task in tasks_data:
                task_id_str = str(task.get("task_id", f"unknown_task_fg_{id(task)}"))
                task_to_suitable_nodes[task_id_str] = []
            return task_to_suitable_nodes

        for task in tasks_data:
            task_id_str = str(task.get("task_id"))
            if not task_id_str or task_id_str == "None":
                logger.warning(
                    f"FuzzyGate: Skipping task with invalid ID: {task.get('task_id')}"
                )
                continue

            logger.debug(f"FuzzyGate: Evaluating nodes for Task '{task_id_str}'...")
            suitable_nodes_for_task_with_scores: list[tuple[float, str]] = []

            for node in nodes_data:
                node_id_str = str(node.get("node_id"))
                if not node_id_str or node_id_str == "None":
                    logger.warning(
                        f"FuzzyGate: Skipping node with invalid ID: {node.get('node_id')}"
                    )
                    continue

                try:
                    suitability_score = self.calculate_node_suitability_for_task(
                        task, node
                    )

                    if suitability_score >= self.suitability_threshold:
                        suitable_nodes_for_task_with_scores.append(
                            (suitability_score, node_id_str)
                        )
                        logger.debug(
                            f"  Node '{node_id_str}' IS SUITABLE for Task '{task_id_str}' (score {suitability_score:.3f})."
                        )
                    else:
                        logger.debug(
                            f"  Node '{node_id_str}' NOT suitable for Task '{task_id_str}' (score {suitability_score:.3f})."
                        )
                except Exception as e:
                    logger.error(
                        f"Error calculating suitability for task '{task_id_str}' on node '{node_id_str}': {e}",
                        exc_info=True,
                    )

            suitable_nodes_for_task_with_scores.sort(key=lambda x: x[0], reverse=True)
            task_to_suitable_nodes[task_id_str] = [
                node_id for score, node_id in suitable_nodes_for_task_with_scores
            ]
            logger.info(
                f"FuzzyGate: Task '{task_id_str}' - Found {len(task_to_suitable_nodes[task_id_str])} suitable nodes."
            )
            logger.debug(
                f"FuzzyGate: Task '{task_id_str}' - Suitable nodes (ordered): {task_to_suitable_nodes[task_id_str]}"
            )

        return task_to_suitable_nodes

    def auto_adjust(
        self, tasks_data: list[dict[str, Any]], nodes_data: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Public method alias for suitability determination."""
        return self.determine_suitable_nodes(tasks_data, nodes_data)
