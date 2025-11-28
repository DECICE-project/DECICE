import logging

import httpx
from fastapi import Depends, HTTPException

from config.config import get_settings
from core.dependencies import get_http_client
from models.models import ClusterState

logger = logging.getLogger(__name__)


class DigitalTwinClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def get_state(self) -> ClusterState:
        """
        Fetches the entire state from the Digital Twin, including
        vertexpools, links, and current jobs.
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v2/model_core")
            response.raise_for_status()
            return ClusterState(**response.json())
        except httpx.RequestError as e:
            logger.warning("Error retrieving data from Digital Twin.")
            raise HTTPException(
                status_code=503,
                detail=f"Service Unavailable: Could not connect to Digital Twin. {e}",
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from Digital Twin: {e.response.text}",
            )


def get_digital_twin_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> DigitalTwinClient:
    settings = get_settings()
    return DigitalTwinClient(client=client, base_url=settings.DT_SERVICE_BASE_URL)
