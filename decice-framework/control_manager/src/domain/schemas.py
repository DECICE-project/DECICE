import datetime
import json
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from uuid import UUID

from pydantic import (BaseModel, ConfigDict, Field, field_serializer,
                      field_validator, model_validator)


class WorkflowStatus(str, Enum):
    PENDING_DATA = "PENDING_DATA"
    PROGRESSING = "PROGRESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, Enum):
    # Pre-compute plane statuses
    WAITING = "WAITING"  # Waiting for dependencies OR data
    READY = "READY"  # Ready to be handled by PSGC and scheduling
    SCHEDULING = "SCHEDULING"  # Being scheduled by DECICE(schedule endpoint)
    # In compute plane statuses
    PENDING = "PENDING"  # Applied to orchestrator AFTER SCHEDULING  but not yet running (PSGC STATUS UPDATE)
    RUNNING = "RUNNING"  # Currently executing in compute plane (PSGC STATUS UPDATE)
    # Completion statuses
    SUCCEEDED = "SUCCEEDED"  # Completed successfully (PSGC STATUS UPDATE)
    FAILED = "FAILED"  # Completed with failure (PSGC STATUS UPDATE)
    CANCELLED = "CANCELLED"  # Cancelled before or during execution


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    valueFrom: Optional[dict[str, Any]] = None


class WorkflowCreateRequest(BaseModel):
    name: str
    storage_filename: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for WorkflowCreateRequest")
        return value


# WorkflowTaskCompletionRequest
class WorkflowTaskCompletionRequest(BaseModel):
    status: TaskStatus
    detail: str | None = None


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    detail: str | None = None


class WorkflowStatusUpdateRequest(BaseModel):
    status: WorkflowStatus
    detail: str | None = None


class MultiTaskStatusUpdate(TaskStatusUpdateRequest):
    task_id: UUID


class PSGCTaskStatusUpdateRequest(BaseModel):
    workflow_id: UUID
    statuses: list[MultiTaskStatusUpdate]


# -------------------


# Models for WorkflowTask
class WorkflowTaskBaseResponse(BaseModel):
    """Common fields for any workflow task returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    image: Optional[str] = None
    command_str: Optional[str] = None
    required_cpu: Optional[str] = None
    required_memory: Optional[str] = None
    required_gpu: Optional[str] = None
    annotations: Optional[dict[str, Any]] = {}
    env: Optional[list[EnvVar]] = []
    labels: Optional[dict[str, Any]] = {}


class JobResponse(WorkflowTaskBaseResponse):
    type: Literal["job"] = "job"


class DeploymentResponse(WorkflowTaskBaseResponse):
    type: Literal["deployment"] = "deployment"
    replicas: int


class HPCJobResponse(WorkflowTaskBaseResponse):
    type: Literal["hpc_job"] = "hpc_job"


class GenericK8sResourceResponse(WorkflowTaskBaseResponse):
    type: Literal["k8s_resource"] = "k8s_resource"


WorkflowTaskResponse = Annotated[
    Union[JobResponse, DeploymentResponse, HPCJobResponse, GenericK8sResourceResponse],
    Field(discriminator="type"),
]


# Models for Workflow
class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    user_id: UUID
    tasks: list[WorkflowTaskResponse] = []


class WorkflowCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workflow: WorkflowResponse
    presigned_url: Optional[str] = None


class PaginatedWorkflowsResponse(BaseModel):
    total: int
    items: list[WorkflowResponse]


# ---------------------


# Models for PSGC communication
class WorkflowTaskPSGCRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    image: Optional[str] = None
    command_str: Optional[str] = None
    required_cpu: Optional[str] = None
    required_memory: Optional[str] = None
    required_gpu: Optional[int] = None
    annotations: Optional[dict[str, Any]] = {}
    env: Optional[list[EnvVar]] = []
    labels: Optional[dict[str, Any]] = {}

    dependencies: list[UUID] = Field(default=[], validation_alias="dependencies")

    @field_validator("dependencies", mode="before")
    @classmethod
    def transform_dependencies(cls, v):
        """
        Accepts dependencies as:
        - list[UUID]
        - list[str] (UUID-like)
        - list[objects with an 'id' attribute that is UUID-like)
        Raises if unsupported types are passed.
        """
        if not isinstance(v, list):
            raise TypeError("dependencies must be a list")

        normalized: list[UUID] = []

        for dep in v:
            # If object has an 'id' attribute, try to use it
            if hasattr(dep, "id"):
                candidate = getattr(dep, "id")
            else:
                candidate = dep

            # else check uuid or uuid-like str
            if isinstance(candidate, UUID):
                normalized.append(candidate)
            elif isinstance(candidate, str):
                try:
                    normalized.append(UUID(candidate))
                except Exception:
                    raise ValueError(
                        f"Invalid UUID string in dependencies: {candidate}"
                    )
            else:
                raise TypeError(
                    f"Unsupported dependency type: {type(dep).__name__}. "
                    "Expected UUID, UUID string, or object with an 'id' attribute."
                )

        return normalized

    @field_serializer("id", "dependencies")
    def serialize_uuids(self, value):
        """Converts UUIDs and lists of UUIDs to strings for JSON serialization."""
        if isinstance(value, list):
            return [str(item) for item in value]
        return str(value)


class JobPSGCRequest(WorkflowTaskPSGCRequest):
    type: Literal["job"] = "job"


class DeploymentPSGCRequest(WorkflowTaskPSGCRequest):
    type: Literal["deployment"] = "deployment"
    replicas: int


class HPCJobPSGCRequest(WorkflowTaskPSGCRequest):
    type: Literal["hpc_job"] = "hpc_job"


class GenericK8sResourcePSGCRequest(WorkflowTaskPSGCRequest):
    type: Literal["k8s_resource"] = "k8s_resource"


class HPCContext(BaseModel):
    """Contains the platform-specific user info needed to run an HPC job."""

    platform_username: str
    default_working_dir: str = None


class WorkflowPSGCRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: WorkflowStatus
    user_id: UUID
    filename: Optional[str] = None

    tasks: list[
        Annotated[
            Union[
                JobPSGCRequest,
                DeploymentPSGCRequest,
                HPCJobPSGCRequest,
                GenericK8sResourcePSGCRequest,
            ],
            Field(discriminator="type"),
        ]
    ]

    hpc_context: Optional[HPCContext] = Field(
        None,
        description="HPC user context, required only if workflow contains HPCJobs.",
    )

    @field_serializer("id", "user_id")
    def serialize_id(self, value: UUID) -> str:
        return str(value)


# Scheduling history


class SchedulingDecisionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_nodes: list[str]
    strategy_used: str
    duration_ms: int
    created_at: datetime.datetime


class SchedulingDecisionTask(SchedulingDecisionBase):
    """
    SchedulingDecision of a task.
    """

    task_id: UUID
    task_name: str


class SchedulingDecisionResponse(SchedulingDecisionTask):
    """
    SchedulingDecisionTask enriched with additional Workflow context.
    """

    workflow_id: UUID
    workflow_name: str


class PaginatedSchedulingDecisionsResponse(BaseModel):
    """A paginated list of scheduling decisions."""

    total: int
    items: list[SchedulingDecisionResponse]


# Healt Check Response
class WorkflowPSGCResponse(BaseModel):
    presigned_url: Optional[str] = None
    message: str


class WorkflowTaskWithStatus(WorkflowTaskPSGCRequest):
    status: str


class JobWithStatus(WorkflowTaskWithStatus):
    type: Literal["job"] = "job"


class DeploymentWithStatus(WorkflowTaskWithStatus):
    type: Literal["deployment"] = "deployment"
    replicas: int


class HPCJobWithStatus(WorkflowTaskWithStatus):
    type: Literal["hpc_job"] = "hpc_job"


WorkflowTaskVariant = Annotated[
    Union[JobWithStatus, DeploymentWithStatus, HPCJobWithStatus],
    Field(discriminator="type"),
]


class WorkflowWithStatusResponse(WorkflowPSGCRequest):
    """Extends WorkflowPSGCRequest by including per-workflowtask status."""

    tasks: list[WorkflowTaskVariant]


class TaskWithSchedulingResponse(BaseModel):
    scheduling: SchedulingDecisionBase | None
    task: WorkflowTaskVariant
    workflow_id: UUID


class PaginatedTasksResponse(BaseModel):
    """API Task list response enriched with Scheduling context"""

    total: int
    tasks: list[TaskWithSchedulingResponse]


# Health Check
class ComponentStatus(BaseModel):
    status: str
    details: Optional[str] = None


class HealthCheckResponse(BaseModel):
    overall_status: str
    message: Optional[str] = None
    components: dict[str, ComponentStatus]
