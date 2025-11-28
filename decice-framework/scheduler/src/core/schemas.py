from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

# Type Aliases
LatencyMatrix = dict[str, dict[str, float]]


# Core Data Structures
class HardwareRequirements(BaseModel):
    """Hardware requirements for a workflow task."""

    required_cpu: int
    required_memory: int
    required_gpu: Optional[str] = None
    # required_storage_mb: Optional[int] = Field(None, ge=0)


class Task(BaseModel):
    """Represents a single unit of work to be scheduled."""

    id: UUID
    requirements: HardwareRequirements
    # submission_time: Optional[int] = None
    # time_limit: Optional[int] = None
    # system: Optional[str] = None

    @field_serializer("id")
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


# TODO: not needed right now
class NodeInfo(BaseModel):
    """Static or semi-static information about a node."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # location: Optional[str] = None
    # rack: Optional[str] = None
    # architecture: Optional[str] = None
    # gpu_model: Optional[str] = None


class NodeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    util: Optional[float] = Field(None, ge=0.0, le=100.0)
    mem_util: Optional[float] = Field(None, ge=0.0, le=100.0)
    network_bandwidth_mbps: Optional[float] = None
    free_disk_gb: Optional[float] = None
    total_disk_gb: Optional[float] = None
    cpu_cores: Optional[float] = Field(None, ge=0.0)
    mem_total: Optional[float] = Field(None, ge=0.0)
    power_watts: Optional[float] = Field(None, ge=0.0)


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    name: Optional[str] = None
    system: Optional[str] = None
    node_info: Optional[NodeInfo] = Field(
        {}, description="Additional information about the node"
    )
    metrics: Optional[NodeMetrics] = Field(
        None,
        description="Various metrics fields for the current node.",
        title="Metrics",
    )


class Device(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    name: Optional[str] = None
    labels: Optional[dict[str, Any]] = Field(
        None, description="Labels that applies to this device."
    )
    device_info: Optional[dict[str, Any]] = Field(
        {}, description="Additional information about the device"
    )


class VertexPool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    vertexpool_labels: Optional[dict[str, Any]] = Field(
        None, description="Additional information about the node"
    )
    nodes: Optional[list[Node]] = Field(
        [], description="Array of nodes within a vertexpool"
    )
    devices: Optional[list[Device]] = Field(
        [], description="Array of devices within this Vertexpool"
    )
    lastUpdated: Optional[float] = Field(
        None, description="When was this data last updated, in epoch time .", ge=0.0
    )


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vertexpool_a_id: Optional[str] = Field(
        None, description="id of the first vertexpool."
    )
    vertexpool_b_id: Optional[str] = Field(
        None, description="id of the second vertexpool."
    )
    network_delay_ms: Optional[float] = Field(
        None,
        description="Network delay of Link in milliseconds between two vertexpools",
    )
    lastUpdated: Optional[float] = Field(
        None, description="When was this data last updated, in epoch time .", ge=0.0
    )


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_labels: Optional[list[str]] = Field(
        [],
        description="Labels that must be set on nodes or vertexpools for this pod to schedule on them.",
    )
    rejected_labels: Optional[list[str]] = Field(
        [],
        description="Labels that must not be set on nodes or vertexpools for this pod to schedule on them.",
    )
    prefered_labels: Optional[list[str]] = Field(
        [],
        description="Labels that should be set on nodes or vertexpools for this pod to schedule on them.",
    )
    retracted_labels: Optional[list[str]] = Field(
        [],
        description="Labels that should not be set on nodes or vertexpools for this pod to schedule on them.",
    )


class Pod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = Field(None, description="Pods id")
    name: Optional[str] = Field(None, description="Pods name")
    scheduled: Optional[bool] = Field(
        None, description="True if pod is scheduled else False"
    )
    restarts: Optional[int] = Field(
        None, description="How many times this pod is restarted"
    )
    running_since: Optional[str] = Field(
        None, description="Timestamp of pod's uninterrupted runtime"
    )
    status: Optional[str] = Field(None, description="Status of the pod")
    namespace: Optional[str] = Field(None, description="Namespace of the pod")
    info: Optional[dict[str, Any]] = Field(
        None, description="Additional information about the pod"
    )
    policies: Optional[list[Policy]] = Field(
        [],
        description="Policies that determine what labels to consider when scheduling this pod.",
    )
    node_id: Optional[str] = Field(
        None, description="Node id that this Pod is hosted in"
    )
    nodename: Optional[str] = Field(
        None, description="Pods nodename , if it is assigned to one"
    )
    job_id: Optional[str] = Field(None, description="Pods job id")


class Weight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models_name: Optional[str] = None
    models_weight: Optional[float] = Field(None, ge=0.0, le=100.0)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    weights: Optional[list[Weight]] = Field(
        [],
        description="Weights to calculate the final score for a node from the model scores.",
    )


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    pods: Optional[list[Pod]] = Field(
        [], description="Pods that may run on the cluster."
    )
    profile: Optional[Profile] = Field(
        None, description="Represents a weighting of model scores.", title="Profile"
    )
    lastUpdated: Optional[float] = Field(
        None, description="When was this data last updated, in epoch time .", ge=0.0
    )


class ClusterState(BaseModel):
    lastUpdated: Optional[float] = Field(
        None, description="When was this data last updated, in epoch time .", ge=0.0
    )
    vertexpools: Optional[list[VertexPool]] = Field(
        [], description="Array of Vertexpools in the cluster."
    )
    links: Optional[list[Link]] = Field(
        [], description="Links that connect two vertexpools"
    )
    jobs: Optional[list[Job]] = Field(
        [], description="Jobs that may run on the cluster"
    )
    cluster_info: Optional[dict[str, Any]] = Field(
        {}, description="Optional additional information about the cluster"
    )


class ScheduleRequest(BaseModel):
    """The structure of the incoming API request for scheduling."""

    tasks: list[Task]
    cluster: ClusterState


# API Response Schemas
class TaskPlacement(BaseModel):
    """Placement decision for a single workflow task."""

    task_id: UUID = Field(
        description="The UUID of the workflow task that was processed."
    )
    target_node_ids: list[str] = Field(
        description="An array of node IDs relevant for placing the workflow task (e.g., the allocated node ID)."
    )
    # Adding strategy for context might be useful
    strategy_used: Optional[str] = Field(
        None, description="The scheduling strategy chosen for this request."
    )


class ScheduleResponse(BaseModel):
    """The structure of the API response after scheduling."""

    placements: list[TaskPlacement] = Field(
        description="A list of workflow tasks placement details."
    )
    scheduling_duration_ms: Optional[float] = Field(
        None,
        description="Time taken for the scheduling strategy execution in milliseconds.",
    )


# Training Schemas
class SchedulerDefinition(BaseModel):
    """Defines the architecture and hyperparameters of a Scheduler."""

    name: str = Field(
        ..., description="Unique identifier for this model (e.g., 'ppo_v2_aggressive')"
    )
    description: Optional[str] = None

    # Hyperparameters (Immutable for the life of the model instance)
    actor_lr: float = 0.0003
    critic_lr: float = 0.001
    gamma: float = 0.99
    gae_lambda: float = 0.95
    policy_clip: float = 0.2
    entropy_coefficient: float = 0.01
    ppo_batch_size: int = 64

    # Architecture
    hidden_layer_size: int = 128  # Example of future-proofing


class TrainingConfig(BaseModel):
    scheduler_name: str
    cycles: int = 10
    episodes_per_cycle: int = 50

    actor_lr: Optional[float] = None
    critic_lr: Optional[float] = None
    gamma: Optional[float] = None
    gae_lambda: Optional[float] = None
    policy_clip: Optional[float] = None
    entropy_coefficient: Optional[float] = None
    epochs_per_update: Optional[int] = None
    batch_size: Optional[int] = None


class TrainingRunRequest(BaseModel):
    """Parameters for a specific training session."""

    scheduler_name: str = Field(
        ..., description="Name of the existing scheduler to train."
    )
    dataset_name: str = Field(
        ..., description="Name of the dataset to use for this run."
    )

    cycles: int = Field(10, description="How many cycles (Simulate -> Train) to run.")
    episodes_per_cycle: int = 50

    # Optional: Load specific weights before starting? (Transfer Learning)
    resume_from_checkpoint: bool = False


class TrainingJobStatus(BaseModel):
    """Status report for a running or completed training job."""

    job_id: str
    scheduler_name: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: float = 0.0  # 0.0 to 1.0
    current_cycle: int = 0
    total_cycles: int = 0
    message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metrics: Optional[dict[str, Any]] = None


class PreprocessingRequest(BaseModel):
    dataset_name: str
    output_buffer_name: str  # e.g., "buffer_v1_heavy_load"


# Health Check Schemas
class ComponentStatus(BaseModel):
    status: str
    details: Optional[str] = None


class HealthCheckResponse(BaseModel):
    overall_status: str
    message: Optional[str] = None
    components: dict[str, ComponentStatus]
