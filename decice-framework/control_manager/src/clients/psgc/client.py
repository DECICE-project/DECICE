import json
import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from pydantic import AnyHttpUrl

from config.config import get_settings
from core.dependencies import get_http_client
from domain.schemas import PSGCTaskStatusUpdateRequest

logger = logging.getLogger(__name__)


class PsgcClient:
    """
    Client for making HTTP requests to the PSGC.
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.client = client
        self.base_url = base_url.rstrip("/")
        logger.info(f"PsgcClient initialized. Base URL: {self.base_url}")

    async def delegate_workflow(
        self,
        workflow_payload: dict,
        filename: Optional[str],
    ) -> dict:
        """
        Sends the workflow payload to the PSGC as a JSON request.
        """
        submit_url = f"{self.base_url}/workflows"
        logger.info(f"Delegating workflow payload to PSGC URL: {submit_url}")

        if filename and "filename" not in workflow_payload:
            workflow_payload["filename"] = filename
        try:
            response = await self.client.post(url=submit_url, json=workflow_payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            error_msg = f"Network error connecting to PSGC: {e}"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"PSGC request failed with status {e.response.status_code}: {e.response.text}"
            raise HTTPException(status_code=e.response.status_code, detail=error_msg)

    async def update_task_status(self, task_update: PSGCTaskStatusUpdateRequest) -> str:
        """
        Updates the status of one or more tasks in the PSGC.
        """
        update_url = f"{self.base_url}/workflows/tasks/status"
        logger.info(
            f"Sending task status update to PSGC at {update_url} "
            f"for {task_update.model_dump(mode='json')}"
        )

        try:
            response = await self.client.post(
                url=update_url, json=task_update.model_dump(mode="json")
            )
            response.raise_for_status()
            logger.info(
                f"Task status update successful for workflow_id={task_update.workflow_id}: "
                f"{response.text}"
            )
            return response.json()
        except httpx.RequestError as e:
            error_msg = f"Network error connecting to PSGC during task update: {e}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_msg
            )
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"PSGC task update failed with status {e.response.status_code}: "
                f"{e.response.text}"
            )
            logger.error(error_msg)
            raise HTTPException(status_code=e.response.status_code, detail=error_msg)


# Dependency Provider Function
def get_psgc_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> PsgcClient:
    """
    FastAPI dependency provider for PsgcClient.
    Injects base URL from settings and shared HTTP client.
    """
    settings = get_settings()
    psgc_base_url: Optional[AnyHttpUrl] = settings.PSGC_BASE_URL
    if psgc_base_url is None:
        raise ValueError(
            "PSGC Base URL (PSGC_BASE_URL) is not configured correctly in settings."
        )
    return PsgcClient(base_url=str(psgc_base_url), client=client)
