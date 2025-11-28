from typing import Generator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from fastapi.testclient import TestClient
from minio import Minio
from testcontainers.core.container import DockerContainer
from testcontainers.minio import MinioContainer
from testcontainers.redis import RedisContainer

from api import app
from config import get_settings


@pytest.fixture(scope="session")
def minio_container() -> Generator[DockerContainer, None, None]:
    """Spins up a MinIO container for the test session."""
    with MinioContainer() as minio:
        yield minio


@pytest.fixture
def minio_client(minio_container: MinioContainer) -> Minio:
    """Provides a configured MinIO client connected to the test container."""
    return minio_container.get_client()


@pytest.fixture(scope="session")
def minio_endpoint(minio_container: MinioContainer) -> str:
    """Provides the endpoint URL for the running MinIO test container."""
    return minio_container.get_config()["endpoint"]


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """
    Spins up a Redis container once for the entire test session using the
    specialized RedisContainer class.
    """
    with RedisContainer() as redis:
        yield redis


@pytest_asyncio.fixture
async def redis_client(redis_container: RedisContainer) -> redis.Redis:
    """
    Provides a configured async Redis client for a single test function.
    It connects to the session-scoped container and ensures the database is
    clean after the test completes.
    """
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = redis.Redis(host=host, port=port, decode_responses=True)

    await client.ping()

    yield client

    await client.flushdb()
    await client.close()


@pytest.fixture
def test_client(
    minio_container: DockerContainer,
    redis_container: RedisContainer,
    monkeypatch,
) -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient that is configured to connect to the
    live test containers for Redis and MinIO.
    """
    minio_endpoint = f"{minio_container.get_container_host_ip()}"
    minio_port = f"{minio_container.get_exposed_port(9000)}"
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    # Monkeypatch env variables
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("SESSION_EXPIRE_SECONDS", "1800")
    monkeypatch.setenv("MINIO_ENDPOINT", minio_endpoint)
    monkeypatch.setenv("MINIO_PORT", minio_port)
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECURE", "False")
    monkeypatch.setenv("CM_SERVICE_HOST", "mock-control-manager")
    monkeypatch.setenv("SLURM_CLIENT_HOST", "mock-slurm-client")
    monkeypatch.setenv("SLURM_CLIENT_PORT", "8060")
    monkeypatch.setenv("INTERNAL_API_KEY", "XuTThABy4NY__123456")
    get_settings.cache_clear()

    with TestClient(app) as client:
        yield client

    get_settings.cache_clear()
