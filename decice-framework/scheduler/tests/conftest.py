from uuid import uuid4

import pytest

from core.schemas import (
    ClusterState,
    HardwareRequirements,
    Link,
    Node,
    NodeInfo,
    NodeMetrics,
    ScheduleRequest,
    Task,
    VertexPool,
)


@pytest.fixture
def sample_hardware_requirements() -> HardwareRequirements:
    """Basic hardware requirements."""
    return HardwareRequirements(required_cpu=2, required_memory=4096, required_gpu=None)


@pytest.fixture
def sample_workload(sample_hardware_requirements) -> Task:
    """A sample Task object."""
    return Task(id=uuid4(), requirements=sample_hardware_requirements)


@pytest.fixture
def sample_node_metrics_low_util() -> NodeMetrics:
    """Node metrics with low utilization."""
    return NodeMetrics(
        util=10.5,
        mem_util=20.0,
        network_bandwidth_mbps=1000.0,
        free_disk_gb=800.0,
        total_disk_gb=1000.0,
        cpu_cores=16.0,
        mem_total=64.0,
        power_watts=100.0,
    )


@pytest.fixture
def sample_node_metrics_high_util() -> NodeMetrics:
    """Node metrics with high utilization."""
    return NodeMetrics(
        util=95.0,
        mem_util=90.0,
        network_bandwidth_mbps=1000.0,
        free_disk_gb=100.0,
        total_disk_gb=1000.0,
        cpu_cores=16.0,
        mem_total=64.0,
        power_watts=250.0,
    )


@pytest.fixture
def sample_node_low_util(sample_node_metrics_low_util) -> Node:
    """A sample Node object with low utilization."""
    return Node(
        id="node-low-util-1",
        name="node-low-util-1.example.com",
        node_info=NodeInfo(location="DC1", rack="R2"),
        metrics=sample_node_metrics_low_util,
    )


@pytest.fixture
def sample_node_high_util(sample_node_metrics_high_util) -> Node:
    """A sample Node object with high utilization."""
    return Node(
        id="node-high-util-1",
        name="node-high-util-1.example.com",
        node_info=NodeInfo(location="DC1", rack="R3", gpu_model="nvidia-a100"),
        metrics=sample_node_metrics_high_util,
    )


@pytest.fixture
def sample_vertex_pool(sample_node_low_util, sample_node_high_util) -> VertexPool:
    """A sample VertexPool containing two nodes."""
    return VertexPool(
        id="pool-a",
        vertexpool_labels={"type": "compute", "region": "us-east"},
        nodes=[sample_node_low_util, sample_node_high_util],
    )


@pytest.fixture
def sample_cluster_state(sample_vertex_pool) -> ClusterState:
    """A sample ClusterState with one pool and basic links."""
    # Add another pool for link testing if needed
    pool_b_nodes = [
        Node(
            id="node-b1", name="node-b1", metrics=NodeMetrics(cpu_cores=8, mem_total=32)
        )
    ]  # Minimal node
    pool_b = VertexPool(
        id="pool-b", vertexpool_labels={"type": "storage"}, nodes=pool_b_nodes
    )

    links = [
        Link(vertexpool_a_id="pool-a", vertexpool_b_id="pool-b", network_delay_ms=5.2),
        Link(vertexpool_a_id="pool-b", vertexpool_b_id="pool-a", network_delay_ms=5.1),
        Link(
            vertexpool_a_id="pool-a", vertexpool_b_id="pool-a", network_delay_ms=0.5
        ),  # Self-link
    ]
    return ClusterState(
        lastUpdated=1700000000.0, vertexpools=[sample_vertex_pool, pool_b], links=links
    )


@pytest.fixture
def sample_schedule_request(sample_workload, sample_cluster_state) -> ScheduleRequest:
    """A complete sample ScheduleRequest."""
    workload2_req = HardwareRequirements(
        required_cpu=8, required_memory=32768, required_gpu="nvidia-a100"
    )
    workload2 = Task(id=uuid4(), requirements=workload2_req)

    return ScheduleRequest(
        tasks=[sample_workload, workload2],
        cluster=sample_cluster_state,
    )
