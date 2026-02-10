import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import verify_internal_traffic
from core.schemas import ScheduleRequest, ScheduleResponse
from services.scheduling_service import SchedulingService, get_scheduling_service

logger = logging.getLogger(__name__)
schedule_router = APIRouter()


@schedule_router.post(
    "/schedule",
    response_model=ScheduleResponse,
    summary="Schedules jobs based on an AI-selected strategy",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
)
async def schedule_jobs_api(
    request_data: ScheduleRequest,
    service: SchedulingService = Depends(get_scheduling_service),
):
    """
    Receives a list of jobs and available nodes, then uses the SchedulingService
    to process them through the AI pipeline and return the final placement decisions.
    """
    logger.info(f"Received scheduling requestTasks: {request_data.tasks}")
    try:
        scheduler_response = service.process_schedule(request_data)
        return scheduler_response
    except HTTPException:
        # Re-raise known HTTP exception thrown by service layer
        raise
    except Exception as e:
        logger.exception(f"An unhandled error occurred in the /schedule endpoint: {e}.")
        # For any other unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred.",
        )
