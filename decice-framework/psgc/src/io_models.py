import json
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from uuid import UUID

from pydantic import (BaseModel, ConfigDict, Field, field_serializer,
                      field_validator, model_validator)


class MinioEventRecord(BaseModel):
    s3: dict


class MinioWebhookPayload(BaseModel):
    EventName: str
    Key: str
    Records: list[MinioEventRecord]


class SlurmWebhookPayload(BaseModel):
    """
    Payload sent by the slurm-client service when a job state changes.
    """

    job_id: str  # The Slurm Job ID (e.g. "12345")
    job_name: str  # The name we assigned (e.g. "psgc-task-{uuid}")
    job_state: str  # e.g., "COMPLETED", "FAILED", "TIMEOUT"
    exit_code: Optional[int] = None
    cluster: Optional[str] = None


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    valueFrom: Optional[dict[str, Any]] = None


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
    """Represents non-compute resources (Service, Namespace) passed to PSGC."""

    type: Literal["k8s_resource"] = "k8s_resource"


class HPCContext(BaseModel):
    """Contains the platform-specific user info needed to run an HPC job."""

    platform_username: str
    default_working_dir: str


class WorkflowPSGCRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: str
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

    @field_serializer("id")
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    @model_validator(mode="before")
    @classmethod
    def validate_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string provided")
        return value


class WorkflowStatus(str, Enum):
    """
    High-level status of an entire Workflow.
    """

    PENDING_DATA = "PENDING_DATA"
    PROGRESSING = "PROGRESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, Enum):
    """
    Status of an individual WorkflowTask.
    """

    WAITING = "WAITING"
    READY = "READY"
    SCHEDULING = "SCHEDULING"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowPSGCResponse(BaseModel):
    """
    Standard response for workflow delegation.
    Includes an optional presigned URL.
    """

    message: str
    presigned_url: Optional[str] = None


# unused for now.
# class Workflow(BaseModel):
#     id: UUID
#     name: str
#     status: WorkflowStatus
#     user_id: UUID


# class UserContext(BaseModel):
#     internal_user_id: UUID
#     hpc_user_id: str


# class WorkflowPayload(BaseModel):
#     workflow_id: UUID
#     workflow: Workflow
#     user_context: UserContext


# ------------------------------------
class TaskStatusUpdateRequest(BaseModel):
    """Payload for updating a single task's status (e.g., PENDING, RUNNING)"""

    status: TaskStatus
    detail: str | None = None


class TaskCompletionRequest(BaseModel):
    """The request body sent by the PSGC when a job finishes."""

    status: TaskStatus
    detail: str | None = None


class MultiTaskStatusUpdate(TaskStatusUpdateRequest):
    task_id: UUID


class PSGCTaskStatusUpdateRequest(BaseModel):
    """Request from CM to PSGC to update multiple tasks."""

    workflow_id: UUID
    statuses: list[MultiTaskStatusUpdate]


class WorkflowStatusUpdateRequest(BaseModel):
    status: str  # e.g., PROGRESSING, SUCCEEDED, FAILED


# Slurm Client Schemas
class SlurmClientRequest(BaseModel):
    username: str
    work_dir: str
    slurm_file_content: str
    task_id: UUID


# Scheduler Schemas
class KubernetesTaskPlacement(BaseModel):
    """
    Represents the scheduling information for a single task.
    """

    task_id: UUID = Field(description="The UUID of the task that was processed.")
    target_node_ids: list[str] = Field(
        description="An array of node UUIDs relevant for placing the task."
    )


class ScheduleResponse(BaseModel):
    """
    The overall response from the scheduling API.
    """

    placements: list[KubernetesTaskPlacement] = Field(
        description="A list of task placement details."
    )
