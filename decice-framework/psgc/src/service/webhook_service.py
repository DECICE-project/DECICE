import logging
from uuid import UUID

from fastapi import Depends

from clients.cm_client import CMClient, get_cm_client
from io_models import (MinioWebhookPayload, SlurmWebhookPayload, TaskStatus,
                       WorkflowStatus)
from repository.redis_workflow_repository import (
    RedisWorkflowRepository, get_redis_workflow_repository)

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, repository: RedisWorkflowRepository, cm_client: CMClient):
        """Service for handling webhook business logic."""
        self.repository = repository
        self.cm_client = cm_client

    async def process_minio_notification(self, payload: MinioWebhookPayload):
        """
        Processes a MinIO webhook event, validates it, and activates the
        initial tasks of the corresponding workflow.
        """
        object_key = payload.Key
        logger.info(f"Processing MinIO webhook for object: {object_key}")

        try:
            key_parts = object_key.split("/")

            if len(key_parts) < 3:
                raise ValueError("Key format invalid, not enough segments")

            workflow_id_str = key_parts[1]
            workflow_id = UUID(workflow_id_str)

        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse workflow_id from key '{object_key}': {e}")
            return

        current_status = await self.repository.get_workflow_status(workflow_id)

        if not current_status:
            logger.warning(
                f"Webhook received for an unknown or completed workflow: {workflow_id}"
            )
            return

        if current_status != WorkflowStatus.PENDING_DATA.value:
            logger.info(
                f"Webhook received for workflow {workflow_id}, but its status is '{current_status}'. No action needed."
            )
            return

        await self.repository.activate_initial_tasks(workflow_id)

        new_workflow_status = WorkflowStatus.PROGRESSING.value

        await self.repository.update_workflow_status(workflow_id, new_workflow_status)

        try:
            await self.cm_client.report_workflow_status(
                workflow_id, new_workflow_status
            )
            logger.info(
                f"Webhook triggered: Marked workflow {workflow_id} as {new_workflow_status} and activated initial tasks."
            )
        except Exception as e:
            logger.error(
                f"Failed to report workflow {workflow_id} as {new_workflow_status} to CM: {e}"
            )

    async def process_slurm_notification(self, payload: SlurmWebhookPayload):
        """
        Handles status updates from the Slurm Client.
        """
        logger.info(
            f"Received Slurm webhook: Job {payload.job_id} ({payload.job_name}) is {payload.job_state}"
        )

        # Extract Task ID from the job name
        # Expected format: "psgc-task-{uuid}"
        try:
            if not payload.job_name.startswith("psgc-task-"):
                logger.warning(f"Ignoring non-PSGC job: {payload.job_name}")
                return

            task_id_str = payload.job_name.replace("psgc-task-", "")
            task_id = UUID(task_id_str)
        except ValueError:
            logger.error(f"Could not parse UUID from job name: {payload.job_name}")
            return

        # Look up the Workflow ID
        workflow_id = await self.repository.get_workflow_id_by_task_id(task_id)
        if not workflow_id:
            logger.error(f"Workflow not found for task {task_id}. Orphaned Slurm job?")
            return

        # Map Slurm state to TaskStatus
        slurm_state = payload.job_state.upper()
        new_status = None

        if slurm_state == "COMPLETED":
            new_status = TaskStatus.SUCCEEDED
        elif slurm_state in ["FAILED", "TIMEOUT", "CANCELLED", "NODE_FAIL"]:
            new_status = TaskStatus.FAILED  # Or CANCELLED if specific
        elif slurm_state == "RUNNING":
            new_status = TaskStatus.RUNNING

        if not new_status:
            logger.debug(
                f"Slurm state '{slurm_state}' is not a terminal/transition state we care about."
            )
            return

        # Update Redis
        await self.repository.update_task_status(workflow_id, task_id, new_status.value)

        # Notify CM
        if new_status in [TaskStatus.SUCCEEDED, TaskStatus.FAILED]:
            await self.cm_client.report_task_completion(
                task_id=task_id,
                completion_status=new_status.value,
                detail=f"Slurm job finished with state {slurm_state} (Exit Code: {payload.exit_code})",
            )
        else:
            await self.cm_client.patch_task_status(
                task_id=task_id,
                status=new_status.value,
                detail=f"Slurm job is {slurm_state}",
            )

        logger.info(f"Successfully updated task {task_id} to {new_status.value}")


# Dependency Injection Provider
def get_webhook_service(
    repo: RedisWorkflowRepository = Depends(get_redis_workflow_repository),
    cm_client: CMClient = Depends(get_cm_client),
) -> WebhookService:
    """FastAPI dependency provider for WebhookService."""
    return WebhookService(repository=repo, cm_client=cm_client)
