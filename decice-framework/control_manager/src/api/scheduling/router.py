import logging
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_serializer

from auth.auth import verify_internal_traffic
from auth.dependencies import get_current_active_user
from domain.schemas import PaginatedSchedulingDecisionsResponse, TaskStatus
from services.promql_wrapper_service import (PromQLWrapperService,
                                             get_promql_wrapper_service)
from services.scheduler_controller_service import (
    SchedulerControllerService, get_scheduler_controller_service)
from services.scheduling_service import (SchedulingService,
                                         get_scheduling_service)
from services.workflow_service import WorkflowService, get_workflow_service

logger = logging.getLogger(__name__)

schedule_router = APIRouter(prefix="/schedule")


class SchedulingRequest(BaseModel):
    id: UUID
    requirements: dict[str, Any]

    @field_serializer("id")
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class TaskPlacement(BaseModel):
    task_id: UUID
    target_node_ids: list[str]
    strategy_used: str | None = None

    @field_serializer("task_id")
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)


class SchedulingDecisionResponse(BaseModel):
    placements: list[TaskPlacement]
    scheduling_duration_ms: float


# TODO: move function to internal
@schedule_router.post(
    "/schedule",
    response_model=SchedulingDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    description="Submit data to digital twin and request new scheduling.",
    summary="Request Scheduling",
    dependencies=[Depends(verify_internal_traffic)],
    include_in_schema=True,
)
async def request_scheduling(
    scheduler_controller_service: Annotated[
        SchedulerControllerService, Depends(get_scheduler_controller_service)
    ],
    promql_service: Annotated[
        PromQLWrapperService, Depends(get_promql_wrapper_service)
    ],
    scheduling_service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    worklow_service: Annotated[WorkflowService, Depends(get_workflow_service)],
    scheduling_request: SchedulingRequest,
):
    logger.info(f"Received scheduling decision {scheduling_request.id}")
    # INFO: for testing
    # target_node = "minikube-m02"
    # return SchedulingDecisionResponse(
    #     placements=[
    #         TaskPlacement(
    #             task_id=scheduling_request.id,
    #             target_node_ids=[target_node],
    #             strategy_used="round-robin",
    #         )
    #     ],
    #     scheduling_duration_ms=123,
    # )
    await worklow_service.update_task_status(
        task_id=scheduling_request.id, status=TaskStatus.SCHEDULING
    )
    try:
        _promql_response = await promql_service.pool()
        scheduler_response = await scheduler_controller_service.schedule(
            scheduling_request.model_dump()
        )

        try:
            await scheduling_service.record_scheduling_results(scheduler_response)
        except Exception:
            logger.error(
                "Failed to persist scheduling decision. This will not block the response."
            )

        return scheduler_response

    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@schedule_router.post(
    "/batch_schedule",
    response_model=SchedulingDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    description="Refresh Digital-Twin snapshot and send batch scheduling request",
    summary="Request Batch Scheduling",
    include_in_schema=True,
)
async def request_batch_scheduling(
    scheduler_controller_service: Annotated[
        SchedulerControllerService, Depends(get_scheduler_controller_service)
    ],
    promql_service: Annotated[
        PromQLWrapperService, Depends(get_promql_wrapper_service)
    ],
    scheduling_service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    worklow_service: Annotated[WorkflowService, Depends(get_workflow_service)],
    scheduling_requests: list[SchedulingRequest],
):
    task_ids = [req.id for req in scheduling_requests]
    logger.info(f"Received batch scheduling decision for tasks {task_ids}")

    for task_id in task_ids:
        await worklow_service.update_task_status(
            task_id=task_id, status=TaskStatus.SCHEDULING
        )

    try:
        _promql_response = await promql_service.pool()
        scheduler_response = await scheduler_controller_service.schedule(
            [req.model_dump() for req in scheduling_requests], batch=True
        )

        try:
            await scheduling_service.record_scheduling_results(scheduler_response)
        except Exception:
            logger.error(
                "Failed to persist batch scheduling decisions. This will not block the response."
            )

        return scheduler_response

    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during batch scheduling.",
        )


@schedule_router.get(
    "/decisions",
    response_model=PaginatedSchedulingDecisionsResponse,
    summary="Query Historical Scheduling Decisions",
    dependencies=[Depends(get_current_active_user)],
)
async def get_scheduling_decisions(
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    target_node: Optional[str] = Query(
        None, description="Filter by the node ID that was scheduled to."
    ),
    strategy: Optional[str] = Query(
        None, description="Filter by the strategy name used."
    ),
    task_id: Optional[UUID] = Query(None, description="Filter by a specific task ID."),
    workflow_id: Optional[UUID] = Query(
        None, description="Filter by a specific workflow ID."
    ),
    offset: int = 0,
    limit: int = Query(default=100, lte=1000),
):
    """
    Retrieves a paginated and filterable list of all historical scheduling
    decisions made by the system, enriched with workflow and workflow task info.
    """
    scheduling_decisions = await service.get_scheduling_history(
        target_node=target_node,
        strategy=strategy,
        task_id=task_id,
        workflow_id=workflow_id,
        offset=offset,
        limit=limit,
    )

    return scheduling_decisions
