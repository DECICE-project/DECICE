import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status

from config.config import get_settings
from core.dependencies import get_http_client

logger = logging.getLogger(__name__)


class PromQLWrapperClient:
    """
    Client for making HTTP requests to the PromQL Wrapper.
    Handles network communication and error handling.
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.client = client
        self.base_url = base_url.rstrip("/")
        logger.info(f"PromQLWrapperClient initialized. Base URL: {self.base_url}")

    async def pool(self) -> dict[str, Any]:
        """
        Calls the /pool endpoint of the PromQL Wrapper service using POST.
        """
        url = f"{self.base_url}/pool"
        logger.info(f"Client making POST request to {url}")
        try:
            response = await self.client.post(url, json={}, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            # Handle network-level errors (connection refused, DNS error, etc.)
            error_msg = f"Network error connecting to PromQL Wrapper: {e}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        except httpx.HTTPStatusError as e:
            # Handle application-level errors (4xx or 5xx responses)
            error_msg = f"PromQL Wrapper request failed with status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=e.response.status_code, detail=error_msg)


def get_promql_wrapper_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> PromQLWrapperClient:
    """
    FastAPI dependency provider for PromQLWrapperClient.
    """
    settings = get_settings()
    promql_wrapper_url = settings.PROMQL_WRAPPER_BASE_URL

    if promql_wrapper_url is None:
        raise ValueError(
            "PromQL Wrapper Base URL (PROMQL_WRAPPER_BASE_URL) is not configured."
        )
    return PromQLWrapperClient(base_url=promql_wrapper_url, client=client)
