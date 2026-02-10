import logging
from typing import Any

from fastapi import Depends, HTTPException

from clients.promql_wrapper.client import PromQLWrapperClient, get_promql_wrapper_client

logger = logging.getLogger(__name__)


class PromQLWrapperService:
    """
    Service layer for the PromQL Wrapper.
    Contains business logic and orchestrates calls to the client.
    """

    def __init__(self, client: PromQLWrapperClient):
        """Initializes the service with its client dependency."""
        self.client = client
        logger.info("PromQLWrapperService initialized.")

    async def pool(self) -> dict[str, Any]:
        """
        Orchestrates the pooling operation by delegating to the client.
        (Future business logic, like caching or data validation, would go here).
        """
        logger.info("Service orchestrating 'pool' operation.")
        try:
            # Delegate the network call entirely to the client
            response_data = await self.client.pool()
            logger.info("Service 'pool' operation completed successfully.")
            return response_data
        except HTTPException as e:
            # Re-raise known HTTP exceptions from the client
            raise e
        except Exception as e:
            # Catch unexpected errors
            logger.exception(
                "An unexpected error occurred in the PromQLWrapperService."
            )
            raise RuntimeError(
                "An unexpected error occurred in the PromQL Wrapper Service."
            ) from e


def get_promql_wrapper_service(
    client: PromQLWrapperClient = Depends(get_promql_wrapper_client),
) -> PromQLWrapperService:
    """
    FastAPI dependency provider for PromQLWrapperService.
    """
    return PromQLWrapperService(client=client)
