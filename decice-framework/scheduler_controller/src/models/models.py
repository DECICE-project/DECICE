import math
import re
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class HardwareRequirements(BaseModel):
    required_cpu: int
    required_memory: int
    required_gpu: str | None = None

    @field_validator("required_cpu", mode="before")
    def convert_cpu(cls, v):
        if v is None:
            return 1

        if isinstance(v, str) and v.endswith("m"):
            cores = int(v[:-1]) / 1000
            return int(-(-cores // 1))
        return int(v)

    @field_validator("required_memory", mode="before")
    def set_mem_req(cls, v):
        if v is None:
            return 128

        if not isinstance(v, str):
            return int(v)

        if not isinstance(v, str):
            raise ValueError("memory must be a string")

        binary_units = {
            "Ki": 1 / 1024,
            "Mi": 1,
            "Gi": 1024,
            "Ti": 1024 * 1024,
            "Pi": 1024**3,
            "Ei": 1024**4,
        }

        decimal_units = {
            "k": 1000 / (1024 * 1024),
            "M": 1e6 / (1024 * 1024),
            "G": 1e9 / (1024 * 1024),
            "T": 1e12 / (1024 * 1024),
            "P": 1e15 / (1024 * 1024),
            "E": 1e18 / (1024 * 1024),
        }

        match = re.match(r"^([0-9.]+)([a-zA-Z]+)?$", v)
        if not match:
            raise ValueError(f"Invalid memory quantity: {v}")
        number, unit = match.groups()
        number = float(number)

        if not unit:
            return math.ceil(number / (1024 * 1024))

        if unit in binary_units:
            return math.ceil(number * binary_units[unit])
        elif unit in decimal_units:
            return math.ceil(number * decimal_units[unit])
        else:
            raise ValueError(f"Unsupported memory unit: {unit}")


class Task(BaseModel):
    id: UUID
    requirements: HardwareRequirements

    @field_serializer("id")
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class Metrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    util: Optional[float] = Field(None, ge=0.0, le=100.0)
    mem_util: Optional[float] = Field(None, ge=0.0, le=100.0)
    network_bandwidth_mbps: Optional[float] = None
    free_disk_gb: Optional[float] = None
    total_disk_gb: Optional[float] = None
    cpu_cores: Optional[float] = Field(None, ge=0.0)
    mem_total: Optional[float] = Field(None, ge=0.0)
    power_watts: Optional[float] = None


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    name: Optional[str] = None
    system: Optional[str] = None
    node_info: Optional[dict[str, Any]] = Field(
        {}, description="Additional information about the node"
    )
    metrics: Optional[Metrics] = Field(
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


class Vertexpool(BaseModel):
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
    vertexpools: Optional[list[Vertexpool]] = Field(
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
    tasks: list[Task]
    cluster: ClusterState


class TaskPlacement(BaseModel):
    """Placement decision for a single task."""

    task_id: UUID = Field(description="The UUID of the task that was processed.")
    target_node_ids: list[str] = Field(
        description="An array of node IDs relevant for placing the task."
    )
    strategy_used: Optional[str] = Field(
        None, description="The scheduling strategy chosen for this request."
    )


class ScheduleResponse(BaseModel):
    """The structure of the API response after scheduling."""

    placements: list[TaskPlacement] = Field(
        description="A list of task placement details."
    )
    scheduling_duration_ms: Optional[float] = Field(
        None,
        description="Time taken for the scheduling strategy execution in milliseconds.",
    )
