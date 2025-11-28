import numpy as np
import pandas as pd
import pytest

from core.features.aggregate import (AvgNodeCpuUtil, AvgNodeDiskUtil,
                                     NumPendingJobs, TotalClusterCpuCores)
from core.schemas import LatencyMatrix


@pytest.fixture
def sample_jobs_df() -> pd.DataFrame:
    """Sample DataFrame similar to DataTransformer output for workloads."""
    data = [
        {
            "workload_id": "job1",
            "required_cpu": 2,
            "required_memory": 4096,
            "gpu_is_required": 0,
        },
        {
            "workload_id": "job2",
            "required_cpu": 4,
            "required_memory": 8192,
            "gpu_is_required": 1,
        },
        {
            "workload_id": "job3",
            "required_cpu": 1,
            "required_memory": 2048,
            "gpu_is_required": 0,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture
def sample_nodes_df() -> pd.DataFrame:
    """Sample DataFrame similar to DataTransformer output for nodes."""
    data = [
        {
            "node_id": "node1",
            "metrics_cpu_cores": 8,
            "metrics_mem_total_mb": 32768,
            "metrics_cpu_util": 50.0,
            "metrics_mem_util": 25.0,
            "metrics_used_disk_mb": 100000,
            "metrics_total_disk_mb": 500000,
            "metrics_available_cpu_cores": 4.0,
            "metrics_available_mem_mb": 24576,
        },
        {
            "node_id": "node2",
            "metrics_cpu_cores": 16,
            "metrics_mem_total_mb": 65536,
            "metrics_cpu_util": 75.0,
            "metrics_mem_util": 50.0,
            "metrics_used_disk_mb": 600000,
            "metrics_total_disk_mb": 1000000,
            "metrics_available_cpu_cores": 4.0,
            "metrics_available_mem_mb": 32768,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture
def empty_jobs_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["workload_id", "required_cpu", "required_memory", "gpu_is_required"]
    )


@pytest.fixture
def empty_nodes_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "node_id",
            "metrics_cpu_cores",
            "metrics_mem_total_mb",
            "metrics_cpu_util",
            "metrics_mem_util",
            "metrics_used_disk_mb",
            "metrics_total_disk_mb",
            "metrics_available_cpu_cores",
            "metrics_available_mem_mb",
        ]
    )


@pytest.fixture
def sample_latency_matrix() -> LatencyMatrix:
    return {}  # Not used by these features, but needed for the method signature


def test_num_pending_jobs(sample_jobs_df, empty_nodes_df, sample_latency_matrix):
    extractor = NumPendingJobs()
    assert extractor.name == "num_pending_jobs"
    result = extractor.calculate(sample_jobs_df, empty_nodes_df, sample_latency_matrix)
    assert result == 3.0


def test_num_pending_jobs_empty(empty_jobs_df, empty_nodes_df, sample_latency_matrix):
    extractor = NumPendingJobs()
    result = extractor.calculate(empty_jobs_df, empty_nodes_df, sample_latency_matrix)
    assert result == 0.0


def test_total_cluster_cpu_cores(
    sample_jobs_df, sample_nodes_df, sample_latency_matrix
):
    extractor = TotalClusterCpuCores()
    assert extractor.name == "total_cluster_cpu_cores"
    result = extractor.calculate(sample_jobs_df, sample_nodes_df, sample_latency_matrix)
    assert result == 8.0 + 16.0  # 24.0


def test_total_cluster_cpu_cores_empty(
    sample_jobs_df, empty_nodes_df, sample_latency_matrix
):
    extractor = TotalClusterCpuCores()
    result = extractor.calculate(sample_jobs_df, empty_nodes_df, sample_latency_matrix)
    assert result == 0.0


def test_avg_node_cpu_util(sample_jobs_df, sample_nodes_df, sample_latency_matrix):
    extractor = AvgNodeCpuUtil()
    assert extractor.name == "avg_node_cpu_util"
    result = extractor.calculate(sample_jobs_df, sample_nodes_df, sample_latency_matrix)
    # Average of 50.0 and 75.0
    assert np.isclose(result, 62.5)


def test_avg_node_cpu_util_empty(sample_jobs_df, empty_nodes_df, sample_latency_matrix):
    extractor = AvgNodeCpuUtil()
    result = extractor.calculate(sample_jobs_df, empty_nodes_df, sample_latency_matrix)
    assert result == 0.0


def test_avg_node_disk_util(sample_jobs_df, sample_nodes_df, sample_latency_matrix):
    extractor = AvgNodeDiskUtil()
    assert extractor.name == "avg_node_disk_util"
    result = extractor.calculate(sample_jobs_df, sample_nodes_df, sample_latency_matrix)
    # Total Used = 100k + 600k = 700k
    # Total Disk = 500k + 1000k = 1500k
    # Avg Util = (700k / 1500k) * 100
    expected = (700000 / 1500000) * 100.0
    assert np.isclose(result, expected)


def test_avg_node_disk_util_empty(
    sample_jobs_df, empty_nodes_df, sample_latency_matrix
):
    extractor = AvgNodeDiskUtil()
    result = extractor.calculate(sample_jobs_df, empty_nodes_df, sample_latency_matrix)
    assert result == 0.0


def test_avg_node_disk_util_zero_total(sample_jobs_df, sample_latency_matrix):
    # Test case where total disk is zero to prevent division by zero
    nodes_data = [
        {"node_id": "node1", "metrics_used_disk_mb": 100, "metrics_total_disk_mb": 0}
    ]
    nodes_df_zero = pd.DataFrame(nodes_data)
    extractor = AvgNodeDiskUtil()
    result = extractor.calculate(sample_jobs_df, nodes_df_zero, sample_latency_matrix)
    assert result == 0.0  # Expect 0 if total is 0
