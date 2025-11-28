import numpy as np
import pytest

from core.features.cluster import (MetricsAvailableCpuCores,
                                   MetricsAvailableMemMb, MetricsCpuCores,
                                   MetricsCpuUtil, MetricsFreeDiskMb,
                                   MetricsMemTotalMb, MetricsMemUtil,
                                   MetricsNetworkBandwidthMbps,
                                   MetricsPowerWatts, MetricsTotalDiskMb,
                                   MetricsUsedDiskMb, NodeIdExtractor,
                                   NodeParentPoolIdExtractor)
from core.schemas import Node, NodeMetrics, VertexPool


def test_node_id_extractor(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = NodeIdExtractor()
    assert extractor.name == "node_id"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == "node-low-util-1"


def test_node_parent_pool_id_extractor(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = NodeParentPoolIdExtractor()
    assert extractor.name == "vertexpool_id"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == "pool-a"


def test_metrics_cpu_util(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsCpuUtil()
    assert extractor.name == "metrics_cpu_util"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 10.5  # 0-100 scale


def test_metrics_mem_util(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsMemUtil()
    assert extractor.name == "metrics_mem_util"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 20.0  # 0-100 scale


def test_metrics_cpu_cores(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsCpuCores()
    assert extractor.name == "metrics_cpu_cores"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 16.0


def test_metrics_mem_total_mb(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsMemTotalMb()
    assert extractor.name == "metrics_mem_total_mb"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 64.0 * 1024  # Convert GB to MB


def test_metrics_free_disk_mb(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsFreeDiskMb()
    assert extractor.name == "metrics_free_disk_mb"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 800.0 * 1024  # Convert GB to MB


def test_metrics_total_disk_mb(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsTotalDiskMb()
    assert extractor.name == "metrics_total_disk_mb"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 1000.0 * 1024  # Convert GB to MB


def test_metrics_used_disk_mb(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsUsedDiskMb()
    assert extractor.name == "metrics_used_disk_mb"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    expected = (1000.0 - 800.0) * 1024  # (Total - Free) * 1024
    assert np.isclose(result, expected)


def test_metrics_available_cpu_cores(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsAvailableCpuCores()
    assert extractor.name == "metrics_available_cpu_cores"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    # Total * (1 - Util%) = 16.0 * (1 - 10.5 / 100.0)
    expected = 16.0 * (1.0 - 0.105)
    assert np.isclose(result, expected)


def test_metrics_available_mem_mb(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsAvailableMemMb()
    assert extractor.name == "metrics_available_mem_mb"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    # (TotalGB * 1024) * (1 - Util%) = (64.0 * 1024) * (1 - 20.0 / 100.0)
    expected = (64.0 * 1024) * (1.0 - 0.20)
    assert np.isclose(result, expected)


def test_metrics_network_bandwidth(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsNetworkBandwidthMbps()
    assert extractor.name == "metrics_network_bandwidth_mbps"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 1000.0


def test_metrics_power_watts(
    sample_node_low_util, sample_vertex_pool, sample_schedule_request
):
    extractor = MetricsPowerWatts()
    assert extractor.name == "metrics_power_watts"
    result = extractor.extract(
        sample_node_low_util, sample_vertex_pool, sample_schedule_request
    )
    assert result == 100.0


# Test cases for None/NaN handling
def test_extractors_handle_none_metrics(sample_vertex_pool, sample_schedule_request):
    node_with_nones = Node(
        id="node-nones",
        name="node-nones",
        metrics=NodeMetrics(
            util=None,
            mem_util=50.0,
            network_bandwidth_mbps=None,
            free_disk_gb=None,
            total_disk_gb=100.0,
            cpu_cores=4.0,
            mem_total=16.0,
            power_watts=None,
        ),
    )
    pool = VertexPool(id="pool-nones", nodes=[node_with_nones])

    assert np.isnan(
        MetricsCpuUtil().extract(node_with_nones, pool, sample_schedule_request)
    )
    assert (
        MetricsMemUtil().extract(node_with_nones, pool, sample_schedule_request) == 50.0
    )
    assert np.isnan(
        MetricsNetworkBandwidthMbps().extract(
            node_with_nones, pool, sample_schedule_request
        )
    )
    assert np.isnan(
        MetricsFreeDiskMb().extract(node_with_nones, pool, sample_schedule_request)
    )
    assert (
        MetricsTotalDiskMb().extract(node_with_nones, pool, sample_schedule_request)
        == 100.0 * 1024
    )
    assert (
        MetricsCpuCores().extract(node_with_nones, pool, sample_schedule_request) == 4.0
    )
    assert (
        MetricsMemTotalMb().extract(node_with_nones, pool, sample_schedule_request)
        == 16.0 * 1024
    )
    assert np.isnan(
        MetricsPowerWatts().extract(node_with_nones, pool, sample_schedule_request)
    )
    # Derived features should also handle Nones
    assert np.isnan(
        MetricsUsedDiskMb().extract(node_with_nones, pool, sample_schedule_request)
    )
    assert np.isnan(
        MetricsAvailableCpuCores().extract(
            node_with_nones, pool, sample_schedule_request
        )
    )
    assert np.isclose(
        MetricsAvailableMemMb().extract(node_with_nones, pool, sample_schedule_request),
        (16.0 * 1024 * 0.5),
    )
