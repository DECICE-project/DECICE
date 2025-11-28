import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio.connection import ConnectionPool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.config import get_settings
from db import db as db_module
from db.models import Base

from . import APIVersion, Tags
from .auth.router import auth_router
from .internal.router import internal_service_router
from .root import root_router
from .scheduling.router import schedule_router
from .users.router import user_router
from .workflows.router import workflow_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Application starting up...", extra={"event": "startup"})

        settings = get_settings()
        app.state.settings = settings
        app.state.startup_healthy = False

        logger.info(
            "Creating database engine", extra={"db.url": str(settings.DATABASE_URL)}
        )
        db_module.engine = create_async_engine(settings.DATABASE_URL)

        logger.info("Creating async session maker")
        session_factory = async_sessionmaker(
            bind=db_module.engine, expire_on_commit=False
        )
        app.state.db_session_factory = session_factory
        logger.info("Async session maker setup complete")

        # TODO: For production,use a migration tool like Alembic.
        # For testing and development, this creates the schema.
        logger.info("Connecting to DB to create tables")
        async with db_module.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")

        # HTTP Client Setup
        logger.info("Setting up HTTP client")
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
        logger.info("HTTP client setup complete")

        # Redis Client Setup
        logger.info("Connecting to Redis", extra={"redis.url": str(settings.REDIS_URL)})
        redis_pool: ConnectionPool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        redis_client = redis.Redis.from_pool(redis_pool)
        await redis_client.ping()
        app.state.redis_client = redis_client
        app.state.redis_pool = redis_pool
        logger.info("Redis connection successful")

        app.state.startup_healthy = True
        logger.info(
            f"{"\033[92m"}Lifespan: Startup Complete{"\033[0m"}",
            extra={"event": "startup_complete"},
        )
    except Exception as e:
        logger.critical("Fatal error during application startup", exc_info=True)
        logger.critical(f"Error Type: {type(e).__name__}, Message: {e}")
        raise

    yield

    # Shutdown
    logger.info(
        f"{"\033[92m"}Lifespan: Shutdown Sequence Starting{"\033[0m"}",
        extra={"event": "shutdown"},
    )

    # Dispose engine
    if db_module.engine:
        await db_module.engine.dispose()
        logger.info("Database engine disposed.")

    # Redis Shutdown
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        logger.info("Closing Redis client connection...")
        try:
            await app.state.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    if hasattr(app.state, "redis_pool") and app.state.redis_pool:
        logger.info("Disconnecting Redis connection pool...")
        try:
            await app.state.redis_pool.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")
    logger.info("Redis resources closed.")

    # Close the shared HTTP client gracefully
    if hasattr(app.state, "http_client"):
        logger.info("Closing shared HTTP client connections...")
        await app.state.http_client.aclose()
        logger.info("Shared HTTP client closed.")
    else:
        logger.warning("No shared HTTP client found in app state during shutdown.")

    logging.info(f"{"\033[92m"}Lifespan: Shutdown Complete{"\033[0m"}")


# FastAPI App Instantiation
def create_app() -> FastAPI:
    """
    Creates and configures the main FastAPI application instance by assembling
    all the necessary components (middleware, routers, etc.).
    """
    settings = get_settings()

    app = FastAPI(
        title="DECICE Control Manager",
        description="DECICE Control Manager OpenAPI specification.",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOWED_METHODS,
        allow_headers=settings.CORS_ALLOWED_HEADERS,
    )

    # Application-level routes
    app.include_router(root_router)

    # Domain-specific routes with a version prefix
    app.include_router(auth_router, prefix=APIVersion.v1, tags=[Tags.auth])
    app.include_router(user_router, prefix=APIVersion.v1, tags=[Tags.user])
    app.include_router(workflow_router, prefix=APIVersion.v1, tags=[Tags.workflow])
    app.include_router(schedule_router, prefix=APIVersion.v1, tags=[Tags.schedule])
    app.include_router(
        internal_service_router, prefix=APIVersion.v1, tags=[Tags.internal]
    )

    return app
