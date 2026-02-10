import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from api import api as main_api
from api.api import create_app
from auth.dependencies import get_current_active_user
from config.config import get_settings
from core.dependencies import get_db_session
from db.models import Base
from domain.user_schemas import PlatformIdentityResponse, User, UserRole


# Container Fixtures (Session-Scoped)
@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Spins up a real PostgreSQL container for the entire test session."""
    with PostgresContainer("postgres:15-alpine", driver="psycopg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container() -> Generator[tuple[RedisContainer, str], None, None]:
    """Spins up a real Redis container and provides its URL."""
    with RedisContainer() as redis:
        redis_url = (
            f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}"
        )
        yield redis, redis_url


# Core Test Fixtures
@pytest.fixture(scope="function")
def test_client(
    test_db_session: AsyncSession,
    postgres_container: PostgresContainer,
    redis_container: tuple[RedisContainer, str],
    monkeypatch,
) -> Generator[TestClient, None, None]:
    """
    The central test fixture. It configures the environment, creates the app,
    and yields a TestClient. This new structure ensures settings are loaded
    correctly *before* the app is initialized.
    """
    pg_url = postgres_container.get_connection_url().replace(
        "postgresql://", "postgresql+psycopg://"
    )
    _, redis_url = redis_container

    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("SESSION_EXPIRE_SECONDS", "1800")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
    )
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOWED_METHODS", "*")
    monkeypatch.setenv("CORS_ALLOWED_HEADERS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "True")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "control-manager-test")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", "")
    monkeypatch.setenv("DT_HOST", "mock-digital-twin")
    monkeypatch.setenv("PROMQL_WRAPPER_HOST", "mock-promql-wrapper")
    monkeypatch.setenv("PSGC_HOST", "mock-psgc")
    monkeypatch.setenv("SCHEDULER_HOST", "mock-ai-scheduler")
    monkeypatch.setenv("SC_HOST", "mock-scheduler-controller")
    monkeypatch.setenv("INTERNAL_API_KEY", "XuTThABy4NY__123456")

    # Clear the lru_cache for get_settings to ensure it reloads the new env vars
    get_settings.cache_clear()

    app = create_app()

    # Apply dependency overrides
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as client:
        # Attach app to client for access in other fixtures
        client.app = app
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a clean database and provides a single session for one test function.
    """
    pg_url = postgres_container.get_connection_url().replace(
        "postgresql://", "postgresql+psycopg://"
    )
    engine = create_async_engine(pg_url)
    TestingSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_platform_identity() -> PlatformIdentityResponse:
    """Provides a mock Pydantic PlatformIdentityResponse schema."""
    return PlatformIdentityResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),  # This will be overwritten by the user fixture
        platform="slurm",
        platform_username="testuser",
        default_working_dir="/home/testuser",
    )


@pytest.fixture
def mock_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    user_id = uuid.uuid4()
    mock_platform_identity.user_id = user_id  # Link them
    return User(
        id=user_id,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        active=True,
        role=UserRole.USER,
        project="decice",
        platform_identity=mock_platform_identity,  # 👈 ADDED
    )


@pytest.fixture
def mock_admin_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    user_id = uuid.uuid4()
    # Create a separate identity for the admin
    admin_identity = mock_platform_identity.model_copy(
        update={
            "id": uuid.uuid4(),
            "user_id": user_id,
            "platform_username": "adminuser",
        }
    )
    return User(
        id=user_id,
        username="adminuser",
        email="admin@example.com",
        full_name="Admin User",
        active=True,
        role=UserRole.ADMIN,
        project="decice-admin",
        platform_identity=admin_identity,  # 👈 ADDED
    )


@pytest.fixture
def authenticated_client(
    test_client: TestClient, mock_user: User
) -> Generator[TestClient, None, None]:
    """Provides an authenticated TestClient for a standard user."""

    async def override_get_current_active_user() -> User:
        return mock_user

    # Access the app instance that was attached to the client
    app = test_client.app
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    yield test_client
    del app.dependency_overrides[get_current_active_user]


@pytest.fixture
def admin_authenticated_client(
    test_client: TestClient, mock_admin_user: User
) -> Generator[TestClient, None, None]:
    """Provides an admin-authenticated TestClient."""

    async def override_get_current_active_user() -> User:
        return mock_admin_user

    app = test_client.app
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    yield test_client
    del app.dependency_overrides[get_current_active_user]
