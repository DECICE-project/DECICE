import pytest

from strategies.load_based_scheduling import (
    calculate_throughput_from_allocations, schedule)


@pytest.fixture
def sample_jobs_list_lbs() -> list[dict]:
    return [
        {"task_id": "jobA", "required_cpu": 1, "required_memory": 100},
        {"task_id": "jobB", "required_cpu": 2, "required_memory": 200},
        {"task_id": "jobC", "required_cpu": 1, "required_memory": 50},
    ]


@pytest.fixture
def sample_nodes_list_lbs() -> list[dict]:
    # Nodes with varying utilization
    return [
        # Node 1: High util, high capacity
        {
            "node_id": "node1",
            "metrics_cpu_cores": 8,
            "metrics_mem_total_mb": 800,
            "metrics_cpu_util": 80.0,
            "metrics_mem_util": 70.0,
        },  # Load = 150
        # Node 2: Low util, low capacity
        {
            "node_id": "node2",
            "metrics_cpu_cores": 2,
            "metrics_mem_total_mb": 200,
            "metrics_cpu_util": 10.0,
            "metrics_mem_util": 20.0,
        },  # Load = 30
        # Node 3: Med util, med capacity
        {
            "node_id": "node3",
            "metrics_cpu_cores": 4,
            "metrics_mem_total_mb": 400,
            "metrics_cpu_util": 40.0,
            "metrics_mem_util": 50.0,
        },  # Load = 90
    ]


@pytest.fixture
def sample_nodes_list_lbs_nofit() -> list[dict]:
    # All nodes too small for jobB
    return [
        {
            "node_id": "nodeS1",
            "metrics_cpu_cores": 1,
            "metrics_mem_total_mb": 100,
            "metrics_cpu_util": 10.0,
            "metrics_mem_util": 10.0,
        },
        {
            "node_id": "nodeS2",
            "metrics_cpu_cores": 1,
            "metrics_mem_total_mb": 150,
            "metrics_cpu_util": 20.0,
            "metrics_mem_util": 20.0,
        },
    ]


def test_lbs_basic_allocation(sample_jobs_list_lbs, sample_nodes_list_lbs):
    allocations = schedule(sample_jobs_list_lbs, sample_nodes_list_lbs)
    # jobA (1c/100m): Fits all. Node2 has lowest load (30). Assign to Node2.
    # jobB (2c/200m): Fits Node1 (8/800), Node3 (4/400). Node2 (2/200) JUST fits.
    #   Load scores: Node1=150, Node2=30, Node3=90. Node2 is still lowest load *and* fits. Assign to Node2.
    # jobC (1c/50m): Fits all. Node1=150, Node2=30 (already assigned A&B, but LBS checks initial load), Node3=90. Node2 still has lowest *initial* load and fits capacity. Assign to Node2.
    # Note: LBS doesn't update load dynamically in this simple version, it picks based on initial state.
    assert allocations.get("jobA") == "node2"
    assert allocations.get("jobB") == "node2"
    assert allocations.get("jobC") == "node2"


def test_lbs_throughput(sample_jobs_list_lbs, sample_nodes_list_lbs):
    allocations = schedule(sample_jobs_list_lbs, sample_nodes_list_lbs)
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list_lbs, sample_nodes_list_lbs
    )
    assert throughput == 3.0  # All jobs should be allocated


def test_lbs_no_jobs(sample_nodes_list_lbs):
    allocations = schedule([], sample_nodes_list_lbs)
    assert allocations == {}
    throughput = calculate_throughput_from_allocations(
        allocations, [], sample_nodes_list_lbs
    )
    assert throughput == 0.0


def test_lbs_no_nodes(sample_jobs_list_lbs):
    allocations = schedule(sample_jobs_list_lbs, [])
    assert len(allocations) == len(sample_jobs_list_lbs)
    assert all(node is None for node in allocations.values())
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list_lbs, []
    )
    assert throughput == 0.0


def test_lbs_no_fit(sample_jobs_list_lbs, sample_nodes_list_lbs_nofit):
    allocations = schedule(sample_jobs_list_lbs, sample_nodes_list_lbs_nofit)
    # jobA (1c/100m) -> Fits S1(1/100), Fits S2(1/150). S1 load = 20, S2 load = 40. Assign to S1.
    # jobB (2c/200m) -> No node fits total capacity. Unallocated.
    # jobC (1c/50m) -> Fits S1(1/100), Fits S2(1/150). S1 load = 20, S2 load = 40. Assign to S1.
    assert allocations.get("jobA") == "nodeS1"
    assert allocations.get("jobB") is None
    assert allocations.get("jobC") == "nodeS1"
    throughput = calculate_throughput_from_allocations(
        allocations, sample_jobs_list_lbs, sample_nodes_list_lbs_nofit
    )
    assert throughput == 2.0
