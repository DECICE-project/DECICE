import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends
from pydantic import AnyHttpUrl

from config.config import get_settings
from core.dependencies import get_http_client

logger = logging.getLogger(__name__)


class SchedulerControllerClient:
    """
    Client for interacting with the Scheduler Controller microservice.
    Handles HTTP communication details.
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        """
        Initializes the client with a base URL and HTTP client instance.

        Args:
            base_url: The base URL for the Scheduler Controller service (injected).
            client: An httpx.AsyncClient instance for making requests (injected).
        """
        self.client = client

        if not base_url:
            raise ValueError(
                "Scheduler Controller base URL provided to client cannot be empty."
            )
        # Store the injected base_url, ensuring no trailing slash
        self.base_url: str = base_url.rstrip("/")
        logger.info(f"SchedulerControllerClient initialized. Base URL: {self.base_url}")

    async def schedule(self, data: Dict[str, Any], batch=False) -> Dict[str, Any]:
        """Sends scheduling request data to the Scheduler Controller."""
        # url = f"{self.base_url}/schedule"
        if batch:
            url = f"{self.base_url}/scheduler-controller-batch"
        else:
            url = f"{self.base_url}/scheduler-controller"
        logger.debug(f"POSTing to Scheduler Controller: {url} with data: {data}")

        try:
            response = await self.client.post(url, json=data)

            logger.debug(
                f"Scheduler Controller raw response status: {response.status_code}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.RequestError as exc:
            # Network errors, DNS errors, connection refused etc.
            error_msg = (
                f"Network error connecting to Scheduler Controller at {url}: {exc}"
            )
            logger.error(error_msg)
            # Raise a standard error type that services/API layer can understand
            raise ConnectionError(error_msg) from exc
        except httpx.HTTPStatusError as exc:
            # Handle 4xx/5xx responses specifically
            error_msg = (
                f"Scheduler Controller request failed at {url} with status {exc.response.status_code}. "
                f"Response: {exc.response.text[:200]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from exc
        except Exception as exc:
            # Catch any other unexpected errors (e.g., json decoding if response wasn't json)
            error_msg = f"An unexpected error occurred during Scheduler Controller communication: {exc}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from exc


# Dependency Provider Function for the client
def get_scheduler_controller_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SchedulerControllerClient:
    """
    FastAPI dependency provider for SchedulerControllerClient.

    Retrieves the base URL from the central configuration settings and
    injects it along with a shared httpx client into a new client instance.
    """
    settings = get_settings()
    sc_base_url: Optional[AnyHttpUrl] = settings.SC_BASE_URL

    if sc_base_url is None:
        logger.critical(
            "Scheduler Controller Base URL (SC_BASE_URL) is not configured!"
        )
        raise ValueError(
            "Scheduler Controller Base URL (SC_BASE_URL) is not configured."
        )

    return SchedulerControllerClient(base_url=str(sc_base_url), client=client)
