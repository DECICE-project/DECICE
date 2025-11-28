import json
import logging
from typing import Any
from uuid import uuid4

import yaml

from db.models import (Deployment, GenericK8sResource, Job, TaskStatus,
                       Workflow, WorkflowStatus)

from .base import AbstractWorkflowParser
from .registry import ParserRegistry

logger = logging.getLogger(__name__)


@ParserRegistry.register
class K8sParser(AbstractWorkflowParser):
    """
    Parses Kubernetes YAML files to extract Job, Deployment, and application-level Generic resources.

    Features:
    - Supports multi-document YAMLs (separated by '---').
    - 'Job' and 'Deployment' (without nodeSelector) are parsed as COMPUTE tasks for the AI Scheduler.
    - 'Job' and 'Deployment' (WITH nodeSelector) are parsed as GENERIC resources (User-managed placement).
    - 'Service', 'ConfigMap', 'Ingress' are parsed as GENERIC resources (Passthrough).
    - 'Namespace', 'Secret', 'ServiceAccount', 'Role', 'RoleBinding' are IGNORED (Admin-managed).
    """

    DEFAULT_CPU = "1"  # 1 Core
    DEFAULT_MEM = "128M"  # 128 Megabytes

    # Resources that are strictly infrastructure/admin level and should NOT be handled here.
    IGNORED_TYPES = {
        "Namespace",
        "Secret",
        "ServiceAccount",
        "Role",
        "RoleBinding",
        "ClusterRole",
        "ClusterRoleBinding",
        "ResourceQuota",
        "LimitRange",
        "NetworkPolicy",
    }

    @classmethod
    def can_parse(cls, filename: str, file_content: bytes) -> bool:
        """Return True if the YAML file contains at least one parseable Kubernetes resource
        that this parser can handle (ignores admin types and Argo workflows)."""

        if not filename.lower().endswith((".yaml", ".yml")):
            return False

        try:
            docs = yaml.safe_load_all(file_content)
        except (yaml.YAMLError, UnicodeDecodeError):
            return False

        IGNORED_TYPES = getattr(cls, "IGNORED_TYPES", set())

        return any(
            isinstance(doc, dict)
            and doc.get("kind")
            and doc.get("apiVersion")
            and doc.get("kind") not in IGNORED_TYPES
            and not doc.get("apiVersion", "").startswith("argoproj.io")
            for doc in docs
        )

    def _has_node_selector(self, data: dict[str, Any]) -> bool:
        """Checks if the manifest already has a node constraint."""
        spec = data.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        if pod_spec.get("nodeSelector"):
            return True
        return False

    def _extract_common_task_details(self, data: dict[str, Any]) -> dict[str, Any]:
        spec = data.get("spec", {}) or {}
        template = spec.get("template", {}) or {}
        pod_metadata = template.get("metadata", {}) or {}
        annotations = pod_metadata.get("annotations", {}) or {}
        labels = pod_metadata.get("labels")
        pod_spec = template.get("spec", {}) or {}

        containers = pod_spec.get("containers", [])
        if not containers:
            raise ValueError(
                f"Resource '{data.get('metadata', {}).get('name')}' has no containers defined."
            )

        container = containers[0]
        resources = container.get("resources", {}).get("requests", {})

        env_list: list[dict] = []
        for env_var in container.get("env", []):
            if isinstance(env_var, dict):
                env_list.append(env_var)

        gpu_count = None
        try:
            gpu_value = resources.get("nvidia.com/gpu")
            if gpu_value is not None:
                gpu_count = int(gpu_value)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not parse GPU resource '{gpu_value}' as an integer. Ignoring."
            )

        cpu_req = resources.get("cpu")
        if not cpu_req:
            logger.info(
                f"Task '{data.get('metadata', {}).get('name')}' missing CPU request. Defaulting to {self.DEFAULT_CPU}."
            )
            cpu_req = self.DEFAULT_CPU

        mem_req = resources.get("memory")
        if not mem_req:
            logger.info(
                f"Task '{data.get('metadata', {}).get('name')}' missing Memory request. Defaulting to {self.DEFAULT_MEM}."
            )
            mem_req = self.DEFAULT_MEM

        command_str = json.dumps(
            container.get("command", []) + container.get("args", [])
        )

        return {
            "image": container.get("image"),
            "command_str": command_str,
            "required_cpu": cpu_req,
            "required_memory": mem_req,
            "required_gpu": gpu_count,
            "annotations": annotations,
            "env": env_list,
            "labels": labels,
        }

    def _parse_job_spec(self, data: dict[str, Any]) -> Job:
        job_metadata = data.get("metadata", {})
        common_details = self._extract_common_task_details(data)
        return Job(
            id=uuid4(),
            name=job_metadata.get("name", "k8s-job"),
            status=TaskStatus.WAITING,
            **common_details,
        )

    def _parse_deployment_spec(self, data: dict[str, Any]) -> Deployment:
        dep_metadata = data.get("metadata", {})
        spec = data.get("spec", {}) or {}
        common_details = self._extract_common_task_details(data)
        return Deployment(
            id=uuid4(),
            name=dep_metadata.get("name", "k8s-deployment"),
            status=TaskStatus.WAITING,
            replicas=spec.get("replicas", 1),
            **common_details,
        )

    def _parse_generic_resource(self, data: dict[str, Any]) -> GenericK8sResource:
        metadata = data.get("metadata", {})
        kind = data.get("kind", "Unknown")
        name = metadata.get("name", f"k8s-{kind.lower()}-{uuid4()}")
        full_definition_json = json.dumps(data)

        return GenericK8sResource(
            id=uuid4(),
            name=name,
            status=TaskStatus.WAITING,
            command_str=full_definition_json,
            required_cpu=None,
            required_memory=None,
            required_gpu=None,
            image=None,
            annotations=metadata.get("annotations", {}),
            env=[],
            dependencies=[],
        )

    def parse(self, file_content_bytes: bytes, filename: str) -> Workflow:
        try:
            file_content = file_content_bytes.decode("utf-8")
            docs = list(yaml.safe_load_all(file_content))
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}") from e

        all_tasks = []
        workflow_name_candidate = None

        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue

            kind = doc.get("kind")
            name = doc.get("metadata", {}).get("name")
            if not kind:
                continue

            if kind in self.IGNORED_TYPES:
                logger.info(f"Skipping admin-managed resource: {kind} '{name}'")
                continue

            try:
                # Check for Manual Node Placement (Bypass Scheduler)
                if self._has_node_selector(doc):
                    logger.info(
                        f"Resource {kind}/{name} has nodeSelector. Treating as User-Managed (Generic)."
                    )
                    task = self._parse_generic_resource(doc)
                    all_tasks.append(task)

                elif kind == "Job":
                    task = self._parse_job_spec(doc)
                    all_tasks.append(task)
                    if not workflow_name_candidate:
                        workflow_name_candidate = name

                elif kind == "Deployment":
                    task = self._parse_deployment_spec(doc)
                    all_tasks.append(task)
                    if not workflow_name_candidate:
                        workflow_name_candidate = name

                else:
                    logger.info(f"Parsing application glue resource: {kind}/{name}")
                    task = self._parse_generic_resource(doc)
                    all_tasks.append(task)

            except Exception as e:
                logger.warning(
                    f"Failed to parse resource {kind}/{name}: {e}. Skipping."
                )
                continue

        if not all_tasks:
            raise ValueError("No valid resources found in the provided YAML.")

        workflow_name = workflow_name_candidate or f"k8s-workflow-{uuid4()}"

        workflow = Workflow(
            id=uuid4(),
            name=workflow_name,
            tasks=all_tasks,
            status=WorkflowStatus.PENDING_DATA,
        )

        return workflow


# INFO: potential future implementations of allowed or forbidden api groups for parsing
# ALLOWED_API_GROUPS = {
#     # Core v1
#     "Pod": {"v1"},
#     "Service": {"v1"},
#     "Namespace": {"v1"},
#     "ConfigMap": {"v1"},
#     "Secret": {"v1"},
#     "PersistentVolume": {"v1"},
#     "PersistentVolumeClaim": {"v1"},
#     "Node": {"v1"},
#     "Event": {"v1"},
#     "Endpoints": {"v1"},
#     "ReplicationController": {"v1"},
#     "ServiceAccount": {"v1"},

#     # Apps/v1
#     "Deployment": {"apps/v1"},
#     "StatefulSet": {"apps/v1"},
#     "DaemonSet": {"apps/v1"},
#     "ReplicaSet": {"apps/v1"},

#     # Batch/v1
#     "Job": {"batch/v1"},
#     "CronJob": {"batch/v1"},

#     # Autoscaling/v2
#     "HorizontalPodAutoscaler": {"autoscaling/v2"},

#     # Networking/v1
#     "Ingress": {"networking.k8s.io/v1"},
#     "IngressClass": {"networking.k8s.io/v1"},
#     "NetworkPolicy": {"networking.k8s.io/v1"},

#     # Policy/v1
#     "PodDisruptionBudget": {"policy/v1"},

#     # RBAC
#     "Role": {"rbac.authorization.k8s.io/v1"},
#     "ClusterRole": {"rbac.authorization.k8s.io/v1"},
#     "RoleBinding": {"rbac.authorization.k8s.io/v1"},
#     "ClusterRoleBinding": {"rbac.authorization.k8s.io/v1"},

#     # Storage
#     "StorageClass": {"storage.k8s.io/v1"},
#     "CSIDriver": {"storage.k8s.io/v1"},
#     "CSINode": {"storage.k8s.io/v1"},
#     "CSIStorageCapacity": {"storage.k8s.io/v1"},
#     "VolumeAttachment": {"storage.k8s.io/v1"},

#     # Authentication
#     "TokenRequest": {"authentication.k8s.io/v1"},
#     "TokenReview": {"authentication.k8s.io/v1"},

#     # Authorization
#     "SubjectAccessReview": {"authorization.k8s.io/v1"},
#     "SelfSubjectAccessReview": {"authorization.k8s.io/v1"},
#     "SelfSubjectRulesReview": {"authorization.k8s.io/v1"},
#     "LocalSubjectAccessReview": {"authorization.k8s.io/v1"},
# }
