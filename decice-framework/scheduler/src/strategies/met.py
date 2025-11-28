"""
Module Name: [met.py]
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


def _met_initialize_dynamic_node_load(nodes_df: pd.DataFrame) -> pd.DataFrame:
    """Initializes dynamic load tracking for MET."""
    if nodes_df.empty:
        # Define expected columns for an empty df
        nodes_df["current_cpu_available"] = pd.Series(dtype="float64")
        nodes_df["current_mem_available"] = pd.Series(dtype="float64")
        nodes_df["current_cpu_util_percent"] = pd.Series(dtype="float64")
        nodes_df["current_mem_util_percent"] = pd.Series(dtype="float64")
        nodes_df["load_score"] = pd.Series(dtype="float64")
        return nodes_df

    nodes_df["current_cpu_available"] = nodes_df["metrics_available_cpu_cores"].astype(
        float
    )
    nodes_df["current_mem_available"] = nodes_df["metrics_available_mem_mb"].astype(
        float
    )
    nodes_df["current_cpu_util_percent"] = nodes_df["metrics_cpu_util"]  # Already 0-100
    nodes_df["current_mem_util_percent"] = nodes_df["metrics_mem_util"]  # Already 0-100
    nodes_df["load_score"] = (
        nodes_df["current_cpu_util_percent"] + nodes_df["current_mem_util_percent"]
    )
    return nodes_df


def _met_update_dynamic_node_load(
    nodes_df: pd.DataFrame,
    allocated_node_id: str,
    job_series: pd.Series,
) -> None:
    """Updates node load after job allocation. Modifies nodes_df IN PLACE."""
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

    if total_cpu > 0:
        nodes_df.loc[node_idx, "current_cpu_util_percent"] = 100.0 * (
            1.0 - (nodes_df.loc[node_idx, "current_cpu_available"] / total_cpu)
        )
    else:
        nodes_df.loc[node_idx, "current_cpu_util_percent"] = 100.0

    if total_mem > 0:
        nodes_df.loc[node_idx, "current_mem_util_percent"] = 100.0 * (
            1.0 - (nodes_df.loc[node_idx, "current_mem_available"] / total_mem)
        )
    else:
        nodes_df.loc[node_idx, "current_mem_util_percent"] = 100.0

    nodes_df.loc[node_idx, "load_score"] = (
        nodes_df.loc[node_idx, "current_cpu_util_percent"]
        + nodes_df.loc[node_idx, "current_mem_util_percent"]
    )


def _met_calculate_execution_time(
    job_series: pd.Series,
    node_series: pd.Series,
) -> float:
    """Calculate expected execution time."""
    job_cpu = float(job_series.get("required_cpu", 0))
    job_mem = float(job_series.get("required_memory", 0))  # MB

    node_cpu_avail = float(node_series.get("current_cpu_available", 0.0))
    node_mem_avail = float(node_series.get("current_mem_available", 0.0))
    node_current_load_metric = float(
        node_series.get("load_score", 0.0)
    )  # Sum % utils (0-200)

    exec_time_cpu = job_cpu / max(0.001, node_cpu_avail) if job_cpu > 0 else 0.0
    exec_time_mem = job_mem / max(0.001, node_mem_avail) if job_mem > 0 else 0.0
    estimated_duration = max(exec_time_cpu, exec_time_mem) + (
        node_current_load_metric * 0.001
    )  # Small factor for load
    return estimated_duration


def _met_allocate_jobs_to_nodes(
    jobs_df: pd.DataFrame,
    nodes_df_dynamic: pd.DataFrame,
    current_sim_time: float,
) -> tuple[pd.DataFrame, float]:
    """Allocate jobs using MET. Modifies jobs_df and nodes_df_dynamic."""
    if jobs_df.empty:
        return (
            jobs_df.assign(allocated_node_id=None, predicted_scheduled_time=None),
            current_sim_time,
        )

    jobs_df["allocated_node_id"] = pd.Series(dtype="object")
    jobs_df["predicted_scheduled_time"] = pd.Series(dtype="float64")

    for job_idx, job_series in jobs_df.iterrows():
        job_id_str = str(job_series.get("task_id"))
        job_eligible_earliest_start = float(
            job_series.get("submission_time", current_sim_time)
        )

        min_execution_time_on_any_node = float("inf")
        selected_node_id_for_job: Optional[str] = None

        job_suitable_node_ids: list[str] = job_series.get("suitable_node_ids", [])
        if not job_suitable_node_ids:
            jobs_df.loc[job_idx, ["allocated_node_id", "predicted_scheduled_time"]] = [
                None,
                None,
            ]
            continue

        candidate_nodes = nodes_df_dynamic[
            nodes_df_dynamic["node_id"].isin(job_suitable_node_ids)
        ]
        if candidate_nodes.empty:
            jobs_df.loc[job_idx, ["allocated_node_id", "predicted_scheduled_time"]] = [
                None,
                None,
            ]
            continue

        for _, node_series in candidate_nodes.iterrows():
            if float(node_series.get("current_cpu_available", 0)) < float(
                job_series.get("required_cpu", 0)
            ) or float(node_series.get("current_mem_available", 0)) < float(
                job_series.get("required_memory", 0)
            ):
                continue

            execution_time = _met_calculate_execution_time(job_series, node_series)
            if execution_time < min_execution_time_on_any_node:
                min_execution_time_on_any_node = execution_time
                selected_node_id_for_job = str(node_series["node_id"])

        if selected_node_id_for_job:
            predicted_start_time = max(current_sim_time, job_eligible_earliest_start)
            jobs_df.loc[job_idx, "allocated_node_id"] = selected_node_id_for_job
            jobs_df.loc[job_idx, "predicted_scheduled_time"] = predicted_start_time
            _met_update_dynamic_node_load(
                nodes_df_dynamic, selected_node_id_for_job, job_series
            )
            logger.debug(
                f"MET: Job {job_id_str} allocated to Node {selected_node_id_for_job} (Est Exec: {min_execution_time_on_any_node:.2f})"
            )
        else:
            jobs_df.loc[job_idx, ["allocated_node_id", "predicted_scheduled_time"]] = [
                None,
                None,
            ]
            logger.debug(f"MET: Job {job_id_str} could not be allocated.")

    return jobs_df, current_sim_time  # Returning original sim time for now


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """Schedule jobs using MET."""
    if not jobs:
        return {}
    if not nodes:
        return {str(job.get("task_id", f"unknown_job_{id(job)}")): None for job in jobs}

    try:
        # DFs will have task_id, node_id etc.
        jobs_df = pd.DataFrame(jobs)
        if "task_id" in jobs_df.columns:
            jobs_df["task_id"] = jobs_df["task_id"].astype(str)

        nodes_df = pd.DataFrame(nodes)
        if "node_id" in nodes_df.columns:
            nodes_df["node_id"] = nodes_df["node_id"].astype(str)
        else:
            raise KeyError("'node_id' column missing in nodes data for MET init")

        nodes_df_dynamic = _met_initialize_dynamic_node_load(nodes_df.copy())
        current_real_time = time.time()
        processed_jobs_df, _ = _met_allocate_jobs_to_nodes(
            jobs_df, nodes_df_dynamic, current_real_time
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
            f"MET Error ({type(e).__name__}): {e}. All jobs unallocated.", exc_info=True
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
    logger.debug("MET: calculate_throughput (fallback) called, re-running schedule().")
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
