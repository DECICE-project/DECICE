import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from db.models import TaskStatus, Workflow, WorkflowTask
from domain.schemas import (
    PSGCTaskStatusUpdateRequest,
    WorkflowCreateRequest,
    WorkflowStatus,
)
from domain.user_schemas import PlatformIdentityResponse
from domain.user_schemas import User as UserSchema
from domain.user_schemas import UserRole
from repositories.workflow_repository import WorkflowRepository
from services.psgc_service import PsgcService
from services.workflow_service import WorkflowService


@pytest.fixture
def mock_user() -> UserSchema:
    """Provides a mock Pydantic User model."""
    user_id = uuid.uuid4()
    identity = PlatformIdentityResponse(
        id=uuid.uuid4(),
        user_id=user_id,
        platform="slurm",
        platform_username="testuser_slurm",
        default_working_dir="/home/testuser_slurm",
    )
    return UserSchema(
        id=user_id,
        username="workflow_user",
        email="wf@user.com",
        active=True,
        role=UserRole.USER,
        project="decice",
        platform_identity=identity,
    )


@pytest.fixture
def mock_parsed_workflow() -> Workflow:
    """Provides a mock SQLAlchemy Workflow model, simulating the output of a parser."""
    return Workflow(
        id=uuid.uuid4(),
        name="parsed-workflow",
        status=WorkflowStatus.PENDING_DATA,
        tasks=[],
    )


@pytest.fixture
def mock_downstream_task() -> WorkflowTask:
    """Provides a mock SQLAlchemy WorkflowTask model for downstream dependency tests."""
    return WorkflowTask(id=uuid.uuid4(), name="downstream-task")


@pytest.fixture
def mock_definition_file() -> MagicMock:
    """Provides a mock FastAPI UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_workflow.yaml"
    file.read = AsyncMock(return_value=b"file content")
    file.seek = AsyncMock()
    return file


@pytest.fixture
def mock_repository() -> MagicMock:
    """Provides a mock of the WorkflowRepository."""
    repo = MagicMock(spec=WorkflowRepository)
    repo.create_full_workflow = AsyncMock()
    repo.update_task_status = AsyncMock()
    repo.find_ready_downstream_tasks = AsyncMock(return_value=([], None))
    repo.cancel_downstream_tasks = AsyncMock(return_value=([], None))
    repo.update_workflow_status = AsyncMock()
    repo.session = MagicMock()
    repo.session.get = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_psgc_service() -> MagicMock:
    """Provides a mock of the PsgcService."""
    service = MagicMock(spec=PsgcService)
    service.delegate_workflow_to_psgc = AsyncMock(return_value={"message": "delegated"})
    service.client = MagicMock()
    service.client.update_task_status = AsyncMock(return_value="ok")
    return service


@pytest.mark.asyncio
class TestWorkflowService:
    """Test suite for the WorkflowService."""

    @patch("services.workflow_service.get_parser")
    async def test_create_workflow_with_storage_file(
        self,
        mock_get_parser: MagicMock,
        mock_repository: MagicMock,
        mock_psgc_service: MagicMock,
        mock_user: UserSchema,
        mock_parsed_workflow: Workflow,
        mock_definition_file: MagicMock,
    ):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed_workflow
        mock_get_parser.return_value = mock_parser
        mock_repository.create_full_workflow.return_value = mock_parsed_workflow

        workflow_request = WorkflowCreateRequest(
            name="test-wf", storage_filename="data.zip"
        )
        service = WorkflowService(
            repository=mock_repository, psgc_service=mock_psgc_service
        )

        await service.create_workflow(
            user=mock_user,
            workflow_request=workflow_request,
            definition_file=mock_definition_file,
        )

        mock_get_parser.assert_called_once()
        mock_parser.parse.assert_called_once()
        assert mock_parsed_workflow.status == WorkflowStatus.PENDING_DATA
        mock_repository.create_full_workflow.assert_awaited_once_with(
            mock_parsed_workflow
        )
        mock_psgc_service.delegate_workflow_to_psgc.assert_awaited_once()

    @patch("services.workflow_service.get_parser")
    async def test_create_workflow_without_storage_file(
        self,
        mock_get_parser: MagicMock,
        mock_repository: MagicMock,
        mock_psgc_service: MagicMock,
        mock_user: UserSchema,
        mock_parsed_workflow: Workflow,
        mock_definition_file: MagicMock,
    ):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_parsed_workflow
        mock_get_parser.return_value = mock_parser
        mock_repository.create_full_workflow.return_value = mock_parsed_workflow

        workflow_request = WorkflowCreateRequest(name="test-wf", storage_filename=None)
        service = WorkflowService(
            repository=mock_repository, psgc_service=mock_psgc_service
        )

        await service.create_workflow(
            user=mock_user,
            workflow_request=workflow_request,
            definition_file=mock_definition_file,
        )

        assert mock_parsed_workflow.status == WorkflowStatus.PROGRESSING
        mock_repository.create_full_workflow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_completion_succeeded_triggers_downstream(
        self,
        mock_repository: MagicMock,
        mock_psgc_service: MagicMock,
        mock_downstream_task: WorkflowTask,
    ):
        """
        GIVEN a completed task with final status SUCCEEDED
        AND a downstream task that is ready to run
        WHEN handle_task_completion is called
        THEN the downstream task is marked READY in the repository
        AND PSGC is updated with the READY status for the downstream task.
        """
        completed_id = uuid.uuid4()
        workflow_id = uuid.uuid4()

        mock_downstream_task.id = uuid.uuid4()
        mock_downstream_task.workflow_id = workflow_id
        mock_downstream_task.dependencies = []

        mock_repository.find_ready_downstream_tasks = AsyncMock(
            return_value=([mock_downstream_task], workflow_id)
        )

        service = WorkflowService(
            repository=mock_repository, psgc_service=mock_psgc_service
        )

        await service.handle_task_completion(
            task_id=completed_id, final_status=TaskStatus.SUCCEEDED
        )

        mock_repository.find_ready_downstream_tasks.assert_awaited_once_with(
            completed_id
        )
        mock_repository.update_task_status.assert_awaited_once_with(
            mock_downstream_task.id, TaskStatus.READY
        )

        mock_psgc_service.client.update_task_status.assert_awaited_once()

        update_request: PSGCTaskStatusUpdateRequest = (
            mock_psgc_service.client.update_task_status.call_args.args[0]
        )
        assert update_request.workflow_id == workflow_id
        assert update_request.statuses[0].task_id == mock_downstream_task.id
        assert update_request.statuses[0].status == TaskStatus.READY

    @pytest.mark.asyncio
    async def test_handle_completion_failed_stops_progression(
        self,
        mock_repository: MagicMock,
        mock_psgc_service: MagicMock,
    ):
        """
        GIVEN a completed task with final status FAILED
        AND multiple downstream tasks depending on it
        WHEN handle_task_completion is called
        THEN all downstream tasks are canceled in the repository
        AND PSGC is updated with CANCELLED status for all downstream tasks.
        """
        completed_id = uuid.uuid4()
        workflow_id = uuid.uuid4()

        canceled_task1 = MagicMock(spec=WorkflowTask, id=uuid.uuid4())
        canceled_task2 = MagicMock(spec=WorkflowTask, id=uuid.uuid4())

        mock_repository.cancel_downstream_tasks = AsyncMock(
            return_value=([canceled_task1, canceled_task2], workflow_id)
        )

        service = WorkflowService(
            repository=mock_repository, psgc_service=mock_psgc_service
        )

        await service.handle_task_completion(
            task_id=completed_id, final_status=TaskStatus.FAILED
        )

        mock_repository.cancel_downstream_tasks.assert_awaited_once_with(completed_id)
        mock_repository.find_ready_downstream_tasks.assert_not_awaited()
        mock_psgc_service.client.update_task_status.assert_awaited_once()
        update_request = mock_psgc_service.client.update_task_status.call_args.args[0]
        assert update_request.workflow_id == workflow_id
        canceled_ids = {s.task_id for s in update_request.statuses}
        assert canceled_ids == {canceled_task1.id, canceled_task2.id}
        for status in update_request.statuses:
            assert status.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_update_workflow_status_not_found_raises_error(
        self,
        mock_repository: MagicMock,
        mock_psgc_service: MagicMock,
    ):
        mock_repository.update_workflow_status.return_value = None

        service = WorkflowService(
            repository=mock_repository, psgc_service=mock_psgc_service
        )

        with pytest.raises(ValueError, match="Workflow with ID .* not found"):
            await service.update_workflow_status(
                workflow_id=uuid.uuid4(), status=WorkflowStatus.SUCCEEDED
            )
