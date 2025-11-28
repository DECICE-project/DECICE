from typing import Any

import numpy as np

from ..schemas import Node, ScheduleRequest, VertexPool
from . import node_feature_registry
from .interfaces import INodeFeatureExtractor


# Base Features
@node_feature_registry.register()
class NodeIdExtractor(INodeFeatureExtractor):
    """Extracts the node's unique identifier."""

    name = "node_id"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        return node.id


@node_feature_registry.register()
class NodeParentPoolIdExtractor(INodeFeatureExtractor):
    """Extracts the ID of the VertexPool the node belongs to."""

    name = "vertexpool_id"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        return pool.id


# Metrics Features
@node_feature_registry.register()
class MetricsCpuUtil(INodeFeatureExtractor):
    """Extracts CPU utilization (0-100 scale), returns np.nan if missing."""

    name = "metrics_cpu_util"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        metric_value = node.metrics.util
        return metric_value if metric_value is not None else np.nan


@node_feature_registry.register()
class MetricsMemUtil(INodeFeatureExtractor):
    """Extracts Memory utilization (0-100 scale), returns np.nan if missing."""

    name = "metrics_mem_util"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        metric_value = node.metrics.mem_util
        return metric_value if metric_value is not None else np.nan


@node_feature_registry.register()
class MetricsNetworkBandwidthMbps(INodeFeatureExtractor):
    """Extracts Network Bandwidth capacity (Mbps), returns np.nan if missing."""

    name = "metrics_network_bandwidth_mbps"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        metric_value = node.metrics.network_bandwidth_mbps
        return metric_value if metric_value is not None else np.nan


@node_feature_registry.register()
class MetricsCpuCores(INodeFeatureExtractor):
    """Extracts total CPU cores, returns np.nan if missing."""

    name = "metrics_cpu_cores"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        metric_value = node.metrics.cpu_cores
        return metric_value if metric_value is not None else np.nan


@node_feature_registry.register()
class MetricsMemTotalMb(INodeFeatureExtractor):
    """Extracts total Memory (converting GB to MB), returns np.nan if missing."""

    name = "metrics_mem_total_mb"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        mem_total_gb = node.metrics.mem_total
        if mem_total_gb is None:
            return np.nan
        return mem_total_gb * 1024.0  # Ensure float conversion


@node_feature_registry.register()
class MetricsFreeDiskMb(INodeFeatureExtractor):
    """Extracts free disk space (converting GB to MB), returns np.nan if missing."""

    name = "metrics_free_disk_mb"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        free_disk_gb = node.metrics.free_disk_gb
        if free_disk_gb is None:
            return np.nan
        return free_disk_gb * 1024.0  # Ensure float conversion


@node_feature_registry.register()
class MetricsTotalDiskMb(INodeFeatureExtractor):
    """Extracts total disk space (converting GB to MB), returns np.nan if missing."""

    name = "metrics_total_disk_mb"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        total_disk_gb = node.metrics.total_disk_gb
        if total_disk_gb is None:
            return np.nan
        return total_disk_gb * 1024.0  # Ensure float conversion


@node_feature_registry.register()
class MetricsPowerWatts(INodeFeatureExtractor):
    """Extracts power consumption (Watts), returns np.nan if missing."""

    name = "metrics_power_watts"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        metric_value = node.metrics.power_watts
        return metric_value if metric_value is not None else np.nan


# Derived Features
@node_feature_registry.register()
class MetricsUsedDiskMb(INodeFeatureExtractor):
    """Calculates used disk space (MB), returns np.nan if inputs missing."""

    name = "metrics_used_disk_mb"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        total_disk_gb = node.metrics.total_disk_gb
        free_disk_gb = node.metrics.free_disk_gb
        if total_disk_gb is None or free_disk_gb is None:
            return np.nan
        # Perform calculation only if inputs are valid
        total_mb = total_disk_gb * 1024.0
        free_mb = free_disk_gb * 1024.0
        # Ensure used disk isn't negative due to reporting lag/errors
        return max(0.0, total_mb - free_mb)


@node_feature_registry.register()
class MetricsAvailableCpuCores(INodeFeatureExtractor):
    """Calculates available CPU cores, returns np.nan if inputs missing."""

    name = "metrics_available_cpu_cores"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        cpu_cores = node.metrics.cpu_cores
        cpu_util = node.metrics.util  # This is 0-100
        if cpu_cores is None or cpu_util is None:
            return np.nan
        # Perform calculation only if inputs are valid
        util_fraction = cpu_util / 100.0
        # Ensure available cores isn't negative due to reporting lag/errors
        return max(0.0, cpu_cores * (1.0 - util_fraction))


@node_feature_registry.register()
class MetricsAvailableMemMb(INodeFeatureExtractor):
    """Calculates available Memory (MB), returns np.nan if inputs missing."""

    name = "metrics_available_mem_mb"

    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        mem_total_gb = node.metrics.mem_total
        mem_util = node.metrics.mem_util  # This is 0-100
        if mem_total_gb is None or mem_util is None:
            return np.nan
        # Perform calculation only if inputs are valid
        mem_util_fraction = mem_util / 100.0
        total_mb = mem_total_gb * 1024.0
        # Ensure available memory isn't negative
        return max(0.0, total_mb * (1.0 - mem_util_fraction))
