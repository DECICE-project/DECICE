import uuid
from unittest.mock import AsyncMock

import pytest

from clients.cm_client import CMClient
from io_models import MinioWebhookPayload
from repository.redis_workflow_repository import RedisWorkflowRepository
from service.webhook_service import WebhookService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provides a mock RedisWorkflowRepository with awaitable methods."""
    repo = AsyncMock(spec=RedisWorkflowRepository)
    repo.get_workflow_status = AsyncMock()
    repo.activate_initial_jobs = AsyncMock()
    repo.update_workflow_status = AsyncMock()
    return repo


@pytest.fixture
def webhook_payload_factory():
    """A factory to create MinioWebhookPayload instances for tests."""

    def _create_payload(
        workflow_id: uuid.UUID = None, key: str = None
    ) -> tuple[MinioWebhookPayload, uuid.UUID]:
        if not workflow_id:
            workflow_id = uuid.uuid4()
        if not key:
            key = f"workflows/{workflow_id}/inputs/data.zip"

        payload = MinioWebhookPayload(
            EventName="s3:ObjectCreated:Put",
            Key=key,
            Records=[{"s3": {}}],
        )
        return payload, workflow_id

    return _create_payload


@pytest.fixture
def mock_cm_client() -> AsyncMock:
    client = AsyncMock(spec=CMClient)
    client.report_workflow_status = AsyncMock()
    return client


@pytest.mark.asyncio
class TestWebhookService:
    async def test_process_notification_happy_path(
        self,
        mock_repository: AsyncMock,
        mock_cm_client: AsyncMock,
        webhook_payload_factory,
    ):
        """
        GIVEN a valid webhook for a workflow in PENDING_DATA state
        WHEN process_minio_notification is called
        THEN the workflow and its initial jobs should be activated.
        """
        payload, workflow_id = webhook_payload_factory()
        mock_repository.get_workflow_status.return_value = "PENDING_DATA"

        service = WebhookService(repository=mock_repository, cm_client=mock_cm_client)

        await service.process_minio_notification(payload)

        mock_repository.get_workflow_status.assert_awaited_once_with(workflow_id)
        mock_repository.activate_initial_tasks.assert_awaited_once_with(workflow_id)
        mock_repository.update_workflow_status.assert_awaited_once_with(
            workflow_id, "PROGRESSING"
        )
        mock_cm_client.report_workflow_status.assert_awaited_once_with(
            workflow_id, "PROGRESSING"
        )

    async def test_process_notification_ignores_wrong_status(
        self,
        mock_repository: AsyncMock,
        mock_cm_client: AsyncMock,
        webhook_payload_factory,
    ):
        """
        GIVEN a webhook for a workflow that is NOT in PENDING_DATA
        WHEN process_minio_notification is called
        THEN no state-changing actions should be taken.
        """
        payload, workflow_id = webhook_payload_factory()
        mock_repository.get_workflow_status.return_value = "RUNNING"

        service = WebhookService(repository=mock_repository, cm_client=mock_cm_client)

        await service.process_minio_notification(payload)

        mock_repository.get_workflow_status.assert_awaited_once_with(workflow_id)
        mock_repository.activate_initial_tasks.assert_not_awaited()
        mock_repository.update_workflow_status.assert_not_awaited()
        mock_cm_client.report_workflow_status.assert_not_awaited()

    async def test_process_notification_ignores_unknown_workflow(
        self,
        mock_repository: AsyncMock,
        mock_cm_client: AsyncMock,
        webhook_payload_factory,
    ):
        """
        GIVEN a webhook for a workflow that does not exist in the repository
        WHEN process_minio_notification is called
        THEN no actions should be taken.
        """
        payload, workflow_id = webhook_payload_factory()
        mock_repository.get_workflow_status.return_value = None

        service = WebhookService(repository=mock_repository, cm_client=mock_cm_client)

        await service.process_minio_notification(payload)

        mock_repository.get_workflow_status.assert_awaited_once_with(workflow_id)
        mock_repository.activate_initial_tasks.assert_not_awaited()
        mock_repository.update_workflow_status.assert_not_awaited()
        mock_cm_client.report_workflow_status.assert_not_awaited()

    async def test_process_notification_handles_malformed_key(
        self,
        mock_repository: AsyncMock,
        mock_cm_client: AsyncMock,
        webhook_payload_factory,
    ):
        """
        GIVEN a webhook with a key that cannot be parsed for a workflow_id
        WHEN process_minio_notification is called
        THEN it should fail gracefully without calling the repository.
        """
        payload, _ = webhook_payload_factory(key="some-other-bucket/some-file.txt")

        service = WebhookService(repository=mock_repository, cm_client=mock_cm_client)

        await service.process_minio_notification(payload)

        mock_repository.get_workflow_status.assert_not_awaited()
        mock_repository.activate_initial_tasks.assert_not_awaited()
        mock_repository.update_workflow_status.assert_not_awaited()
        mock_cm_client.report_workflow_status.assert_not_awaited()
