"""
Module Name: [min_max.py]
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

import pandas as pd

logger = logging.getLogger(__name__)


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """Min-Max using correct keys."""
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs:
        return {}
    if not nodes:
        return {str(job.get("task_id", f"unknown_job_{id(job)}")): None for job in jobs}

    try:
        node_df = pd.DataFrame(nodes)
        if "node_id" in node_df.columns:
            node_df["node_id"] = node_df["node_id"].astype(str)
        else:
            raise KeyError("'node_id' column missing in nodes data")

        node_df["heuristic_load"] = node_df.get("metrics_cpu_util", 0.0) + node_df.get(
            "metrics_mem_util", 0.0
        )

        for job_item in jobs:
            job_id_str = str(job_item.get("task_id"))
            if not job_id_str or job_id_str == "None":
                continue

            job_cpu_req = float(job_item.get("required_cpu", 0))
            job_mem_req = float(job_item.get("required_memory", 0))
            job_net_req = 0.0

            suitable_nodes_df = node_df[
                (node_df.get("metrics_cpu_cores", 0.0) >= job_cpu_req)
                & (node_df.get("metrics_mem_total_mb", 0.0) >= job_mem_req)
                & (node_df.get("metrics_network_bandwidth_mbps", 0.0) >= job_net_req)
            ]

            selected_node_id_str: Optional[str] = None
            if not suitable_nodes_df.empty:
                min_load_idx = suitable_nodes_df["heuristic_load"].idxmin()
                selected_node_series = suitable_nodes_df.loc[min_load_idx]
                selected_node_id_str = str(selected_node_series["node_id"])
                job_allocation[job_id_str] = selected_node_id_str

                node_df.loc[
                    node_df["node_id"] == selected_node_id_str, "heuristic_load"
                ] += (job_cpu_req + job_mem_req)
                logger.debug(
                    f"Job {job_id_str} assigned to Node {selected_node_id_str}. New load: {node_df.loc[node_df['node_id'] == selected_node_id_str, 'heuristic_load'].iloc[0]:.2f}"
                )
            else:
                job_allocation[job_id_str] = None
                logger.info(f"MinMax: Job {job_id_str} could not be allocated.")

        return job_allocation

    except (KeyError, Exception) as e:
        logger.error(
            f"MinMax Error ({type(e).__name__}): {e}. All jobs unallocated.",
            exc_info=True,
        )
        return {
            str(job.get("task_id", f"unknown_job_err_{id(job)}")): None for job in jobs
        }


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
        "MinMax: calculate_throughput (fallback) called, re-running schedule()."
    )
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
