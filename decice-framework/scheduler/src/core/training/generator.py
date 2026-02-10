import datetime
import json
import logging
import random
import time
import uuid
from pathlib import Path
from typing import Any, Tuple

logger = logging.getLogger(__name__)

# Reusing the constants from your original script
JOB_ARCHETYPES = {
    "cpu_heavy": (
        (8, 64),
        (4096, 32768),
        [None],
        (10240, 102400),
        (1800, 14400),
        "HPC",
    ),
    "mem_heavy": (
        (2, 16),
        (65536, 262144),
        [None],
        (51200, 204800),
        (3600, 28800),
        "BigMem",
    ),
    "gpu_job": (
        (4, 32),
        (16384, 131072),
        ["nvidia-a100", "nvidia-h100"],
        (20480, 102400),
        (1800, 10800),
        "GPU",
    ),
    "small_short": (
        (1, 2),
        (1024, 4096),
        [None],
        (1024, 10240),
        (300, 1800),
        "Interactive",
    ),
    "balanced": (
        (2, 8),
        (8192, 65536),
        [None, "nvidia-t4"],
        (10240, 51200),
        (3600, 14400),
        "General",
    ),
}
JOB_TYPE_WEIGHTS = [0.25, 0.20, 0.25, 0.15, 0.15]

NODE_ARCHETYPES = {
    "compute_node": (
        (16, 64),
        (64, 256),
        (512, 2048),
        (1000, 10000),
        [None],
        {"location": "DC1"},
    ),
    "gpu_node": (
        (32, 96),
        (128, 512),
        (1024, 4096),
        (10000, 40000),
        ["nvidia-a100", "nvidia-h100"],
        {"location": "DC1", "rack": "G1"},
    ),
    "edge_node": (
        (2, 8),
        (8, 32),
        (128, 512),
        (100, 1000),
        [None],
        {"location": "Edge-Site-A"},
    ),
}
NODE_TYPE_WEIGHTS = [0.5, 0.3, 0.2]

UTILIZATION_PROFILES = {
    "low": ((5, 25), (10, 30), (10, 40)),
    "medium": ((25, 65), (30, 70), (30, 70)),
    "high": ((65, 95), (70, 98), (60, 95)),
}
UTILIZATION_PROFILE_WEIGHTS = [0.4, 0.4, 0.2]


class ScenarioGenerator:
    """
    Encapsulates logic for generating synthetic scheduling scenarios.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _get_random_timestamp(
        self, days_ago_max: int = 1, days_ago_min: int = 0
    ) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        delta_seconds_max = days_ago_max * 24 * 60 * 60
        delta_seconds_min = days_ago_min * 24 * 60 * 60
        random_offset = random.randint(delta_seconds_min, delta_seconds_max)
        return int((now - datetime.timedelta(seconds=random_offset)).timestamp())

    def _generate_workload(self) -> dict[str, Any]:
        job_type_name = random.choices(
            list(JOB_ARCHETYPES.keys()), weights=JOB_TYPE_WEIGHTS, k=1
        )[0]
        (cpu_r, mem_mb_r, gpu_opts, sto_mb_r, time_r, sys_hint) = JOB_ARCHETYPES[
            job_type_name
        ]

        requirements = {
            "required_cpu": random.randint(*cpu_r),
            "required_memory": random.randint(*mem_mb_r),
            "required_gpu": random.choice(gpu_opts),
        }
        return {
            "id": str(uuid.uuid4()),
            "requirements": requirements,
            "submission_time": self._get_random_timestamp(),
            "time_limit": random.randint(*time_r),
            "system": sys_hint if random.random() < 0.5 else None,
        }

    def _generate_node(self, node_idx: int) -> dict[str, Any]:
        node_type_name = random.choices(
            list(NODE_ARCHETYPES.keys()), weights=NODE_TYPE_WEIGHTS, k=1
        )[0]
        (cpu_r, mem_gb_r, disk_gb_r, net_r, gpu_opts, info_base) = NODE_ARCHETYPES[
            node_type_name
        ]

        util_profile_name = random.choices(
            list(UTILIZATION_PROFILES.keys()), weights=UTILIZATION_PROFILE_WEIGHTS, k=1
        )[0]
        (cpu_util_r, mem_util_r, disk_util_r) = UTILIZATION_PROFILES[util_profile_name]

        total_disk = float(random.randint(*disk_gb_r))
        disk_used_perc = random.uniform(*disk_util_r) / 100.0

        metrics = {
            "util": round(random.uniform(*cpu_util_r), 2),
            "mem_util": round(random.uniform(*mem_util_r), 2),
            "network_bandwidth_mbps": float(random.randint(*net_r)),
            "cpu_cores": float(random.randint(*cpu_r)),
            "mem_total": float(random.randint(*mem_gb_r)),
            "total_disk_gb": total_disk,
            "free_disk_gb": round(total_disk * (1.0 - disk_used_perc), 1),
            "power_watts": (
                round(random.uniform(50, 400), 1) if random.random() < 0.7 else None
            ),
        }
        node_info = info_base.copy()
        node_info["gpu_model"] = random.choice(gpu_opts)

        return {
            "id": f"{node_type_name}-{node_idx:02d}",
            "name": f"{node_type_name}-{node_idx:02d}.cluster.local",
            "system": info_base.get("location", "default_system"),
            "node_info": node_info,
            "metrics": metrics,
        }

    def generate_batch(
        self,
        num_files: int,
        job_range: Tuple[int, int],
        node_range: Tuple[int, int] = (10, 50),
    ) -> int:
        """Generates a batch of JSON scenario files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generated_count = 0

        for i in range(num_files):
            num_jobs = random.randint(*job_range)
            num_nodes = random.randint(*node_range)
            num_pools = min(3, num_nodes)

            workloads = [self._generate_workload() for _ in range(num_jobs)]
            nodes = [self._generate_node(n) for n in range(num_nodes)]

            # Pools and Links logic (simplified for brevity)
            pools = [
                {"id": f"pool-{p + 1}", "nodes": [], "vertexpool_labels": {}}
                for p in range(num_pools)
            ]
            for idx, node in enumerate(nodes):
                pools[idx % num_pools]["nodes"].append(node)

            links = []  # (Add link generation logic if needed)

            data = {
                "workloads": workloads,  # Map to 'tasks' in Schemas if needed, using generic generator keys here
                "tasks": workloads,  # Dual compatibility for now
                "cluster": {
                    "lastUpdated": time.time(),
                    "vertexpools": pools,
                    "links": links,
                },
            }

            filename = self.output_dir / f"synthetic_{i}_{int(time.time())}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            generated_count += 1

        return generated_count
