import logging
from typing import AsyncGenerator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a SQLAlchemy AsyncSession from the factory
    stored in app.state.
    """
    session_factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "db_session_factory", None
    )

    if session_factory is None:
        logger.error(
            "Database session factory 'db_session_factory' not found in application state! "
            "Check lifespan function."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service is not available.",
        )

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            logger.exception("Exception in request, rolling back DB session.")
            await session.rollback()
            raise
        finally:
            logger.debug("Closing DB session.")
