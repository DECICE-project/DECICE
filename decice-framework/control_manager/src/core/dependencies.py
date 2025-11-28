import logging
from typing import AsyncGenerator

import httpx
import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a SQLAlchemy AsyncSession from the factory
    stored in app.state.
    """
    session_factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "db_session_factory", None
    )

    if session_factory is None:
        logger.error(
            "Database session factory 'db_session_factory' not found in application state! "
            "Check lifespan function."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service is not available.",
        )

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            logger.exception("Exception in request, rolling back DB session.")
            await session.rollback()
            raise
        finally:
            logger.debug("Closing DB session.")


async def get_redis_client(request: Request) -> redis.Redis:
    """
    FastAPI dependency to retrieve the shared redis.Redis client instance
    created during application lifespan startup and stored in app.state.
    """
    redis_client: redis.Redis | None = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
        logger.error(
            "Redis client not found in application state! Check lifespan setup and Redis connection."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session storage service is not available.",
        )
    return redis_client
