import logging

from fastapi import Depends

from clients.digital_twin import DigitalTwinClient, get_digital_twin_client
from clients.scheduler import SchedulerClient, get_scheduler_client
from models.models import ScheduleRequest, Task

logger = logging.getLogger(__name__)


class OrchestrationService:
    def __init__(
        self,
        dt_client: DigitalTwinClient,
        scheduler_client: SchedulerClient,
    ):
        self.dt_client = dt_client
        self.scheduler_client = scheduler_client

    async def process_scheduling(self, task: Task) -> dict:
        # Fetch data from Digital Twin
        dt_state = await self.dt_client.get_state()

        # Construct payload
        schedule_request = ScheduleRequest(tasks=[task], cluster=dt_state)

        # Post to Scheduler
        logger.info("Sending Digital Twin state.")
        scheduler_response = await self.scheduler_client.schedule(schedule_request)

        return scheduler_response

    async def process_scheduling_batch(self, tasks: list[Task]) -> dict:
        # Fetch data from Digital Twin
        dt_state = await self.dt_client.get_state()

        # Construct payload
        schedule_request = ScheduleRequest(tasks=tasks, cluster=dt_state)

        # Post to Scheduler
        logger.info("Sending Digital Twin state.")
        scheduler_response = await self.scheduler_client.schedule(schedule_request)

        return scheduler_response


def get_orchestration_service(
    dt_client: DigitalTwinClient = Depends(get_digital_twin_client),
    scheduler_client: SchedulerClient = Depends(get_scheduler_client),
) -> OrchestrationService:
    return OrchestrationService(dt_client=dt_client, scheduler_client=scheduler_client)
