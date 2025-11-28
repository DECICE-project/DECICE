from unittest.mock import AsyncMock, MagicMock

import pytest

from clients.scheduler_controller.client import SchedulerControllerClient
from services.scheduler_controller_service import SchedulerControllerService


@pytest.fixture
def mock_scheduler_client() -> MagicMock:
    """Provides a mock of the SchedulerControllerClient with an awaitable 'schedule' method."""
    client = MagicMock(spec=SchedulerControllerClient)
    client.schedule = AsyncMock()
    return client


@pytest.fixture
def scheduler_service(mock_scheduler_client: MagicMock) -> SchedulerControllerService:
    """Provides an instance of SchedulerControllerService initialized with the mock client."""
    return SchedulerControllerService(client=mock_scheduler_client)


@pytest.mark.asyncio
class TestSchedulerControllerService:
    """Test suite for the SchedulerControllerService."""

    async def test_schedule_success(
        self,
        scheduler_service: SchedulerControllerService,
        mock_scheduler_client: MagicMock,
    ):
        """
        GIVEN valid scheduling data
        WHEN the schedule method is called
        THEN it should delegate the call to the client and return the client's response.
        """
        input_data = {"id": "some-uuid", "requirements": {"cpu": "1"}}
        expected_response = {"id": "some-uuid", "target_node": "node-1"}
        mock_scheduler_client.schedule.return_value = expected_response

        response = await scheduler_service.schedule(data=input_data, batch=False)

        mock_scheduler_client.schedule.assert_awaited_once_with(
            data=input_data, batch=False
        )
        assert response == expected_response

    async def test_schedule_propagates_connection_error(
        self,
        scheduler_service: SchedulerControllerService,
        mock_scheduler_client: MagicMock,
    ):
        """
        GIVEN the client raises a ConnectionError
        WHEN the schedule method is called
        THEN the service should propagate the same ConnectionError.
        """
        input_data = {"id": "some-uuid"}
        mock_scheduler_client.schedule.side_effect = ConnectionError(
            "Unable to connect"
        )

        with pytest.raises(ConnectionError, match="Unable to connect"):
            await scheduler_service.schedule(data=input_data)

    async def test_schedule_propagates_value_error(
        self,
        scheduler_service: SchedulerControllerService,
        mock_scheduler_client: MagicMock,
    ):
        """
        GIVEN the client raises a ValueError (e.g., from a 4xx response)
        WHEN the schedule method is called
        THEN the service should propagate the same ValueError.
        """
        input_data = {"id": "some-uuid"}
        mock_scheduler_client.schedule.side_effect = ValueError("Invalid input")

        with pytest.raises(ValueError, match="Invalid input"):
            await scheduler_service.schedule(data=input_data)

    async def test_schedule_handles_unexpected_error(
        self,
        scheduler_service: SchedulerControllerService,
        mock_scheduler_client: MagicMock,
    ):
        """
        GIVEN the client raises an unexpected error
        WHEN the schedule method is called
        THEN the service should catch it and raise a generic RuntimeError.
        """
        input_data = {"id": "some-uuid"}
        mock_scheduler_client.schedule.side_effect = TypeError(
            "Something unexpected happened"
        )

        with pytest.raises(RuntimeError, match="An unexpected error occurred"):
            await scheduler_service.schedule(data=input_data)
