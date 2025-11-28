"""
Module Name: [load_based_scheduling.py]
Author: M. Bidollahkhani
Contributors: []
Reviewer: []
Date Created: [2024.09.18]
Last Modified: [2024.12.25]

Description:

Version History:
    v1.0 - [18.09.2024] - Initial version implemented.
    v1.1 - [2024.12.25] - Calculate throughput as the number of successfully allocated jobs
Notes:
    -
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """
    Schedule jobs using Load-Based Scheduling.
    Allocates jobs to the node that fits total capacity and has lowest current CPU+Mem utilization.
    """
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs:
        logger.info("LoadBasedScheduling: No jobs to schedule.")
        return job_allocation
    if not nodes:
        logger.warning("LoadBasedScheduling: No nodes available. All jobs unallocated.")
        for job_in_list in jobs:
            job_allocation[
                str(job_in_list.get("id", f"unknown_job_{id(job_in_list)}"))
            ] = None
        return job_allocation

    for job_item in jobs:
        job_id_str = str(job_item.get("task_id"))
        if not job_id_str:
            logger.warning("LoadBasedScheduling: Skipping job with missing ID.")
            continue

        job_cpu_req = float(job_item.get("required_cpu", 0))
        job_mem_req = float(job_item.get("required_memory", 0))  # Assuming MB

        best_node_for_job: Optional[dict[str, Any]] = None
        min_load_score = float("inf")

        for node_item in nodes:
            node_id_str_current_node = str(node_item.get("node_id"))

            # Node utilization values are 0.0-100.0 from DataTransformer node features
            node_cpu_util_percent = float(
                node_item.get("metrics_cpu_util", 100.0)
            )  # Default high if missing
            node_mem_util_percent = float(
                node_item.get("metrics_mem_util", 100.0)
            )  # Default high if missing

            # Current Load Score Calculation (CPU + Memory Load Only)
            current_node_load_score = node_cpu_util_percent + node_mem_util_percent

            logger.debug(
                f"Evaluating Node {node_id_str_current_node} for Job {job_id_str}. "
                f"CPU Util %: {node_cpu_util_percent:.2f}, Mem Util %: {node_mem_util_percent:.2f}. "
                f"Current Load Score: {current_node_load_score:.2f}."
            )

            if current_node_load_score < min_load_score:
                # Check total capacity
                node_total_cpu = float(node_item.get("metrics_cpu_cores", 0))
                node_total_mem_mb = float(node_item.get("metrics_mem_total_mb", 0))

                if node_total_cpu >= job_cpu_req and node_total_mem_mb >= job_mem_req:
                    min_load_score = current_node_load_score
                    best_node_for_job = node_item
                    logger.debug(
                        f"Node {node_id_str_current_node} is new best candidate for job {job_id_str} (Score: {min_load_score:.2f}, Fits capacity)."
                    )
                else:
                    logger.debug(
                        f"Node {node_id_str_current_node} has lower score ({current_node_load_score:.2f}) but cannot fit job {job_id_str} (Req CPU: {job_cpu_req}, Req Mem: {job_mem_req} vs Tot CPU: {node_total_cpu}, Tot Mem: {node_total_mem_mb})."
                    )

        selected_node_id_str: Optional[str] = None
        if best_node_for_job:
            selected_node_id_str = str(best_node_for_job["node_id"])
            logger.info(
                f"Job '{job_id_str}' assigned to Node '{selected_node_id_str}' (Load score: {min_load_score:.2f})"
            )
        else:
            logger.info(
                f"Job '{job_id_str}' could not be allocated. No suitable node found (either due to load or capacity)."
            )

        job_allocation[job_id_str] = selected_node_id_str

    return job_allocation


def calculate_throughput_from_allocations(
    allocations: Optional[dict[str, Optional[str]]],
    jobs: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
) -> float:
    """Calculates throughput as the number of successfully allocated jobs."""
    if not allocations:
        return 0.0
    return float(sum(1 for node_id in allocations.values() if node_id is not None))


def calculate_throughput(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> float:
    """Fallback: Calculates throughput by running schedule()."""
    if not jobs or not nodes:
        return 0.0
    logger.debug(
        "LoadBasedScheduling: calculate_throughput (fallback) called, re-running schedule()."
    )
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
