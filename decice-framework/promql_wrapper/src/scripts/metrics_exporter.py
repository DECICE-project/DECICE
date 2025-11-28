import json
import logging
import random
import sys
import time
from typing import Union

from prometheus_client import Gauge, start_http_server

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


NODE_UNAME_INFO = Gauge(
    "node_uname_info", "Mocked node information for joins", ["nodename", "pod"]
)
NODE_CPU_SECONDS_TOTAL = Gauge(
    "node_cpu_seconds_total",
    "Mocked total CPU seconds by mode",
    ["nodename", "mode", "pod"],
)
NODE_NODE_NUM_CPU_SUM = Gauge(
    "node:node_num_cpu:sum", "Mocked number of CPU cores", ["node", "pod"]
)
NODE_MEMORY_MEMTOTAL_BYTES = Gauge(
    "node_memory_MemTotal_bytes", "Mocked total memory in bytes", ["nodename", "pod"]
)
NODE_MEMORY_MEMFREE_BYTES = Gauge(
    "node_memory_MemFree_bytes", "Mocked free memory in bytes", ["nodename", "pod"]
)
NODE_MEMORY_CACHED_BYTES = Gauge(
    "node_memory_Cached_bytes", "Mocked cached memory in bytes", ["nodename", "pod"]
)
NODE_MEMORY_BUFFERS_BYTES = Gauge(
    "node_memory_Buffers_bytes", "Mocked buffer memory in bytes", ["nodename", "pod"]
)
NODE_NETWORK_RECEIVE_BYTES_TOTAL = Gauge(
    "node_network_receive_bytes_total",
    "Mocked total network received bytes",
    ["nodename", "device", "pod"],
)
NODE_FILESYSTEM_SIZE_BYTES = Gauge(
    "node_filesystem_size_bytes",
    "Mocked total filesystem size",
    ["nodename", "mountpoint", "pod"],
)
NODE_FILESYSTEM_AVAIL_BYTES = Gauge(
    "node_filesystem_avail_bytes",
    "Mocked available filesystem size",
    ["nodename", "mountpoint", "pod"],
)
NODE_POWER_WATTS = Gauge(
    "node_power_watts", "Mocked power consumption in watts", ["nodename", "pod"]
)
DECICE_NODE_INFO = Gauge(
    "decice_node_info", "Mocked static info about a node", ["nodename", "vertexpool_id"]
)
DECICE_VERTEXPOOL_LABELS = Gauge(
    "decice_vertexpool_labels",
    "Mocked labels for a vertexpool",
    ["vertexpool_id", "vertexpool_labels"],
)
DECICE_PING_LATENCY_MS = Gauge(
    "decice_ping_latency_ms",
    "Mocked network latency",
    ["nodename", "target_name", "target_type", "target_device_id"],
)
DECICE_DEVICE_INFO = Gauge(
    "decice_device_info",
    "Mocked static info about a device",
    ["device_id", "vertexpool_id"],
)
DECICE_DEVICE_LABELS = Gauge(
    "decice_device_labels", "Mocked labels for a device", ["device_id", "device_labels"]
)


def load_simulation_config(filepath: str):
    """Loads the JSON file that defines the cluster simulation."""
    log.info(f"Loading simulation config from {filepath}")
    with open(filepath, "r") as f:
        return json.load(f)


def _get_value(
    metric_entry: Union[float, int, dict, None], default: float = 0.0
) -> float:
    """
    Helper to extract a scalar value from the config, handling both direct values
    and dictionary distributions (mean/stdev).
    """
    if metric_entry is None:
        return default

    if isinstance(metric_entry, (int, float)):
        return float(metric_entry)

    if isinstance(metric_entry, dict):
        mean = float(metric_entry.get("mean", default))
        stdev = float(metric_entry.get("stdev", 0.0))
        if stdev > 0:
            # Generate a random value based on normal distribution
            return random.normalvariate(mean, stdev)
        return mean

    return default


def update_metrics(config: dict):
    """Updates all Prometheus gauges to mimic a real node-exporter label structure."""
    log.debug("Updating metrics...")

    vp_map = {vp.get("id"): vp for vp in config.get("vertexpools", [])}

    for vp_id, vp in vp_map.items():
        labels_json = json.dumps(vp.get("vertexpool_labels"))
        # --------------------------------------------------

        DECICE_VERTEXPOOL_LABELS.labels(
            vertexpool_id=vp_id, vertexpool_labels=labels_json
        ).set(1)

        for node in vp.get("nodes", []):
            nodename = node.get("name")
            metrics = node.get("metrics", {})
            mock_pod_name = f"node-exporter-{nodename}-xyz"

            NODE_UNAME_INFO.labels(nodename=nodename, pod=mock_pod_name).set(1)
            DECICE_NODE_INFO.labels(nodename=nodename, vertexpool_id=vp_id).set(1)

            cpu_util = _get_value(metrics.get("util"), default=random.uniform(5, 15))
            cpu_util = max(0.0, min(100.0, cpu_util))

            mem_util_percent = _get_value(
                metrics.get("mem_util"), default=random.uniform(10, 20)
            )
            mem_util_percent = max(0.0, min(100.0, mem_util_percent))

            cpu_cores = _get_value(metrics.get("cpu_cores"), default=0)
            mem_total_mb = _get_value(
                metrics.get("mem_total"), default=0
            )  # JSON is in MB
            total_disk_gb = _get_value(metrics.get("total_disk_gb"), default=0)
            free_disk_gb = _get_value(metrics.get("free_disk_gb"), default=0)
            bw_mbps = _get_value(metrics.get("network_bandwidth_mbps"), default=0)
            power_watts = _get_value(metrics.get("power_watts"), default=0)
            power_factor = _get_value(metrics.get("power_factor"), default=1.0)

            current_idle_time = (100 - cpu_util) / 100 * time.time()
            NODE_CPU_SECONDS_TOTAL.labels(
                nodename=nodename, mode="idle", pod=mock_pod_name
            ).set(current_idle_time)
            NODE_CPU_SECONDS_TOTAL.labels(
                nodename=nodename, mode="user", pod=mock_pod_name
            ).set(0)

            NODE_NODE_NUM_CPU_SUM.labels(node=nodename, pod=mock_pod_name).set(
                cpu_cores
            )

            mem_total_bytes = mem_total_mb * (1024 * 1024)
            mem_used_bytes = mem_total_bytes * (mem_util_percent / 100)
            mem_free_bytes = mem_total_bytes - mem_used_bytes

            NODE_MEMORY_MEMTOTAL_BYTES.labels(nodename=nodename, pod=mock_pod_name).set(
                mem_total_bytes
            )
            NODE_MEMORY_MEMFREE_BYTES.labels(nodename=nodename, pod=mock_pod_name).set(
                mem_free_bytes
            )
            NODE_MEMORY_CACHED_BYTES.labels(nodename=nodename, pod=mock_pod_name).set(0)
            NODE_MEMORY_BUFFERS_BYTES.labels(nodename=nodename, pod=mock_pod_name).set(
                0
            )

            current_total_bytes = ((bw_mbps * 1024 * 1024) / 8) * time.time()
            NODE_NETWORK_RECEIVE_BYTES_TOTAL.labels(
                nodename=nodename, device="eth0", pod=mock_pod_name
            ).set(current_total_bytes)

            NODE_FILESYSTEM_SIZE_BYTES.labels(
                nodename=nodename, mountpoint="/", pod=mock_pod_name
            ).set(total_disk_gb * (1000**3))
            NODE_FILESYSTEM_AVAIL_BYTES.labels(
                nodename=nodename, mountpoint="/", pod=mock_pod_name
            ).set(free_disk_gb * (1000**3))

            if power_watts > 0:
                simulated_power = power_watts
            else:
                simulated_power = max(20.0 + (cpu_util * power_factor), 10.0)

            NODE_POWER_WATTS.labels(nodename=nodename, pod=mock_pod_name).set(
                simulated_power
            )

        for device in vp.get("devices", []):
            DECICE_DEVICE_INFO.labels(
                device_id=device.get("id"), vertexpool_id=vp_id
            ).set(1)
            DECICE_DEVICE_LABELS.labels(
                device_id=device.get("id"),
                device_labels=json.dumps(device.get("labels")),
            ).set(1)

    for link in config.get("links", []):
        vp_a_id = link.get("vertexpool_a_id")
        vp_b_id = link.get("vertexpool_b_id")

        delay = _get_value(link.get("network_delay_ms"), default=10.0)

        source_vp = vp_map.get(vp_a_id)
        if not source_vp or not source_vp.get("nodes"):
            continue
        source_node_name = source_vp.get("nodes")[0].get("name")

        target_vp = vp_map.get(vp_b_id)
        if not target_vp or not target_vp.get("nodes"):
            continue
        target_node_name = target_vp.get("nodes")[0].get("name")

        DECICE_PING_LATENCY_MS.labels(
            nodename=source_node_name,
            target_name=target_node_name,
            target_type="node",
            target_device_id="",
        ).set(delay)

    log.debug("Metrics updated.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        log.error("Usage: python metrics_exporter.py <path_to_simulation.json>")
        sys.exit(1)

    sim_path = sys.argv[1]

    try:
        config = load_simulation_config(sim_path)
    except FileNotFoundError:
        log.error(f"Simulation file not found at: {sim_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        log.error(f"Could not parse JSON from file: {sim_path}")
        sys.exit(1)

    start_http_server(8001)
    log.info("Metrics exporter running on http://localhost:8001")

    while True:
        try:
            update_metrics(config)
            time.sleep(15)
        except KeyboardInterrupt:
            log.info("Shutting down metrics exporter.")
            sys.exit(0)
        except Exception:
            log.exception("An error occurred during metrics update loop.")
            time.sleep(15)
