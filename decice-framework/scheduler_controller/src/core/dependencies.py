import logging

import httpx
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    FastAPI dependency to retrieve the shared httpx.AsyncClient instance.

    The client instance is created during application startup via the lifespan
    manager and stored in `request.app.state.http_client`.
    """
    http_client: httpx.AsyncClient | None = getattr(
        request.app.state, "http_client", None
    )

    if http_client is None:
        logger.error(
            "Shared httpx.AsyncClient 'http_client' not found in application state! Check lifespan function."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HTTP client service is not available.",
        )

    return http_client
