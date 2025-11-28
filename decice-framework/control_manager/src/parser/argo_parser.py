import json
import logging
from collections import defaultdict
from typing import Any
from uuid import UUID, uuid4

import yaml

from db.models import Job, TaskStatus, Workflow

from .base import AbstractWorkflowParser
from .registry import ParserRegistry

logger = logging.getLogger(__name__)


@ParserRegistry.register
class ArgoYAMLParser(AbstractWorkflowParser):

    @classmethod
    def can_parse(cls, filename: str, file_content: bytes) -> bool:
        if not filename.lower().endswith((".yaml", ".yml")):
            return False
        try:
            data = yaml.safe_load(file_content)
            return (
                isinstance(data, dict)
                and data.get("apiVersion") == "argoproj.io/v1alpha1"
                and data.get("kind") == "Workflow"
            )
        except (yaml.YAMLError, UnicodeDecodeError):
            return False

    def parse(self, file_content_bytes: bytes, filename: str) -> Workflow:
        """
        Parses an Argo Workflow YAML to build the dependency graph for the jobs.

        This parser performs two critical functions:
        1. Validates the presence of a 'dev.decice.com/storage-request' annotation
           at the top level of the workflow.
        2. Extracts job-specific details, including hardware requirements and annotations,
           from each container template.
        """
        try:
            file_content = file_content_bytes.decode("utf-8")
            argo_dict = yaml.safe_load(file_content)
            if not isinstance(argo_dict, dict) or argo_dict.get("kind") != "Workflow":
                raise ValueError("YAML file is not a valid Argo Workflow.")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}") from e

        workflow_metadata = argo_dict.get("metadata", {})
        workflow_annotations = workflow_metadata.get("annotations", {})
        storage_request = workflow_annotations.get("dev.decice.com/storage-request")

        if not storage_request:
            raise ValueError(
                "A 'dev.decice.com/storage-request' annotation is required "
                "in the top-level metadata section of the Argo Workflow."
            )

        spec = argo_dict.get("spec", {})
        entrypoint_name = spec.get("entrypoint")
        if not entrypoint_name:
            raise ValueError("Argo Workflow must have an 'entrypoint'.")

        templates_by_name = {t["name"]: t for t in spec.get("templates", [])}
        dag_template = templates_by_name.get(entrypoint_name)
        if not dag_template or "dag" not in dag_template:
            raise ValueError(f"Entrypoint '{entrypoint_name}' is not a DAG template.")

        dag_tasks = dag_template.get("dag", {}).get("tasks", [])
        if not dag_tasks:
            raise ValueError("Entrypoint DAG has no tasks defined.")

        task_name_to_jobs_map = defaultdict(list)
        all_jobs = []
        workflow_id = uuid4()

        for task in dag_tasks:
            task_name = task.get("name")
            template_name = task.get("template")
            if not task_name or not template_name:
                continue

            container_template = templates_by_name.get(template_name)
            if not container_template or "container" not in container_template:
                logger.warning(
                    f"Task '{task_name}' references non-container template '{template_name}'. Skipping."
                )
                continue

            items_to_loop = task.get("withItems")
            if items_to_loop:
                for i, item in enumerate(items_to_loop):
                    new_job = self._create_job_from_template(
                        f"{task_name}-{i}",
                        container_template,
                        workflow_id,
                    )
                    task_name_to_jobs_map[task_name].append(new_job)
                    all_jobs.append(new_job)
            else:
                new_job = self._create_job_from_template(
                    task_name,
                    container_template,
                    workflow_id,
                )
                task_name_to_jobs_map[task_name].append(new_job)
                all_jobs.append(new_job)

        for task in dag_tasks:
            task_name = task.get("name")
            jobs_for_current_task = task_name_to_jobs_map.get(task_name, [])
            dependency_job_objects = []
            for dependency_name in task.get("dependencies", []):
                dependency_jobs = task_name_to_jobs_map.get(dependency_name, [])
                dependency_job_objects.extend(dependency_jobs)

            if dependency_job_objects:
                for current_job in jobs_for_current_task:
                    current_job.dependencies.extend(dependency_job_objects)

        workflow = Workflow(
            id=workflow_id,
            name=workflow_metadata.get("generateName", "argo-workflow-"),
            tasks=all_jobs,
            status=TaskStatus.WAITING,
        )

        return workflow

    def _create_job_from_template(
        self,
        name: str,
        template: dict[str, Any],
        workflow_id: UUID,
    ) -> Job:
        """Helper function to create a single Job object from an Argo template."""
        container_spec = template.get("container", {})

        resources = container_spec.get("resources", {}).get("requests", {})
        template_metadata = template.get("metadata", {})
        annotations = template_metadata.get("annotations", {})
        env_list = container_spec.get("env", [])

        gpu_count = None
        try:
            gpu_value = resources.get("nvidia.com/gpu")
            if gpu_value is not None:
                gpu_count = int(gpu_value)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not parse GPU resource value '{gpu_value}' as an integer for job '{name}'. Ignoring."
            )

        command_list = container_spec.get("command", []) + container_spec.get(
            "args", []
        )

        return Job(
            id=uuid4(),
            name=name,
            status=TaskStatus.WAITING,
            image=container_spec.get("image"),
            command_str=json.dumps(command_list),
            workflow_id=workflow_id,
            required_cpu=resources.get("cpu"),
            required_memory=resources.get("memory"),
            required_gpu=gpu_count,
            annotations=annotations,
            dependencies=[],
            env=env_list,
        )
