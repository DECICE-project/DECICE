from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session, get_http_client, get_redis_client


@pytest.fixture
def mock_request():
    """Fixture for a mock FastAPI Request object."""
    request = MagicMock(spec=Request)
    request.app.state = MagicMock()
    return request


@pytest.mark.asyncio
async def test_get_http_client_success(mock_request):
    """Test successful retrieval of httpx.AsyncClient from app state."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_request.app.state.http_client = mock_client

    client = await get_http_client(mock_request)
    assert client == mock_client


@pytest.mark.asyncio
async def test_get_http_client_not_found(mock_request):
    """Test HTTPException when httpx.AsyncClient is not found in app state."""
    mock_request.app.state.http_client = None

    with pytest.raises(HTTPException) as exc_info:
        await get_http_client(mock_request)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "HTTP client service is not available." in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_db_session_yields_session(mock_request):
    """
    Test that get_db_session yields an AsyncSession when the factory
    is correctly set in app.state.
    """
    mock_session = AsyncMock(spec=AsyncSession)

    mock_async_context_manager = AsyncMock()
    mock_async_context_manager.__aenter__.return_value = mock_session
    mock_async_context_manager.__aexit__.return_value = (
        False  # Ensures no exception is re-raised
    )

    mock_session_factory = MagicMock(return_value=mock_async_context_manager)

    mock_request.app.state.db_session_factory = mock_session_factory

    session_yielded = False
    async for session in get_db_session(request=mock_request):
        assert session is mock_session
        assert isinstance(session, AsyncSession)
        session_yielded = True

    assert session_yielded, "The dependency did not yield a session."
    mock_session_factory.assert_called_once()
    mock_async_context_manager.__aenter__.assert_called_once()
    mock_async_context_manager.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_get_db_session_factory_not_found(mock_request):
    """
    Test that get_db_session raises an HTTPException if the session factory
    is not found in the application state.
    """
    if hasattr(mock_request.app.state, "db_session_factory"):
        delattr(mock_request.app.state, "db_session_factory")

    with pytest.raises(HTTPException) as exc_info:
        async for _ in get_db_session(request=mock_request):
            pass

    assert exc_info.value.status_code == 500
    assert "Database service is not available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_redis_client_success(mock_request):
    """Test successful retrieval of redis.Redis client from app state."""
    mock_redis_client = MagicMock(spec=redis.Redis)
    mock_request.app.state.redis_client = mock_redis_client

    client = await get_redis_client(mock_request)
    assert client == mock_redis_client


@pytest.mark.asyncio
async def test_get_redis_client_not_found(mock_request):
    """Test HTTPException when redis.Redis client is not found in app state."""
    mock_request.app.state.redis_client = None

    with pytest.raises(HTTPException) as exc_info:
        await get_redis_client(mock_request)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Session storage service is not available." in exc_info.value.detail
