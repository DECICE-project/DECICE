import logging
from parser.factory import get_parser
from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, UploadFile

from db.models import (SchedulingDecision, TaskStatus, User, Workflow,
                       WorkflowTask)
from domain.schemas import (MultiTaskStatusUpdate, PSGCTaskStatusUpdateRequest,
                            WorkflowCreateRequest, WorkflowCreateResponse,
                            WorkflowStatus)
from repositories.workflow_repository import (WorkflowRepository,
                                              get_workflow_repository)
from services.psgc_service import PsgcService, get_psgc_service

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Service layer for orchestrating workflow creation, delegation, and state progression.
    """

    def __init__(
        self,
        repository: WorkflowRepository,
        psgc_service: PsgcService,
    ):
        """Initializes the service with all its necessary dependencies."""
        self.repository = repository
        self.psgc_service = psgc_service

    async def create_workflow(
        self,
        *,
        user: User,
        workflow_request: WorkflowCreateRequest,
        definition_file: UploadFile,
    ) -> WorkflowCreateResponse:
        """
        Parses and saves a new workflow, then delegates it to the PSGC.
        """
        definition_content = await definition_file.read()
        await definition_file.seek(0)

        logger.info(f"Parsing definition file '{definition_file.filename}'...")
        parser = get_parser(
            filename=definition_file.filename, file_content=definition_content
        )
        db_workflow: Workflow = parser.parse(
            file_content_bytes=definition_content, filename=definition_file.filename
        )

        db_workflow.name = workflow_request.name
        db_workflow.user_id = user.id

        # Set the correct initial statuses for the Workflow and its Tasks
        if workflow_request.storage_filename:
            logger.info(
                f"Workflow requires data file '{workflow_request.storage_filename}'. Setting status to PENDING_DATA."
            )
            db_workflow.status = WorkflowStatus.PENDING_DATA
            # All tasks will keep their default 'PENDING_DEPENDENCIES' status
        else:
            logger.info("No data file required. Workflow is ready for progression.")
            # This workflow can start immediately
            db_workflow.status = WorkflowStatus.PROGRESSING

            # Mark all tasks with no dependencies as READY
            for task in db_workflow.tasks:
                if not task.dependencies:
                    task.status = TaskStatus.READY

        logger.info(f"Saving workflow '{db_workflow.name}' to the database.")
        created_workflow = await self.repository.create_full_workflow(db_workflow)

        logger.info(f"Delegating workflow {created_workflow.id} to PSGC...")
        psgc_response = await self.psgc_service.delegate_workflow_to_psgc(
            storage_filename=workflow_request.storage_filename,
            workflow=created_workflow,
            user=user,
        )
        logger.info(f"PSGC delegation response: {psgc_response.get('message')}")
        final_presigned_url = psgc_response.get("presigned_url")

        return WorkflowCreateResponse(
            workflow=created_workflow, presigned_url=final_presigned_url
        )

    async def handle_task_completion(self, *, task_id: UUID, final_status: TaskStatus):
        """
        Handles the completion of a task and progresses the workflow graph.
        Also notifies the PSGC of any downstream status updates.
        """
        update_list: list[MultiTaskStatusUpdate] = []
        workflow_id: Optional[UUID] = None

        if final_status in [
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            logger.info(
                f"Task {task_id} completed with status {final_status}, stopping downstream progression."
            )
            # Find and cancel all downstream tasks in the database
            tasks_cancelled, workflow_id = (
                await self.repository.cancel_downstream_tasks(task_id)
            )
            for task in tasks_cancelled:
                # Add to the list to notify PSGC
                update_list.append(
                    MultiTaskStatusUpdate(
                        status=TaskStatus.CANCELLED,
                        detail="Cancelled by upstream task failure.",
                        task_id=task.id,
                    )
                )

        elif final_status == TaskStatus.SUCCEEDED:
            # Find any downstream tasks that are now ready to run
            ready_tasks, workflow_id = (
                await self.repository.find_ready_downstream_tasks(task_id)
            )

            if not ready_tasks:
                logger.info(
                    f"Task {task_id} completed, no downstream tasks are ready to run."
                )
                if not workflow_id:
                    # Manually get workflow_id to check for workflow completion
                    task = await self.repository.session.get(WorkflowTask, task_id)
                    if task:
                        workflow_id = task.workflow_id
            else:
                logger.info(
                    f"Task {task_id} completed, marking tasks {[t.id for t in ready_tasks]} as READY."
                )
                for task in ready_tasks:
                    # Update status in our DB
                    await self.repository.update_task_status(task.id, TaskStatus.READY)
                    # Add to the list to notify PSGC
                    update_list.append(
                        MultiTaskStatusUpdate(
                            status=TaskStatus.READY,
                            detail="Dependencies met, task is ready.",
                            task_id=task.id,
                        )
                    )

        # If any tasks were updated (READY or CANCELLED), notify the PSGC
        if update_list and workflow_id:
            logger.info(
                f"Notifying PSGC of {len(update_list)} status updates for workflow {workflow_id}"
            )
            update_request = PSGCTaskStatusUpdateRequest(
                workflow_id=workflow_id, statuses=update_list
            )
            try:
                # We use the 'update_task_status' method on the client
                await self.psgc_service.client.update_task_status(update_request)
            except Exception as e:
                # Log the error but don't fail the whole operation,
                # PSGC will pick it up in its reconciliation loop.
                logger.error(
                    f"Failed to send status updates to PSGC: {e}", exc_info=True
                )

    async def update_workflow_status(
        self, workflow_id: UUID, status: Union[WorkflowStatus, str]
    ):
        """Updates the status of a workflow."""
        status_value = status.value if hasattr(status, "value") else str(status)
        logger.info(f"Updating status for workflow {workflow_id} to {status_value}")

        updated_workflow = await self.repository.update_workflow_status(
            workflow_id=workflow_id, status=status
        )

        if not updated_workflow:
            raise ValueError(f"Workflow with ID {workflow_id} not found.")

        return updated_workflow

    async def get_workflow_by_id(self, workflow_id: UUID) -> Optional[Workflow]:
        """Retrieves a single workflow with its details."""
        return await self.repository.get_workflow_with_details_by_id(workflow_id)

    async def get_all_workflows(
        self, offset: int, limit: int
    ) -> tuple[list[Workflow], int]:
        """Retrieves a paginated list of all workflows."""
        return await self.repository.list_workflows(offset=offset, limit=limit)

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
    ):
        """Updates the status of a specific task and handles progression logic."""
        logger.info(f"Updating status for task {task_id} to {status.value}")
        await self.repository.update_task_status(task_id=task_id, status=status)

        # If the task reached a terminal state, run the progression logic
        if status in [
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            await self.handle_task_completion(
                task_id=task_id,
                final_status=status,
            )

    async def delete_workflow(self, workflow_id: UUID):
        """
        Cancels all non-finished tasks in the workflow,
        updates PSGC, and then deletes the workflow.
        """
        logger.info(f"Deleting workflow {workflow_id} and cancelling unfinished tasks")

        # Get all tasks that need to be cancelled
        tasks_canceled = await self.repository.cancel_all_non_finished_tasks(
            workflow_id
        )
        update_list: list[MultiTaskStatusUpdate] = []

        # Update each task in our DB and add it to the notification list
        for task in tasks_canceled:
            await self.update_task_status(task.id, TaskStatus.CANCELLED)
            update_list.append(
                MultiTaskStatusUpdate(
                    status=TaskStatus.CANCELLED,
                    detail="CM: Workflow deleted by user.",
                    task_id=task.id,
                )
            )

        # Send one batch notification to PSGC
        if update_list:
            update = PSGCTaskStatusUpdateRequest(
                workflow_id=workflow_id,
                statuses=update_list,
            )
            try:
                await self.psgc_service.client.update_task_status(update)
                logger.info(
                    f"PSGC notified of {len(update_list)} cancelled tasks for workflow {workflow_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send cancel updates to PSGC: {e}", exc_info=True
                )
                # We still proceed with deletion

        # Delete the workflow from DB
        return await self.repository.delete_workflow_by_id(workflow_id)

    async def list_tasks(
        self,
        workflow_ids: Optional[list[UUID]] = None,
        statuses: Optional[list[TaskStatus]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[tuple[WorkflowTask, SchedulingDecision | None]], int]:
        """
        Lists tasks with optional workflow/status filters, including scheduling info.
        """
        return await self.repository.list_tasks_with_scheduling(
            workflow_ids=workflow_ids,
            statuses=statuses,
            offset=offset,
            limit=limit,
        )


def get_workflow_service(
    repository: WorkflowRepository = Depends(get_workflow_repository),
    psgc_service: PsgcService = Depends(get_psgc_service),
) -> WorkflowService:
    """FastAPI dependency provider for WorkflowService."""
    return WorkflowService(
        repository=repository,
        psgc_service=psgc_service,
    )
