import json
import uuid

import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from minio import Minio

from api import app
from auth.auth import verify_internal_traffic


@pytest.mark.asyncio
class TestApiEndpoints:
    async def test_create_workflow_with_data_file(
        self, test_client: TestClient, redis_client: redis.Redis, minio_client: Minio
    ):
        """
        GIVEN a workflow submission that requires a data file
        WHEN a POST request is made to the /workflows endpoint
        THEN the workflow state should be saved to Redis with PENDING_DATA status,
        AND a valid presigned MinIO URL should be returned.
        """
        app.dependency_overrides[verify_internal_traffic] = lambda: True
        workflow_id = uuid.uuid4()
        workflow_data = {
            "id": str(workflow_id),
            "name": "api-test-workflow",
            "status": "PENDING_DATA",
            "user_id": str(uuid.uuid4()),
            "tasks": [],
            "filename": "data.zip",
            "hpc_context": None,
        }

        response = test_client.post("/workflows", json=workflow_data)

        assert response.status_code == 201, response.json()

        response_data = response.json()
        assert "presigned_url" in response_data
        presigned_url = response_data["presigned_url"]

        assert isinstance(presigned_url, str)

        assert f"/workflows/{workflow_id}/inputs/data.zip" in presigned_url

        repo_prefix = "psgc:workflow"
        status = await redis_client.get(f"{repo_prefix}:{workflow_id}:overall_status")
        assert status == "PENDING_DATA"

    async def test_minio_webhook_activates_workflow(
        self, test_client: TestClient, redis_client: redis.Redis
    ):
        """
        GIVEN a workflow exists in Redis with PENDING_DATA status
        WHEN a valid MinIO webhook is received for that workflow's data file
        THEN the workflow's status in Redis should be updated to PROGRESSING.
        """
        workflow_id = uuid.uuid4()
        repo_prefix = "psgc:workflow"
        workflow_def = {
            "id": str(workflow_id),
            "tasks": [{"id": str(uuid.uuid4()), "dependencies": []}],
        }

        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.set(
                f"{repo_prefix}:{workflow_id}:definition", json.dumps(workflow_def)
            )
            pipe.set(f"{repo_prefix}:{workflow_id}:overall_status", "PENDING_DATA")
            await pipe.execute()

        payload = {
            "EventName": "s3:ObjectCreated:Put",
            "Key": f"workflows/{workflow_id}/inputs/data.zip",
            "Records": [{"s3": {}}],
        }

        response = test_client.post("/webhooks/minio", json=payload)

        assert response.status_code == 202

        final_status = await redis_client.get(
            f"{repo_prefix}:{workflow_id}:overall_status"
        )
        assert final_status == "PROGRESSING"
