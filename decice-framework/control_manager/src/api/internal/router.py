import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.auth import verify_internal_traffic
from domain.schemas import (
    PaginatedTasksResponse,
    SchedulingDecisionBase,
    TaskStatus,
    TaskStatusUpdateRequest,
    TaskWithSchedulingResponse,
    WorkflowStatusUpdateRequest,
)
from services.workflow_service import WorkflowService, get_workflow_service

logger = logging.getLogger(__name__)

internal_service_router = APIRouter(prefix="/internal")


@internal_service_router.patch(
    "/workflow/{workflow_id}/status",
    summary="Update Workflow Status (Callback)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_traffic)],
    include_in_schema=True,
)
async def update_workflow_status_callback(
    workflow_id: UUID,
    update_request: WorkflowStatusUpdateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Receives the status of an entire workflow from a PSGC."""
    status_val = getattr(status, "value", status)
    logger.debug(
        f"Attempting to update status for workflow {workflow_id} to '{status_val}'"
    )
    try:
        await workflow_service.update_workflow_status(
            workflow_id=workflow_id, status=update_request.status.value
        )
        return {"message": "Workflow status updated successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating workflow status for {workflow_id}, detail: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )


@internal_service_router.patch(
    "/task/{task_id}/status",
    summary="Update Workflow Task Status (Callback)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_traffic)],
    include_in_schema=True,
)
async def task_status_callback(
    task_id: UUID,
    status_update: TaskStatusUpdateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Receives status update of a single workflow task from a PSGC."""
    logger.info(
        f"Received completion status '{status_update.status}' for task_id: {task_id}"
    )
    try:
        await workflow_service.update_task_status(
            task_id=task_id, status=status_update.status
        )
        return {"message": "Workflow Task status updated successfully."}
    except Exception as e:
        logger.exception(f"Error processing status update for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process workflow task status update.",
        )


@internal_service_router.get(
    "/task/",
    summary="List workflow tasks with optional scheduling info.",
    response_model=PaginatedTasksResponse,
    dependencies=[Depends(verify_internal_traffic)],
    include_in_schema=True,
)
async def list_tasks(
    workflow_ids: list[UUID] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    workflow_service: WorkflowService = Depends(get_workflow_service),
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
