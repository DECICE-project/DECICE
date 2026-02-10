import logging
from typing import Any

from fastapi import Depends

from clients.scheduler_controller.client import (
    SchedulerControllerClient,
    get_scheduler_controller_client,
)

logger = logging.getLogger(__name__)


class SchedulerControllerService:
    """
    Service layer for orchestrating interactions with the Scheduler Controller.
    Provides a buffer between application logic and the raw client.
    """

    def __init__(
        self,
        client: SchedulerControllerClient = Depends(get_scheduler_controller_client),
    ):
        """Initializes the service with an injected Scheduler Controller client."""
        self.client = client
        logger.info("SchedulerControllerService initialized.")

    async def schedule(self, data: dict[str, Any], batch=False) -> dict[str, Any]:
        """
        Processes scheduling data and forwards it to the Scheduler Controller via the client.
        (Add any service-level logic, validation, or data mapping here).
        """
        logger.info("Forwarding schedule request via SchedulerControllerService.")

        try:
            # Delegate the actual HTTP call to the injected client
            response = await self.client.schedule(data=data, batch=batch)
            logger.info("Received successful schedule response from client.")
            return response
        except (ConnectionError, ValueError, RuntimeError) as e:
            logger.error(
                f"SchedulerControllerClient raised an error during schedule: {e}"
            )
            raise e
        except Exception as e:
            logger.exception(
                f"Unexpected error in SchedulerControllerService.schedule: {e}"
            )
            raise RuntimeError(
                "An unexpected error occurred in the Scheduler Controller service."
            ) from e


# Dependency Provider Function
def get_scheduler_controller_service(
    service: SchedulerControllerService = Depends(SchedulerControllerService),
) -> SchedulerControllerService:
    """FastAPI dependency provider for SchedulerControllerService."""
    return service
