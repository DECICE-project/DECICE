"""
Module Name: [shortest_job_first.py]
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
    """SJF using correct keys."""
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs:
        return {}

    try:
        sorted_jobs = sorted(
            jobs,
            key=lambda job: (
                float(job.get("required_cpu", 0)) + float(job.get("required_memory", 0))
            ),
        )
    except (KeyError, TypeError) as e:
        logger.error(f"SJF: Error sorting jobs: {e}. Check keys.", exc_info=True)
        return {
            str(job.get("task_id", f"unknown_job_err_{id(job)}")): None for job in jobs
        }

    if not nodes:
        logger.warning("SJF: No nodes available.")
        return {
            str(job_item.get("task_id", f"unknown_job_{id(job_item)}")): None
            for job_item in sorted_jobs
        }

    for job_item in sorted_jobs:
        job_id_str = str(job_item.get("task_id"))
        if not job_id_str or job_id_str == "None":
            continue

        job_cpu_req = float(job_item.get("required_cpu", 0))
        job_mem_req = float(job_item.get("required_memory", 0))

        assigned_node_id: Optional[str] = None
        for node_item in nodes:
            node_total_cpu = float(node_item.get("metrics_cpu_cores", 0))
            node_total_mem_mb = float(node_item.get("metrics_mem_total_mb", 0))

            if node_total_cpu >= job_cpu_req and node_total_mem_mb >= job_mem_req:
                assigned_node_id = str(node_item["node_id"])
                logger.debug(
                    f"Job {job_id_str} assigned to first fit Node {assigned_node_id} by SJF."
                )
                break

        job_allocation[job_id_str] = assigned_node_id
        if assigned_node_id is None:
            logger.debug(f"Job {job_id_str} found no node with capacity (SJF).")

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
        "ShortestJobFirst: calculate_throughput (fallback) called, re-running schedule()."
    )
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
