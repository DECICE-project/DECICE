import httpx
from fastapi import Depends, HTTPException

from config.config import get_settings
from core.dependencies import get_http_client
from models.models import ScheduleRequest


class SchedulerClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def schedule(self, deployment: ScheduleRequest) -> dict:
        try:
            response = await self.client.post(
                f"{self.base_url}/schedule", json=deployment.model_dump()
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service Unavailable: Could not connect to Scheduler. {e}",
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from Scheduler: {e.response.text}",
            )


def get_scheduler_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SchedulerClient:
    settings = get_settings()
    return SchedulerClient(client=client, base_url=settings.SCHEDULER_SERVICE_BASE_URL)
