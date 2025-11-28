from abc import ABC, abstractmethod
from uuid import UUID

from io_models import WorkflowPSGCRequest


class AbstractWorkflowStateRepository(ABC):
    @abstractmethod
    async def save_workflow_state(
        self, workflow_request: WorkflowPSGCRequest, initial_workflow_status: str
    ):
        raise NotImplementedError

    @abstractmethod
    async def get_workflow_definition(self, workflow_id: UUID) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def get_workflow_status(self, workflow_id: UUID) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def update_workflow_status(self, workflow_id: UUID, status: str):
        raise NotImplementedError

    @abstractmethod
    async def get_task_statuses(self, workflow_id: UUID) -> dict[str, str]:
        """Renamed from get_job_statuses"""
        raise NotImplementedError

    @abstractmethod
    async def get_task_status(self, workflow_id: UUID, task_id: UUID) -> str | None:
        """Renamed from get_job_status"""
        raise NotImplementedError

    @abstractmethod
    async def update_task_status(self, workflow_id: UUID, task_id: UUID, status: str):
        """Renamed from update_job_status"""
        raise NotImplementedError

    @abstractmethod
    async def get_active_workflow_ids(self) -> list[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def get_workflow_ids_by_status(self, status: str) -> list[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def delete_workflow_state(self, workflow_id: UUID):
        raise NotImplementedError

    @abstractmethod
    async def activate_initial_tasks(self, workflow_id: UUID) -> int:
        """Renamed from activate_initial_jobs"""
        raise NotImplementedError

    @abstractmethod
    async def set_task_statuses(
        self, workflow_id: UUID, mapping: dict[str, str]
    ) -> int:
        """Set multiple task statuses at once."""
        raise NotImplementedError

    @abstractmethod
    async def set_task_external_id(
        self, workflow_id: UUID, task_id: UUID, external_id: str
    ):
        """Map an internal task ID to an external system ID (e.g., Slurm Job ID)."""
        raise NotImplementedError

    @abstractmethod
    async def get_task_external_id(
        self, workflow_id: UUID, task_id: UUID
    ) -> str | None:
        """Retrieve the external ID for a task."""
        raise NotImplementedError

    @abstractmethod
    async def get_workflow_id_by_task_id(self, task_id: UUID) -> UUID | None:
        """Reverse lookup: Find the parent workflow for a given task."""
        raise NotImplementedError
