#!/usr/bin/env python3
"""
Prometheus Metrics Client
Unified client for fetching all scheduler metrics from Prometheus
"""

import aiohttp
import asyncio
import json
from typing import Dict, Optional, List
from datetime import datetime


class PrometheusMetricsClient:
    """Client for fetching metrics from Prometheus"""

    def __init__(
        self,
        prometheus_url: str = "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090",
    ):
        self.prometheus_url = prometheus_url
        self.session = None

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def query_prometheus(self, query: str) -> Optional[Dict]:
        """Execute PromQL query"""
        try:
            session = await self._get_session()
            url = f"{self.prometheus_url}/api/v1/query"
            params = {"query": query}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                else:
                    print(f"Prometheus query failed: {response.status}")
                    return None
        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return None

    async def get_volcano_metrics(self) -> Dict:
        """Get Volcano scheduler metrics"""
        metrics = {}

        # Volcano CPU usage
        cpu_query = 'rate(container_cpu_usage_seconds_total{pod=~"volcano-scheduler.*", container!="POD", container!=""}[5m])'
        cpu_data = await self.query_prometheus(cpu_query)
        if cpu_data and cpu_data.get("result"):
            cpu_usage = sum(float(result["value"][1]) for result in cpu_data["result"])
            metrics["cpu_cores"] = round(cpu_usage, 4)

        # Volcano memory usage
        memory_query = 'container_memory_usage_bytes{pod=~"volcano-scheduler.*", container!="POD", container!=""}'
        memory_data = await self.query_prometheus(memory_query)
        if memory_data and memory_data.get("result"):
            memory_bytes = sum(
                float(result["value"][1]) for result in memory_data["result"]
            )
            metrics["memory_mb"] = round(memory_bytes / (1024 * 1024), 2)

        # Volcano job queue length (if available)
        queue_query = "volcano_queue_job_count"
        queue_data = await self.query_prometheus(queue_query)
        if queue_data and queue_data.get("result"):
            queue_jobs = sum(
                float(result["value"][1]) for result in queue_data["result"]
            )
            metrics["queue_jobs"] = int(queue_jobs)
        else:
            metrics["queue_jobs"] = 0

        # Overall cluster CPU/Memory (Volcano manages cluster resources)
        cluster_cpu_query = (
            '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100'
        )
        cluster_cpu_data = await self.query_prometheus(cluster_cpu_query)
        if cluster_cpu_data and cluster_cpu_data.get("result"):
            metrics["cpu_percent"] = round(
                float(cluster_cpu_data["result"][0]["value"][1]), 2
            )
        else:
            metrics["cpu_percent"] = 0.0

        cluster_memory_query = "(1 - avg(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
        cluster_memory_data = await self.query_prometheus(cluster_memory_query)
        if cluster_memory_data and cluster_memory_data.get("result"):
            metrics["memory_percent"] = round(
                float(cluster_memory_data["result"][0]["value"][1]), 2
            )
        else:
            metrics["memory_percent"] = 0.0

        return metrics

    async def get_hpc_metrics(self) -> Dict:
        """Get remote HPC cluster metrics from Prometheus (excluding cn01-cn08 k8s nodes)

        Note: cn-kube partition filtering is done at the exporter level (simple-hpc-exporter.py)
        """
        metrics = {}

        # Detailed CPU and Memory utilization (for unified load calculation)
        cpu_query = 'remote_hpc_cpu_utilization_percent{host="192.168.23.14"}'
        cpu_data = await self.query_prometheus(cpu_query)
        if cpu_data and cpu_data.get("result"):
            metrics["cpu_utilization_percent"] = float(
                cpu_data["result"][0]["value"][1]
            )

        memory_query = 'remote_hpc_memory_utilization_percent{host="192.168.23.14"}'
        memory_data = await self.query_prometheus(memory_query)
        if memory_data and memory_data.get("result"):
            metrics["memory_utilization_percent"] = float(
                memory_data["result"][0]["value"][1]
            )

        # Legacy utilization (for backward compatibility)
        utilization_query = 'remote_hpc_utilization_percent{host="192.168.23.14"}'
        util_data = await self.query_prometheus(utilization_query)
        if util_data and util_data.get("result"):
            metrics["utilization_percent"] = float(util_data["result"][0]["value"][1])

        # HPC nodes
        nodes_total_query = 'remote_hpc_nodes_total{host="192.168.23.14"}'
        nodes_data = await self.query_prometheus(nodes_total_query)
        if nodes_data and nodes_data.get("result"):
            metrics["nodes_total"] = int(float(nodes_data["result"][0]["value"][1]))

        nodes_idle_query = 'remote_hpc_nodes_idle{host="192.168.23.14"}'
        idle_data = await self.query_prometheus(nodes_idle_query)
        if idle_data and idle_data.get("result"):
            metrics["nodes_available"] = int(float(idle_data["result"][0]["value"][1]))

        # HPC jobs
        jobs_running_query = 'remote_hpc_jobs_running{host="192.168.23.14"}'
        running_data = await self.query_prometheus(jobs_running_query)
        if running_data and running_data.get("result"):
            metrics["jobs_running"] = int(float(running_data["result"][0]["value"][1]))

        jobs_pending_query = 'remote_hpc_jobs_pending{host="192.168.23.14"}'
        pending_data = await self.query_prometheus(jobs_pending_query)
        if pending_data and pending_data.get("result"):
            metrics["jobs_pending"] = int(float(pending_data["result"][0]["value"][1]))

        # HPC capacity score
        capacity_query = 'remote_hpc_capacity_score{host="192.168.23.14"}'
        capacity_data = await self.query_prometheus(capacity_query)
        if capacity_data and capacity_data.get("result"):
            metrics["capacity_score"] = float(capacity_data["result"][0]["value"][1])

        # HPC load score
        load_query = 'remote_hpc_load_score{host="192.168.23.14"}'
        load_data = await self.query_prometheus(load_query)
        if load_data and load_data.get("result"):
            metrics["load_score"] = float(load_data["result"][0]["value"][1])

        return metrics

    async def get_all_scheduler_metrics(self) -> Dict:
        """Get metrics for all schedulers"""
        volcano_metrics, hpc_metrics = await asyncio.gather(
            self.get_volcano_metrics(), self.get_hpc_metrics()
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "volcano": volcano_metrics,
            "hpc": hpc_metrics,
        }

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


class IntelligentSchedulerService:
    """Service for making intelligent scheduling decisions based on Prometheus metrics"""

    def __init__(self, prometheus_client: PrometheusMetricsClient):
        self.prometheus_client = prometheus_client

    async def get_scheduling_recommendation(self, job_data: Dict) -> str:
        """
        Get scheduling recommendation based on current metrics from Prometheus
        """
        # Check if scheduler is explicitly specified
        scheduler_target = job_data.get("schedulerTarget")
        if scheduler_target in ["VOLCANO", "INTERLINK_SLURM"]:
            return scheduler_target

        # For AUTO mode, make intelligent decision
        try:
            metrics = await self.prometheus_client.get_all_scheduler_metrics()

            volcano_metrics = metrics.get("volcano", {})
            hpc_metrics = metrics.get("hpc", {})

            # Decision logic based on metrics
            decision_factors = self._analyze_scheduling_factors(
                volcano_metrics, hpc_metrics
            )

            if decision_factors["prefer_hpc"]:
                return "INTERLINK_SLURM"
            else:
                return "VOLCANO"

        except Exception as e:
            print(f"Error getting scheduling recommendation: {e}")
            return "VOLCANO"  # Default fallback

    def _analyze_scheduling_factors(
        self, volcano_metrics: Dict, hpc_metrics: Dict
    ) -> Dict:
        """Advanced load comparison algorithm for intelligent scheduling"""

        # Calculate load scores for both schedulers (0-100, lower is better)
        volcano_load_score = self._calculate_volcano_load_score(volcano_metrics)
        hpc_load_score = self._calculate_hpc_load_score(hpc_metrics)

        # Determine preference based on load comparison
        load_difference = abs(volcano_load_score - hpc_load_score)
        prefer_hpc = hpc_load_score < volcano_load_score

        # Only switch if there's a meaningful difference (> 15 points)
        if load_difference < 15:
            # Loads are similar, prefer Volcano (local cluster) for better latency
            prefer_hpc = False
            decision_reason = f"Load similar (V:{volcano_load_score:.1f}, H:{hpc_load_score:.1f}) - prefer local Volcano"
        else:
            decision_reason = f"Load difference significant: Volcano={volcano_load_score:.1f}, HPC={hpc_load_score:.1f}"

        factors = {
            "prefer_hpc": prefer_hpc,
            "volcano_load_score": volcano_load_score,
            "hpc_load_score": hpc_load_score,
            "load_difference": load_difference,
            "decision_reason": decision_reason,
            "reasons": [],
        }

        # Add detailed reasoning
        if prefer_hpc:
            factors["reasons"].append(
                f"HPC is less loaded (score: {hpc_load_score:.1f} vs {volcano_load_score:.1f})"
            )
        else:
            factors["reasons"].append(
                f"Volcano is preferred (score: {volcano_load_score:.1f} vs {hpc_load_score:.1f})"
            )

        # Add specific load factors
        factors["reasons"].extend(self._get_load_details(volcano_metrics, hpc_metrics))

        return factors

    def _calculate_volcano_load_score(self, volcano_metrics: Dict) -> float:
        """Calculate Volcano cluster load score (0-100, lower is better)"""
        if not volcano_metrics:
            return 100.0  # Maximum penalty if no data

        cpu_percent = volcano_metrics.get("cluster_cpu_percent", 0)
        memory_percent = volcano_metrics.get("cluster_memory_percent", 0)
        queue_jobs = volcano_metrics.get("queue_jobs", 0)

        # Weighted load calculation
        # CPU and Memory are primary factors (40% each)
        # Queue length is secondary (20%)
        cpu_load = min(cpu_percent, 100.0) * 0.4
        memory_load = min(memory_percent, 100.0) * 0.4
        queue_load = min(queue_jobs * 10, 100.0) * 0.2  # Each queued job adds 10 points

        total_load = cpu_load + memory_load + queue_load
        return min(total_load, 100.0)

    def _calculate_hpc_load_score(self, hpc_metrics: Dict) -> float:
        """Calculate HPC cluster load score using UNIFIED formula (0-100, lower is better)

        Uses the same formula as Volcano: CPU 40% + Memory 40% + Queue 20%
        """
        if not hpc_metrics or hpc_metrics.get("nodes_total", 0) == 0:
            return 100.0  # Maximum penalty if HPC unavailable

        # Get detailed CPU and Memory metrics (now available from enhanced exporter)
        cpu_utilization = hpc_metrics.get("cpu_utilization_percent", 0)
        memory_utilization = hpc_metrics.get("memory_utilization_percent", 0)
        jobs_pending = hpc_metrics.get("jobs_pending", 0)

        # UNIFIED FORMULA (same as Volcano): CPU 40% + Memory 40% + Queue 20%
        cpu_score = min(cpu_utilization, 100.0) * 0.4
        memory_score = min(memory_utilization, 100.0) * 0.4
        queue_score = (
            min(jobs_pending * 10, 100.0) * 0.2
        )  # Each pending job adds 10 points, max 100

        total_load = cpu_score + memory_score + queue_score
        return min(total_load, 100.0)

    def _get_load_details(self, volcano_metrics: Dict, hpc_metrics: Dict) -> List[str]:
        """Get detailed load information for reasoning"""
        details = []

        # Volcano details
        volcano_cpu = volcano_metrics.get("cluster_cpu_percent", 0)
        volcano_memory = volcano_metrics.get("cluster_memory_percent", 0)
        volcano_queue = volcano_metrics.get("queue_jobs", 0)

        details.append(
            f"Volcano: CPU {volcano_cpu:.1f}%, Memory {volcano_memory:.1f}%, Queue {volcano_queue}"
        )

        # HPC details
        hpc_util = hpc_metrics.get("utilization_percent", 0)
        hpc_pending = hpc_metrics.get("jobs_pending", 0)
        hpc_nodes_avail = hpc_metrics.get("nodes_available", 0)
        hpc_nodes_total = hpc_metrics.get("nodes_total", 0)

        details.append(
            f"HPC: Utilization {hpc_util:.1f}%, Pending {hpc_pending}, Available nodes {hpc_nodes_avail}/{hpc_nodes_total}"
        )

        return details

    async def get_cluster_status_summary(self) -> Dict:
        """Get a summary of all cluster statuses for monitoring"""
        metrics = await self.prometheus_client.get_all_scheduler_metrics()

        volcano = metrics.get("volcano", {})
        hpc = metrics.get("hpc", {})

        return {
            "timestamp": metrics["timestamp"],
            "volcano": {
                "status": "healthy" if volcano.get("cpu_cores", 0) > 0 else "unknown",
                "cluster_cpu_percent": volcano.get("cluster_cpu_percent", 0),
                "cluster_memory_percent": volcano.get("cluster_memory_percent", 0),
                "queue_jobs": volcano.get("queue_jobs", 0),
            },
            "hpc": {
                "status": "healthy" if hpc.get("nodes_total", 0) > 0 else "unavailable",
                "utilization_percent": hpc.get("utilization_percent", 0),
                "capacity_score": hpc.get("capacity_score", 0),
                "jobs_running": hpc.get("jobs_running", 0),
                "jobs_pending": hpc.get("jobs_pending", 0),
            },
        }
