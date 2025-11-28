"""
Module Name: [ilp_init.py]
Author: Sachin Nanavati
Contributors: []
Reviewer: [M. Bidollahkhani]
Date Created: [2024.07.01]
Last Modified: [2024.12.25]

Description:

Version History:
    v1.0 - [01.07.2024] - Initial stable ILP scheduling algorithm
    v1.1 - [2024.09.18] - Adding the throughput computation method
    v1.2 - [2024.12.25] - Calculate throughput as the number of successfully allocated jobs
Notes:
    -
"""

import logging
from typing import Any, Optional

import pulp

logger = logging.getLogger(__name__)

ILP_SOLVER_TIMEOUT_SECONDS = 30


def schedule(
    jobs: list[dict[str, Any]], nodes: list[dict[str, Any]]
) -> dict[str, Optional[str]]:
    """
    Schedule jobs on nodes based on ILP to minimize maximum CPU load on any node,
    respecting CPU and memory capacities.

    Args:
        jobs (list[dict[str, Any]]): List of job dictionaries. Expected keys include:
            'id' (str representation of UUID),
            'required_cpu' (int/float),      # <-- UPDATED KEY NAME
            'required_memory' (int/float, in MB). # <-- UPDATED KEY NAME
        nodes (list[dict[str, Any]]): List of node dictionaries. Expected keys include:
            'id' (str representation of UUID),
            'metrics_available_cpu_cores' (float, already accounts for current load),
            'metrics_available_mem_mb' (float, already accounts for current load).

    Returns:
        dict[str, Optional[str]]: Job ID (str) to Node ID (str) allocation,
                                  or None if a job is unallocated or an error occurs.
    """
    job_allocation: dict[str, Optional[str]] = {}

    if not jobs or not nodes:
        logger.warning("ILP: No jobs or no nodes provided. Returning empty allocation.")
        for job in jobs:
            job_allocation[str(job.get("task_id", f"unknown_job_{id(job)}"))] = None
        return job_allocation

    try:
        # Ensure IDs are strings for PuLP variable naming and dictionary keys
        job_details: dict[str, dict[str, Any]] = {
            str(job["task_id"]): job for job in jobs
        }
        node_details: dict[str, dict[str, Any]] = {
            str(node["node_id"]): node for node in nodes
        }

        job_ids_str: list[str] = list(job_details.keys())
        node_ids_str: list[str] = list(node_details.keys())

        # Extract job requested resources (keys from DataTransformer output)
        requested_cu: dict[str, float] = {
            job_id: float(job_details[job_id]["required_cpu"]) for job_id in job_ids_str
        }
        requested_mem: dict[str, float] = {
            job_id: float(job_details[job_id]["required_memory"])
            for job_id in job_ids_str  # Assumed to be in MB
        }

        # Extract node available capacities (using pre-calculated fields from DataTransformer output)
        capacities_cpu: dict[str, float] = {
            node_id: float(node_details[node_id]["metrics_available_cpu_cores"])
            for node_id in node_ids_str
        }
        capacities_mem: dict[str, float] = {
            node_id: float(node_details[node_id]["metrics_available_mem_mb"])
            for node_id in node_ids_str
        }

        # Define the ILP problem
        problem = pulp.LpProblem("Job_Placement_ILP", pulp.LpMinimize)

        # Decision variables: x_ij = 1 if job i is assigned to node j, 0 otherwise
        x = pulp.LpVariable.dicts(
            "x",
            ((job_id, node_id) for job_id in job_ids_str for node_id in node_ids_str),
            cat="Binary",
        )

        # Objective variable: L_max = maximum CPU load (sum of required_cpu) on any node
        L_max = pulp.LpVariable("L_max", lowBound=0)
        problem += L_max, "Minimize_Maximum_Node_CPU_Load"

        # Constraints
        # Each job must be assigned to exactly one node
        for i in job_ids_str:
            problem += (
                pulp.lpSum(x[i, j] for j in node_ids_str) == 1,
                f"Job_Assignment_Constraint_{i}",
            )

        # Resource capacity constraints for each node
        for j in node_ids_str:
            # CPU capacity constraint
            problem += (
                pulp.lpSum(requested_cu[i] * x[i, j] for i in job_ids_str)
                <= capacities_cpu[j],
                f"CPU_Capacity_Constraint_{j}",
            )
            # Memory capacity constraint
            problem += (
                pulp.lpSum(requested_mem[i] * x[i, j] for i in job_ids_str)
                <= capacities_mem[j],
                f"Memory_Capacity_Constraint_{j}",
            )

            # Link L_max to the CPU load on this node
            problem += (
                pulp.lpSum(requested_cu[i] * x[i, j] for i in job_ids_str) <= L_max,
                f"Max_Load_Definition_Constraint_{j}",
            )

        logger.info(
            f"ILP: Starting solver for {len(job_ids_str)} jobs and {len(node_ids_str)} nodes."
        )
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=ILP_SOLVER_TIMEOUT_SECONDS)
        problem.solve(solver)

        # Process results
        if problem.status == pulp.LpStatusOptimal:
            logger.info(
                f"ILP: Optimal solution found. Target L_max = {pulp.value(L_max):.2f}"
            )
            for i_str in job_ids_str:
                assigned_node_id_str = None
                for j_str in node_ids_str:
                    if pulp.value(x[i_str, j_str]) == 1:
                        assigned_node_id_str = j_str
                        break
                job_allocation[i_str] = assigned_node_id_str
                logger.debug(f"Job {i_str} assigned to Node {assigned_node_id_str}")
        elif problem.status == pulp.LpStatusNotSolved:
            # Could be due to timeout or other issues before finding a solution
            logger.warning(
                f"ILP: Solver did not find a solution (Status: {pulp.LpStatus[problem.status]}). Possible timeout ({ILP_SOLVER_TIMEOUT_SECONDS}s). Jobs unallocated."
            )
            for i_str in job_ids_str:
                job_allocation[i_str] = None
        else:  # Covers Infeasible, Unbounded, Undefined
            logger.warning(
                f"ILP: Solution not optimal. Status: {pulp.LpStatus[problem.status]}. Jobs unallocated."
            )
            for i_str in job_ids_str:
                job_allocation[i_str] = None

    except (pulp.apis.core.PulpSolverError, KeyError, Exception) as e:
        logger.error(
            f"ILP Error ({type(e).__name__}): {e}. All jobs unallocated.", exc_info=True
        )
        for job in jobs:
            job_allocation[str(job.get("task_id", f"unknown_job_err_{id(job)}"))] = None

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
    logger.debug("ILP: calculate_throughput (fallback) called, re-running schedule().")
    job_allocations = schedule(jobs, nodes)
    return calculate_throughput_from_allocations(job_allocations, jobs, nodes)
