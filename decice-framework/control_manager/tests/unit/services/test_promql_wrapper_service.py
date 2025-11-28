from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from clients.promql_wrapper.client import PromQLWrapperClient
from services.promql_wrapper_service import PromQLWrapperService


@pytest.fixture
def mock_promql_client() -> AsyncMock:
    """Provides a mock of the PromQLWrapperClient with an awaitable pool method."""
    return AsyncMock(spec=PromQLWrapperClient)


@pytest.fixture
def promql_service(mock_promql_client: AsyncMock) -> PromQLWrapperService:
    """Provides an instance of PromQLWrapperService initialized with the mock client."""
    return PromQLWrapperService(client=mock_promql_client)


class TestPromQLWrapperService:
    """Test suite for the refactored PromQLWrapperService."""

    @pytest.mark.asyncio
    async def test_pool_delegates_to_client(
        self, promql_service: PromQLWrapperService, mock_promql_client: AsyncMock
    ):
        """
        GIVEN a healthy client
        WHEN the service's pool method is called
        THEN it should delegate the call directly to the client's pool method
        AND return its result.
        """
        expected_response = {"status": "success", "data": [1, 2, 3]}
        mock_promql_client.pool.return_value = expected_response

        response_data = await promql_service.pool()

        mock_promql_client.pool.assert_awaited_once()

        assert response_data == expected_response

    @pytest.mark.asyncio
    async def test_pool_propagates_http_exception_from_client(
        self, promql_service: PromQLWrapperService, mock_promql_client: AsyncMock
    ):
        """
        GIVEN a client that raises an HTTPException
        WHEN the service's pool method is called
        THEN the service should propagate that same HTTPException.
        """
        http_exception = HTTPException(status_code=404, detail="Not Found")
        mock_promql_client.pool.side_effect = http_exception

        with pytest.raises(HTTPException) as exc_info:
            await promql_service.pool()

        assert exc_info.value is http_exception
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_pool_wraps_unexpected_client_error_in_runtime_error(
        self, promql_service: PromQLWrapperService, mock_promql_client: AsyncMock
    ):
        """
        GIVEN a client that raises a non-HTTP, unexpected exception
        WHEN the service's pool method is called
        THEN the service should catch it and raise a generic RuntimeError.
        """
        mock_promql_client.pool.side_effect = ValueError("A strange client error")

        with pytest.raises(RuntimeError) as exc_info:
            await promql_service.pool()

        assert isinstance(exc_info.value.__cause__, ValueError)
        assert "A strange client error" in str(exc_info.value.__cause__)
