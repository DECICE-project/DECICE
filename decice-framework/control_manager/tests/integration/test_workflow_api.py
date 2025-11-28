import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from db.models import Job, PlatformIdentity
from db.models import User as UserModel
from db.models import Workflow
from domain.user_schemas import User as UserSchema


@pytest.mark.asyncio
class TestWorkflowAPI:
    """Integration test suite for the workflow submission API."""

    async def test_submit_workflow_success(
        self,
        authenticated_client: TestClient,
        test_db_session: AsyncSession,
        mock_user: UserSchema,
        monkeypatch,
    ):
        """
        GIVEN a valid user, workflow metadata, and a K8s Job definition file
        WHEN a POST request is made to the /workflow/ endpoint
        THEN the workflow and its task are created correctly in the database.
        """
        # Create the user in the test DB
        db_identity = PlatformIdentity(
            id=mock_user.platform_identity.id,
            user_id=mock_user.id,
            platform=mock_user.platform_identity.platform,
            platform_username=mock_user.platform_identity.platform_username,
            default_working_dir=mock_user.platform_identity.default_working_dir,
        )
        db_user = UserModel(
            id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            full_name=mock_user.full_name,
            project=mock_user.project,
            hashed_password="a-test-password",
            platform_identity=db_identity,
        )
        test_db_session.add(db_user)
        await test_db_session.commit()
        await test_db_session.refresh(db_user)

        # Mock the PsgcService external call
        mock_psgc_response = {
            "message": "Delegation successful",
            "presigned_url": "http://s3.mock.url/upload-here",
        }
        mock_delegate = AsyncMock(return_value=mock_psgc_response)

        monkeypatch.setattr(
            "services.workflow_service.PsgcService.delegate_workflow_to_psgc",
            mock_delegate,
        )

        # Prepare the multipart/form-data payload
        workflow_metadata = {"name": "my-first-k8s-workflow"}
        k8s_job_yaml = b"""
          apiVersion: batch/v1
          kind: Job
          metadata:
            name: pi-job
          spec:
            template:
              metadata:
                annotations:
                  dev.decice.com/storage-request: "1Gi"
              spec:
                containers:
                - name: pi
                  image: perl
                  command: ["perl",  "-Mbignum=bpi", "-wle", "print bpi(2000)"]
                restartPolicy: Never
        """
        files = {
            "workflow": (None, json.dumps(workflow_metadata), "application/json"),
            "definition_file": ("pi-job.yaml", k8s_job_yaml, "application/x-yaml"),
        }

        response = authenticated_client.post("/v1/workflow/", files=files)

        assert response.status_code == 201, response.json()
        response_data = response.json()

        assert response_data["presigned_url"] == "http://s3.mock.url/upload-here"
        assert response_data["workflow"]["name"] == "my-first-k8s-workflow"

        # Verify the database state
        query = (
            select(Workflow)
            .where(Workflow.name == "my-first-k8s-workflow")
            .options(selectinload(Workflow.tasks))
        )
        result = await test_db_session.execute(query)
        created_workflow = result.scalar_one_or_none()

        assert created_workflow is not None
        assert created_workflow.user_id == mock_user.id
        assert len(created_workflow.tasks) == 1
        assert created_workflow.tasks[0].name == "pi-job"

    async def test_submit_workflow_unauthorized(self, test_client: TestClient):
        """
        GIVEN an unauthenticated client
        WHEN a POST request is made to the /workflow/ endpoint
        THEN the response should be 401 Unauthorized.
        """
        files = {
            "workflow": (None, json.dumps({"name": "unauth-workflow"})),
            "definition_file": (None, b"apiVersion: batch/v1\nkind: Job..."),
        }
        response = test_client.post("/v1/workflow/", files=files)
        assert response.status_code == 401

    async def test_get_single_workflow_success(
        self,
        authenticated_client: TestClient,
        test_db_session: AsyncSession,
        mock_user: UserSchema,
    ):
        """
        GIVEN an existing workflow in the database associated with the user
        WHEN a GET request is made to /workflow/{workflow_id}
        THEN the response should be 200 OK with the correct workflow details.
        """
        # Create the user IN THE DATABASE first
        db_identity = PlatformIdentity(
            id=mock_user.platform_identity.id,
            user_id=mock_user.id,
            platform=mock_user.platform_identity.platform,
            platform_username=mock_user.platform_identity.platform_username,
            default_working_dir=mock_user.platform_identity.default_working_dir,
        )
        db_user = UserModel(
            id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            full_name=mock_user.full_name,
            project=mock_user.project,
            hashed_password="a-test-password",
            platform_identity=db_identity,
        )
        test_db_session.add(db_user)
        await test_db_session.commit()

        # Create the workflow linked to the user
        new_workflow = Workflow(
            name="my-retrievable-workflow",
            user_id=mock_user.id,
            tasks=[
                Job(
                    name="retrieved-job-1",
                    image="test/image:v1",
                    command_str='["echo", "hello"]',
                    type="job",
                )
            ],
        )
        test_db_session.add(new_workflow)
        await test_db_session.commit()
        await test_db_session.refresh(new_workflow)

        response = authenticated_client.get(f"/v1/workflow/{new_workflow.id}")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == str(new_workflow.id)
        assert response_data["user_id"] == str(mock_user.id)
        assert len(response_data["tasks"]) == 1
        assert response_data["tasks"][0]["name"] == "retrieved-job-1"

    async def test_get_nonexistent_workflow_returns_404(
        self, authenticated_client: TestClient
    ):
        """
        GIVEN a UUID that does not correspond to any workflow
        WHEN a GET request is made to /workflow/{nonexistent_id}
        THEN the response should be 404 Not Found.
        """
        nonexistent_id = uuid.uuid4()
        response = authenticated_client.get(f"/v1/workflow/{nonexistent_id}")
        assert response.status_code == 404
