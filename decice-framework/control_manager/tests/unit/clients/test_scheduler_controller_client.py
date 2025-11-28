from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from clients.scheduler_controller.client import SchedulerControllerClient


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Provides a mock httpx.AsyncClient with an awaitable 'post' method."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.post = AsyncMock()
    return client


@pytest.fixture
def scheduler_client(mock_http_client: MagicMock) -> SchedulerControllerClient:
    """Provides an instance of SchedulerControllerClient with a mock client."""
    return SchedulerControllerClient(
        base_url="http://mock-scheduler:8020", client=mock_http_client
    )


class TestSchedulerControllerClient:
    """Test suite for the SchedulerControllerClient."""

    @pytest.mark.asyncio
    async def test_schedule_success(
        self, scheduler_client: SchedulerControllerClient, mock_http_client: MagicMock
    ):
        """
        GIVEN valid data and a successful API response
        WHEN the schedule method is called
        THEN it should make a POST request to the correct URL and return the JSON response.
        """
        expected_url = "http://mock-scheduler:8020/scheduler-controller"
        request_data = {"id": "job1", "cpu": 1}
        response_data = {"id": "job1", "node": "worker-1"}

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=response_data)
        mock_http_client.post.return_value = mock_response

        result = await scheduler_client.schedule(data=request_data)

        mock_http_client.post.assert_awaited_once_with(expected_url, json=request_data)
        mock_response.raise_for_status.assert_called_once()
        assert result == response_data

    @pytest.mark.asyncio
    async def test_schedule_handles_request_error(
        self, scheduler_client: SchedulerControllerClient, mock_http_client: MagicMock
    ):
        request_data = {"id": "job1"}
        request_error = httpx.RequestError("Connection failed", request=None)
        mock_http_client.post.side_effect = request_error

        with pytest.raises(
            ConnectionError, match="Network error connecting to Scheduler Controller"
        ):
            await scheduler_client.schedule(data=request_data)

    @pytest.mark.asyncio
    async def test_schedule_handles_http_status_error(
        self, scheduler_client: SchedulerControllerClient, mock_http_client: MagicMock
    ):
        request_data = {"id": "job1"}
        mock_response = httpx.Response(
            status_code=400, text="Bad Request", request=None
        )
        status_error = httpx.HTTPStatusError(
            message="Bad Request", request=None, response=mock_response
        )
        mock_http_client.post.side_effect = status_error

        with pytest.raises(ValueError, match="Scheduler Controller request failed"):
            await scheduler_client.schedule(data=request_data)

    @pytest.mark.asyncio
    async def test_schedule_handles_unexpected_error(
        self, scheduler_client: SchedulerControllerClient, mock_http_client: MagicMock
    ):
        request_data = {"id": "job1"}
        mock_http_client.post.side_effect = TypeError("Unexpected issue")

        with pytest.raises(RuntimeError, match="An unexpected error occurred"):
            await scheduler_client.schedule(data=request_data)

    def test_initialization_fails_with_empty_url(self, mock_http_client: MagicMock):
        """
        GIVEN an empty base_url
        WHEN the client is initialized
        THEN it must raise a ValueError.
        """
        with pytest.raises(
            ValueError,
            match="Scheduler Controller base URL provided to client cannot be empty",
        ):
            SchedulerControllerClient(base_url="", client=mock_http_client)
