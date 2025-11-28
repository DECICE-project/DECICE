import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.dependencies import get_db_session
from db.models import PlatformIdentity
from db.models import User as DBUser

logger = logging.getLogger(__name__)


class UserRepository:
    """Concrete repository for User data."""

    def __init__(self, session: AsyncSession):
        """Initializes the repository with an active database session."""
        self.session = session

    async def create(self, entity: DBUser) -> None:
        """Adds a new user entity to the database."""
        logger.debug(f"Creating user: {entity.username}")
        self.session.add(entity)
        try:
            await self.session.commit()
            await self.session.refresh(entity)
            logger.info(f"User created: {entity.username} (ID: {entity.id})")
        except Exception as e:
            logger.error(f"Error creating user {entity.username}: {e}")
            await self.session.rollback()
            raise

    async def get_by_id(self, user_id: UUID) -> Optional[DBUser]:
        """Retrieves a user entity by ID (str). Raises ValueError if not found."""
        logger.debug(f"Fetching user by ID (str): {user_id}")
        statement = (
            select(DBUser)
            .where(DBUser.id == user_id)
            .options(joinedload(DBUser.platform_identity))
        )
        result = await self.session.execute(statement)
        user = result.scalars().first()
        return user

    async def get_all(self) -> list[DBUser]:
        """Retrieves all user entities."""
        logger.debug("Fetching all users")
        statement = select(DBUser).options(joinedload(DBUser.platform_identity))

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update(self, entity: DBUser) -> None:
        """Updates an existing user entity in the database."""
        logger.debug(f"Updating user: {entity.username} (ID: {entity.id})")
        self.session.add(entity)
        try:
            await self.session.commit()
            await self.session.refresh(entity)
            logger.info(f"User updated: {entity.username} (ID: {entity.id})")
        except Exception as e:
            logger.error(f"Error updating user {entity.username}: {e}")
            await self.session.rollback()
            raise

    async def delete(self, user_id: UUID) -> None:
        """Deletes a user entity by its primary key (ID as string)."""
        logger.debug(f"Deleting user by ID (str): {user_id}")
        try:
            statement = select(DBUser).where(DBUser.id == user_id)
            user = (await self.session.execute(statement)).scalars().first()
            if user is None:
                logger.warning(f"User with ID {user_id} not found for deletion.")
                raise ValueError(f"User with ID {user_id} not found.")
            await self.session.delete(user)
            await self.session.commit()

        except ValueError:
            raise  # Re-raise the ValueError if user not found
        except Exception as e:
            logger.error(f"Error deleting user ID {user_id}: {e}")
            await self.session.rollback()
            raise

    async def get_by_name(self, username: str) -> Optional[DBUser]:
        """Retrieves a user entity by username."""
        logger.debug(f"Fetching user by username: {username}")
        statement = (
            select(DBUser)
            .where(DBUser.username == username)
            .options(joinedload(DBUser.platform_identity))
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[DBUser]:
        """Retrieves a user entity by email."""
        logger.debug(f"Fetching user by email: {email}")

        statement = (
            select(DBUser)
            .where(DBUser.email == email)
            .options(joinedload(DBUser.platform_identity))
        )

        result = await self.session.execute(statement)
        return result.scalars().first()

    async def create_platform_identity(
        self, identity: PlatformIdentity
    ) -> PlatformIdentity:
        """Adds a new PlatformIdentity to the session and commits."""
        logger.debug(
            f"Adding new platform identity for user {identity.user_id} on platform {identity.platform}"
        )
        self.session.add(identity)
        try:
            await self.session.commit()
            await self.session.refresh(identity)
            logger.info(
                f"Successfully created identity {identity.id} for user {identity.user_id}."
            )
            return identity
        except Exception as e:
            logger.error(f"Error creating platform identity: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_platform_identities_by_user(
        self, user_id: UUID
    ) -> list[PlatformIdentity]:
        """Retrieves all platform identities for a given user ID."""
        logger.debug(f"Fetching all platform identities for user_id: {user_id}")
        stmt = select(PlatformIdentity).where(PlatformIdentity.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_identity_by_details(
        self, user_id: UUID, platform: str, platform_username: str
    ) -> Optional[PlatformIdentity]:
        """
        Finds a platform identity by the unique combination of user, platform,
        and platform_username.
        """
        logger.debug(
            f"Checking for existing identity: user_id={user_id}, platform={platform}, username={platform_username}"
        )
        stmt = select(PlatformIdentity).where(
            and_(
                PlatformIdentity.user_id == user_id,
                PlatformIdentity.platform == platform,
                PlatformIdentity.platform_username == platform_username,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# Dependency Provider Function
def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """FastAPI dependency provider for UserRepository."""
    return UserRepository(session=session)
