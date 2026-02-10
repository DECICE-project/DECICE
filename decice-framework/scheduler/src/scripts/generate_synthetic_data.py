import argparse
import datetime
import json
import logging
import random
import time
import uuid
from pathlib import Path
from typing import Any

from config.config import get_settings

logger = logging.getLogger(__name__)

# Job Archetypes: (cpu_range, mem_mb_range, gpu_options, storage_mb_range, time_limit_sec_range, system_hint)
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

# Node Archetypes: (cpu_cores_range, mem_total_gb_range, total_disk_gb_range, network_mbps_range, gpu_options, node_info_base)
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

# Util Profiles: (cpu_util_perc_range, mem_util_perc_range, disk_used_perc_range)
UTILIZATION_PROFILES = {
    "low": ((5, 25), (10, 30), (10, 40)),
    "medium": ((25, 65), (30, 70), (30, 70)),
    "high": ((65, 95), (70, 98), (60, 95)),
}
UTILIZATION_PROFILE_WEIGHTS = [0.4, 0.4, 0.2]


def get_random_timestamp(days_ago_max: int = 1, days_ago_min: int = 0) -> int:
    """Generates a random Unix timestamp."""
    now = datetime.datetime.now(datetime.timezone.utc)
    delta_seconds_max = days_ago_max * 24 * 60 * 60
    delta_seconds_min = days_ago_min * 24 * 60 * 60
    random_offset = random.randint(delta_seconds_min, delta_seconds_max)
    return int((now - datetime.timedelta(seconds=random_offset)).timestamp())


def generate_workload() -> dict[str, Any]:
    """Generates a single workload dict matching the Workload schema."""
    job_type_name = random.choices(
        list(JOB_ARCHETYPES.keys()), weights=JOB_TYPE_WEIGHTS, k=1
    )[0]
    (cpu_r, mem_mb_r, gpu_opts, sto_mb_r, time_r, sys_hint) = JOB_ARCHETYPES[
        job_type_name
    ]

    requirements = {
        "required_cpu": random.randint(cpu_r[0], cpu_r[1]),
        "required_memory": random.randint(mem_mb_r[0], mem_mb_r[1]),
        "required_gpu": random.choice(gpu_opts),
        # "required_storage_mb": random.randint(sto_mb_r[0], sto_mb_r[1]) # Uncomment when we add storage
    }
    return {
        "id": str(uuid.uuid4()),
        "requirements": requirements,
        "submission_time": get_random_timestamp(),
        "time_limit": random.randint(time_r[0], time_r[1]),
        "system": sys_hint if random.random() < 0.5 else None,
    }


def generate_node(node_idx: int) -> dict[str, Any]:
    """Generates a single node dict matching the Node schema."""
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

    total_disk = float(random.randint(disk_gb_r[0], disk_gb_r[1]))
    disk_used_perc = random.uniform(disk_util_r[0], disk_util_r[1]) / 100.0

    metrics = {
        "util": round(random.uniform(cpu_util_r[0], cpu_util_r[1]), 2),  # 0-100
        "mem_util": round(random.uniform(mem_util_r[0], mem_util_r[1]), 2),  # 0-100
        "network_bandwidth_mbps": float(random.randint(net_r[0], net_r[1])),
        "cpu_cores": float(random.randint(cpu_r[0], cpu_r[1])),
        "mem_total": float(random.randint(mem_gb_r[0], mem_gb_r[1])),  # In GB
        "total_disk_gb": total_disk,
        "free_disk_gb": round(total_disk * (1.0 - disk_used_perc), 1),
        "power_watts": (
            round(random.uniform(50, 400), 1) if random.random() < 0.7 else None
        ),
    }
    node_info = info_base.copy()
    node_info["gpu_model"] = random.choice(gpu_opts)

    return {
        "id": f"{node_type_name}-{node_idx:02d}",  # Readable ID
        "name": f"{node_type_name}-{node_idx:02d}.cluster.local",
        "system": info_base.get("location", "default_system"),
        "node_info": node_info,
        "metrics": metrics,
    }


def generate_scenario_data(
    num_jobs_range, num_nodes_range, num_pools
) -> dict[str, Any]:
    """Generates a dict matching the ScheduleRequest schema."""
    num_jobs = random.randint(num_jobs_range[0], num_jobs_range[1])
    num_nodes = random.randint(num_nodes_range[0], num_nodes_range[1])

    workloads = [generate_workload() for _ in range(num_jobs)]
    nodes = [generate_node(i) for i in range(num_nodes)]

    # Distribute nodes into pools
    pools = []
    pool_ids = []
    if num_nodes > 0:
        actual_num_pools = min(num_pools, num_nodes)
        nodes_per_pool = num_nodes // actual_num_pools
        remainder = num_nodes % actual_num_pools
        start_idx = 0
        for i in range(actual_num_pools):
            pool_id = f"pool-{i + 1}"
            pool_ids.append(pool_id)
            count = nodes_per_pool + (1 if i < remainder else 0)
            end_idx = start_idx + count
            pool_nodes = nodes[start_idx:end_idx]
            start_idx = end_idx
            pools.append(
                {
                    "id": pool_id,
                    "vertexpool_labels": {
                        "region": random.choice(["east", "west", "central"])
                    },
                    "nodes": pool_nodes,
                }
            )

    # Create links
    links = []
    if len(pool_ids) > 1:
        for p1 in pool_ids:
            for p2 in pool_ids:
                delay = 0.5 if p1 == p2 else round(random.uniform(2.0, 20.0), 1)
                links.append(
                    {
                        "vertexpool_a_id": p1,
                        "vertexpool_b_id": p2,
                        "network_delay_ms": delay,
                    }
                )

    cluster_state = {"lastUpdated": time.time(), "vertexpools": pools, "links": links}
    return {"workloads": workloads, "cluster": cluster_state}


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic ScheduleRequest scenarios."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/scenarios/training",
        help="Directory to save JSON files.",
    )
    parser.add_argument(
        "--num_files", type=int, default=10, help="Number of files to generate."
    )
    parser.add_argument("--jobs_min", type=int, default=1, help="Min jobs per file.")
    parser.add_argument("--jobs_max", type=int, default=20, help="Max jobs per file.")
    parser.add_argument("--nodes_min", type=int, default=2, help="Min nodes per file.")
    parser.add_argument("--nodes_max", type=int, default=50, help="Max nodes per file.")
    parser.add_argument(
        "--pools", type=int, default=2, help="Number of vertex pools to create."
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=settings.LOG_LEVEL.value,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating {args.num_files} scenario files into {output_path}...")
    for i in range(args.num_files):
        scenario_data = generate_scenario_data(
            (args.jobs_min, args.jobs_max), (args.nodes_min, args.nodes_max), args.pools
        )
        file_name = output_path / f"scenario_{i + 1:03d}_{get_random_timestamp()}.json"
        try:
            with open(file_name, "w") as f:
                json.dump(scenario_data, f, indent=2)
            logger.info(
                f"Generated {file_name} with {len(scenario_data['workloads'])} workloads and {len(scenario_data['cluster']['vertexpools'])} pools."
            )
        except Exception as e:
            logger.error(f"Failed to write scenario {file_name}: {e}", exc_info=True)
    logger.info("Data generation complete.")


if __name__ == "__main__":
    main()
