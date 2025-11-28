import uuid

import pytest
import redis.asyncio as redis

from io_models import WorkflowPSGCRequest
from repository.redis_workflow_repository import RedisWorkflowRepository


@pytest.mark.asyncio
class TestRedisWorkflowRepository:
    async def test_save_and_get_workflow_state(self, redis_client: redis.Redis):
        """
        GIVEN a live Redis instance
        WHEN we save a workflow's state
        THEN we should be able to retrieve it correctly.
        """
        repo = RedisWorkflowRepository(redis_client=redis_client)

        workflow_id = uuid.uuid4()
        workflow_request = WorkflowPSGCRequest(
            id=workflow_id,
            name="integration-test-wf",
            status="PENDING",
            user_id=uuid.uuid4(),
            tasks=[],
            filename="data.zip",
        )

        await repo.save_workflow_state(workflow_request, "PENDING_DATA")

        status = await repo.get_workflow_status(workflow_id)
        assert status == "PENDING_DATA"

        definition = await repo.get_workflow_definition(workflow_id)
        assert definition is not None
        assert definition["id"] == str(workflow_id)
