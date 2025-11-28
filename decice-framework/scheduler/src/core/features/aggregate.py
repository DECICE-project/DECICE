from . import aggregate_feature_registry
from .interfaces import IAggregateFeatureExtractor

# Aggregate Feature Implementations
# These features consume the DataFrames produced by the SchedulerDataTransformer
# and aggregate them into single values for the final feature vector.


@aggregate_feature_registry.register()
class NumPendingJobs(IAggregateFeatureExtractor):
    name = "num_pending_jobs"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return float(len(jobs_df))


@aggregate_feature_registry.register()
class TotalRequestedCpu(IAggregateFeatureExtractor):
    name = "total_requested_cpu"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["required_cpu"].sum())
            if not jobs_df.empty and "required_cpu" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalRequestedMemMb(IAggregateFeatureExtractor):
    name = "total_requested_mem_mb"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        # Assuming 'required_memory' in jobs_df is already in MB
        return (
            float(jobs_df["required_memory"].sum())
            if not jobs_df.empty and "required_memory" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalRequestedGpu(IAggregateFeatureExtractor):
    name = "total_requested_gpu"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        # 'gpu_is_required' is 1 if GPU needed, 0 otherwise
        # INFO: can be more than 1 GPU
        return (
            float(jobs_df["gpu_is_required"].sum())
            if not jobs_df.empty and "gpu_is_required" in jobs_df.columns
            else 0.0
        )


# NOTE: initial FeatureEngineer had 'total_requested_storage_mb',
# 'avg_storage_req_per_job_mb'. These require 'storage_req' in jobs_df,
# which isn't produced by the current SchedulerDataTransformer.
# We can add corresponding IWorkflowTaskFeatureExtractor if needed.
# Feasibility of storage_req has been discussed though


@aggregate_feature_registry.register()
class AvgCpuReqPerJob(IAggregateFeatureExtractor):
    name = "avg_cpu_req_per_job"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["required_cpu"].mean())
            if not jobs_df.empty and "required_cpu" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class AvgMemReqPerJobMb(IAggregateFeatureExtractor):
    name = "avg_mem_req_per_job_mb"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["required_memory"].mean())
            if not jobs_df.empty and "required_memory" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class AvgGpuReqPerJob(IAggregateFeatureExtractor):
    name = "avg_gpu_req_per_job"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["gpu_is_required"].mean())
            if not jobs_df.empty and "gpu_is_required" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class MaxCpuReq(IAggregateFeatureExtractor):
    name = "max_cpu_req"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["required_cpu"].max())
            if not jobs_df.empty and "required_cpu" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class MaxMemReqMb(IAggregateFeatureExtractor):
    name = "max_mem_req_mb"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            float(jobs_df["required_memory"].max())
            if not jobs_df.empty and "required_memory" in jobs_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class NumAvailableNodes(IAggregateFeatureExtractor):
    name = "num_available_nodes"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return float(len(nodes_df))


@aggregate_feature_registry.register()
class TotalClusterCpuCores(IAggregateFeatureExtractor):
    name = "total_cluster_cpu_cores"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_cpu_cores"].sum()
            if not nodes_df.empty and "metrics_cpu_cores" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalClusterMemMb(IAggregateFeatureExtractor):
    name = "total_cluster_mem_mb"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_mem_total_mb"].sum()
            if not nodes_df.empty and "metrics_mem_total_mb" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalClusterDiskMb(IAggregateFeatureExtractor):
    name = "total_cluster_disk_mb"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_total_disk_mb"].sum()
            if not nodes_df.empty and "metrics_total_disk_mb" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class AvgNodeCpuUtil(IAggregateFeatureExtractor):
    name = "avg_node_cpu_util"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_cpu_util"].mean()
            if not nodes_df.empty and "metrics_cpu_util" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class AvgNodeMemUtil(IAggregateFeatureExtractor):
    name = "avg_node_mem_util"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_mem_util"].mean()
            if not nodes_df.empty and "metrics_mem_util" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class AvgNodeDiskUtil(IAggregateFeatureExtractor):
    name = "avg_node_disk_util"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        avg_node_disk_util = 0.0
        if (
            not nodes_df.empty
            and "metrics_used_disk_mb" in nodes_df.columns
            and "metrics_total_disk_mb" in nodes_df.columns
            and nodes_df["metrics_total_disk_mb"].sum() > 1e-6  # Avoid division by zero
        ):
            avg_node_disk_util = (
                nodes_df["metrics_used_disk_mb"].sum()
                / nodes_df["metrics_total_disk_mb"].sum()
            ) * 100.0  # Convert fraction to percentage 0-100
        return float(avg_node_disk_util)


@aggregate_feature_registry.register()
class TotalAvailableCpuCluster(IAggregateFeatureExtractor):
    name = "total_available_cpu_cluster"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_available_cpu_cores"].sum()
            if not nodes_df.empty and "metrics_available_cpu_cores" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalAvailableMemCluster(IAggregateFeatureExtractor):
    name = "total_available_mem_cluster"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_available_mem_mb"].sum()
            if not nodes_df.empty and "metrics_available_mem_mb" in nodes_df.columns
            else 0.0
        )


@aggregate_feature_registry.register()
class TotalAvailableDiskCluster(IAggregateFeatureExtractor):
    name = "total_available_disk_cluster"

    def calculate(self, jobs_df, nodes_df, latency_matrix) -> float:
        return (
            nodes_df["metrics_free_disk_mb"].sum()
            if not nodes_df.empty and "metrics_free_disk_mb" in nodes_df.columns
            else 0.0
        )
