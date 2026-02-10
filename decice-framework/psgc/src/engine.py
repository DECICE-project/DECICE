import asyncio
import json
import logging
import time
from uuid import UUID

from kubernetes_asyncio import client as k8s_client
from kubernetes_asyncio import watch

from clients.cm_client import CMClient
from config import ServiceSettings
from io_models import ScheduleResponse, TaskStatus, WorkflowStatus
from repository.redis_workflow_repository import RedisWorkflowRepository
from service.kubernetes_service import KubernetesService
from service.slurm_service import SlurmService
from service.storage_service import StorageService

logger = logging.getLogger(__name__)

RECONCILIATION_INTERVAL = 10
STUCK_JOB_CHECK_INTERVAL_SECONDS = 30
PENDING_DATA_CHECK_INTERVAL_SECONDS = 60


class PsgcEngine:
    """The proactive, watcher-driven orchestration engine for the PSGC."""

    def __init__(
        self,
        k8s_service: KubernetesService,
        slurm_service: SlurmService,
        cm_client: CMClient,
        repository: RedisWorkflowRepository,
        storage_service: StorageService,
        settings: ServiceSettings,
    ):
        """Initializes the engine with all its necessary service dependencies."""
        self.k8s_service = k8s_service
        self.slurm_service = slurm_service
        self.cm_client = cm_client
        self.repository = repository
        self.storage_service = storage_service
        self.settings = settings
        logger.info("PSGC Engine initialized.")

    async def run_global_loops(self):
        """Starts the engine's concurrent loops for events and reconciliation."""
        logger.info("Engine starting global execution loops...")
        await asyncio.gather(
            self._run_periodic_reconciliation(), self._run_watcher_loop()
        )

    async def _run_watcher_loop(self):
        """A single, global loop that watches all Kubernetes Job events."""
        logger.info("Engine Watcher Loop started.")
        w = watch.Watch()
        while True:
            try:
                async for event in w.stream(
                    self.k8s_service.batch_v1_api.list_namespaced_job,
                    namespace="default",
                    label_selector="managed-by=psgc",
                    timeout_seconds=60,
                ):
                    await self._handle_k8s_job_event(event)
            except asyncio.CancelledError:
                logger.info("Watcher loop cancelled.")
                break
            except Exception as e:
                logger.error(
                    f"Watcher stream disconnected: {e}. Reconnecting...",
                    exc_info=True,
                )
                await asyncio.sleep(5)

    async def _handle_k8s_job_event(self, event: dict):
        """Dispatches Kubernetes job events based on event type."""
        event_type = event.get("type")
        job_object = event.get("object")

        if event.get("type") != "MODIFIED" or not job_object or not job_object.status:
            return

        labels = job_object.metadata.labels or {}
        workflow_id_str = labels.get("psgc.workflow_id")
        # Look for the new label 'psgc.task_id'
        task_id_str = labels.get("psgc.task_id")

        if not workflow_id_str or not task_id_str:
            return

        try:
            workflow_id = UUID(workflow_id_str)
            task_id = UUID(task_id_str)
        except ValueError:
            logger.warning(
                f"Invalid UUID in K8s labels: {workflow_id_str}, {task_id_str}"
            )
            return

        current_status = await self.repository.get_task_status(workflow_id, task_id)

        # If it's already in a terminal state in our DB, ignore further K8s events
        if current_status in [
            TaskStatus.SUCCEEDED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        ]:
            return

        is_succeeded = job_object.status.succeeded and job_object.status.succeeded > 0
        is_failed = job_object.status.failed and job_object.status.failed > 0
        is_running = (job_object.status.active or 0) > 0 and not (
            is_failed or is_succeeded
        )

        final_status = None
        detail = ""

        if is_running:
            if current_status != TaskStatus.RUNNING.value:
                # Update DB and notify CM
                await self.repository.update_task_status(
                    workflow_id, task_id, TaskStatus.RUNNING.value
                )
                await self.cm_client.patch_task_status(
                    task_id=task_id,
                    status=TaskStatus.RUNNING.value,
                    detail="Kubernetes job started running.",
                )
            return

        elif is_succeeded:
            final_status = TaskStatus.SUCCEEDED.value
            detail = "Job completed via K8s watcher."
            
            # Release the PVC lock by deleting the completed job
            job_name = job_object.metadata.name
            try:
                logger.info(f"Task {task_id} succeeded. Deleting K8s Job '{job_name}' to release PVC lock.")
                await self.k8s_service.delete_job(job_name, "default")
            except Exception as e:
                logger.warning(f"Failed to auto-delete successful job {job_name}: {e}")
        elif is_failed:
            final_status = TaskStatus.FAILED.value
            detail = "Job failed via K8s watcher."

        if final_status:
            logger.info(f"Watcher detected status {final_status} for task {task_id}.")
            await self.repository.update_task_status(workflow_id, task_id, final_status)
            await self.cm_client.report_task_completion(
                task_id=task_id,
                completion_status=final_status,
                detail=detail,
            )

    async def _run_periodic_reconciliation(self):
        """Periodically reconciles the state of all active workflows."""
        logger.info("Engine Periodic Reconciliation Loop started.")
        last_stuck_check = 0
        last_pending_data_check = 0

        while True:
            try:
                now = time.time()

                if now - last_pending_data_check > PENDING_DATA_CHECK_INTERVAL_SECONDS:
                    logger.debug(
                        "Running periodic check for workflows stuck in PENDING_DATA..."
                    )
                    await self.reconcile_pending_data_workflows()
                    last_pending_data_check = now

                active_workflows = await self.repository.get_active_workflow_ids()
                logger.debug(
                    f"Found {len(active_workflows)} active workflows to reconcile."
                )
                reconciliation_tasks = [
                    self.reconcile_one_workflow(wf_id) for wf_id in active_workflows
                ]

                if now - last_stuck_check > STUCK_JOB_CHECK_INTERVAL_SECONDS:
                    logger.debug("Running periodic check for stuck/timed-out tasks...")
                    stuck_tasks = [
                        self.reconcile_running_tasks(wf_id)
                        for wf_id in active_workflows
                    ]
                    reconciliation_tasks.extend(stuck_tasks)
                    last_stuck_check = now

                if reconciliation_tasks:
                    await asyncio.gather(*reconciliation_tasks)

            except Exception as e:
                logger.error(
                    f"Unhandled exception in reconciliation loop: {e}", exc_info=True
                )

            await asyncio.sleep(RECONCILIATION_INTERVAL)

    async def reconcile_pending_data_workflows(self):
        """Finds workflows waiting for data and checks object storage for their files."""
        pending_ids = await self.repository.get_workflow_ids_by_status(
            WorkflowStatus.PENDING_DATA.value
        )
        if not pending_ids:
            return

        logger.info(f"Found {len(pending_ids)} workflows in PENDING_DATA to check.")
        for workflow_id in pending_ids:
            try:
                definition = await self.repository.get_workflow_definition(workflow_id)
                if not definition or not definition.get("filename"):
                    continue

                object_key = f"{workflow_id}/inputs/{definition['filename']}"

                if self.storage_service.object_exists(
                    bucket_name="workflows", object_name=object_key
                ):
                    logger.warning(
                        f"Safety net triggered for workflow {workflow_id}. "
                        "File found in storage but webhook was missed. Activating now."
                    )
                    await self.repository.activate_initial_tasks(workflow_id)

                    new_status = WorkflowStatus.PROGRESSING.value
                    await self.repository.update_workflow_status(
                        workflow_id, new_status
                    )
                    await self.cm_client.report_workflow_status(workflow_id, new_status)

            except Exception as e:
                logger.error(
                    f"Error during pending data reconciliation for {workflow_id}: {e}",
                    exc_info=True,
                )

    async def reconcile_one_workflow(self, workflow_id: UUID):
        """Checks a workflow's state, submits ready tasks, and handles completion."""
        definition = await self.repository.get_workflow_definition(workflow_id)
        if not definition:
            return

        statuses = await self.repository.get_task_statuses(workflow_id)

        # Use 'tasks' key
        for task_data in definition.get("tasks", []):
            task_id_str = task_data["id"]
            if statuses.get(task_id_str) == TaskStatus.READY.value:
                logger.info(f"Reconciler found READY task {task_id_str}. Submitting...")
                await self.repository.update_task_status(
                    workflow_id, UUID(task_id_str), TaskStatus.SCHEDULING.value
                )
                asyncio.create_task(
                    self.submit_task(workflow_id, task_data, definition)
                )

        # Call cleanup check
        await self.reconcile_workflow_cleanup(workflow_id, statuses, definition)

    async def reconcile_workflow_cleanup(
        self, workflow_id: UUID, statuses: dict, definition: dict
    ):
        """Handles workflow completion and cleanup only when all tasks are in a terminal state."""
        terminal_statuses = {
            TaskStatus.SUCCEEDED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        }

        task_list = definition.get("tasks", [])
        if not task_list:
            return

        # Ensure all tasks defined are in the statuses map
        if len(statuses) != len(task_list):
            return

        # Check if all are terminal
        if any(status not in terminal_statuses for status in statuses.values()):
            return

        # Determine final workflow status
        if all(status == TaskStatus.SUCCEEDED.value for status in statuses.values()):
            final_workflow_status = WorkflowStatus.SUCCEEDED.value
        else:
            # If any failed or cancelled, the workflow failed
            final_workflow_status = WorkflowStatus.FAILED.value

        logger.info(
            f"Workflow {workflow_id} has completed with status: {final_workflow_status}"
        )
        await self._cleanup_workflow(workflow_id, final_workflow_status)

    async def _cleanup_workflow(self, workflow_id: UUID, final_status: str):
        try:
            await self.cm_client.report_workflow_status(
                workflow_id=workflow_id, status=final_status
            )
        except Exception as e:
            logger.error(
                f"Failed to report final workflow status for {workflow_id}: {e}"
            )

        definition = await self.repository.get_workflow_definition(workflow_id)
        if definition and definition.get("annotations", {}).get(
            "dev.decice.com/storage-request"
        ):
            pvc_name = f"pvc-{workflow_id}"
            await self.k8s_service.delete_pvc(name=pvc_name, namespace="default")

        await self.repository.delete_workflow_state(workflow_id)
        logger.info(f"Cleaned up state for completed workflow {workflow_id}.")

    async def reconcile_running_tasks(self, workflow_id: UUID):
        statuses = await self.repository.get_task_statuses(workflow_id)
        definition = await self.repository.get_workflow_definition(workflow_id)
        if not definition:
            return
        tasks_map = {t["id"]: t for t in definition.get("tasks", [])}

        for task_id_str, status in statuses.items():
            if status == TaskStatus.RUNNING.value:
                task_id = UUID(task_id_str)
                task_data = tasks_map.get(task_id_str)

                if not task_data:
                    continue

                job_type = task_data.get("type", "job")

                # Skip Slurm jobs (handled by webhook)
                if job_type == "hpc_job":
                    continue

                # Determine Resource Name and Type
                resource_name = None
                is_job = True

                if job_type == "k8s_resource":
                    # Generic resources (could be anything, but we check if it's compute-like)
                    try:
                        manifest = json.loads(task_data.get("command_str", "{}"))
                        kind = manifest.get("kind")
                        if kind in ["Deployment", "StatefulSet", "DaemonSet"]:
                            is_job = False
                            resource_name = manifest.get("metadata", {}).get("name")
                        elif kind == "Job":
                            is_job = True
                            resource_name = manifest.get("metadata", {}).get("name")
                        # Ignore Services/ConfigMaps here for now
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse generic resource manifest during reconciliation for task {task_id}: {e}"
                        )
                        continue
                elif job_type == "deployment":
                    resource_name = f"psgc-job-{task_id}"
                    is_job = False
                elif job_type == "job":
                    resource_name = f"psgc-job-{task_id}"
                    is_job = True

                if not resource_name:
                    continue

                # Check for Failure
                failure_reason = await self.k8s_service.get_pod_failure_reason(
                    resource_name, "default", is_job=is_job
                )

                if failure_reason:
                    logger.warning(
                        f"Task {task_id} ({resource_name}) failed: {failure_reason}"
                    )
                    logger.warning(
                        "Likely Cause: Node selector does not match any available node."
                    )
                    logger.warning(
                        "Action: Deleting stuck resource and marking task FAILED."
                    )
                    # Delete the stuck resource
                    if job_type == "k8s_resource":
                        await self.k8s_service.delete_generic_resource(
                            json.loads(task_data.get("command_str")), "default"
                        )
                    elif job_type == "deployment":
                        await self.k8s_service.delete_deployment(
                            resource_name, "default"
                        )
                    else:
                        await self.k8s_service.delete_job(resource_name, "default")

                    # Report Failure
                    await self.repository.update_task_status(
                        workflow_id, task_id, TaskStatus.FAILED.value
                    )
                    await self.cm_client.report_task_completion(
                        task_id=task_id,
                        completion_status=TaskStatus.FAILED.value,
                        detail=failure_reason,
                    )

    async def cancel_task(self, workflow_id: UUID, task_data: dict):
        """
        Actively stops/deletes the underlying resource for a task.
        """
        task_id = UUID(task_data["id"])
        job_type = task_data.get("type", "job")

        # Standard name for compute tasks
        resource_name = f"psgc-job-{task_id}"

        logger.info(f"Cancelling task {task_id} (Type: {job_type})...")

        try:
            if job_type == "deployment":
                await self.k8s_service.delete_deployment(
                    name=resource_name, namespace="default"
                )

            elif job_type == "job":
                await self.k8s_service.delete_job(
                    name=resource_name, namespace="default"
                )

            elif job_type == "k8s_resource":
                # For generic resources, we must deserialize the command_str to get Kind/Name
                manifest_json = task_data.get("command_str")
                if manifest_json:
                    resource_body = json.loads(manifest_json)
                    await self.k8s_service.delete_generic_resource(
                        resource_body, "default"
                    )
                else:
                    logger.warning(
                        f"Cannot delete generic resource {task_id}: missing definition."
                    )

            # Update status
            await self.repository.update_task_status(
                workflow_id, task_id, TaskStatus.CANCELLED.value
            )
            logger.info(f"Task {task_id} successfully cancelled and resource deleted.")

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)

    async def submit_task(
        self, workflow_id: UUID, task_data: dict, workflow_definition: dict
    ):
        """Handles the full lifecycle of submitting one task."""
        task_id = UUID(task_data["id"])
        job_type = task_data.get("type", "job")

        try:
            if job_type in ("job", "deployment"):
                logger.info(f"Submitting task {task_id} to Kubernetes")
                await self._submit_k8s_task(workflow_id, task_data, workflow_definition)
            elif job_type == "hpc_job":
                logger.info(f"Submitting task {task_id} to Slurm")
                await self._submit_slurm_task(
                    workflow_id, task_data, workflow_definition
                )
            # Handle Generic K8s Resources (Namespace, Service, etc.)
            elif job_type == "k8s_resource":
                logger.info(
                    f"Applying generic resource {task_id} to Kubernetes (Skipping Scheduler)"
                )
                await self._submit_generic_k8s_resource(workflow_id, task_data)
            else:
                raise ValueError(f"Unknown task type: '{job_type}'")
        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}", exc_info=True)
            await self.repository.update_task_status(
                workflow_id, task_id, TaskStatus.FAILED.value
            )
            await self.cm_client.report_task_completion(
                task_id=task_id,
                completion_status=TaskStatus.FAILED.value,
                detail=str(e),
            )

    async def _submit_generic_k8s_resource(self, workflow_id: UUID, task_data: dict):
        """Directly applies a generic K8s resource manifest."""
        task_id = UUID(task_data["id"])
        try:
            manifest_json = task_data.get("command_str")
            if not manifest_json:
                raise ValueError("No manifest found in command_str")

            resource_body = json.loads(manifest_json)
            kind = resource_body.get("kind")

            await self.k8s_service.apply_generic_manifest(
                resource=resource_body, namespace="default"
            )

            logger.info(f"Applied generic resource {task_id} (Kind: {kind})")

            if kind in ["Deployment", "Job", "StatefulSet", "Pod"]:
                new_status = TaskStatus.RUNNING.value
                detail = "Generic workload applied. Watching for status."
            else:
                # Services, etc. are "done" immediately
                new_status = TaskStatus.SUCCEEDED.value
                detail = "Infrastructure resource applied successfully."

            await self.repository.update_task_status(workflow_id, task_id, new_status)

            if new_status == TaskStatus.SUCCEEDED.value:
                await self.cm_client.report_task_completion(
                    task_id=task_id, completion_status=new_status, detail=detail
                )
            else:
                # Notify CM that it is running, so UI updates
                await self.cm_client.patch_task_status(
                    task_id=task_id, status=new_status, detail=detail
                )

        except Exception as e:
            logger.error(f"Failed to apply generic resource {task_id}: {e}")
            # Fail the task immediately if YAML could not be applied
            await self.repository.update_task_status(
                workflow_id, task_id, TaskStatus.FAILED.value
            )
            await self.cm_client.report_task_completion(
                task_id=task_id,
                completion_status=TaskStatus.FAILED.value,
                detail=f"Failed to apply resource: {str(e)}",
            )

    async def _submit_k8s_task(
        self, workflow_id: UUID, task_data: dict, workflow_definition: dict
    ):
        """Submits a task to Kubernetes."""
        task_id = UUID(task_data["id"])

        storage_request = task_data.get("annotations", {}).get(
            "dev.decice.com/storage-request"
        )
        if not storage_request:
            storage_request = workflow_definition.get("annotations", {}).get(
                "dev.decice.com/storage-request"
            )
        if storage_request:
            pvc_name = f"pvc-{workflow_id}"
            await self.k8s_service.ensure_pvc_exists(
                name=pvc_name, size=storage_request, namespace="default"
            )

        requirements = {
            "required_cpu": task_data.get("required_cpu"),
            "required_memory": task_data.get("required_memory"),
            "required_gpu": task_data.get("required_gpu"),
        }

        target_node = None # Default to None

        if not self.settings.SCHED_WEBHOOK:
            decision: ScheduleResponse = await self.cm_client.get_scheduling_decision(
                task_id, requirements
            )
            logger.info(f"Scheduling decision for {task_id}: {decision}")

            # Find the target node for this task_id
            target_node = None
            for placement in decision.get("placements", []):
                if placement.get("task_id") == str(task_id):
                    target_nodes = placement.get("target_node_ids", [])
                    if target_nodes:
                        target_node = target_nodes[0]  # pick the first node
                    break

            if not target_node:
                raise ValueError("Scheduler did not return a target node.")

        k8s_job_name = f"psgc-job-{task_id}"
        manifest = self._build_k8s_job_manifest(
            k8s_job_name, workflow_id, task_data, workflow_definition, target_node
        )
        await self.k8s_service.apply_job(manifest, namespace="default")

        # Update status to PENDING (submitted to K8s)
        await self.repository.update_task_status(
            workflow_id, task_id, TaskStatus.PENDING.value
        )

        # Notify CM
        await self.cm_client.patch_task_status(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            detail="Job submitted to Kubernetes.",
        )

    async def _submit_slurm_task(
        self, workflow_id: UUID, task_data: dict, workflow_definition: dict
    ):
        """Submits a task to Slurm via the slurm-client service."""
        task_id = UUID(task_data["id"])

        hpc_context = workflow_definition.get("hpc_context")
        if not hpc_context or not hpc_context.get("platform_username"):
            raise ValueError(
                f"Missing hpc_context.platform_username for HPCJob {task_id}"
            )

        username = hpc_context["platform_username"]
        work_dir = hpc_context.get("default_working_dir")

        script_content = task_data.get("command_str")
        if not script_content:
            raise ValueError(
                f"Missing sbatch script content (command_str) for HPCJob {task_id}"
            )

        # Call the Slurm Service
        slurm_response = await self.slurm_service.submit_job(
            sbatch_file=script_content,
            username=username,
            work_dir=work_dir,
            task_id=task_id,
        )

        slurm_job_id = slurm_response.get("job_id")
        if not slurm_job_id:
            raise ValueError(f"Slurm Client did not return a job_id: {slurm_response}")

        logger.info(
            f"Slurm task {task_id} submitted. Upstream Slurm job ID: {slurm_job_id}"
        )

        # Store the external Slurm Job ID for later
        await self.repository.set_task_external_id(
            workflow_id, task_id, str(slurm_job_id)
        )

        # Update status to PENDING
        await self.repository.update_task_status(
            workflow_id, task_id, TaskStatus.PENDING.value
        )

        # Notify CM
        await self.cm_client.patch_task_status(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            detail=f"Job submitted to Slurm. Slurm Job ID: {slurm_job_id}",
        )

        logger.info(f"Slurm task {task_id} marked as PENDING. Awaiting webhook.")

    def _build_k8s_job_manifest(
        self,
        k8s_job_name: str,
        workflow_id: UUID,
        task_data: dict,
        workflow_definition: dict,
        target_node: str | None = None,
    ) -> k8s_client.V1Job:
        """Constructs the complete Kubernetes Job manifest."""
        init_containers = []
        volumes = [
            k8s_client.V1Volume(
                name="workdir", empty_dir=k8s_client.V1EmptyDirVolumeSource()
            )
        ]
        volume_mounts = [k8s_client.V1VolumeMount(name="workdir", mount_path="/data")]

        storage_req = task_data.get("annotations", {}).get("dev.decice.com/storage-request")
        if not storage_req:
            storage_req = workflow_definition.get("annotations", {}).get("dev.decice.com/storage-request")

        if storage_req:
            pvc_name = f"pvc-{workflow_id}"
            volumes[0] = k8s_client.V1Volume(
                name="workdir",
                persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=pvc_name
                ),
            )

        # if workflow_definition.get("annotations", {}).get(
        #     "dev.decice.com/storage-request"
        # ):
        #     pvc_name = f"pvc-{workflow_id}"
        #     volumes[0] = k8s_client.V1Volume(
        #         name="workdir",
        #         persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
        #             claim_name=pvc_name
        #         ),
        #     )

        if workflow_definition.get("filename"):
            filename = workflow_definition["filename"]
            # object_key = f"workflows/{workflow_id}/inputs/{filename}"
            object_key = f"{workflow_id}/inputs/{filename}"
            downloader = k8s_client.V1Container(
                name="mc-downloader",
                image="minio/mc",
                command=["sh", "-c"],
                args=[
                    "set -ex; "
                    "mc alias set myminio $MINIO_SERVER $MINIO_ACCESS_KEY $MINIO_SECRET_KEY; "
                    f"mc cp myminio/workflows/{object_key} /data/{filename}; " 
                    "ls -l /data;"
                ],
                env=[
                    k8s_client.V1EnvVar(
                        name="MINIO_SERVER",
                        # value=f"http://{self.settings.MINIO_ENDPOINT}",
                        # NOTE: change this for production
                        value="http://minio:9000",
                    ),
                    k8s_client.V1EnvVar(
                        name="MINIO_ACCESS_KEY", value=self.settings.MINIO_ACCESS_KEY
                    ),
                    k8s_client.V1EnvVar(
                        name="MINIO_SECRET_KEY", value=self.settings.MINIO_SECRET_KEY
                    ),
                ],
                volume_mounts=volume_mounts,
            )
            init_containers.append(downloader)

            if filename.lower().endswith(".zip"):
                unzipper = k8s_client.V1Container(
                    name="unzipper",
                    image="alpine:latest", 
                    command=["sh", "-c"],
                    args=[
                        "set -ex; "
                        "if [ ! -f /data/.unzipped ]; then "
                        f"  unzip -o /data/{filename} -d /data/; "
                        "  touch /data/.unzipped; "
                        "else "
                        "  echo 'Already unzipped'; "
                        "fi"
                    ],
                    volume_mounts=volume_mounts,
                )
                init_containers.append(unzipper)

        requests = {
            "cpu": task_data.get("required_cpu"),
            "memory": task_data.get("required_memory"),
        }
        limits = requests.copy()
        if task_data.get("required_gpu"):
            gpu_str = str(task_data["required_gpu"])
            requests["nvidia.com/gpu"] = gpu_str
            limits["nvidia.com/gpu"] = gpu_str
        resources = k8s_client.V1ResourceRequirements(requests=requests, limits=limits)

        raw_command = task_data.get("command_str", "[]")
        try:
            # Try to parse as JSON (Argo/K8s style)
            command_list = json.loads(raw_command)
            # If it parsed as a single string, wrap it for sh -c
            if isinstance(command_list, str):
                command_list = ["sh", "-c", command_list]
        except (json.JSONDecodeError, TypeError):
            # It's a raw shell string (Snakemake style), wrap it for Kubernetes
            command_list = ["sh", "-c", raw_command]

        main_container = k8s_client.V1Container(
            name="main-container",
            image=task_data.get("image"),
            command=command_list,
            resources=resources,
            volume_mounts=volume_mounts,
        )

        # main_container = k8s_client.V1Container(
        #     name="main-container",
        #     image=task_data.get("image"),
        #     command=json.loads(task_data.get("command_str", "[]")),
        #     resources=resources,
        #     volume_mounts=volume_mounts,
        # )

        annotations = task_data.get("annotations", {})

        hpc_context = workflow_definition.get("hpc_context", {})
        if hpc_context.get("platform_username"):
            annotations["interlink.com/username"] = hpc_context["platform_username"]

        if task_data.get("env"):
            env_vars = []
            for env in task_data["env"]:
                env_var = k8s_client.V1EnvVar(
                    name=env["name"],
                    value=env.get("value"),
                    value_from=env.get("valueFrom"),
                )
                env_vars.append(env_var)
            main_container.env = env_vars

        pod_specs = {
            "init_containers": init_containers,
            "containers": [main_container],
            "volumes": volumes,
            "restart_policy": "Never"
        }

        if target_node:
            pod_specs["node_selector"] = {"kubernetes.io/hostname": target_node}

        pod_template = k8s_client.V1PodTemplateSpec(
            metadata=k8s_client.V1ObjectMeta(annotations=annotations),
            spec=k8s_client.V1PodSpec(**pod_specs),
        )
        if task_data.get("labels"):
            pod_template.metadata.labels = (
                {**pod_template.metadata.labels, **task_data["labels"]}
                if pod_template.metadata.labels
                else task_data["labels"]
            )

        job_spec = k8s_client.V1JobSpec(template=pod_template, backoff_limit=2)

        return k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s_client.V1ObjectMeta(
                name=k8s_job_name,
                labels={
                    "managed-by": "psgc",
                    "psgc.workflow_id": str(workflow_id),
                    "psgc.task_id": str(task_data["id"]),
                },
            ),
            spec=job_spec,
        )