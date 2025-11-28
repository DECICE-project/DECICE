import asyncio
import logging
import time
from typing import Dict, List, Tuple
from uuid import UUID

import httpx
from fastapi import Depends

from config import get_settings
from core.dependencies import get_http_client
from io_models import TaskCompletionRequest, TaskStatusUpdateRequest

logger = logging.getLogger(__name__)


class AsyncBatcher:
    """
    Small async utility that batches near-simultaneous calls into a single
    request. Items submitted within a short window are grouped together
    (up to a max batch size), and worker_fn is invoked once with the whole
    batch instead of one call per item.
    """

    def __init__(self, worker_fn, max_wait_ms=5, max_batch_size=32):
        self.worker_fn = worker_fn
        self.queue: asyncio.Queue[Tuple[Dict, asyncio.Future]] = asyncio.Queue()
        self.max_wait = max_wait_ms / 1000
        self.max_batch_size = max_batch_size
        self._task = asyncio.create_task(self._worker())

    async def submit(self, payload: Dict) -> Dict:
        fut = asyncio.get_event_loop().create_future()
        await self.queue.put((payload, fut))
        return await fut

    async def _worker(self):
        while True:
            payload, fut = await self.queue.get()
            batch = [(payload, fut)]
            start = time.perf_counter()

            # collect batch
            while len(batch) < self.max_batch_size:
                remaining = self.max_wait - (time.perf_counter() - start)
                if remaining <= 0:
                    break

                try:
                    payload, fut = await asyncio.wait_for(
                        self.queue.get(), timeout=remaining
                    )
                    batch.append((payload, fut))
                except asyncio.TimeoutError:
                    break

            payloads = [p for p, _ in batch]
            futures = [f for _, f in batch]

            try:
                result = await self.worker_fn(payloads)
                for f in futures:
                    if not f.done():
                        f.set_result(result)
            except Exception as e:
                for f in futures:
                    if not f.done():
                        f.set_exception(e)


class CMClient:
    """
    A client for the PSGC to make API calls back to the Control Manager.
    Handles network communication and error handling.
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient,
        enable_batching=False,
        batch_max_size=32,
        batch_max_wait_ms=1000,
    ):
        """
        Initializes the client.

        Args:
            base_url: The base URL for the CM service (injected).
            client: An httpx.AsyncClient instance for making requests (injected).
        """
        self.http_client = client
        if not base_url:
            raise ValueError("CM base URL cannot be empty.")
        self.base_url = base_url.rstrip("/")
        logger.info(f"CMClient initialized. Base URL: {self.base_url}")

        self.enable_batching = enable_batching
        self.batch_max_size = batch_max_size
        self.batch_max_wait_ms = batch_max_wait_ms

        if self.enable_batching:
            logger.info(
                f"Scheduler batching ENABLED: size={self.batch_max_size}, wait={self.batch_max_wait_ms}ms"
            )
            self._decision_batcher = AsyncBatcher(
                worker_fn=self._call_scheduler_batch,
                max_batch_size=self.batch_max_size,
                max_wait_ms=self.batch_max_wait_ms,
            )
        else:
            logger.info("Scheduler batching DISABLED")
            self._decision_batcher = None

    async def get_scheduling_decision(self, task_id: UUID, requirements: dict) -> dict:
        """
        Calls the CM's central scheduler to get a placement decision for a task.
        """
        payload = {"id": str(task_id), "requirements": requirements}

        # Use batcher if enabled
        if self._decision_batcher:
            return await self._decision_batcher.submit(payload)

        return await self._call_scheduler_single(payload)

    async def _call_scheduler_single(self, payload: dict) -> dict:
        "Send a scheduling request payload for a task to the CM and return the ScheduleResponse."

        url = f"{self.base_url}/schedule/schedule"
        logger.info(f"Requesting scheduling decision for task {payload} from {url}")

        try:
            response = await self.http_client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            error_msg = f"Network error connecting to CM scheduler at {url}: {e}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"CM scheduler request failed at {url} with status {e.response.status_code}. "
                f"Response: {e.response.text[:200]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def _call_scheduler_batch(self, batch_payloads: List[dict]) -> dict:
        """Send a scheduling request for list of task payloads to the CM and return the ScheduleResponse."""

        url = f"{self.base_url}/schedule/batch_schedule"
        logger.info(
            f"Requesting scheduling decision for task payloads {batch_payloads} from {url}"
        )

        try:
            response = await self.http_client.post(
                url, json=batch_payloads, timeout=15.0
            )
            response.raise_for_status()

            data = response.json()
            return data

        except httpx.RequestError as e:
            error_msg = f"Network error performing scheduler batch at {url}: {e}"
            logger.error(msg, exc_info=True)
            raise ConnectionError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = (
                f"Scheduler batch failed at {url} with status "
                f"{e.response.status_code}: {e.response.text[:200]}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def patch_task_status(self, task_id: UUID, status: str, detail: str):
        """
        Calls the CM's callback endpoint to patch a non-terminal status
        (e.g., PENDING, RUNNING).
        """
        url = f"{self.base_url}/internal/task/{task_id}/status"

        payload = TaskStatusUpdateRequest(status=status, detail=detail)

        try:
            response = await self.http_client.patch(
                url, json=payload.model_dump(mode="json"), timeout=15.0
            )
            response.raise_for_status()
            logger.info(
                f"Successfully patched status for task {task_id} with {payload.model_dump_json()}"
            )
        except httpx.RequestError as e:
            error_msg = f"Network error patching task status to {url}: {e}."
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Failed patching task status at {url} with status {e.response.status_code} for {task_id} "
                f"Response: {e.response.text[:200]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def report_task_completion(
        self, task_id: UUID, completion_status: str, detail: str
    ):
        """
        Calls the CM's callback endpoint to report a terminal status.
        (e.g., SUCCEEDED, FAILED, CANCELLED)
        """
        url = f"{self.base_url}/internal/task/{task_id}/status"

        payload = TaskCompletionRequest(status=completion_status, detail=detail)

        logger.info(f"Reporting task completion for {task_id} to {url}")

        try:
            # Use PATCH here, as the CM's endpoint is the same for all status updates
            response = await self.http_client.patch(
                url, json=payload.model_dump(mode="json"), timeout=15.0
            )
            response.raise_for_status()
            logger.info(f"Successfully reported completion for task {task_id}")
        except httpx.RequestError as e:
            error_msg = f"Network error reporting task completion to {url}: {e}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Reporting task completion failed at {url} with status {e.response.status_code}. "
                f"Response: {e.response.text[:200]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def report_workflow_status(self, workflow_id: UUID, status: str):
        """
        Calls the CM's callback endpoint to report the status of an entire workflow.
        """
        url = f"{self.base_url}/internal/workflow/{workflow_id}/status"
        payload = {"status": status, "detail": "Status updated by PSGC."}
        logger.info(f"Reporting workflow status for {workflow_id} to {url}")

        try:
            response = await self.http_client.patch(url, json=payload, timeout=15.0)
            response.raise_for_status()
            logger.info(f"Successfully reported status for workflow: {workflow_id}")
        except httpx.RequestError as e:
            error_msg = f"Network error reporting workflow status to {url}: {e}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Reporting workflow status failed at {url} with status {e.response.status_code}. "
                f"Response: {e.response.text[:200]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e


# Dependency Provider Function
def get_cm_client(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> CMClient:
    """
    FastAPI dependency provider for CMClient.
    Injects the base URL, scheduler batch request options from settings and a shared HTTP client.
    """
    settings = get_settings()
    if not settings.CM_SERVICE_BASE_URL:
        raise ValueError("CM_BASE_URL is not configured correctly in settings.")

    return CMClient(
        base_url=str(settings.CM_SERVICE_BASE_URL),
        client=client,
        enable_batching=settings.SCHEDULER_BATCHING_ENABLED,
        batch_max_size=settings.SCHEDULER_BATCH_MAX_SIZE,
        batch_max_wait_ms=settings.SCHEDULER_BATCH_MAX_WAIT_MS,
    )
