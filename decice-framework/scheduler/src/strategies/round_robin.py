"""
Module Name: [round_robin.py]
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
    """Round Robin using correct keys."""
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs:
        return {}
    if not nodes:
        return {str(job.get("task_id", f"unknown_job_{id(job)}")): None for job in jobs}

    node_count = len(nodes)

    for idx, job_item in enumerate(jobs):
        job_id_str = str(job_item.get("task_id"))
        if not job_id_str or job_id_str == "None":
            continue

        job_cpu_req = float(job_item.get("required_cpu", 0))
        job_mem_req = float(job_item.get("required_memory", 0))

        selected_node_dict = nodes[idx % node_count]
        selected_node_id_str = str(selected_node_dict["node_id"])

        node_total_cpu = float(selected_node_dict.get("metrics_cpu_cores", 0))
        node_total_mem_mb = float(selected_node_dict.get("metrics_mem_total_mb", 0))

        if node_total_cpu >= job_cpu_req and node_total_mem_mb >= job_mem_req:
            job_allocation[job_id_str] = selected_node_id_str
        else:
            job_allocation[job_id_str] = None
            logger.debug(
                f"Job {job_id_str} could not fit on Node {selected_node_id_str} (RR)."
            )

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
        "RoundRobin: calculate_throughput (fallback) called, re-running schedule()."
    )
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
