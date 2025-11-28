"""
Module Name: [mct.py]
Author: M. Bidollahkhani
Contributors: [Giorgi Mamulashvili]
Reviewer: [Giorgi Mamulashvili]
Date Created: [2023.11.03]
Last Modified: [2024.12.25]

Description:

Version History:
    v1.0 - [03.11.2023] - HOSHMAND: Initial creation and implementation of the AI Scheduler workflow.
    v2.0 - [01.06.2024] - Modification based on the I/O and revision on the method.
    v2.1 - [01.08.2024] - Added the throughput computation
    v2.2 - [2024.12.25] - Calculate throughput as the number of successfully allocated jobs
Notes:
    -
"""

import logging
import time
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _initialize_dynamic_node_load(nodes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Initializes DataFrame columns for dynamic load tracking within the MCT strategy.
    Uses pre-calculated available resources from DataTransformer as starting points.
    Calculates initial 'load_score' based on current utilization percentages.
    """
    if nodes_df.empty:
        # Define expected columns for an empty df to avoid errors downstream
        nodes_df["current_cpu_available"] = pd.Series(dtype="float64")
        nodes_df["current_mem_available"] = pd.Series(dtype="float64")
        nodes_df["current_cpu_util_percent"] = pd.Series(dtype="float64")
        nodes_df["current_mem_util_percent"] = pd.Series(dtype="float64")
        nodes_df["load_score"] = pd.Series(dtype="float64")
        return nodes_df

    # Start with pre-calculated available resources
    nodes_df["current_cpu_available"] = nodes_df["metrics_available_cpu_cores"].astype(
        float
    )
    nodes_df["current_mem_available"] = nodes_df["metrics_available_mem_mb"].astype(
        float
    )

    # Calculate current utilizations in percent for load scoring (0-100 scale)
    # metrics_cpu_util and metrics_mem_util are 0.0-1.0
    nodes_df["current_cpu_util_percent"] = nodes_df["metrics_cpu_util"] * 100.0
    nodes_df["current_mem_util_percent"] = nodes_df["metrics_mem_util"] * 100.0

    # Define a 'load_score' for selecting nodes (lower is better for some interpretations)
    # Original MCT implies node selection is based on earliest completion time,
    # which implicitly considers load via execution_time.
    # The 'load' column in original `calculate_completion_time` was sum of % utilizations.
    nodes_df["load_score"] = (
        nodes_df["current_cpu_util_percent"] + nodes_df["current_mem_util_percent"]
    )

    return nodes_df


def _update_dynamic_node_load(
    nodes_df: pd.DataFrame,
    allocated_node_id: str,
    job_series: pd.Series,
) -> None:
    """Updates node load. Modifies nodes_df IN PLACE."""
    node_idx = nodes_df.index[nodes_df["node_id"] == allocated_node_id]
    if node_idx.empty:
        return

    job_cpu_req = float(job_series.get("required_cpu", 0))
    job_mem_req = float(job_series.get("required_memory", 0))

    nodes_df.loc[node_idx, "current_cpu_available"] -= job_cpu_req
    nodes_df.loc[node_idx, "current_mem_available"] -= job_mem_req
    nodes_df.loc[node_idx, "current_cpu_available"] = nodes_df.loc[
        node_idx, "current_cpu_available"
    ].apply(lambda x: max(0, x))
    nodes_df.loc[node_idx, "current_mem_available"] = nodes_df.loc[
        node_idx, "current_mem_available"
    ].apply(lambda x: max(0, x))

    total_cpu = float(nodes_df.loc[node_idx, "metrics_cpu_cores"].iloc[0])
    total_mem = float(nodes_df.loc[node_idx, "metrics_mem_total_mb"].iloc[0])

    new_cpu_util_percent = (
        100.0
        * (1.0 - (nodes_df.loc[node_idx, "current_cpu_available"].iloc[0] / total_cpu))
        if total_cpu > 0
        else 100.0
    )
    new_mem_util_percent = (
        100.0
        * (1.0 - (nodes_df.loc[node_idx, "current_mem_available"].iloc[0] / total_mem))
        if total_mem > 0
        else 100.0
    )
    nodes_df.loc[node_idx, "load_score"] = new_cpu_util_percent + new_mem_util_percent


def _calculate_completion_time(
    job_series: pd.Series, node_series: pd.Series, current_timestamp: float
) -> float:
    """
    Calculate the expected completion time for a job on a given node.
    Uses job_series and node_series (rows from DataFrames).
    """
    # job_start_time: use submission_time if available and relevant, else current_timestamp
    # Original 'time_limit_seconds' seemed to be used as an eligibility/arrival time.
    # Our 'time_limit' is duration. 'submission_time' is job arrival.
    job_arrival_time = float(job_series.get("submission_time", current_timestamp))

    # Effective start time for calculation: cannot be earlier than current_timestamp or job's own arrival
    effective_start_time = max(current_timestamp, job_arrival_time)

    job_cpu = float(job_series.get("required_cpu", 0))
    job_mem = float(job_series.get("required_memory", 0))

    # Use current (dynamically changing) available resources from the node_series
    node_cpu_avail = float(node_series.get("current_cpu_available", 0.0))
    node_mem_avail = float(node_series.get("current_mem_available", 0.0))
    node_load_score = float(
        node_series.get("load_score", 0.0)
    )  # This is sum of % utils

    # Simplified execution time estimation (can be made more complex)
    # If a resource is 0, execution time for that component is effectively infinite if job requests it.
    exec_time_cpu = job_cpu / max(0.001, node_cpu_avail) if job_cpu > 0 else 0.0
    exec_time_mem = (
        job_mem / max(0.001, node_mem_avail) if job_mem > 0 else 0.0
    )  # Assuming mem req is a proxy for mem-bound exec time

    # Taking the dominant resource factor for execution time.
    # The 'node_load_score' in original was sum of % utilizations, used as an additive factor.
    # This could represent queueing delay or general slowness due to load.
    estimated_execution_duration = max(exec_time_cpu, exec_time_mem)  # Simplified

    completion_time = (
        effective_start_time + estimated_execution_duration + (node_load_score * 0.01)
    )  # Scale load_score impact

    return completion_time


def _allocate_jobs_to_nodes_mct(
    jobs_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    current_timestamp: float,
) -> pd.DataFrame:
    """
    Allocate jobs to nodes using Minimum Completion Time (MCT) strategy.
    Modifies jobs_df by adding 'allocated_node_id' and 'predicted_scheduled_time'.
    Modifies nodes_df by updating loads.
    """
    if jobs_df.empty:
        return jobs_df.assign(allocated_node_id=None, predicted_scheduled_time=None)

    jobs_df["allocated_node_id"] = pd.Series(dtype="object")
    jobs_df["predicted_scheduled_time"] = pd.Series(dtype="float64")

    # Iterate through jobs
    for job_idx, job_series in jobs_df.iterrows():
        min_completion_time = float("inf")
        selected_node_id: Optional[str] = None

        job_id_str = str(job_series.get("task_id"))
        # 'suitable_node_ids' is a list of string UUIDs added by FuzzyGate
        job_suitable_node_ids: list[str] = job_series.get("suitable_node_ids", [])

        if not job_suitable_node_ids:
            logger.debug(
                f"MCT: Job {job_id_str} has no suitable nodes from pre-filtering. Skipping."
            )
            jobs_df.loc[job_idx, "allocated_node_id"] = None
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = None
            continue

        candidate_nodes = nodes_df[nodes_df["node_id"].isin(job_suitable_node_ids)]

        if candidate_nodes.empty:
            logger.debug(
                f"MCT: Job {job_id_str} - no candidate nodes found from suitable_node_ids list in current nodes_df. Skipping."
            )
            jobs_df.loc[job_idx, "allocated_node_id"] = None
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = None
            continue

        for node_idx_df, node_series in candidate_nodes.iterrows():
            # Check basic fit against *current* available resources before calculating complex completion time
            if float(node_series.get("current_cpu_available", 0)) < float(
                job_series.get("cpu_req", 0)
            ) or float(node_series.get("current_mem_available", 0)) < float(
                job_series.get("mem_req", 0)
            ):
                continue  # Cannot fit on this node right now

            completion_time = _calculate_completion_time(
                job_series, node_series, current_timestamp
            )
            if completion_time < min_completion_time:
                min_completion_time = completion_time
                selected_node_id = str(node_series["node_id"])

        if selected_node_id:
            # INFO: selected_node_series is fetched here. While not directly used in the current
            # simplified 'predicted_start_time' calculation below, it holds the full data
            # of the chosen node. It would be essential for a more accurate calculation of
            # 'predicted_scheduled_time' by determining the job's specific execution
            # duration on this selected node (e.g., predicted_start_time = min_completion_time - execution_duration_on_node).
            # This can be revisited for a more sophisticated calculation later.
            selected_node_series = nodes_df[
                nodes_df["node_id"] == selected_node_id
            ].iloc[0]

            # Current simplified version of predicted_start_time:
            job_arrival_time = float(
                job_series.get("submission_time", current_timestamp)
            )
            predicted_start_time = max(current_timestamp, job_arrival_time)
            # It would start after current_timestamp, and potentially after other jobs finish on the node.
            # The MCT logic implies jobs are assigned to the node that *will finish it earliest*,
            # considering current node load. The `min_completion_time` is key.

            jobs_df.loc[job_idx, "allocated_node_id"] = selected_node_id
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = (
                predicted_start_time  # This is a simplification
            )

            _update_dynamic_node_load(
                nodes_df, selected_node_id, job_series
            )  # nodes_df is modified in place
            logger.debug(
                f"MCT: Job {job_id_str} allocated to Node {selected_node_id} (Est. Comp Time: {min_completion_time:.2f})"
            )
        else:
            jobs_df.loc[job_idx, "allocated_node_id"] = None
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = None
            logger.debug(
                f"MCT: Job {job_id_str} could not be allocated (no suitable node found or fit)."
            )

    return jobs_df


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """
    Schedule jobs on nodes using the MCT (Minimum Completion Time) strategy.
    """
    if not jobs:
        logger.info("MCT: No jobs to schedule.")
        return {}
    if not nodes:
        logger.warning("MCT: No nodes available. All jobs will be unallocated.")
        return {str(job.get("task_id", f"unknown_job_{id(job)}")): None for job in jobs}

    try:
        # Convert input lists of dicts to DataFrames
        # Important: Ensure string IDs if they are not already, for consistent merging/lookup if needed.
        # Assuming 'id' from to_dict(orient='records') is already stringified UUID.
        jobs_df = pd.DataFrame(jobs)
        if "task_id" in jobs_df.columns:
            jobs_df["task_id"] = jobs_df["task_id"].astype(str)

        nodes_df = pd.DataFrame(nodes)
        if "node_id" in nodes_df.columns:
            nodes_df["node_id"] = nodes_df["node_id"].astype(str)
        else:
            raise KeyError("'node_id' column missing in nodes data")

        # Initialize dynamic load columns on a copy of nodes_df to avoid modifying input dicts implicitly
        nodes_df_dynamic = _initialize_dynamic_node_load(nodes_df.copy())

        # Get current time (timestamp in seconds) - used for job eligibility and completion time calculations
        current_timestamp = time.time()

        # Sort jobs? MCT often processes jobs in a fixed order or based on some heuristic (e.g., FCFS based on submission_time)
        # For this version, we process jobs as they come in the list.
        # If sorting is needed: jobs_df.sort_values(by='submission_time', inplace=True)

        processed_jobs_df = _allocate_jobs_to_nodes_mct(
            jobs_df, nodes_df_dynamic, current_timestamp
        )

        # Convert result to simple dict: job_id -> node_id
        job_allocation: dict[str, Optional[str]] = {}
        for _, row in processed_jobs_df.iterrows():
            job_allocation[str(row["task_id"])] = (
                str(row["allocated_node_id"])
                if pd.notna(row["allocated_node_id"])
                else None
            )

        return job_allocation

    except KeyError as e:
        logger.error(
            f"MCT: KeyError during scheduling, likely due to missing expected data field: {e}",
            exc_info=True,
        )
        return {
            str(job.get("id", f"unknown_job_key_error_{id(job)}")): None for job in jobs
        }
    except Exception as e:
        logger.error(f"MCT: Unexpected error during scheduling: {e}", exc_info=True)
        return {
            str(job.get("id", f"unknown_job_unexpected_error_{id(job)}")): None
            for job in jobs
        }


def calculate_throughput_from_allocations(
    allocations: Optional[dict[str, Optional[str]]],
    jobs: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
) -> float:
    if not allocations:
        return 0.0
    successful_allocations = sum(
        1 for node_id in allocations.values() if node_id is not None
    )
    return float(successful_allocations)


def calculate_throughput(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> float:
    if not jobs or not nodes:
        return 0.0
    logger.debug("MCT: calculate_throughput (fallback) called, re-running schedule().")
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
