import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from clients.cm_client import CMClient
from config import ServiceSettings
from engine import PsgcEngine
from repository.redis_workflow_repository import RedisWorkflowRepository
from service.kubernetes_service import KubernetesService
from service.slurm_service import SlurmService
from service.storage_service import StorageService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_k8s_service() -> AsyncMock:
    """Provides a mock KubernetesService."""
    return AsyncMock(spec=KubernetesService)


@pytest.fixture
def mock_slurm_service() -> AsyncMock:
    """Provides a mock SlurmService."""
    return AsyncMock(spec=SlurmService)


@pytest.fixture
def mock_cm_client() -> AsyncMock:
    """Provides a mock CMClient, pre-configured for a successful scheduling decision."""
    client = AsyncMock(spec=CMClient)
    client.get_scheduling_decision.return_value = {
        "placements": [
            {
                "task_id": "42443cfe-3e3c-4e36-8c66-383db691b81b",
                "target_node_ids": ["k8s-worker-node-1"],
                "strategy_used": "mock-strategy",
            }
        ]
    }

    client.patch_workload_status = AsyncMock()
    client.report_job_completion = AsyncMock()

    return client


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provides a mock RedisWorkflowRepository."""
    return AsyncMock(spec=RedisWorkflowRepository)


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Provides a mock StorageService."""
    return MagicMock(spec=StorageService)


@pytest.fixture
def mock_settings() -> MagicMock:
    """
    Provides a mock ServiceSettings object.
    """
    settings = MagicMock(spec=ServiceSettings)
    settings.MINIO_ENDPOINT = "mock-minio:9000"
    settings.MINIO_ACCESS_KEY = "mock-access-key"
    settings.MINIO_SECRET_KEY = "mock-secret-key"
    # Mock the sched. webhook enable flag - set it to False for testing purposes
    settings.SCHED_WEBHOOK=False
    return settings


@pytest.mark.asyncio
class TestPsgcEngine:
    async def test_submit_job_happy_path(
        self,
        mock_k8s_service: AsyncMock,
        mock_slurm_service: AsyncMock,
        mock_cm_client: AsyncMock,
        mock_repository: AsyncMock,
        mock_storage_service: MagicMock,
        mock_settings: MagicMock,
    ):
        """
        GIVEN a job ready for submission and all downstream services are healthy
        WHEN the submit_job method is called
        THEN it should get a scheduling decision, apply a K8s manifest, and update the status to PENDING.
        """
        engine = PsgcEngine(
            k8s_service=mock_k8s_service,
            slurm_service=mock_slurm_service,
            cm_client=mock_cm_client,
            repository=mock_repository,
            storage_service=mock_storage_service,
            settings=mock_settings,
        )

        workflow_id = uuid.uuid4()
        job_id = uuid.UUID("42443cfe-3e3c-4e36-8c66-383db691b81b")

        job_data = {
            "id": str(job_id),
            "name": "test-job-1",
            "image": "ubuntu:latest",
            "command_str": '["echo", "hello"]',
            "required_cpu": "100m",
            "required_memory": "128Mi",
            "required_gpu": None,
            "annotations": {},
            "type": "job",
            "env": [],
        }
        workflow_definition = {
            "id": str(workflow_id),
            "name": "test-workflow",
            "annotations": {"dev.decice.com/storage-request": "1Gi"},
            "filename": "data.zip",
            "user_context": {"hpc_user_id": "testuser"},
            "hpc_context": {"platform_username": "testuser"},
        }

        await engine.submit_task(
            workflow_id=workflow_id,
            task_data=job_data,
            workflow_definition=workflow_definition,
        )

        mock_k8s_service.ensure_pvc_exists.assert_awaited_once_with(
            name=f"pvc-{workflow_id}", size="1Gi", namespace="default"
        )
        mock_cm_client.get_scheduling_decision.assert_awaited_once()
        mock_k8s_service.apply_job.assert_awaited_once()

        mock_repository.update_task_status.assert_awaited_once_with(
            workflow_id, job_id, "PENDING"
        )

        mock_cm_client.patch_task_status.assert_awaited_once_with(
            task_id=job_id,
            status="PENDING",
            detail="Job submitted to Kubernetes.",
        )

        mock_cm_client.report_task_completion.assert_not_awaited()

    async def test_submit_job_handles_scheduling_failure(
        self,
        mock_k8s_service: AsyncMock,
        mock_slurm_service: AsyncMock,
        mock_cm_client: AsyncMock,
        mock_repository: AsyncMock,
        mock_storage_service: MagicMock,
        mock_settings: MagicMock,
    ):
        """
        GIVEN the CMClient fails to return a scheduling decision
        WHEN the submit_job method is called
        THEN it should mark the job as FAILED and report the failure.
        """
        mock_cm_client.get_scheduling_decision.side_effect = ValueError(
            "Scheduler is down"
        )

        engine = PsgcEngine(
            k8s_service=mock_k8s_service,
            slurm_service=mock_slurm_service,
            cm_client=mock_cm_client,
            repository=mock_repository,
            storage_service=mock_storage_service,
            settings=mock_settings,
        )

        workflow_id = uuid.uuid4()
        job_id = uuid.UUID("42443cfe-3e3c-4e36-8c66-383db691b81b")
        job_data = {"id": str(job_id), "type": "job", "annotations": {}}
        workflow_definition = {"annotations": {}, "user_context": {}, "hpc_context": {}}

        await engine.submit_task(workflow_id, job_data, workflow_definition)

        mock_repository.update_task_status.assert_awaited_once_with(
            workflow_id, job_id, "FAILED"
        )
        mock_cm_client.report_task_completion.assert_awaited_once_with(
            task_id=job_id, completion_status="FAILED", detail="Scheduler is down"
        )
        mock_k8s_service.apply_job.assert_not_awaited()

    async def test_submit_job_handles_kubernetes_failure(
        self,
        mock_k8s_service: AsyncMock,
        mock_slurm_service: AsyncMock,
        mock_cm_client: AsyncMock,
        mock_repository: AsyncMock,
        mock_storage_service: MagicMock,
        mock_settings: MagicMock,
    ):
        """
        GIVEN the Kubernetes service fails to apply the job manifest
        WHEN the submit_job method is called
        THEN it should mark the job as FAILED and report the failure.
        """
        from kubernetes_asyncio.client.rest import ApiException

        mock_k8s_service.apply_job.side_effect = ApiException(
            status=500, reason="API Server Error"
        )

        engine = PsgcEngine(
            k8s_service=mock_k8s_service,
            slurm_service=mock_slurm_service,
            cm_client=mock_cm_client,
            repository=mock_repository,
            storage_service=mock_storage_service,
            settings=mock_settings,
        )

        workflow_id = uuid.uuid4()
        job_id = uuid.UUID("42443cfe-3e3c-4e36-8c66-383db691b81b")
        job_data = {
            "id": str(job_id),
            "image": "test-image",
            "type": "job",
            "annotations": {},
            "env": [],
        }
        workflow_definition = {"annotations": {}, "user_context": {}, "hpc_context": {}}

        await engine.submit_task(workflow_id, job_data, workflow_definition)

        mock_repository.update_task_status.assert_awaited_once_with(
            workflow_id, job_id, "FAILED"
        )
        mock_cm_client.report_task_completion.assert_awaited_once()
        mock_cm_client.get_scheduling_decision.assert_awaited_once()
