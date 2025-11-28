import logging

import httpx
from fastapi import Depends

from config.settings import SlurmClientSettings, get_settings
from core.dependencies import get_http_client

logger = logging.getLogger(__name__)


class PSGCClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.client = client

    async def send_task_status_update(self, payload: dict):
        """
        Forwards the Slurm status update to the PSGC.
        """
        url = f"{self.base_url}/webhooks/slurm"
        logger.info(f"Forwarding Slurm event to PSGC at {url}: {payload}")

        try:
            response = await self.client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Successfully delivered webhook to PSGC.")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to PSGC: {e}")
            # We generally don't raise here to avoid crashing the Slurm Epilog script call,
            # but logging is critical.
        except httpx.HTTPStatusError as e:
            logger.error(
                f"PSGC returned error {e.response.status_code}: {e.response.text}"
            )


def get_psgc_client(
    settings: SlurmClientSettings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> PSGCClient:
    return PSGCClient(base_url=settings.PSGC_SERVICE_BASE_URL, client=client)
