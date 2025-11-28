import logging
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, status

from config.config import get_settings
from models.models import Task
from services.orchestration import (OrchestrationService,
                                    get_orchestration_service)
from auth.auth import verify_internal_traffic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...", extra={"event": "startup"})

    settings = get_settings()
    app.state.settings = settings

    # HTTP Client Setup
    logger.info("Initialize HTTP Client")
    http_headers = {
        "X-Internal-Api-Key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }
    http_limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    http_timeout = httpx.Timeout(timeout=10.0)
    shared_http_client = httpx.AsyncClient(
        timeout=http_timeout, limits=http_limits, headers=http_headers
    )
    app.state.http_client = shared_http_client
    logger.info("HTTP Client setup complete")

    yield

    # Close the shared HTTP client gracefully
    if hasattr(app.state, "http_client"):
        logger.info("Closing shared HTTP client connections...")
        await app.state.http_client.aclose()
        logger.info("Shared HTTP client closed.")
    else:
        logger.warning("No shared HTTP client found in app state during shutdown.")

    logging.info("Application shutdown complete.")


app = FastAPI(
    title="DECICE Scheduler Controller",
    description="DECICE Scheduler Controller",
    lifespan=lifespan,
    docs_url="/",
)


@app.post("/scheduler-controller", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_internal_traffic)],)
async def schedule_tasks(
    task: Task,
    service: OrchestrationService = Depends(get_orchestration_service),
):
    """
    Receives a workflow task, enriches it with node data from the Digital Twin,
    and forwards it to the Scheduler to get a placement decision.
    """
    try:
        response_data = await service.process_scheduling(task)
        return response_data
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.exception("An unexpected internal error occurred in the API layer.")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal error occurred: {exc}"
        )


@app.post("/scheduler-controller-batch", status_code=status.HTTP_201_CREATED)
async def schedule_tasks(
    tasks: list[Task],
    service: OrchestrationService = Depends(get_orchestration_service),
):
    """
    Receives workflow tasks, enriches it with node data from the Digital Twin,
    and forwards it to the Scheduler to get a placement decisions.
    """
    try:
        response_data = await service.process_scheduling_batch(tasks)
        return response_data
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.exception("An unexpected internal error occurred in the API layer.")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal error occurred: {exc}"
        )


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    description="Health check",
    summary="Health check",
)
async def health_check():
    return status.HTTP_200_OK
