# --- START FILE: strategies/olb.py ---
"""
Module Name: [olb.py]
Author: M. Bidollahkhani
Contributors: [Giorgi Mamulashvili]
Reviewer: [Giorgi Mamulashvili]
Date Created: [2023.11.03]
Last Modified: [2024.12.25] - Added default node logic.

Description: Implements the OLB (Opportunistic Load Balancing) scheduling strategy.

Version History:
    v1.0 - [03.11.2023] - HOSHMAND: Initial creation.
    v2.0 - [01.06.2024] - Modification based on I/O and revision.
    v2.1 - [01.08.2024] - Added throughput computation.
    v2.2 - [2024.12.25] - Calculate throughput as allocated jobs count.
    v2.3 - [Current]   - Added default node creation if no nodes are provided.
Notes:
    - Default node has minimal capacity (1 CPU, 1 MB RAM).
"""

import logging
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _olb_initialize_dynamic_node_data(nodes_df: pd.DataFrame) -> pd.DataFrame:
    """Initializes DataFrame columns for dynamic resource tracking for OLB."""
    if nodes_df.empty:
        # Define expected columns for an empty df
        nodes_df["current_cpu_available"] = pd.Series(dtype="float64")
        nodes_df["current_mem_available"] = pd.Series(dtype="float64")
        nodes_df["heuristic_load_score"] = pd.Series(dtype="float64")  # Lower is better
        return nodes_df

    # Start with pre-calculated available resources from DataTransformer
    # Ensure columns exist, providing a default of 0 if missing
    nodes_df["current_cpu_available"] = nodes_df.get(
        "metrics_available_cpu_cores", pd.Series(0.0, index=nodes_df.index)
    ).astype(float)
    nodes_df["current_mem_available"] = nodes_df.get(
        "metrics_available_mem_mb", pd.Series(0.0, index=nodes_df.index)
    ).astype(float)

    # Calculate current utilizations in percent for load scoring (0-100 scale)
    # metrics_cpu_util and metrics_mem_util are 0-100 from transformer
    current_cpu_util_percent = nodes_df.get(
        "metrics_cpu_util", pd.Series(100.0, index=nodes_df.index)
    )  # Default 100% util if missing
    current_mem_util_percent = nodes_df.get(
        "metrics_mem_util", pd.Series(100.0, index=nodes_df.index)
    )  # Default 100% util if missing

    # 'heuristic_load_score' is the sum of current percentage utilizations (lower is better)
    nodes_df["heuristic_load_score"] = (
        current_cpu_util_percent + current_mem_util_percent
    )

    return nodes_df


def _olb_update_node_resources_and_load(
    nodes_df: pd.DataFrame, allocated_node_id: str, job_series: pd.Series
) -> None:
    """Updates node load after allocation. Modifies nodes_df IN PLACE."""
    node_idx = nodes_df.index[nodes_df["node_id"] == allocated_node_id]
    if node_idx.empty:
        logger.warning(f"OLB UpdateLoad: Node ID '{allocated_node_id}' not found.")
        return

    job_cpu_req = float(job_series.get("required_cpu", 0))
    job_mem_req = float(job_series.get("required_memory", 0))

    # Decrease available resources
    nodes_df.loc[node_idx, "current_cpu_available"] -= job_cpu_req
    nodes_df.loc[node_idx, "current_mem_available"] -= job_mem_req

    # Ensure available resources don't go below zero
    nodes_df.loc[node_idx, "current_cpu_available"] = nodes_df.loc[
        node_idx, "current_cpu_available"
    ].apply(lambda x: max(0, x))
    nodes_df.loc[node_idx, "current_mem_available"] = nodes_df.loc[
        node_idx, "current_mem_available"
    ].apply(lambda x: max(0, x))

    # Recalculate current utilization percentages and heuristic_load_score
    # Use .iloc[0] safely because we checked node_idx is not empty
    total_cpu = float(nodes_df.loc[node_idx, "metrics_cpu_cores"].iloc[0])
    total_mem = float(nodes_df.loc[node_idx, "metrics_mem_total_mb"].iloc[0])

    new_cpu_util_percent = 100.0
    if total_cpu > 0:
        new_cpu_util_percent = 100.0 * (
            1.0 - (nodes_df.loc[node_idx, "current_cpu_available"].iloc[0] / total_cpu)
        )

    new_mem_util_percent = 100.0
    if total_mem > 0:
        new_mem_util_percent = 100.0 * (
            1.0 - (nodes_df.loc[node_idx, "current_mem_available"].iloc[0] / total_mem)
        )

    nodes_df.loc[node_idx, "heuristic_load_score"] = (
        new_cpu_util_percent + new_mem_util_percent
    )


def _olb_allocate_jobs_to_nodes(
    jobs_df: pd.DataFrame,
    nodes_df_dynamic: pd.DataFrame,
    current_sim_time: float,
) -> tuple[pd.DataFrame, float]:
    """Allocate jobs using OLB logic. Modifies jobs_df and nodes_df_dynamic."""
    if jobs_df.empty:
        return (
            jobs_df.assign(allocated_node_id=None, predicted_scheduled_time=None),
            current_sim_time,
        )

    jobs_df["allocated_node_id"] = pd.Series(dtype="object")
    jobs_df["predicted_scheduled_time"] = pd.Series(dtype="float64")

    for job_idx, job_series in jobs_df.iterrows():
        job_id_str = str(job_series.get("task_id"))
        job_cpu_req = float(job_series.get("required_cpu", 0))
        job_mem_req = float(job_series.get("required_memory", 0))
        job_eligible_earliest_start = float(
            job_series.get("submission_time", current_sim_time)
        )

        # Sort nodes by load ascending (use copy to avoid modifying view)
        sorted_candidate_nodes_df = nodes_df_dynamic.sort_values(
            by="heuristic_load_score"
        ).copy()
        allocated_node_id_for_job: Optional[str] = None

        for _, node_series in sorted_candidate_nodes_df.iterrows():
            # Check *currently available* resources
            if (
                float(node_series.get("current_cpu_available", 0)) >= job_cpu_req
                and float(node_series.get("current_mem_available", 0)) >= job_mem_req
            ):
                # allocated_node_id_for_job = str(node_series["id"])
                allocated_node_id_for_job = str(node_series["node_id"])
                break  # Found least loaded suitable node

        if allocated_node_id_for_job:
            predicted_start_time = max(current_sim_time, job_eligible_earliest_start)
            jobs_df.loc[job_idx, "allocated_node_id"] = allocated_node_id_for_job
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = predicted_start_time

            # Advance sim time by OLB heuristic (simple +1.0)
            current_sim_time = predicted_start_time + 1.0

            _olb_update_node_resources_and_load(
                nodes_df_dynamic, allocated_node_id_for_job, job_series
            )
            logger.debug(
                f"OLB: Job {job_id_str} allocated to Node {allocated_node_id_for_job} at sim_time ~{predicted_start_time:.2f}. New sim_time: {current_sim_time:.2f}"
            )
        else:
            jobs_df.loc[job_idx, "allocated_node_id"] = None
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = None
            logger.debug(f"OLB: Job {job_id_str} could not be allocated.")

    return jobs_df, current_sim_time


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """Schedule jobs using OLB (Opportunistic Load Balancing)."""
    if not jobs:
        logger.info("OLB: No jobs to schedule.")
        return {}

    if not nodes:
        logger.warning(
            "OLB: No nodes provided. Using a single default node with minimal capacity."
        )
        # Create a default node dictionary with keys expected by the logic
        default_node = {
            "id": "default_node_0",
            "metrics_cpu_cores": 1.0,  # Total capacity
            "metrics_mem_total_mb": 1.0,  # Total capacity
            "metrics_cpu_util": 0.0,  # Current utilization (0-100)
            "metrics_mem_util": 0.0,  # Current utilization (0-100)
            "metrics_available_cpu_cores": 1.0,  # Available = Total * (1 - Util/100)
            "metrics_available_mem_mb": 1.0,  # Available = Total * (1 - Util/100)
            "metrics_network_bandwidth_mbps": 0.0,
            "metrics_free_disk_mb": 0.0,
            "metrics_total_disk_mb": 0.0,
            "metrics_used_disk_mb": 0.0,
            "metrics_power_watts": None,
            "node_gpu_type": None,
            "vertexpool_id": "default_pool",
        }
        nodes = [default_node]

    try:
        jobs_df = pd.DataFrame(jobs)
        if "task_id" in jobs_df.columns:
            jobs_df["task_id"] = jobs_df["task_id"].astype(str)

        nodes_df = pd.DataFrame(nodes)
        if "node_id" in nodes_df.columns:
            nodes_df["node_id"] = nodes_df["node_id"].astype(str)
        else:
            raise KeyError("'node_id' column missing")
        # Ensure essential columns exist even for the default node case
        for col, default_val in [
            ("metrics_cpu_cores", 0.0),
            ("metrics_mem_total_mb", 0.0),
            ("metrics_cpu_util", 100.0),
            ("metrics_mem_util", 100.0),
            ("metrics_available_cpu_cores", 0.0),
            ("metrics_available_mem_mb", 0.0),
        ]:
            if col not in nodes_df.columns:
                nodes_df[col] = default_val

        nodes_df_dynamic = _olb_initialize_dynamic_node_data(nodes_df.copy())
        initial_sim_time = 0.0  # OLB starts from 0
        processed_jobs_df, _ = _olb_allocate_jobs_to_nodes(
            jobs_df, nodes_df_dynamic, initial_sim_time
        )

        job_allocation: dict[str, Optional[str]] = {}
        for _, row in processed_jobs_df.iterrows():
            job_allocation[str(row["task_id"])] = (
                str(row["allocated_node_id"])
                if pd.notna(row["allocated_node_id"])
                else None
            )
        return job_allocation

    except (KeyError, Exception) as e:
        logger.error(
            f"OLB Error ({type(e).__name__}): {e}. All jobs unallocated.", exc_info=True
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
    if not jobs:
        return 0.0
    # If nodes is empty, schedule will handle it with a default node.
    logger.debug("OLB: calculate_throughput (fallback) called, re-running schedule().")
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
