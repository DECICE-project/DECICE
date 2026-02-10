import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload, with_polymorphic

from core.dependencies import get_db_session
from db.models import (
    Deployment,
    HPCJob,
    Job,
    SchedulingDecision,
    TaskStatus,
    Workflow,
    WorkflowTask,
    WorkflowTaskDependency,
)
from domain.schemas import TaskStatus, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_full_workflow(self, db_workflow: Workflow) -> Workflow:
        """Atomically creates a new Workflow and all its associated WorkflowTask objects."""
        logger.debug(
            f"Attempting to create full workflow '{db_workflow.name}' in database."
        )
        try:
            self.session.add(db_workflow)
            await self.session.flush()
            workflow_id = db_workflow.id
            await self.session.commit()

            # Reload to get relationships populated
            stmt = (
                select(Workflow)
                .where(Workflow.id == workflow_id)
                .options(
                    selectinload(Workflow.tasks).selectinload(WorkflowTask.dependencies)
                )
            )
            result = await self.session.execute(stmt)
            created_workflow = result.unique().scalar_one()

            logger.info(
                f"Successfully created workflow {created_workflow.id} with {len(created_workflow.tasks)} tasks."
            )
            return created_workflow
        except SQLAlchemyError as e:
            logger.error(
                f"Database error while creating workflow '{db_workflow.name}': {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def update_workflow_status(self, workflow_id: UUID, status: str):
        try:
            stmt = (
                update(Workflow).where(Workflow.id == workflow_id).values(status=status)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Updated workflow {workflow_id} status to {status}")

            # Return the updated workflow object to satisfy the service layer if needed
            return await self.session.get(Workflow, workflow_id)
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error updating workflow status: {e}", exc_info=True)
            raise

    async def update_task_status(self, task_id: UUID, status: str):
        try:
            stmt = (
                update(WorkflowTask)
                .where(WorkflowTask.id == task_id)
                .values(status=status)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Updated task {task_id} status to {status}")
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error updating task status: {e}", exc_info=True)
            raise

    async def get_pending_downstream_tasks(
        self, completed_task_id: UUID
    ) -> tuple[list[WorkflowTask], UUID]:
        """
        Finds all tasks that depend on the completed_task_id and are currently WAITING.
        Returns the tasks and the workflow_id they belong to.
        """
        try:
            # Find the workflow_id first
            task_query = select(WorkflowTask).where(
                WorkflowTask.id == completed_task_id
            )
            task_result = await self.session.execute(task_query)
            completed_task = task_result.scalar_one_or_none()

            if not completed_task:
                return [], None

            workflow_id = completed_task.workflow_id

            # Find downstream tasks (children)
            # Join WorkflowTaskDependency where upstream_task_id == completed_task_id
            # Select the *downstream* task (child)
            query = (
                select(WorkflowTask)
                .join(
                    WorkflowTaskDependency,
                    WorkflowTaskDependency.downstream_task_id == WorkflowTask.id,
                )
                .where(WorkflowTaskDependency.upstream_task_id == completed_task_id)
                .where(WorkflowTask.status == TaskStatus.WAITING)
                .options(selectinload(WorkflowTask.dependencies))
            )
            result = await self.session.execute(query)
            tasks = result.scalars().all()

            return list(tasks), workflow_id

        except SQLAlchemyError as e:
            logger.error(
                f"Error finding downstream tasks for {completed_task_id}: {e}",
                exc_info=True,
            )
            raise

    async def check_task_dependencies_met(self, task: WorkflowTask) -> bool:
        """
        Checks if all dependencies for a specific task are SUCCEEDED.
        """
        try:
            if not task.dependencies:
                return True

            # Get the IDs of all upstream parents
            parent_ids = [dep.id for dep in task.dependencies]

            # Count how many of those parents are SUCCEEDED
            query = (
                select(func.count())
                .select_from(WorkflowTask)
                .where(WorkflowTask.id.in_(parent_ids))
                .where(WorkflowTask.status == TaskStatus.SUCCEEDED)
            )
            result = await self.session.execute(query)
            succeeded_count = result.scalar_one()

            return succeeded_count == len(parent_ids)

        except SQLAlchemyError as e:
            logger.error(
                f"Error checking dependencies for task {task.id}: {e}", exc_info=True
            )
            raise

    async def find_ready_downstream_tasks(
        self, completed_task_id: UUID
    ) -> tuple[list[WorkflowTask], UUID | None]:
        """
        Identifies which downstream tasks are now fully ready to run because
        all their dependencies (including the one that just finished) are met.
        """
        potential_tasks, workflow_id = await self.get_pending_downstream_tasks(
            completed_task_id
        )
        if not potential_tasks:
            return [], None

        logger.debug("Checking which downstream tasks are fully ready...")

        ready_tasks = []
        for task in potential_tasks:
            # Verify ALL dependencies for this candidate task are met,
            # not just the one that just finished.
            if await self.check_task_dependencies_met(task):
                ready_tasks.append(task)

        logger.info(
            f"Found {len(ready_tasks)} fully ready downstream tasks for {completed_task_id}."
        )
        return ready_tasks, workflow_id

    async def cancel_downstream_tasks(self, start_id: UUID):
        """
        Recursively cancels all tasks that depend on the given start_id.
        Used when a task fails to prevent dependent tasks from waiting forever.
        """
        logger.debug(f"Recursively cancelling downstream tasks for {start_id}")

        td = WorkflowTaskDependency.__table__

        # Recursive CTE to find all downstream descendants
        # Start with immediate children (where upstream == start_id)
        downstream = (
            select(td.c.downstream_task_id.label("id"))
            .where(td.c.upstream_task_id == start_id)
            .cte(name="downstream", recursive=True)
        )

        td_alias = aliased(td)
        downstream_alias = aliased(downstream)

        # Recursive step: find children of the children
        downstream = downstream.union_all(
            select(td_alias.c.downstream_task_id).join(
                downstream_alias,
                td_alias.c.upstream_task_id == downstream_alias.c.id,
            )
        )

        stmt = select(WorkflowTask).where(WorkflowTask.id.in_(select(downstream.c.id)))

        result = await self.session.scalars(stmt)
        tasks = result.all()

        if not tasks:
            logger.debug("No downstream tasks found.")
            return [], None

        workflow_id = None
        for task in tasks:
            workflow_id = task.workflow_id
            # Only cancel if not already finished
            if task.status not in [
                TaskStatus.SUCCEEDED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                task.status = TaskStatus.CANCELLED
                logger.info(f"Cancelled downstream task: {task.name} ({task.id})")

        await self.session.commit()
        return list(tasks), workflow_id

    async def cancel_all_non_finished_tasks(self, workflow_id: UUID):
        """Cancels all tasks in a workflow that are not yet finished."""
        logger.debug(f"Fetching all non-finished tasks for workflow {workflow_id}")

        try:
            stmt = select(WorkflowTask).where(
                WorkflowTask.workflow_id == workflow_id,
                WorkflowTask.status.notin_(
                    [
                        TaskStatus.SUCCEEDED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                    ]
                ),
            )
            result = await self.session.execute(stmt)
            tasks_canceled = result.scalars().all()

            return list(tasks_canceled)
        except SQLAlchemyError as e:
            logger.error(
                f"Database error while fetching non-finished tasks in workflow {workflow_id}: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def delete_workflow_by_id(self, workflow_id: UUID) -> bool:
        """
        Deletes a workflow by its ID. Returns True if deleted, False if not found.
        """
        logger.debug(f"Attempting to delete workflow {workflow_id}")

        try:
            stmt = select(Workflow).where(Workflow.id == workflow_id)
            result = await self.session.execute(stmt)
            workflow = result.scalar_one_or_none()

            if not workflow:
                logger.warning(f"Workflow {workflow_id} not found for deletion.")
                return False

            await self.session.delete(workflow)
            await self.session.commit()
            logger.info(f"Workflow {workflow_id} deleted successfully.")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting workflow {workflow_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_workflow_with_details_by_id(
        self, workflow_id: UUID
    ) -> Optional[Workflow]:
        """
        Retrieves a workflow by ID, eagerly loading tasks
        and only the UUIDs of their dependencies.
        """
        try:
            logger.debug(f"Fetching detailed workflow by ID: {workflow_id}")

            # use polymorphic type to also eagerly load type columns: for example deployment replicas
            task_poly = with_polymorphic(WorkflowTask, [Job, HPCJob, Deployment])

            stmt = (
                select(Workflow)
                .options(
                    selectinload(Workflow.tasks.of_type(task_poly)).selectinload(
                        task_poly.dependencies
                    )
                )
                .where(Workflow.id == workflow_id)
            )

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
            raise

    async def list_workflows(
        self, offset: int = 0, limit: int = 100
    ) -> tuple[list[Workflow], int]:
        """
        Retrieves a paginated list of workflows and the total count.
        """
        logger.debug(f"Fetching workflows with offset={offset}, limit={limit}")

        polymorphic_tasks = with_polymorphic(WorkflowTask, "*")

        base_query = select(Workflow).where(Workflow.status != WorkflowStatus.CANCELLED)

        items_stmt = (
            base_query.order_by(Workflow.id)
            .offset(offset)
            .limit(limit)
            .options(selectinload(Workflow.tasks.of_type(polymorphic_tasks)))
        )
        count_stmt = select(func.count()).select_from(base_query)

        items_result = await self.session.execute(items_stmt)
        count_result = await self.session.execute(count_stmt)

        workflows = items_result.scalars().all()
        total = count_result.scalar_one()

        return workflows, total

    async def delete_workflow_by_id(self, workflow_id: UUID) -> bool:
        """
        Deletes a workflow by its ID. Returns True if deleted, False if not found.
        """
        logger.debug(f"Attempting to delete workflow {workflow_id}")

        try:
            stmt = select(Workflow).where(Workflow.id == workflow_id)
            result = await self.session.execute(stmt)
            workflow = result.scalar_one_or_none()

            if not workflow:
                logger.warning(f"Workflow {workflow_id} not found for deletion.")
                return False

            await self.session.delete(workflow)
            await self.session.commit()
            logger.info(f"Workflow {workflow_id} deleted successfully.")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting workflow {workflow_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def list_tasks_with_scheduling(
        self,
        workflow_ids: Optional[list[UUID]] = None,
        statuses: Optional[list[TaskStatus]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[tuple[WorkflowTask, SchedulingDecision | None]], int]:
        """
        List tasks with optional workflow/status filters, including scheduling info.
        """
        task_poly = with_polymorphic(WorkflowTask, "*")

        query = (
            select(task_poly, SchedulingDecision)
            .join(Workflow, task_poly.workflow_id == Workflow.id)
            .outerjoin(SchedulingDecision, SchedulingDecision.task_id == task_poly.id)
            .options(selectinload(task_poly.dependencies))
        )

        if workflow_ids:
            query = query.where(task_poly.workflow_id.in_(workflow_ids))
        if statuses:
            query = query.where(task_poly.status.in_(statuses))

        query = (
            query.offset(offset).limit(limit).order_by(SchedulingDecision.created_at)
        )

        # total count query
        count_query = select(func.count()).select_from(task_poly)
        if workflow_ids:
            count_query = count_query.where(task_poly.workflow_id.in_(workflow_ids))
        if statuses:
            count_query = count_query.where(task_poly.status.in_(statuses))

        items_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)

        items = items_result.all()  # list of tuples (WorkflowTask, SchedulingDecision)
        total = count_result.scalar_one()

        return items, total


def get_workflow_repository(
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowRepository:
    return WorkflowRepository(session)
