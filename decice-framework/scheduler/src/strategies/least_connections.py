"""
Module Name: [least_connections.py]
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
    Schedule jobs on nodes based on the Least Connections heuristic.
    Selects the node with the least number of jobs already assigned to it by this strategy run,
    provided the node has sufficient total capacity for the job.

    Args:
        jobs (list[dict[str, Any]]): List of job dictionaries. Expected keys:
            'id' (str UUID), 'cpu_req', 'mem_req' (MB).
        nodes (list[dict[str, Any]]): List of node dictionaries. Expected keys:
            'id' (str UUID), 'metrics_cpu_cores', 'metrics_mem_total_mb'.

    Returns:
        dict[str, Optional[str]]: Job ID (str) to Node ID (str) allocation,
                                  or None if unallocated.
    """
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs:
        logger.info("LeastConnections: No jobs to schedule.")
        return job_allocation
    if not nodes:
        logger.warning(
            "LeastConnections: No nodes available for scheduling. All jobs will be unallocated."
        )
        return {str(job.get("task_id", f"unknown_job_{id(job)}")): None for job in jobs}

    # Initialize connections count for each node for this scheduling run
    # Keys are stringified node IDs
    node_connections: dict[str, int] = {str(node["node_id"]): 0 for node in nodes}

    for job in jobs:
        job_id_str = str(job.get("task_id"))
        if not job_id_str:
            logger.warning("LeastConnections: Skipping job with missing ID.")
            continue

        job_cpu_req = float(job.get("required_cpu", 0))
        job_mem_req = float(job.get("required_memory", 0))

        # Filter nodes that can handle the job's *total* requirements (ignoring current load for suitability)
        suitable_nodes_for_capacity: list[dict[str, Any]] = []
        for node in nodes:
            node_total_cpu = float(node.get("metrics_cpu_cores", 0))
            node_total_mem_mb = float(node.get("metrics_mem_total_mb", 0))

            if node_total_cpu >= job_cpu_req and node_total_mem_mb >= job_mem_req:
                suitable_nodes_for_capacity.append(node)

        selected_node_id_str: Optional[str] = None
        if suitable_nodes_for_capacity:
            # Select the node with the least current connections (from this strategy's perspective)
            # Ensure node IDs used with node_connections are strings
            selected_node_dict = min(
                suitable_nodes_for_capacity,
                key=lambda n: node_connections[str(n["node_id"])],
            )
            selected_node_id_str = str(selected_node_dict["node_id"])
            node_connections[selected_node_id_str] += 1
            logger.debug(
                f"Job {job_id_str} assigned to Node {selected_node_id_str} (connections: {node_connections[selected_node_id_str]})"
            )
        else:
            logger.debug(
                f"Job {job_id_str} could not find any node with sufficient total capacity."
            )

        job_allocation[job_id_str] = selected_node_id_str

    return job_allocation


def calculate_throughput_from_allocations(
    allocations: Optional[dict[str, Optional[str]]],
    jobs: list[dict[str, Any]],  # Unused in this specific implementation
    nodes: list[dict[str, Any]],  # Unused in this specific implementation
) -> float:
    """
    Calculates throughput as the number of successfully allocated jobs
    from a provided allocation dictionary.
    """
    if not allocations:
        return 0.0
    successful_allocations = sum(
        1 for node_id in allocations.values() if node_id is not None
    )
    return float(successful_allocations)


def calculate_throughput(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> float:
    """
    Fallback: Calculates throughput by running the schedule function first.
    This is less efficient and primarily for standalone testing or if Kairos needs it.
    """
    if not jobs or not nodes:  # Check jobs as well for consistency
        return 0.0

    logger.debug(
        "LeastConnections: calculate_throughput (fallback) called, re-running schedule()."
    )
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
