import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends

from db.models import SchedulingDecision
from domain.schemas import (PaginatedSchedulingDecisionsResponse,
                            SchedulingDecisionResponse)
from repositories.scheduling_repository import (SchedulingRepository,
                                                get_scheduling_repository)

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    Service layer for handling and persisting scheduling data.
    """

    def __init__(self, repository: SchedulingRepository):
        self.repository = repository
        logger.info("SchedulingService initialized.")

    async def record_scheduling_results(self, response_data: dict[str, Any]) -> None:
        """
        Parses the scheduler's response and creates historical
        SchedulingDecision records for each placement.
        """
        try:
            placements = response_data.get("placements", [])
            duration_ms = response_data.get("scheduling_duration_ms", 0)

            if not placements:
                logger.warning("Received scheduling response with no placements.")
                return

            new_decisions: list[SchedulingDecision] = []
            for placement in placements:
                task_id_str = placement.get("task_id")
                if not task_id_str:
                    logger.error(f"Skipping placement with no task_id: {placement}")
                    continue

                decision = SchedulingDecision(
                    task_id=UUID(task_id_str),
                    target_nodes=placement.get("target_node_ids", []),
                    strategy_used=placement.get("strategy_used", "unknown"),
                    duration_ms=duration_ms,
                )
                new_decisions.append(decision)

            if new_decisions:
                await self.repository.create_decisions(new_decisions)

        except Exception as e:
            logger.exception(
                f"Failed to record scheduling decisions: {e}", exc_info=True
            )

    async def get_scheduling_history(
        self,
        *,
        target_node: Optional[str] = None,
        strategy: Optional[str] = None,
        task_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> PaginatedSchedulingDecisionsResponse:
        """
        Retrieves the filterable, paginated history of scheduling decisions.
        """

        results, total = await self.repository.list_decisions_by_criteria(
            target_node=target_node,
            strategy=strategy,
            task_id=task_id,
            workflow_id=workflow_id,
            offset=offset,
            limit=limit,
        )

        items = [
            SchedulingDecisionResponse(
                task_id=task.id,
                task_name=task.name,
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                target_nodes=decision.target_nodes,
                strategy_used=decision.strategy_used,
                duration_ms=decision.duration_ms,
                created_at=decision.created_at,
            )
            for (decision, task, workflow) in results
        ]

        return PaginatedSchedulingDecisionsResponse(total=total, items=items)


def get_scheduling_service(
    repository: SchedulingRepository = Depends(get_scheduling_repository),
) -> SchedulingService:
    """FastAPI dependency provider for SchedulingService."""
    return SchedulingService(repository=repository)
