import pytest

from strategies.round_robin import (calculate_throughput_from_allocations,
                                    schedule)


@pytest.fixture
def sample_jobs_list() -> list[dict]:
    return [
        {"task_id": "job1", "required_cpu": 1, "required_memory": 100},
        {"task_id": "job2", "required_cpu": 4, "required_memory": 400},
        {"task_id": "job3", "required_cpu": 1, "required_memory": 100},
        {"task_id": "job4", "required_cpu": 8, "required_memory": 800},
    ]


@pytest.fixture
def sample_nodes_list() -> list[dict]:
    # Node capacities (total, not available) are checked by round_robin
    return [
        {"node_id": "nodeA", "metrics_cpu_cores": 2, "metrics_mem_total_mb": 200},
        {"node_id": "nodeB", "metrics_cpu_cores": 4, "metrics_mem_total_mb": 500},
        {"node_id": "nodeC", "metrics_cpu_cores": 8, "metrics_mem_total_mb": 1000},
    ]


@pytest.fixture
def sample_nodes_list_one_small() -> list[dict]:
    return [{"node_id": "nodeX", "metrics_cpu_cores": 1, "metrics_mem_total_mb": 50}]


def test_round_robin_basic_allocation(sample_jobs_list, sample_nodes_list):
    allocations = schedule(sample_jobs_list, sample_nodes_list)
    # job1 (1c/100m) -> nodeA (2c/200m) - Fits
    # job2 (4c/400m) -> nodeB (4c/500m) - Fits
    # job3 (1c/100m) -> nodeC (8c/1000m) - Fits
    # job4 (8c/800m) -> nodeA (2c/200m) - Does NOT Fit
    assert allocations.get("job1") == "nodeA"
    assert allocations.get("job2") == "nodeB"
    assert allocations.get("job3") == "nodeC"
    assert allocations.get("job4") is None


def test_round_robin_throughput(sample_jobs_list, sample_nodes_list):
    allocations = schedule(sample_jobs_list, sample_nodes_list)
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list, sample_nodes_list
    )
    assert throughput == 3.0  # job1, job2, job3 allocated


def test_round_robin_no_jobs(sample_nodes_list):
    allocations = schedule([], sample_nodes_list)
    assert allocations == {}
    throughput = calculate_throughput_from_allocations(
        allocations, [], sample_nodes_list
    )
    assert throughput == 0.0


def test_round_robin_no_nodes(sample_jobs_list):
    allocations = schedule(sample_jobs_list, [])
    assert len(allocations) == len(sample_jobs_list)
    assert all(node is None for node in allocations.values())
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list, []
    )
    assert throughput == 0.0


def test_round_robin_no_fit(sample_jobs_list, sample_nodes_list_one_small):
    # Only one node, too small for most jobs
    allocations = schedule(sample_jobs_list, sample_nodes_list_one_small)
    # job1 (1c/100m) -> nodeX (1c/50m) - Does NOT fit Mem
    # job2 (4c/400m) -> nodeX (1c/50m) - Does NOT fit
    # job3 (1c/100m) -> nodeX (1c/50m) - Does NOT fit Mem
    # job4 (8c/800m) -> nodeX (1c/50m) - Does NOT fit
    assert len(allocations) == len(sample_jobs_list)
    assert all(node is None for node in allocations.values())
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list, sample_nodes_list_one_small
    )
    assert throughput == 0.0
