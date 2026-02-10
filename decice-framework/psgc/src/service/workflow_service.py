import logging

from fastapi import Depends

from io_models import PSGCTaskStatusUpdateRequest, WorkflowPSGCRequest
from repository.redis_workflow_repository import (
    RedisWorkflowRepository,
    get_redis_workflow_repository,
)
from service.storage_service import StorageService, get_storage_service

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(
        self,
        repository: RedisWorkflowRepository,
        storage_service: StorageService,
    ):
        """Service for handling delegated workflows on the PSGC."""
        self.repository = repository
        self.storage_service = storage_service

    async def create_workflow_and_get_upload_url(
        self,
        *,
        workflow_request: WorkflowPSGCRequest,
        filename: str,
    ) -> str:
        """
        Orchestrates creating a workflow and optionally generating its data upload URL.
        """

        # determine the initial status for the workflow
        initial_workflow_status = (
            "PENDING_DATA" if workflow_request.filename else "PROGRESSING"
        )
        logger.info(
            f"Workflow {workflow_request.id} will be saved with initial status: {initial_workflow_status}"
        )

        # save the workflow's state to Redis with the correct status
        await self.repository.save_workflow_state(
            workflow_request=workflow_request,
            initial_workflow_status=initial_workflow_status,
        )

        # if a file is expected, generate and return the presigned URL
        upload_url = None
        if workflow_request.filename:
            logger.info(
                f"Filename '{workflow_request.filename}' provided. Generating presigned URL."
            )
            bucket_name = "workflows"
            # path structure for easy reverse lookup from the webhook
            object_name = f"{workflow_request.id}/inputs/{workflow_request.filename}"
            upload_url = self.storage_service.generate_presigned_url(
                bucket_name=bucket_name, object_name=object_name
            )

        return upload_url

    async def update_task_statuses(
        self, task_updates: PSGCTaskStatusUpdateRequest
    ) -> int:
        """
        Updates the status of multiple tasks in the repository.
        This is called by the CM to notify of new READY/CANCELLED tasks.
        """
        failed_updates = []
        successful_updates = {}

        # Get all current task statuses for this workflow
        current_task_statuses = await self.repository.get_task_statuses(
            task_updates.workflow_id
        )

        for status_update in task_updates.statuses:
            task_id_str = str(status_update.task_id)

            # Check if this task is known to us (validation)
            if task_id_str not in current_task_statuses:
                failed_updates.append(status_update.task_id)
                continue

            successful_updates[task_id_str] = status_update.status.value

        if failed_updates:
            logger.error(
                f"Partial task update failure for workflow {task_updates.workflow_id}. "
                f"Failed Tasks: {failed_updates}, "
                f"Valid Tasks: {list(successful_updates.keys())}"
            )

        if not successful_updates:
            logger.warning(
                f"No valid task updates for workflow {task_updates.workflow_id}"
            )
            return 0

        return await self.repository.set_task_statuses(
            task_updates.workflow_id, successful_updates
        )


def get_workflow_service(
    repo: RedisWorkflowRepository = Depends(get_redis_workflow_repository),
    storage: StorageService = Depends(get_storage_service),
) -> WorkflowService:
    """FastAPI dependency provider for the PSGC's WorkflowService."""
    return WorkflowService(repository=repo, storage_service=storage)
