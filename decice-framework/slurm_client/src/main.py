import logging
import sys
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from api import jobs, users, webhooks, root
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles the Slurm Clients's application startup, shutdown, and the lifecycle
    of all shared resources.
    """
    logger.info("Slurm Client application starting up...")
    settings = get_settings()
    app.state.settings = settings

    # Initialize Shared Clients
    logger.info("Initialize HTTP Client")
    http_headers = {
        "X-Internal-Api-Key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }
    http_limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    http_timeout = httpx.Timeout(timeout=10.0)
    http_client = httpx.AsyncClient(
        timeout=http_timeout, limits=http_limits, headers=http_headers
    )
    app.state.http_client = http_client

    yield

    # Graceful Shutdown
    logger.info("Slurm Client application shutting down...")
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
        logger.info("HTTP client shut down.")

    logger.info("Shutdown complete.")


app = FastAPI(
    title="Slurm API Client",
    version="1.0.0",
    description="FastAPI-based gateway for submitting jobs to Slurm via the REST API",
    lifespan=lifespan,
)

# Routes
app.include_router(root.router)
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(users.router, prefix="/accounting", tags=["users"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])


def main():
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.CLIENT_HOST,
        port=settings.CLIENT_PORT,
        reload=settings.RELOAD,
    )


if __name__ == "__main__":
    main()
