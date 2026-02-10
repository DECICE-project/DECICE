import json
import logging

from fastapi import Request
from kubernetes_asyncio import client
from kubernetes_asyncio.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesService:
    """
    A stateless, asynchronous client for the Kubernetes API.
    Handles Jobs, Deployments, PVCs, and Generic Resources.
    """

    def __init__(self, api_client: client.ApiClient):
        self.api_client = api_client
        self.core_v1_api = client.CoreV1Api(api_client)
        self.batch_v1_api = client.BatchV1Api(api_client)
        self.apps_v1_api = client.AppsV1Api(api_client)

    async def ensure_pvc_exists(self, name: str, namespace: str, size: str):
        """Checks if a PVC exists. If not, it creates one."""
        try:
            await self.core_v1_api.read_namespaced_persistent_volume_claim(
                name, namespace
            )
            logger.info(f"PVC '{name}' already exists in namespace '{namespace}'.")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"PVC '{name}' not found. Creating it with size {size}...")
                await self.create_pvc(name, namespace, size)
            else:
                logger.error(f"API Error checking for PVC '{name}': {e}")
                raise

    async def create_pvc(self, name: str, namespace: str, size: str):
        """Creates a new PersistentVolumeClaim."""
        pvc_manifest = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": size}),
            ),
        )
        try:
            await self.core_v1_api.create_namespaced_persistent_volume_claim(
                namespace, pvc_manifest
            )
            logger.info(f"Successfully created PVC '{name}' with size {size}.")
        except ApiException as e:
            logger.error(f"API Error creating PVC '{name}': {e}", exc_info=True)
            raise

    async def delete_pvc(self, name: str, namespace: str):
        """Deletes a PersistentVolumeClaim."""
        try:
            await self.core_v1_api.delete_namespaced_persistent_volume_claim(
                name, namespace
            )
            logger.info(f"Successfully deleted PVC '{name}'.")
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Tried to delete PVC '{name}' but it was already gone.")
                return
            logger.error(f"API Error deleting PVC '{name}': {e}", exc_info=True)
            raise

    async def get_job_status(self, name: str, namespace: str) -> dict | None:
        """Gets the status of a specific Kubernetes Job."""
        try:
            job = await self.batch_v1_api.read_namespaced_job_status(name, namespace)
            status = job.status
            return {
                "succeeded": status.succeeded or 0,
                "failed": status.failed or 0,
                "active": status.active or 0,
            }
        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"API Error getting job status for {name}: {e}")
            raise

    async def get_pod_failure_reason(
        self, resource_name: str, namespace: str, is_job: bool = True
    ) -> str | None:
        """
        Checks if the pods belonging to a job or deployment are stuck in a failure state.
        Useful for catching ImagePullBackOff early.
        """
        try:
            if is_job:
                # Jobs automatically label pods with 'job-name'
                label_selector = f"job-name={resource_name}"
                pods = await self.core_v1_api.list_namespaced_pod(
                    namespace=namespace, label_selector=label_selector
                )
                items = pods.items
            else:
                # INFO: For Deployments, finding pods is trickier without knowing the specific matchLabels.
                # A robust heuristic is checking if the pod name starts with the deployment name,
                # as K8s names pods <deployment>-<replicaset>-<hash>.
                all_pods = await self.core_v1_api.list_namespaced_pod(
                    namespace=namespace
                )
                items = [
                    p
                    for p in all_pods.items
                    if p.metadata.name.startswith(resource_name)
                ]

            if not items:
                return None

            for pod in items:
                # Check for Scheduling Failures (Pending + Unschedulable)
                if pod.status.phase == "Pending" and pod.status.conditions:
                    for cond in pod.status.conditions:
                        if (
                            cond.type == "PodScheduled"
                            and cond.status == "False"
                            and cond.reason == "Unschedulable"
                        ):
                            if "unbound immediate PersistentVolumeClaims" in cond.message:
                                continue
                            return f"Scheduling Failed: {cond.message}"

                # Check for Container Failures
                if not pod.status.container_statuses:
                    continue

                for container_status in pod.status.container_statuses:
                    state = container_status.state

                    # Check for Waiting errors (Image issues, config errors)
                    if state.waiting and state.waiting.reason in [
                        "ErrImagePull",
                        "ImagePullBackOff",
                        "InvalidImageName",
                        "CreateContainerConfigError",
                    ]:
                        return f"Pod stuck: {state.waiting.reason} - {state.waiting.message}"

                    # Check for Terminated errors (CrashLoop)
                    if state.terminated and state.terminated.exit_code != 0:
                        if state.waiting and "BackOff" in state.waiting.reason:
                            return f"Pod stuck: {state.waiting.reason}"
            return None
        except ApiException as e:
            logger.error(f"Error checking pod status for {resource_name}: {e}")
            return None

    async def delete_job(self, name: str, namespace: str):
        """Deletes a Kubernetes Job."""
        try:
            await self.batch_v1_api.delete_namespaced_job(
                name, namespace, propagation_policy="Background"
            )
            logger.info(f"Deleted job '{name}' from namespace '{namespace}'.")
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Tried to delete job '{name}' but it was already gone.")
                return
            logger.error(f"API Error deleting job {name}: {e}")
            raise

    async def delete_deployment(self, name: str, namespace: str):
        """Deletes a Kubernetes Deployment."""
        try:
            await self.apps_v1_api.delete_namespaced_deployment(
                name, namespace, propagation_policy="Background"
            )
            logger.info(f"Deleted deployment '{name}' from namespace '{namespace}'.")
        except ApiException as e:
            if e.status == 404:
                logger.warning(
                    f"Tried to delete deployment '{name}' but it was already gone."
                )
                return
            logger.error(f"API Error deleting deployment {name}: {e}")
            raise

    async def apply_job(
        self, job_manifest: client.V1Job, namespace: str
    ) -> client.V1Job:
        """Applies a V1Job manifest to the cluster."""
        try:
            created_job = await self.batch_v1_api.create_namespaced_job(
                body=job_manifest, namespace=namespace
            )
            return created_job
        except ApiException as e:
            if e.status == 409:
                logger.warning(
                    f"Job '{job_manifest.metadata.name}' already exists. Deleting and recreating."
                )
                await self.delete_job(
                    name=job_manifest.metadata.name, namespace=namespace
                )
                created_job = await self.batch_v1_api.create_namespaced_job(
                    body=job_manifest, namespace=namespace
                )
                return created_job
            logger.error(f"API Error applying job: {e}", exc_info=True)
            raise

    async def apply_generic_manifest(self, resource: dict, namespace: str):
        """
        Applies a generic Kubernetes resource (Service, Namespace, Deployment, etc.).
        Routes the resource to the correct API endpoint based on its 'kind'.
        """
        kind = resource.get("kind")
        metadata = resource.get("metadata", {})
        name = metadata.get("name")

        if not kind:
            raise ValueError("Resource missing 'kind' field.")

        logger.info(f"Applying generic resource: Kind={kind}, Name={name}")

        try:
            if kind == "Namespace":
                # Namespaces are cluster-scoped
                await self.core_v1_api.create_namespace(body=resource)
            elif kind == "Service":
                await self.core_v1_api.create_namespaced_service(
                    namespace=namespace, body=resource
                )
            elif kind == "ConfigMap":
                await self.core_v1_api.create_namespaced_config_map(
                    namespace=namespace, body=resource
                )
            elif kind == "Secret":
                await self.core_v1_api.create_namespaced_secret(
                    namespace=namespace, body=resource
                )
            elif kind == "Deployment":
                await self.apps_v1_api.create_namespaced_deployment(
                    namespace=namespace, body=resource
                )
            elif kind == "StatefulSet":
                await self.apps_v1_api.create_namespaced_stateful_set(
                    namespace=namespace, body=resource
                )
            else:
                logger.warning(
                    f"Generic apply not implemented for Kind '{kind}'. Skipping."
                )
                return

            logger.info(f"Successfully applied {kind} '{name}'")

        except ApiException as e:
            if e.status == 409:
                logger.info(f"Resource {kind} '{name}' already exists. Ignoring.")
                return
            logger.error(f"API Error applying {kind} '{name}': {e}", exc_info=True)
            raise

    async def delete_generic_resource(self, resource: dict, namespace: str):
        """
        Deletes a generic Kubernetes resource.
        Used during task cancellation to clean up non-job resources.
        """
        kind = resource.get("kind")
        metadata = resource.get("metadata", {})
        name = metadata.get("name")

        if not kind or not name:
            logger.warning(
                "Cannot delete generic resource: missing kind or name in definition."
            )
            return

        logger.info(f"Deleting generic resource: Kind={kind}, Name={name}")

        try:
            if kind == "Namespace":
                await self.core_v1_api.delete_namespace(name=name)
            elif kind == "Service":
                await self.core_v1_api.delete_namespaced_service(
                    name=name, namespace=namespace
                )
            elif kind == "ConfigMap":
                await self.core_v1_api.delete_namespaced_config_map(
                    name=name, namespace=namespace
                )
            elif kind == "Secret":
                await self.core_v1_api.delete_namespaced_secret(
                    name=name, namespace=namespace
                )
            elif kind == "Deployment":
                await self.delete_deployment(name, namespace)
            elif kind == "StatefulSet":
                await self.apps_v1_api.delete_namespaced_stateful_set(
                    name=name, namespace=namespace, propagation_policy="Background"
                )
            else:
                logger.warning(
                    f"Generic delete not implemented for Kind '{kind}'. Skipping."
                )
                return

            logger.info(f"Successfully deleted {kind} '{name}'")

        except ApiException as e:
            if e.status == 404:
                logger.info(f"Resource {kind} '{name}' already gone. Ignoring.")
                return
            logger.error(f"API Error deleting {kind} '{name}': {e}", exc_info=True)
            raise


def get_kubernetes_service(request: Request) -> KubernetesService:
    if not hasattr(request.app.state, "k8s_api_client"):
        raise RuntimeError(
            "Kubernetes client not initialized. Check app lifespan management."
        )
    return KubernetesService(api_client=request.app.state.k8s_api_client)
