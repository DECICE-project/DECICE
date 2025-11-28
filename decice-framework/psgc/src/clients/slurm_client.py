import logging
from uuid import UUID

import httpx
from fastapi import Depends

from config import get_settings
from core.dependencies import get_http_client
from io_models import SlurmClientRequest

logger = logging.getLogger(__name__)


class SlurmClient:
    """
    Client for the PSGC to communicate with the internal Slurm Client service.
    """

    def __init__(self, base_url: str, http_client: httpx.AsyncClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client
        logger.info(f"SlurmClient initialized. Base URL: {self.base_url}")

    async def submit_job(
        self, sbatch_file: str, username: str, work_dir: str, task_id: UUID
    ) -> dict:
        """
        Submits a Slurm job, using the task_id for correlation.
        """

        payload = SlurmClientRequest(
            username=username,
            work_dir=work_dir,
            slurm_file_content=sbatch_file,
            task_id=task_id,
        )
        url = f"{self.base_url}/jobs/submit"

        try:
            response = await self.http_client.post(
                url,
                json=payload.model_dump(mode="json"),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            error_msg = f"Network error connecting to scheduler at {url}: {e}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Slurm API returned error {e.response.status_code} for {url}: "
                f"{e.response.text}"
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e

    async def get_job_info(self, job_id: int):
        # This would take a Slurm job ID (int), not UUID
        pass


# Dependency Provider Function
def get_slurm_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> SlurmClient:
    """
    FastAPI dependency provider for SlurmClient.
    """
    settings = get_settings()
    if not settings.SLURM_CLIENT_BASE_URL:
        raise ValueError(
            "SLURM_CLIENT_BASE_URL is not configured correctly in settings."
        )
    return SlurmClient(base_url=str(settings.SLURM_CLIENT_BASE_URL), client=client)
