import json
import logging
from uuid import UUID

import redis.asyncio as redis
from fastapi import Depends

from core.dependencies import get_redis_client
from io_models import TaskStatus, WorkflowPSGCRequest

from .abstract_repository import AbstractWorkflowStateRepository

logger = logging.getLogger(__name__)


class RedisWorkflowRepository(AbstractWorkflowStateRepository):
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client
        self.workflow_key_prefix = "psgc:workflow"
        self.active_workflows_key = "psgc:active_workflows"
        self.task_lookup_prefix = "psgc:task_lookup"
        logger.info("RedisWorkflowRepository initialized.")

    def _get_key(self, workflow_id: UUID, *suffixes: str) -> str:
        return f"{self.workflow_key_prefix}:{workflow_id}:{':'.join(suffixes)}"

    async def save_workflow_state(
        self, workflow_request: WorkflowPSGCRequest, initial_workflow_status: str
    ):
        """Saves the initial workflow state in a single atomic transaction."""
        workflow_id = workflow_request.id
        workflow_id_str = str(workflow_id)
        definition_key = self._get_key(workflow_id, "definition")
        statuses_key = self._get_key(workflow_id, "statuses")
        overall_status_key = self._get_key(workflow_id, "overall_status")

        workflow_json = workflow_request.model_dump_json()

        async with self.client.pipeline(transaction=True) as pipe:
            pipe.set(definition_key, workflow_json)

            initial_task_statuses = {}
            # Iterate over 'tasks'
            for task in workflow_request.tasks:
                pipe.set(f"{self.task_lookup_prefix}:{task.id}", workflow_id_str)
                # If the workflow is starting as PROGRESSING and this task has no dependencies, it's READY.
                if not task.dependencies and initial_workflow_status == "PROGRESSING":
                    initial_task_statuses[str(task.id)] = TaskStatus.READY.value
                else:
                    # Otherwise, all tasks must start as WAITING.
                    initial_task_statuses[str(task.id)] = TaskStatus.WAITING.value

            if initial_task_statuses:
                pipe.hset(statuses_key, mapping=initial_task_statuses)

            pipe.set(overall_status_key, initial_workflow_status)
            pipe.sadd(self.active_workflows_key, workflow_id_str)

            await pipe.execute()
        logger.info(
            f"Saved initial state for workflow {workflow_id} with status {initial_workflow_status}"
        )

    async def get_workflow_definition(self, workflow_id: UUID) -> dict | None:
        key = self._get_key(workflow_id, "definition")
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def get_task_statuses(self, workflow_id: UUID) -> dict[str, str]:
        """Renamed from get_job_statuses"""
        key = self._get_key(workflow_id, "statuses")
        return await self.client.hgetall(key)

    async def get_task_status(self, workflow_id: UUID, task_id: UUID) -> str | None:
        """Renamed from get_job_status"""
        key = self._get_key(workflow_id, "statuses")
        return await self.client.hget(key, str(task_id))

    async def update_task_status(self, workflow_id: UUID, task_id: UUID, status: str):
        """Renamed from update_job_status"""
        key = self._get_key(workflow_id, "statuses")
        await self.client.hset(key, str(task_id), status)
        logger.debug(f"Updated status for task {task_id} to {status}")

    async def get_workflow_status(self, workflow_id: UUID) -> str | None:
        key = self._get_key(workflow_id, "overall_status")
        return await self.client.get(key)

    async def update_workflow_status(self, workflow_id: UUID, status: str):
        key = self._get_key(workflow_id, "overall_status")
        await self.client.set(key, status)

    async def get_active_workflow_ids(self) -> list[UUID]:
        members = await self.client.smembers(self.active_workflows_key)
        return [UUID(member) for member in members]

    async def delete_workflow_state(self, workflow_id: UUID):
        keys_to_delete = [
            self._get_key(workflow_id, "definition"),
            self._get_key(workflow_id, "statuses"),
            self._get_key(workflow_id, "overall_status"),
        ]

        # Cleanup external ID mappings
        # We need to know the task IDs to delete their external mapping keys
        statuses_key = self._get_key(workflow_id, "statuses")
        task_ids = await self.client.hkeys(statuses_key)
        for task_id in task_ids:
            keys_to_delete.append(f"{statuses_key}:{task_id}:external_id")

        async with self.client.pipeline(transaction=True) as pipe:
            pipe.delete(*keys_to_delete)
            pipe.srem(self.active_workflows_key, str(workflow_id))
            await pipe.execute()

    async def get_workflow_ids_by_status(self, status: str) -> list[UUID]:
        active_ids = await self.get_active_workflow_ids()
        if not active_ids:
            return []
        pipe = self.client.pipeline()
        for wf_id in active_ids:
            pipe.get(self._get_key(wf_id, "overall_status"))
        statuses = await pipe.execute()
        return [active_ids[i] for i, s in enumerate(statuses) if s == status]

    async def activate_initial_tasks(self, workflow_id: UUID) -> int:
        """Renamed from activate_initial_jobs"""
        definition = await self.get_workflow_definition(workflow_id)
        if not definition:
            return 0
        statuses_key = self._get_key(workflow_id, "statuses")

        # Use 'tasks' from the stored definition JSON
        tasks_to_activate = {
            task["id"]: TaskStatus.READY.value
            for task in definition.get("tasks", [])
            if not task.get("dependencies")
        }

        if tasks_to_activate:
            await self.client.hset(statuses_key, mapping=tasks_to_activate)
            logger.info(
                f"Activated {len(tasks_to_activate)} initial tasks for workflow {workflow_id}."
            )
            return len(tasks_to_activate)
        return 0

    async def set_task_statuses(
        self, workflow_id: UUID, mapping: dict[str, str]
    ) -> int:
        """Set multiple task statuses at once."""
        statuses_key = self._get_key(workflow_id, "statuses")
        if not mapping:
            return 0
        await self.client.hset(statuses_key, mapping=mapping)
        logger.info(f"Set {len(mapping)} task statuses for workflow {workflow_id}.")
        return len(mapping)

    async def set_task_external_id(
        self, workflow_id: UUID, task_id: UUID, external_id: str
    ):
        """Stores a mapping from our internal Task UUID to an external ID."""
        key = f"{self._get_key(workflow_id, 'statuses')}:{task_id}:external_id"
        await self.client.set(key, external_id)

    async def get_task_external_id(
        self, workflow_id: UUID, task_id: UUID
    ) -> str | None:
        """Retrieves the external ID for a given internal Task UUID."""
        key = f"{self._get_key(workflow_id, 'statuses')}:{task_id}:external_id"
        return await self.client.get(key)

    async def get_workflow_id_by_task_id(self, task_id: UUID) -> UUID | None:
        """Retrieves the workflow ID for a given task ID."""
        val = await self.client.get(f"{self.task_lookup_prefix}:{task_id}")
        return UUID(val) if val else None


# Dependency Injection Provider
def get_redis_workflow_repository(
    client: redis.Redis = Depends(get_redis_client),
) -> RedisWorkflowRepository:
    return RedisWorkflowRepository(redis_client=client)
