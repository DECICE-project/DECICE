import logging
import time

import redis
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.schemas import ComponentStatus, HealthCheckResponse

logger = logging.getLogger(__name__)
root_router = APIRouter()


@root_router.get(
    "/", include_in_schema=False, status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def home():
    """Redirects the root path to the API documentation."""
    return RedirectResponse(url="/docs/")


@root_router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Performs a deep health check of the service and its dependencies",
    tags=["health"],
)
async def health_check(request: Request):
    """
    Performs a deep health check of the service and its critical dependencies.

    - Checks if the application completed its startup sequence.
    - Performs a live PING to the Redis server.
    - Performs a live query to the PostgreSQL database.
    """
    component_statuses: dict[str, ComponentStatus] = {}
    is_overall_healthy = True

    # Check application startup
    startup_healthy = getattr(request.app.state, "startup_healthy", False)
    if startup_healthy:
        component_statuses["startup"] = ComponentStatus(
            status="OK", details="All components initialized successfully."
        )
    else:
        component_statuses["startup"] = ComponentStatus(
            status="ERROR", details="Application startup failed. Check logs."
        )
        is_overall_healthy = False

    # Live check for Redis
    try:
        redis_client: redis.Redis | None = getattr(
            request.app.state, "redis_client", None
        )
        if not redis_client:
            raise RuntimeError("Redis client not found in app state.")

        start_time = time.monotonic()
        await redis_client.ping()
        duration_ms = (time.monotonic() - start_time) * 1000
        component_statuses["redis"] = ComponentStatus(
            status="OK", details=f"Ping successful in {duration_ms:.2f} ms."
        )
    except Exception as e:
        component_statuses["redis"] = ComponentStatus(
            status="ERROR", details=f"Connection failed: {e}"
        )
        is_overall_healthy = False
        logger.error("Health Check: Redis connection failed.", exc_info=True)

    # Live check for PostgreSQL Database
    try:
        session_factory: async_sessionmaker[AsyncSession] | None = getattr(
            request.app.state, "db_session_factory", None
        )
        if not session_factory:
            raise RuntimeError("Database session factory not found in app state.")

        start_time = time.monotonic()
        async with session_factory() as session:
            # Execute a simple read only query.
            await session.execute(text("SELECT 1"))
        duration_ms = (time.monotonic() - start_time) * 1000
        component_statuses["database"] = ComponentStatus(
            status="OK", details=f"Connection successful in {duration_ms:.2f} ms."
        )
    except Exception as e:
        component_statuses["database"] = ComponentStatus(
            status="ERROR", details=f"Connection failed: {e}"
        )
        is_overall_healthy = False
        logger.error("Health Check: Database connection failed.", exc_info=True)

    # Determine final status
    if is_overall_healthy:
        response_status = status.HTTP_200_OK
        overall_status = "healthy"
        message = "Application and all dependencies are operational."
    else:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
        message = "One or more critical dependencies are not operational."

    health_response = HealthCheckResponse(
        overall_status=overall_status,
        message=message,
        components=component_statuses,
    )

    if not is_overall_healthy:
        raise HTTPException(
            status_code=response_status, detail=health_response.model_dump()
        )

    return health_response
