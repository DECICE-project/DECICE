import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from io_models import WorkflowPSGCRequest
from repository.redis_workflow_repository import RedisWorkflowRepository
from service.storage_service import StorageService
from service.workflow_service import WorkflowService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provides a mock RedisWorkflowRepository."""
    return AsyncMock(spec=RedisWorkflowRepository)


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Provides a mock StorageService."""
    service = MagicMock(spec=StorageService)
    service.generate_presigned_url.return_value = "http://mock-minio.com/presigned-url"
    return service


@pytest.fixture
def base_workflow_request() -> WorkflowPSGCRequest:
    """Provides a basic, valid WorkflowPSGCRequest for use in tests."""
    return WorkflowPSGCRequest(
        id=uuid.uuid4(),
        name="test-workflow",
        status="PENDING",
        user_id=uuid.uuid4(),
        tasks=[],
        filename=None,
    )


@pytest.mark.asyncio
class TestWorkflowService:
    async def test_create_workflow_with_data_file(
        self,
        mock_repository: AsyncMock,
        mock_storage_service: MagicMock,
        base_workflow_request: WorkflowPSGCRequest,
    ):
        """
        GIVEN a workflow that requires a data file (filename is provided)
        WHEN create_workflow_and_get_upload_url is called
        THEN it should save the workflow with PENDING_DATA status and return a presigned URL.
        """
        base_workflow_request.filename = "my-data.zip"

        service = WorkflowService(
            repository=mock_repository, storage_service=mock_storage_service
        )

        upload_url = await service.create_workflow_and_get_upload_url(
            workflow_request=base_workflow_request,
            filename="my-data.zip",
        )

        assert upload_url == "http://mock-minio.com/presigned-url"
        mock_storage_service.generate_presigned_url.assert_called_once()

        mock_repository.save_workflow_state.assert_awaited_once_with(
            workflow_request=base_workflow_request,
            initial_workflow_status="PENDING_DATA",
        )

    async def test_create_workflow_without_data_file(
        self,
        mock_repository: AsyncMock,
        mock_storage_service: MagicMock,
        base_workflow_request: WorkflowPSGCRequest,
    ):
        """
        GIVEN a workflow that does NOT require a data file (filename is None)
        WHEN create_workflow_and_get_upload_url is called
        THEN it should save the workflow with READY status and return None for the URL.
        """
        service = WorkflowService(
            repository=mock_repository, storage_service=mock_storage_service
        )

        upload_url = await service.create_workflow_and_get_upload_url(
            workflow_request=base_workflow_request,
            filename=None,
        )

        assert upload_url is None
        mock_storage_service.generate_presigned_url.assert_not_called()

        mock_repository.save_workflow_state.assert_awaited_once_with(
            workflow_request=base_workflow_request,
            initial_workflow_status="PROGRESSING",
        )
