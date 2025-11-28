import logging
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException as HttpException
from fastapi import UploadFile

from clients.psgc.client import PsgcClient, get_psgc_client
from db.models import User, Workflow
from domain.schemas import (DeploymentPSGCRequest,
                            GenericK8sResourcePSGCRequest, HPCContext,
                            HPCJobPSGCRequest, JobPSGCRequest,
                            WorkflowPSGCRequest, WorkflowPSGCResponse)

logger = logging.getLogger(__name__)


class PsgcService:
    """
    Service layer for interacting with the PSGC.
    Translates internal database models into the API contract.
    """

    def __init__(self, client: PsgcClient):
        self.client = client

    async def delegate_workflow_to_psgc(
        self,
        workflow: Workflow,
        user: User,
        storage_filename: Optional[str],
    ) -> dict:
        """
        Builds the payload and passes it along with the file to the client.
        """
        logger.info(f"Preparing delegation payload for workflow {workflow.id}")

        task_requests = []
        for task in workflow.tasks:
            task_data = {
                "id": task.id,
                "name": task.name,
                "image": task.image,
                "command_str": task.command_str,
                "required_cpu": task.required_cpu,
                "required_memory": task.required_memory,
                "required_gpu": task.required_gpu,
                "annotations": task.annotations,
                "env": task.env,
                "dependencies": [dep.id for dep in task.dependencies],
                "labels": task.labels,
            }

            if task.type == "job":
                task_requests.append(JobPSGCRequest(**task_data))
            elif task.type == "deployment":
                replicas = getattr(task, "replicas", 1)
                task_requests.append(
                    DeploymentPSGCRequest(**task_data, replicas=replicas)
                )
            elif task.type == "hpc_job":
                task_requests.append(HPCJobPSGCRequest(**task_data))
            elif task.type == "k8s_resource":
                task_requests.append(GenericK8sResourcePSGCRequest(**task_data))
            else:
                logger.warning(f"Skipping unknown task type: {task.type}")

        # Build the HPC context if it exists
        hpc_context = None
        if user.platform_identity:
            hpc_context = HPCContext(
                platform_username=user.platform_identity.platform_username,
                default_working_dir=user.platform_identity.default_working_dir,
            )

        # Build the final request object
        try:
            workflow_psgc_request = WorkflowPSGCRequest(
                id=workflow.id,
                name=workflow.name,
                status=workflow.status,
                user_id=user.id,
                filename=storage_filename,
                tasks=task_requests,
                hpc_context=hpc_context,
            )
        except Exception as e:
            logger.error(f"Failed to build PSGC request schema: {e}", exc_info=True)
            raise ValueError(f"Schema mismatch when building request: {e}")

        psgc_response_dict: dict = await self.client.delegate_workflow(
            workflow_payload=workflow_psgc_request.model_dump(mode="json"),
            filename=storage_filename,
        )
        try:
            WorkflowPSGCResponse.model_validate(psgc_response_dict)
            return psgc_response_dict
        except Exception as e:
            error_msg = f"Failed to parse PSGC response for workflow, response dict: {psgc_response_dict},  {workflow.id}: {e}"
            logger.error(error_msg)
            raise HttpException(
                status_code=500,
                detail=error_msg,
            )


def get_psgc_service(
    client: PsgcClient = Depends(get_psgc_client),
) -> PsgcService:
    """FastAPI dependency provider for PsgcService."""
    return PsgcService(client=client)
