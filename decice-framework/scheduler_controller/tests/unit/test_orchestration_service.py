import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from clients.digital_twin import DigitalTwinClient
from clients.scheduler import SchedulerClient
from models.models import (
    ClusterState,
    HardwareRequirements,
    Node,
    ScheduleRequest,
    Task,
    Vertexpool,
)
from services.orchestration import OrchestrationService, get_orchestration_service


@pytest.fixture
def mock_cluster_state() -> ClusterState:
    """Provides a realistic, mock ClusterState object."""
    return ClusterState(
        lastUpdated=123456789.0,
        vertexpools=[
            Vertexpool(
                id="vp-1",
                vertexpool_labels=None,
                nodes=[Node(id="node-1", name="Test Node")],
                devices=[],
            )
        ],
        links=[],
    )


@pytest.fixture
def mock_dt_client(mock_cluster_state: ClusterState) -> AsyncMock:
    """Provides a mock DigitalTwinClient."""
    client = AsyncMock(spec=DigitalTwinClient)
    client.get_state = AsyncMock(return_value=mock_cluster_state)
    return client


@pytest.fixture
def mock_scheduler_client() -> AsyncMock:
    """Provides a mock SchedulerClient."""
    client = AsyncMock(spec=SchedulerClient)
    client.schedule = AsyncMock(
        return_value={"placements": [], "scheduling_duration_ms": 10.0}
    )
    return client


@pytest.fixture
def sample_task() -> Task:
    """Provides a valid Task object."""
    return Task(
        id=uuid.uuid4(),
        requirements=HardwareRequirements(required_cpu=1, required_memory="512Mi"),
    )


class TestOrchestrationService:
    @pytest.mark.asyncio
    async def test_process_scheduling_success(
        self,
        mock_dt_client: AsyncMock,
        mock_scheduler_client: AsyncMock,
        mock_cluster_state: ClusterState,
        sample_task: Task,
    ):
        """
        GIVEN a valid Task
        WHEN process_scheduling is called
        THEN it should fetch DT state, wrap the task in a ScheduleRequest, and call the Scheduler.
        """
        service = OrchestrationService(
            dt_client=mock_dt_client, scheduler_client=mock_scheduler_client
        )

        result = await service.process_scheduling(sample_task)

        mock_dt_client.get_state.assert_awaited_once()

        mock_scheduler_client.schedule.assert_awaited_once()

        call_args = mock_scheduler_client.schedule.call_args[0]
        sent_request = call_args[0]

        assert isinstance(sent_request, ScheduleRequest)
        assert sent_request.cluster == mock_cluster_state
        assert len(sent_request.tasks) == 1
        assert sent_request.tasks[0] == sample_task

        assert result == {"placements": [], "scheduling_duration_ms": 10.0}

    @pytest.mark.asyncio
    async def test_process_scheduling_handles_dt_client_exception(
        self,
        mock_dt_client: AsyncMock,
        mock_scheduler_client: AsyncMock,
        sample_task: Task,
    ):
        """
        GIVEN the DigitalTwinClient raises an HTTPException (e.g., DT unavailable)
        WHEN process_scheduling is called
        THEN it should propagate the exception and NOT call the Scheduler.
        """
        mock_dt_client.get_state.side_effect = HTTPException(
            status_code=503, detail="DT is down"
        )

        service = OrchestrationService(
            dt_client=mock_dt_client, scheduler_client=mock_scheduler_client
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.process_scheduling(sample_task)

        assert exc_info.value.status_code == 503
        assert "DT is down" in exc_info.value.detail

        mock_scheduler_client.schedule.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_scheduling_handles_scheduler_exception(
        self,
        mock_dt_client: AsyncMock,
        mock_scheduler_client: AsyncMock,
        sample_task: Task,
    ):
        """
        GIVEN the SchedulerClient raises an error
        WHEN process_scheduling is called
        THEN it should propagate the exception.
        """
        mock_scheduler_client.schedule.side_effect = ValueError(
            "Scheduler Internal Error"
        )

        service = OrchestrationService(
            dt_client=mock_dt_client, scheduler_client=mock_scheduler_client
        )

        with pytest.raises(ValueError) as exc_info:
            await service.process_scheduling(sample_task)

        assert "Scheduler Internal Error" in str(exc_info.value)

        # DT should have been called, but Scheduler failed
        mock_dt_client.get_state.assert_awaited_once()
        mock_scheduler_client.schedule.assert_awaited_once()


def test_get_orchestration_service(
    mock_dt_client: AsyncMock, mock_scheduler_client: AsyncMock
):
    """Tests the dependency injection provider function."""

    service = get_orchestration_service(
        dt_client=mock_dt_client, scheduler_client=mock_scheduler_client
    )

    assert isinstance(service, OrchestrationService)
    assert service.dt_client == mock_dt_client
    assert service.scheduler_client == mock_scheduler_client
