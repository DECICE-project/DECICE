import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from domain.schemas import TaskStatus, WorkflowStatus
from domain.user_schemas import UserRole


class Base(DeclarativeBase): ...


class WorkflowTaskDependency(Base):
    """
    Associates a Task (downstream) with another Task it depends on (upstream).
    Example: If B depends on A, then:
      - upstream_task_id = A.id
      - downstream_task_id = B.id
    """

    __tablename__ = "workflow_task_dependency"

    downstream_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_task.id", ondelete="CASCADE"),
        primary_key=True,
    )
    upstream_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_task.id", ondelete="CASCADE"),
        primary_key=True,
    )


# A WorkflowTask (Job) can be multiple things (Job, HPCJob, Deployment etc.)
class WorkflowTask(Base):
    """
    Base model for any executable entity (a 'node' in the graph),
    like a Job or a Deployment.
    """

    __tablename__ = "workflow_task"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", create_type=True),
        index=True,
        default=TaskStatus.WAITING,
    )

    image: Mapped[Optional[str]] = mapped_column(String)
    command_str: Mapped[Optional[str]] = mapped_column(String)
    required_cpu: Mapped[Optional[str]] = mapped_column(String)
    required_memory: Mapped[Optional[str]] = mapped_column(String)
    required_gpu: Mapped[Optional[int]] = mapped_column(Integer)
    annotations: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    env: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=[])
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)

    platform_job_id: Mapped[Optional[str]] = mapped_column(
        String, index=True, nullable=True
    )
    platform_identity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("platform_identity.id"), nullable=True
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow.id", ondelete="CASCADE")
    )
    workflow: Mapped["Workflow"] = relationship(back_populates="tasks")

    # Tasks that THIS task depends on (Upstream Parents)
    dependencies: Mapped[list["WorkflowTask"]] = relationship(
        "WorkflowTask",
        secondary="workflow_task_dependency",
        primaryjoin=id == WorkflowTaskDependency.downstream_task_id,
        secondaryjoin=id == WorkflowTaskDependency.upstream_task_id,
        back_populates="dependents",
        cascade="all",
        passive_deletes=True,
    )

    # Tasks that depend on THIS task (Downstream Children)
    dependents: Mapped[list["WorkflowTask"]] = relationship(
        "WorkflowTask",
        secondary="workflow_task_dependency",
        primaryjoin=id == WorkflowTaskDependency.upstream_task_id,
        secondaryjoin=id == WorkflowTaskDependency.downstream_task_id,
        back_populates="dependencies",
        cascade="all",
        passive_deletes=True,
    )

    type: Mapped[str] = mapped_column(String(50))
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "task",
    }


class Job(WorkflowTask):
    """A Task that runs to completion."""

    __mapper_args__ = {
        "polymorphic_identity": "job",
    }


class HPCJob(Job):
    """A Job Task specifically for an HPC/SLURM platform."""

    __mapper_args__ = {
        "polymorphic_identity": "hpc_job",
    }


class Deployment(WorkflowTask):
    """A long-running Task (service)."""

    replicas: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {
        "polymorphic_identity": "deployment",
    }


class GenericK8sResource(WorkflowTask):
    """
    Represents non-compute Kubernetes resources (Services, Namespaces, ConfigMaps, etc.)
    that just need to be applied to the cluster.
    """

    __mapper_args__ = {
        "polymorphic_identity": "k8s_resource",
    }


class Workflow(Base):
    """
    SQLAlchemy ORM model for the 'workflow' table.
    This is the top-level container for a set of tasks.
    """

    __tablename__ = "workflow"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, index=True)

    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status_enum", create_type=True),
        index=True,
        default=WorkflowStatus.PENDING_DATA,
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="workflows")

    tasks: Mapped[list["WorkflowTask"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PlatformIdentity(Base):
    __tablename__ = "platform_identity"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String, index=True, nullable=False)
    platform_username: Mapped[str] = mapped_column(String, nullable=False)
    default_working_dir: Mapped[str] = mapped_column(String)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), unique=True)
    user: Mapped["User"] = relationship(back_populates="platform_identity")
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "platform_username", name="uq_user_platform_username"
        ),
    )


class User(Base):
    """
    SQLAlchemy ORM model for the 'user' table.
    """

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER.value
    )
    project: Mapped[Optional[str]] = mapped_column(String, nullable=False)

    workflows: Mapped[list["Workflow"]] = relationship(back_populates="user")

    platform_identity: Mapped["PlatformIdentity"] = relationship(
        back_populates="user", cascade="all, delete-orphan", single_parent=True
    )
    # INFO: once we deal with multiple platforms we implement it as a list
    # platform_identities: Mapped[list["PlatformIdentity"]] = relationship(
    #     back_populates="user", cascade="all, delete-orphan"
    # )
    # platform_identity_id: Mapped[UUID] = mapped_column(
    #     ForeignKey("platform_identity.id"), nullable=False
    # )


class SchedulingDecision(Base):
    """
    Represents a historical record of a scheduling decision made for a task.
    """

    __tablename__ = "scheduling_decision"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    target_nodes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    strategy_used: Mapped[str] = mapped_column(String, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_task.id", ondelete="CASCADE"),
        primary_key=True,
    )
