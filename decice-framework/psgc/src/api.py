import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from kubernetes_asyncio import client as k8s_client
from kubernetes_asyncio import config as k8s_config
from kubernetes_asyncio.config.config_exception import ConfigException
from minio import Minio
from redis import ConnectionPool

from auth.auth import verify_internal_traffic
from clients.cm_client import CMClient
from clients.slurm_client import SlurmClient
from config import get_settings
from engine import PsgcEngine
from io_models import (MinioWebhookPayload, PSGCTaskStatusUpdateRequest,
                       SlurmWebhookPayload, WorkflowPSGCRequest,
                       WorkflowPSGCResponse)
from repository.redis_workflow_repository import RedisWorkflowRepository
from service.kubernetes_service import KubernetesService
from service.slurm_service import SlurmService
from service.storage_service import StorageService
from service.webhook_service import WebhookService, get_webhook_service
from service.workflow_service import WorkflowService, get_workflow_service
from storage.minio_storage import MinioStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def create_k8s_api_client() -> k8s_client.ApiClient:
    """
    Creates a Kubernetes ApiClient, automatically selecting between in-cluster
    configuration and a local kubeconfig file.
    """
    try:
        # First, try to load the configuration from within a Kubernetes cluster.
        k8s_config.load_incluster_config()
        logger.info("Using in-cluster Kubernetes configuration.")
    except ConfigException:
        # If that fails, fall back to loading from the local kubeconfig file.
        await k8s_config.load_kube_config()
        logger.info("Using local kubeconfig for Kubernetes configuration.")

    return k8s_client.ApiClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles the PSGC's application startup, shutdown, and the lifecycle
    of all shared resources and background tasks.
    """
    logger.info("PSGC application starting up...")
    settings = get_settings()
    app.state.settings = settings

    logger.info("Initialize HTTP Client")
    http_headers = {
        "X-Internal-Api-Key": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }
    http_limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    http_timeout = httpx.Timeout(timeout=10.0)
    http_client = httpx.AsyncClient(
        timeout=http_timeout, limits=http_limits, headers=http_headers
    )
    app.state.http_client = http_client

    logger.info("Initialize K8s Client")
    k8s_api_client = await create_k8s_api_client()
    app.state.k8s_api_client = k8s_api_client

    # Redis Client Setup
    logger.info(f"Connecting to Redis: {settings.REDIS_URL}")
    try:
        redis_pool: ConnectionPool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        redis_client = redis.Redis.from_pool(redis_pool)
        await redis_client.ping()
        app.state.redis_client = redis_client
        app.state.redis_pool = redis_pool
        logger.info("Redis client connected and stored in app.state.redis_client")
    except Exception as e:
        logger.exception(
            f"FATAL: Could not connect to Redis at {settings.REDIS_URL}. Application startup aborted."
        )
        raise RuntimeError(
            f"Failed to connect to mandatory Redis service at {settings.REDIS_URL}"
        ) from e

    logger.info(f"Connecting to MinIO: {settings.MINIO_ENDPOINT}:{settings.MINIO_PORT}")
    minio_endpoint_url = f"{settings.MINIO_ENDPOINT}:{settings.MINIO_PORT}"
    try:
        minio_client = Minio(
            minio_endpoint_url,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        minio_client.list_buckets()
        app.state.minio_client = minio_client
        logger.info("MinIO client connected.")
    except Exception as e:
        logger.exception(
            f"FATAL: Could not connect to MinIO at {settings.MINIO_ENDPOINT}:{settings.MINIO_PORT}."
        )
        raise RuntimeError("Failed to connect to mandatory MinIO service") from e

    # Instantiate and Start the PSGC Engine
    k8s_service = KubernetesService(api_client=app.state.k8s_api_client)
    slurm_http_client = SlurmClient(
        base_url=str(settings.SLURM_CLIENT_BASE_URL), http_client=http_client
    )
    cm_client = CMClient(
        base_url=str(settings.CM_SERVICE_BASE_URL),
        client=http_client,
        enable_batching=settings.SCHEDULER_BATCHING_ENABLED,
        batch_max_size=settings.SCHEDULER_BATCH_MAX_SIZE,
        batch_max_wait_ms=settings.SCHEDULER_BATCH_MAX_WAIT_MS,
    )

    slurm_service = SlurmService(slurm_client=slurm_http_client)
    redis_repo = RedisWorkflowRepository(redis_client=app.state.redis_client)
    minio_backend = MinioStorage(client=app.state.minio_client)
    storage_service = StorageService(storage_backend=minio_backend)

    engine_instance = PsgcEngine(
        k8s_service=k8s_service,
        slurm_service=slurm_service,
        cm_client=cm_client,
        repository=redis_repo,
        storage_service=storage_service,
        settings=settings,
    )
    app.state.engine_task = asyncio.create_task(engine_instance.run_global_loops())
    logger.info("PSGC Engine has been started in the background.")

    yield

    # Graceful Shutdown
    logger.info("PSGC application shutting down...")
    await http_client.aclose()
    await k8s_api_client.close()

    if hasattr(app.state, "engine_task") and app.state.engine_task:
        app.state.engine_task.cancel()
        try:
            await app.state.engine_task
        except asyncio.CancelledError:
            logger.info("Engine task successfully cancelled.")

    # Redis Shutdown
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        logger.info("Closing Redis client connection...")
        try:
            await app.state.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    if hasattr(app.state, "redis_pool") and app.state.redis_pool:
        logger.info("Disconnecting Redis connection pool...")
        try:
            await app.state.redis_pool.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")

    logger.info("Shutdown complete.")


app = FastAPI(
    title="Platform Specific Glue Code (PSGC)",
    description="A service to orchestrate workflows on a specific target platform (e.g., Kubernetes).",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def home():
    return RedirectResponse(url="/docs/")


@app.get("/health", status_code=status.HTTP_200_OK, summary="Health Check")
async def health_check():
    return Response(status_code=status.HTTP_200_OK)


@app.post(
    "/workflows",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new workflow definition",
    tags=["Workflows"],
    response_model=WorkflowPSGCResponse,
    dependencies=[Depends(verify_internal_traffic)],
)
async def create_workflow_endpoint(
    workflow: WorkflowPSGCRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Receives a workflow definition from the Control Manager, saves its state,
    and returns a pre-signed URL for data upload if required.
    """
    try:
        logger.info(f"Received delegation for workflow: {workflow.id}")

        upload_url = await workflow_service.create_workflow_and_get_upload_url(
            workflow_request=workflow,
            filename=workflow.filename,
        )

        if upload_url:
            return WorkflowPSGCResponse(
                presigned_url=upload_url,
                message="Workflow created successfully. Data upload required.",
            )
        else:
            return WorkflowPSGCResponse(
                presigned_url=None,
                message="Workflow created successfully. No data upload required.",
            )

    except Exception as e:
        logger.exception(f"Error processing workflow {workflow.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )


@app.post(
    "/workflows/tasks/status",
    status_code=status.HTTP_200_OK,
    summary="Update Task Statuses (CM Callback)",
    tags=["Workflows"],
    dependencies=[Depends(verify_internal_traffic)],
)
async def handle_task_status(
    tasks_update: PSGCTaskStatusUpdateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Receives a task update from the Control Manager,
    and updates PSGC task state.
    """
    try:
        logger.info(f"Received task update request: {tasks_update}")
        _ = await workflow_service.update_task_statuses(tasks_update)
        return {
            "detail": f"Updated task statuses for workflow {tasks_update.workflow_id}"
        }
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error updating tasks {tasks_update}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )


@app.post(
    "/webhooks/minio",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook for MinIO upload events",
    tags=["Internal Webhooks"],
    # dependencies=[Depends(verify_internal_traffic)],
)
async def handle_minio_webhook(
    payload: MinioWebhookPayload,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Receives a notification from MinIO when a file is uploaded, triggering
    the start of a data-dependent workflow.
    """
    try:
        await webhook_service.process_minio_notification(payload)
        return {"status": "event accepted"}
    except Exception:
        # It's crucial to not return a 5xx error to prevent retry storms from MinIO.
        logger.exception("An unexpected error occurred in the MinIO webhook handler.")
        return {"status": "error", "detail": "Internal server error."}

@app.post(
    "/api/scheduler/filter",
    status_code=status.HTTP_200_OK,
    summary="Webhook for scheduler filter request",
    tags=["Internal Webhooks"],
)
async def scheduler_filter(received: dict):
    """
    Filters nodes for pods managed by 'psgc'.
    - If the pod has the correct labels.
    - Otherwise, it allows all nodes to be considered.
    """
    pod = received.get("Pod", {})
    metadata = pod.get("metadata", {})
    labels = metadata.get("labels", {})

    # Do the filtering only for pods managed by DECICE
    if (
        labels.get("managed-by") == "psgc"
        and "psgc.workflow_id" in labels
        and "psgc.task_id" in labels
    ):
        node_names = received.get("NodeNames", [])
        if not node_names:
            return {"NodeNames": []}

        workflow_id = labels["psgc.workflow_id"]
        task_id = labels["psgc.task_id"]

        # TODO: get the requirements from redis psgc:workflows:workflow_id:definitions:task_id:req_cpu,gpu,mem
        # get the chosen node from cm_client.get_scheduling_decision(job_id, requirements, node_names)
        chosen_node = node_names[0]

        logger.info(
            f"Pod for workflow '{workflow_id}', job '{task_id}' "
            f"will be scheduled on node '{chosen_node}'"
        )

        # 4. Return the filtered list containing only the chosen node
        return {"NodeNames": [chosen_node]}
    else:
        # Not managed by DECICE, so we skip filtering and return the received list
        logger.info("Pod does not have required 'psgc' labels, skipping filter.")
        return {"NodeNames": received.get("NodeNames", [])}

@app.post(
    "/webhooks/slurm",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Webhook for Slurm job events",
    tags=["Internal Webhooks"],
    dependencies=[Depends(verify_internal_traffic)],
)
async def handle_slurm_webhook(
    payload: SlurmWebhookPayload,
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """
    Receives a notification from the Slurm Client when a job changes state.
    """
    try:
        await webhook_service.process_slurm_notification(payload)
        return {"status": "event accepted"}
    except Exception:
        logger.exception("An unexpected error occurred in the Slurm webhook handler.")
        return {"status": "error", "detail": "Internal server error."}
