from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TaskStatus, Workflow, WorkflowTask
from domain.schemas import WorkflowStatus
from repositories.workflow_repository import WorkflowRepository, get_workflow_repository


@pytest.fixture
def mock_session():
    """Fixture for a mock SQLAlchemy AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def workflow_repository(mock_session):
    """Fixture for WorkflowRepository with a mock session."""
    return WorkflowRepository(session=mock_session)


@pytest.fixture
def sample_workflow():
    """Fixture for a sample Workflow object."""
    return Workflow(
        id=uuid4(),
        name="Test Workflow",
        status=WorkflowStatus.PROGRESSING,
        user_id=uuid4(),
        tasks=[],
    )


@pytest.fixture
def sample_task(sample_workflow):
    """Fixture for a sample WorkflowTask object."""
    return WorkflowTask(
        id=uuid4(),
        name="Test Task",
        workflow_id=sample_workflow.id,
        status=TaskStatus.WAITING,
    )


@pytest.mark.asyncio
async def test_create_full_workflow_success(
    workflow_repository, mock_session, sample_workflow, sample_task
):
    """Test successful creation of a full workflow."""
    sample_workflow.tasks.append(sample_task)

    mock_result = MagicMock(spec=Result)
    mock_result.unique.return_value.scalar_one.return_value = sample_workflow

    mock_session.execute.return_value = mock_result

    created_workflow = await workflow_repository.create_full_workflow(sample_workflow)

    mock_session.add.assert_called_once_with(sample_workflow)
    mock_session.commit.assert_called_once()
    mock_session.execute.assert_called_once()

    assert created_workflow.id == sample_workflow.id
    assert len(created_workflow.tasks) == 1
    assert created_workflow.tasks[0].id == sample_task.id


@pytest.mark.asyncio
async def test_create_full_workflow_failure(
    workflow_repository, mock_session, sample_workflow
):
    """Test failure during creation of a full workflow due to SQLAlchemyError."""
    # Simulate failure on flush (which happens before commit in the code)
    mock_session.flush.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await workflow_repository.create_full_workflow(sample_workflow)

    mock_session.add.assert_called_once_with(sample_workflow)
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_workflow_with_details_by_id_found(
    workflow_repository, mock_session, sample_workflow, sample_task
):
    """Test retrieving a workflow by ID when found."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = sample_workflow
    mock_session.execute.return_value = mock_result

    workflow = await workflow_repository.get_workflow_with_details_by_id(
        sample_workflow.id
    )

    mock_session.execute.assert_called_once()
    assert workflow == sample_workflow


@pytest.mark.asyncio
async def test_get_workflow_with_details_by_id_not_found(
    workflow_repository, mock_session
):
    """Test retrieving a workflow by ID when not found."""
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    workflow = await workflow_repository.get_workflow_with_details_by_id(uuid4())

    assert workflow is None


@pytest.mark.asyncio
async def test_update_workflow_status_success(
    workflow_repository, mock_session, sample_workflow
):
    """Test successful update of workflow status."""
    # The repo executes an update, commits, then gets the workflow
    mock_session.get.return_value = sample_workflow

    updated_status = WorkflowStatus.SUCCEEDED
    updated_workflow = await workflow_repository.update_workflow_status(
        sample_workflow.id, updated_status
    )

    # Verify UPDATE executed
    mock_session.execute.assert_called_once()
    # Verify Commit
    mock_session.commit.assert_called_once()
    # Verify Refetch
    mock_session.get.assert_called_once_with(Workflow, sample_workflow.id)

    assert updated_workflow == sample_workflow


@pytest.mark.asyncio
async def test_update_workflow_status_not_found(workflow_repository, mock_session):
    """Test updating workflow status when workflow is not found."""
    # The UPDATE runs (affecting 0 rows), Commit happens, GET returns None
    mock_session.get.return_value = None

    updated_workflow = await workflow_repository.update_workflow_status(
        uuid4(), WorkflowStatus.FAILED
    )

    # In SQL-based updates, we still execute and commit even if 0 rows matched
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
    assert updated_workflow is None


@pytest.mark.asyncio
async def test_update_workflow_status_failure(
    workflow_repository, mock_session, sample_workflow
):
    """Test failure during workflow status update due to SQLAlchemyError."""
    # Simulate error during execution of the UPDATE statement
    mock_session.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await workflow_repository.update_workflow_status(
            sample_workflow.id, WorkflowStatus.FAILED
        )

    # Removed 'add' assertion, verifying 'execute' instead
    mock_session.execute.assert_called_once()
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_task_status_success(
    workflow_repository, mock_session, sample_task
):
    """Test successful update of task status."""
    mock_session.execute.return_value = MagicMock()

    await workflow_repository.update_task_status(sample_task.id, TaskStatus.SUCCEEDED)

    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_status_failure(
    workflow_repository, mock_session, sample_task
):
    """Test failure during task status update due to SQLAlchemyError."""
    mock_session.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await workflow_repository.update_task_status(sample_task.id, TaskStatus.FAILED)

    mock_session.execute.assert_called_once()
    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_find_ready_downstream_tasks_with_dependencies_ready(
    workflow_repository, mock_session
):
    """Test finding ready downstream tasks when dependencies are met."""
    completed_task_id = uuid4()
    downstream_task_id = uuid4()
    workflow_id = uuid4()

    # Downstream task
    downstream_task = MagicMock(spec=WorkflowTask)
    downstream_task.id = downstream_task_id
    downstream_task.name = "Downstream Task"
    downstream_task.workflow_id = workflow_id
    downstream_task.status = TaskStatus.WAITING

    # Mock get_pending_downstream_tasks to return our candidate
    workflow_repository.get_pending_downstream_tasks = AsyncMock(
        return_value=([downstream_task], workflow_id)
    )

    # Mock check_task_dependencies_met to return True
    workflow_repository.check_task_dependencies_met = AsyncMock(return_value=True)

    (
        ready_tasks,
        returned_workflow_id,
    ) = await workflow_repository.find_ready_downstream_tasks(completed_task_id)

    assert len(ready_tasks) == 1
    assert ready_tasks[0].id == downstream_task_id
    assert returned_workflow_id == workflow_id


@pytest.mark.asyncio
async def test_find_ready_downstream_tasks_with_dependencies_not_ready(
    workflow_repository,
):
    """Test finding ready downstream tasks when dependencies are not met."""
    completed_task_id = uuid4()
    downstream_task_id = uuid4()
    workflow_id = uuid4()

    downstream_task = MagicMock(spec=WorkflowTask)
    downstream_task.id = downstream_task_id

    # Mock get_pending_downstream_tasks
    workflow_repository.get_pending_downstream_tasks = AsyncMock(
        return_value=([downstream_task], workflow_id)
    )

    # Mock check_task_dependencies_met to return False
    workflow_repository.check_task_dependencies_met = AsyncMock(return_value=False)

    (
        ready_tasks,
        returned_workflow_id,
    ) = await workflow_repository.find_ready_downstream_tasks(completed_task_id)

    # Should be empty because dependency check returned False
    assert ready_tasks == []
    assert returned_workflow_id == workflow_id


@pytest.mark.asyncio
async def test_list_workflows_success(
    workflow_repository, mock_session, sample_workflow
):
    """Test successful retrieval of a paginated list of workflows."""
    mock_items_result = MagicMock(spec=Result)
    mock_items_result.scalars.return_value.all.return_value = [sample_workflow]

    mock_count_result = MagicMock(spec=Result)
    mock_count_result.scalar_one.return_value = 1

    mock_session.execute.side_effect = [mock_items_result, mock_count_result]

    sample_workflow.status = WorkflowStatus.SUCCEEDED

    workflows, total = await workflow_repository.list_workflows(offset=0, limit=10)

    assert len(workflows) == 1
    assert workflows[0] == sample_workflow
    assert total == 1
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_workflow_repository(mock_session):
    """Test the dependency injection function get_workflow_repository."""
    repo = get_workflow_repository(session=mock_session)
    assert isinstance(repo, WorkflowRepository)
    assert repo.session == mock_session
