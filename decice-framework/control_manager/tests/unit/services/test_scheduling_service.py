import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import SchedulingDecision, Workflow, WorkflowTask
from domain.schemas import PaginatedSchedulingDecisionsResponse
from repositories.scheduling_repository import SchedulingRepository
from services.scheduling_service import (SchedulingService,
                                         get_scheduling_service)


@pytest.fixture
def mock_repository() -> MagicMock:
    """Provides a mock of the SchedulingRepository."""
    repo = MagicMock(spec=SchedulingRepository)
    repo.create_decisions = AsyncMock()
    repo.list_decisions_by_criteria = AsyncMock()
    return repo


@pytest.fixture
def scheduler_response_json() -> dict:
    """
    Provides a sample JSON response from the scheduler.
    Updated to use 'task_id' to match the new schema standard.
    """
    return {
        "placements": [
            {
                "task_id": str(uuid.uuid4()),  # --- [FIX] Updated key ---
                "target_node_ids": ["node-1", "node-2"],
                "strategy_used": "strategy-A",
            },
            {
                "task_id": str(uuid.uuid4()),  # --- [FIX] Updated key ---
                "target_node_ids": ["node-3"],
                "strategy_used": "strategy-B",
            },
        ],
        "scheduling_duration_ms": 120,
    }


@pytest.mark.asyncio
class TestSchedulingService:
    """Test suite for the SchedulingService."""

    async def test_record_scheduling_results_success(
        self, mock_repository: MagicMock, scheduler_response_json: dict
    ):
        """
        GIVEN a valid scheduler response
        WHEN record_scheduling_results is called
        THEN it should parse the data and call repository.create_decisions.
        """
        service = SchedulingService(repository=mock_repository)
        await service.record_scheduling_results(scheduler_response_json)

        mock_repository.create_decisions.assert_awaited_once()

        args, _ = mock_repository.create_decisions.call_args
        created_decisions = args[0]

        assert isinstance(created_decisions, list)
        assert len(created_decisions) == 2

        assert isinstance(created_decisions[0], SchedulingDecision)

        # --- [FIX] Match updated fixture key ---
        assert created_decisions[0].task_id == uuid.UUID(
            scheduler_response_json["placements"][0]["task_id"]
        )
        assert created_decisions[0].target_nodes == ["node-1", "node-2"]
        assert created_decisions[0].strategy_used == "strategy-A"
        assert created_decisions[0].duration_ms == 120

        assert created_decisions[1].strategy_used == "strategy-B"

    async def test_record_scheduling_results_no_placements(
        self, mock_repository: MagicMock
    ):
        """
        GIVEN a scheduler response with no placements
        WHEN record_scheduling_results is called
        THEN it should do nothing and not call the repository.
        """
        service = SchedulingService(repository=mock_repository)
        await service.record_scheduling_results({"placements": []})

        mock_repository.create_decisions.assert_not_awaited()

    @patch("services.scheduling_service.logger")
    async def test_record_scheduling_results_handles_db_error(
        self,
        mock_logger: MagicMock,
        mock_repository: MagicMock,
        scheduler_response_json: dict,
    ):
        """
        GIVEN the repository throws an error
        WHEN record_scheduling_results is called
        THEN it should catch the exception and log it, without re-raising.
        """
        mock_repository.create_decisions.side_effect = Exception("DB Connection Failed")

        service = SchedulingService(repository=mock_repository)

        await service.record_scheduling_results(scheduler_response_json)

        mock_repository.create_decisions.assert_awaited_once()
        mock_logger.exception.assert_called_once_with(
            "Failed to record scheduling decisions: DB Connection Failed", exc_info=True
        )

    async def test_get_scheduling_history_success(self, mock_repository: MagicMock):
        """
        GIVEN a valid repository response
        WHEN get_scheduling_history is called
        THEN it should transform the DB tuples into the correct Pydantic response.
        """
        mock_task = WorkflowTask(
            id=uuid.uuid4(), name="job-1", workflow_id=uuid.uuid4()
        )
        mock_workflow = Workflow(id=mock_task.workflow_id, name="workflow-A")
        mock_decision = SchedulingDecision(
            id=uuid.uuid4(),
            task_id=mock_task.id,
            target_nodes=["node-1"],
            strategy_used="bin_packing",
            duration_ms=50,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )

        repo_result = ([(mock_decision, mock_task, mock_workflow)], 1)

        mock_repository.list_decisions_by_criteria.return_value = repo_result

        service = SchedulingService(repository=mock_repository)
        response = await service.get_scheduling_history(
            offset=10, limit=50, target_node="node-1"
        )

        mock_repository.list_decisions_by_criteria.assert_awaited_once_with(
            target_node="node-1",
            strategy=None,
            task_id=None,
            workflow_id=None,
            offset=10,
            limit=50,
        )

        assert isinstance(response, PaginatedSchedulingDecisionsResponse)
        assert response.total == 1
        assert len(response.items) == 1

        item = response.items[0]
        assert item.task_id == mock_task.id
        assert item.task_name == "job-1"
        assert item.workflow_id == mock_workflow.id
        assert item.workflow_name == "workflow-A"
        assert item.strategy_used == "bin_packing"
        assert item.created_at == mock_decision.created_at


def test_get_scheduling_service(mock_repository: MagicMock):
    """Tests the dependency provider function."""
    service = get_scheduling_service(repository=mock_repository)
    assert isinstance(service, SchedulingService)
    assert service.repository == mock_repository
