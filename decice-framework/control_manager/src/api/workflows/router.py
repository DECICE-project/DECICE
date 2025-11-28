import logging
import sys
from uuid import UUID

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)

from auth.dependencies import get_current_active_user
from domain.schemas import (PaginatedTasksResponse, PaginatedWorkflowsResponse,
                            SchedulingDecisionBase, TaskStatus,
                            TaskWithSchedulingResponse, WorkflowCreateRequest,
                            WorkflowCreateResponse, WorkflowWithStatusResponse)
from domain.user_schemas import User
from services.workflow_service import WorkflowService, get_workflow_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


workflow_router = APIRouter(prefix="/workflow")


@workflow_router.post(
    "/",
    summary="Submit a New Workflow",
    response_model=WorkflowCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow(
    workflow: WorkflowCreateRequest,
    current_user: User = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    definition_file: UploadFile = File(
        ..., description="A Kubernetes Job or Deployment YAML file."
    ),
):
    """Handles workflow submission including metadata and the definition file."""
    logger.info(f"User {current_user.id} submitting workflow '{workflow.name}'.")
    try:
        response = await workflow_service.create_workflow(
            user=current_user,
            workflow_request=workflow,
            definition_file=definition_file,
        )

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@workflow_router.get(
    "/", response_model=PaginatedWorkflowsResponse, summary="List All Workflows"
)
async def list_all_workflows(
    service: WorkflowService = Depends(get_workflow_service),
    _current_user: User = Depends(get_current_active_user),
    offset: int = 0,
    limit: int = Query(default=100, lte=1000),
):
    """Retrieves a paginated list of all workflows."""
    workflows, total = await service.get_all_workflows(offset=offset, limit=limit)
    return PaginatedWorkflowsResponse(total=total, items=workflows)


@workflow_router.get(
    "/{workflow_id}",
    response_model=WorkflowWithStatusResponse,
    summary="Get a Specific Workflow",
)
async def get_single_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
    _current_user: User = Depends(get_current_active_user),
):
    """Retrieves a single workflow and its associated tasks."""
    workflow = await service.get_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=404, detail=f"Workflow with ID {workflow_id} not found."
        )
    resp = WorkflowWithStatusResponse(
        id=workflow.id,
        name=workflow.name,
        status=workflow.status,
        user_id=workflow.user_id,
        filename=getattr(workflow, "storage_filename", None),
        tasks=workflow.tasks,
        hpc_context=getattr(workflow, "hpc_context", None),
    )
    return resp


@workflow_router.delete(
    "/{workflow_id}",
    summary="Delete a Workflow",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workflow(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Deletes a workflow by its ID after cancelling all non-finished workflow tasks
    and notifying PSGC.
    """
    logger.info(f"Request received to delete workflow {workflow_id}")

    try:
        deleted = await workflow_service.delete_workflow(workflow_id)
        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Workflow with ID {workflow_id} not found."
            )
        return {"message": f"Workflow {workflow_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow {workflow_id}",
        )


@workflow_router.get(
    "/task/",
    summary="List workflow tasks with optional scheduling info.",
    response_model=PaginatedTasksResponse,
)
async def list_tasks(
    workflow_ids: list[UUID] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    _current_user: User = Depends(get_current_active_user),
):
    try:
        status_enums = [TaskStatus(s) for s in statuses] if statuses else None

        tasks_with_scheduling, total = await workflow_service.list_tasks(
            workflow_ids=workflow_ids,
            statuses=status_enums,
            offset=offset,
            limit=limit,
        )

        tasks: list[TaskWithSchedulingResponse] = []

        for task, scheduling in tasks_with_scheduling:
            if scheduling is None:
                # Scheduling is missing → Response should use `None`
                tasks.append(
                    TaskWithSchedulingResponse(
                        task=task.__dict__,
                        scheduling=None,
                        workflow_id=task.workflow_id,
                    )
                )
            else:
                # Scheduling exists → enrich with workflow + task metadata
                scheduling_model = SchedulingDecisionBase(
                    **scheduling.__dict__,
                )
                tasks.append(
                    TaskWithSchedulingResponse(
                        task=task.__dict__,
                        scheduling=scheduling_model,
                        workflow_id=task.workflow_id,
                    )
                )

        return PaginatedTasksResponse(total=total, tasks=tasks)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Failed to list workflow tasks.",
        )
