import logging

import httpx
from fastapi import Depends, HTTPException

from config.config import get_settings
from core.dependencies import get_http_client
from models.models import DeciceDigitalTwin

logger = logging.getLogger(__name__)


class DigitalTwinClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")
        logger.info(f"DigitalTwinClient initialized for base URL: {self.base_url}")

    async def post_model_core(self, digital_twin_data: DeciceDigitalTwin):
        """Posts the complete Digital Twin model to the DT service."""
        url = f"{self.base_url}/api/v2/model_core"

        logger.info(f"Posting Digital Twin snapshot to {url}")
        logger.debug(f"Snapshot lastUpdated: {digital_twin_data.lastUpdated}")

        try:
            response = await self.client.post(
                url,
                json=digital_twin_data.model_dump(),
                timeout=30.0,
            )

            logger.debug(f"Received response with status code: {response.status_code}")

            response.raise_for_status()

            logger.info("Successfully posted snapshot to Digital Twin.")

        except httpx.RequestError as e:
            logger.error(
                f"Network error while trying to connect to Digital Twin at {e.request.url}: {e}"
            )
            raise HTTPException(
                status_code=503,
                detail="Service Unavailable: Could not connect to Digital Twin.",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Digital Twin service returned an error: "
                f"Status={e.response.status_code}, "
                f"Response='{e.response.text[:150]}...'"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from Digital Twin: {e.response.text}",
            )


def get_digital_twin_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> DigitalTwinClient:
    settings = get_settings()
    return DigitalTwinClient(client=client, base_url=str(settings.DT_BASE_URL))
