import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse

from auth.auth import verify_internal_traffic
from clients.digital_twin import DigitalTwinClient
from config.config import ServiceSettings, get_settings
from services.snapshot_service import SnapshotService, get_snapshot_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def update_dt_background_task(service: SnapshotService):
    """The background task, now receiving the service as a dependency."""
    settings = get_settings()
    logger.info(
        f"Background update enabled. Will update Digital-Twin every {settings.AUTO_UPDATE_DT_FREQUENCY_SECONDS} seconds."
    )
    while True:
        try:
            logger.info("Performing periodic Digital-Twin update...")
            await service.create_and_post_snapshot()
        except Exception:
            logger.exception(
                "An error occurred during the periodic Digital-Twin update."
            )

        await asyncio.sleep(settings.AUTO_UPDATE_DT_FREQUENCY_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's lifespan, including the background task."""
    logger.info("Application starting up...", extra={"event": "startup"})
    settings = get_settings()

    # HTTP Client Setup
    logger.info("Initialize HTTP Client")
    http_headers = {
        "X-Internal-Api-Key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }
    http_limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    http_timeout = httpx.Timeout(timeout=10.0)
    shared_http_client = httpx.AsyncClient(
        timeout=http_timeout, limits=http_limits, headers=http_headers
    )
    app.state.http_client = shared_http_client
    logger.info("HTTP Client setup complete")

    update_task = None
    if settings.AUTO_UPDATE_DT_ENABLED:
        # Manually create the service for the background task
        dt_client = DigitalTwinClient(
            client=shared_http_client, base_url=str(settings.DT_BASE_URL)
        )
        snapshot_service = SnapshotService(dt_client=dt_client)

        # Start the background task
        update_task = asyncio.create_task(update_dt_background_task(snapshot_service))

    yield

    logger.info("Application shutting down...")
    if update_task:
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            logger.info("Background update task was successfully cancelled.")

    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
        logger.info("Shared HTTP client closed.")


app = FastAPI(
    title="Prometheus JSON Wrapper",
    description="A service to fetch data from Prometheus, transform it, and post it to the DECICE Digital Twin.",
    version="0.4.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def home():
    return RedirectResponse(url="/docs/")


@app.post(
    "/pool",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a Manual Digital Twin Update",
    description="Triggers a one-off task to fetch data from Prometheus and update the Digital Twin.",
    dependencies=[Depends(verify_internal_traffic)],
)
async def trigger_manual_update(
    service: SnapshotService = Depends(get_snapshot_service),
):
    try:
        logger.info("Manual Digital Twin update triggered via /pool endpoint.")
        await service.create_and_post_snapshot()
        logger.info("Manual Digital Twin update completed successfully.")
        return {"message": "Digital Twin update completed successfully."}
    except HTTPException as exc:
        logger.warning(
            f"A handled HTTP error occurred during the manual update: {exc.detail}"
        )
        raise exc
    except Exception as exc:
        logger.exception(
            f"An unexpected internal error occurred during the manual update: {exc}"
        )
        raise HTTPException(
            status_code=500, detail="An unexpected internal error occurred."
        )


@app.get("/health", status_code=status.HTTP_200_OK, summary="Health Check")
async def health_check():
    return {"status": status.HTTP_200_OK}


@app.get("/settings", response_model=ServiceSettings, summary="Get Service Settings")
async def get_service_settings() -> ServiceSettings:
    return get_settings()
