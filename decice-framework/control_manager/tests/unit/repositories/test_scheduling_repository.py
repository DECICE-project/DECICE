import logging
from typing import Optional, Sequence
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db_session
from db.models import SchedulingDecision, Workflow, WorkflowTask

logger = logging.getLogger(__name__)


class SchedulingRepository:
    """Repository for all SchedulingDecision related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_decisions(self, decisions: Sequence[SchedulingDecision]) -> bool:
        """
        Atomically creates one or more SchedulingDecision records.
        """
        logger.debug(
            f"Adding {len(decisions)} new scheduling decisions to the session."
        )
        try:
            self.session.add_all(decisions)
            await self.session.commit()
            logger.info(
                f"Successfully committed {len(decisions)} scheduling decisions."
            )
            return True
        except SQLAlchemyError as e:
            logger.error(
                f"Database error while creating scheduling decisions: {e}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def list_decisions_by_criteria(
        self,
        *,
        target_node: Optional[str] = None,
        strategy: Optional[str] = None,
        task_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[tuple[SchedulingDecision, WorkflowTask, Workflow]], int]:
        """
        Retrieves a paginated list of scheduling decisions, joined with
        their corresponding WorkflowTask and Workflow, based on filter criteria.
        """
        logger.debug(
            f"Querying scheduling decisions with filters: node={target_node}, "
            f"strategy={strategy}, task_id={task_id}, workflow_id={workflow_id}"
        )

        query = (
            select(SchedulingDecision, WorkflowTask, Workflow)
            .join(WorkflowTask, SchedulingDecision.task_id == WorkflowTask.id)
            .join(Workflow, WorkflowTask.workflow_id == Workflow.id)
        )

        count_query = (
            select(func.count())
            .select_from(SchedulingDecision)
            .join(WorkflowTask, SchedulingDecision.task_id == WorkflowTask.id)
            .join(Workflow, WorkflowTask.workflow_id == Workflow.id)
        )

        if target_node:
            query = query.where(SchedulingDecision.target_nodes.contains(target_node))
            count_query = count_query.where(
                SchedulingDecision.target_nodes.contains(target_node)
            )

        if strategy:
            query = query.where(SchedulingDecision.strategy_used == strategy)
            count_query = count_query.where(
                SchedulingDecision.strategy_used == strategy
            )

        if task_id:
            query = query.where(WorkflowTask.id == task_id)
            count_query = count_query.where(WorkflowTask.id == task_id)

        if workflow_id:
            query = query.where(Workflow.id == workflow_id)
            count_query = count_query.where(Workflow.id == workflow_id)

        query = (
            query.order_by(SchedulingDecision.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        try:
            items_result = await self.session.execute(query)
            total_result = await self.session.execute(count_query)

            items = items_result.all()
            total = total_result.scalar_one()

            return items, total

        except SQLAlchemyError as e:
            logger.error(f"Database error while querying decisions: {e}", exc_info=True)
            raise


def get_scheduling_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SchedulingRepository:
    return SchedulingRepository(session=session)
