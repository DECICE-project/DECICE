import logging
from uuid import UUID

from fastapi import Depends

from db.models import PlatformIdentity
from db.models import User as DBUser
from domain.user_schemas import (PlatformIdentityCreate,
                                 PlatformIdentityResponse, User, UserCreate,
                                 UserRole, UserUpdate)
from repositories.user_repository import UserRepository, get_user_repository

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user-related operations, using the adjusted repository."""

    def __init__(
        self, repository: UserRepository = Depends(get_user_repository)
    ) -> None:
        self.user_repository = repository
        logger.info("UserService initialized.")

    async def create_user(self, user_create: UserCreate, hashed_password: str) -> User:
        """Creates a user, persists, and returns the corresponding User schema."""
        logger.info(f"Attempting to create user: {user_create.username}")

        # Check if username or email already exists
        if await self.user_repository.get_by_name(user_create.username):
            logger.warning(
                f"User with username '{user_create.username}' already exists."
            )
            raise ValueError("User with this username already exists.")
        if await self.user_repository.get_by_email(user_create.email):
            logger.warning(f"User with email '{user_create.email}' already exists.")
            raise ValueError("User with this email already exists.")

        db_identity = PlatformIdentity(
            platform=user_create.platform,
            platform_username=user_create.platform_username,
            default_working_dir=user_create.default_working_dir,
        )

        db_user = DBUser(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            role=UserRole.USER,
            project=user_create.project,
            hashed_password=hashed_password,
            # TODO: change in future implementation, user needs to activate account
            active=True,
            platform_identity=db_identity,
        )
        try:
            await self.user_repository.create(db_user)
            # we need to fetch the created user to get its ID and return the full User schema
            # assume username is unique and sufficient for immediate fetch
            created_db_user = await self.user_repository.get_by_name(db_user.username)
            if created_db_user is None:
                # This would be unexpected if create didn't raise an error
                logger.error(
                    f"Failed to fetch user '{db_user.username}' immediately after creation."
                )
                raise ValueError("Failed to verify user creation.")
            logger.info(
                f"User '{created_db_user.username}' created successfully (ID: {created_db_user.id})"
            )
            return User.model_validate(created_db_user, from_attributes=True)
        except ValueError:  # Re-raise ValueErrors from existence checks
            raise
        except Exception as e:
            logger.error(f"Failed to create user {user_create.username}: {e}")
            raise ValueError("Could not create user.") from e

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Gets a user by ID (str) and returns User schema. Raises ValueError if not found."""
        logger.debug(f"Getting user by ID (str): {user_id}")
        db_user = await self.user_repository.get_by_id(user_id)

        if db_user is None:
            logger.warning(f"User ID '{user_id}' not found in repository.")
            raise ValueError("User not found.")

        return User.model_validate(db_user, from_attributes=True)

    async def get_user_by_name(self, username: str) -> User:
        """Gets a user by username and returns User schema. Raises ValueError if not found."""
        logger.debug(f"Getting user by username: {username}")
        db_user = await self.user_repository.get_by_name(username)
        if db_user is None:
            logger.warning(f"Username '{username}' not found.")
            raise ValueError("User not found.")
        return User.model_validate(db_user, from_attributes=True)

    async def get_userdb_by_name(self, username: str) -> DBUser:
        """Gets a user by username and returns the raw DBUser model. Raises ValueError if not found."""
        logger.debug(f"Getting DBUser by username: {username}")
        db_user = await self.user_repository.get_by_name(username)
        if db_user is None:
            logger.warning(f"Username '{username}' not found (DBUser).")
            raise ValueError("User not found.")
        return db_user

    async def get_all_users(self) -> list[User]:
        """Gets all users and returns list of User schemas."""
        logger.debug("Getting all users.")
        db_users = await self.user_repository.get_all()
        return [User.model_validate(user, from_attributes=True) for user in db_users]

    async def update_user(self, username: str, user_update: UserUpdate) -> User:
        """Updates a user identified by username using UserUpdate data."""
        logger.info(f"Attempting to update user: {username}")
        db_user = await self.get_userdb_by_name(username)

        update_data = user_update.model_dump(exclude_unset=True)
        updated = False
        for key, value in update_data.items():
            if hasattr(db_user, key):
                if key in ["id", "username"]:
                    continue  # Prevent updating immutable fields
                if getattr(db_user, key) != value:
                    setattr(db_user, key, value)
                    updated = True
                    logger.debug(f"Updating user {username}: Set {key} to {value}")
            else:
                logger.warning(
                    f"Invalid field '{key}' ignored during user update for {username}."
                )

        if updated:
            # TODO: Update 'updated_at' timestamp if needed
            try:
                await self.user_repository.update(db_user)
                # Fetch the updated user again to return the latest state
                updated_db_user = await self.user_repository.get_by_name(username)
                if updated_db_user is None:  # Should not happen if update succeeded
                    raise ValueError("Failed to retrieve user after update.")
                logger.info(f"Successfully updated user: {username}")
                return User.model_validate(updated_db_user, from_attributes=True)

            except Exception as e:
                logger.error(f"Failed to update user {username} in DB: {e}")
                raise ValueError("Failed to save user updates.") from e
        else:
            logger.info(f"No changes applied for user: {username}")
            return User.model_validate(db_user, from_attributes=True)

    async def delete_user(self, user_id: UUID) -> None:
        """Deletes a user by ID (str). Raises ValueError if user not found."""
        logger.info(f"Attempting to delete user ID (str): {user_id}")

        # explicitly check if user exists first
        await self.get_user_by_id(user_id)

        try:
            await self.user_repository.delete(user_id)
            logger.info(f"Delete operation completed for user ID (str): {user_id}")
        except Exception as e:
            logger.error(f"Error during deletion for user ID {user_id}: {e}")
            raise ValueError("Failed to delete user.") from e

    async def check_if_user_exists(self, username: str) -> bool:
        """Checks if a user exists by username."""
        logger.debug(f"Checking existence for username: {username}")
        db_user = await self.user_repository.get_by_name(username)
        return db_user is not None

    async def check_if_email_exists(self, email: str) -> bool:
        """Checks if a user exists by email."""
        logger.debug(f"Checking existence for email: {email}")
        db_user = await self.user_repository.get_by_email(email)
        return db_user is not None

    async def create_platform_identity_for_user(
        self, identity_create: PlatformIdentityCreate, user_id: UUID
    ) -> PlatformIdentityResponse:
        """Creates a new platform identity and links it to the user."""
        logger.info(
            f"Creating platform identity for user {user_id} on platform {identity_create.platform}"
        )

        # Check if identity already exists
        existing_identity = await self.user_repository.get_identity_by_details(
            user_id=user_id,
            platform=identity_create.platform,
            platform_username=identity_create.platform_username,
        )
        if existing_identity:
            logger.warning(
                f"User {user_id} already has an identity for platform {identity_create.platform} "
                f"with username {identity_create.platform_username}."
            )
            raise ValueError(
                "This combination of user, platform, and username already exists."
            )

        db_identity = PlatformIdentity(**identity_create.model_dump(), user_id=user_id)

        try:
            created_identity = await self.user_repository.create_platform_identity(
                db_identity
            )
            return PlatformIdentityResponse.model_validate(created_identity)
        except Exception as e:
            logger.error(
                f"Service: Failed to create platform identity for user {user_id}: {e}",
                exc_info=True,
            )
            if "uq_user_platform_username" in str(e):
                raise ValueError(
                    "This combination of user, platform, and username already exists."
                )
            raise ValueError(f"Could not create platform identity: {e}")

    async def get_platform_identities_for_user(
        self, user_id: UUID
    ) -> list[PlatformIdentityResponse]:
        """Retrieves all platform identities for a specific user."""
        logger.debug(f"Getting platform identities for user {user_id}")
        db_identities = await self.user_repository.get_platform_identities_by_user(
            user_id
        )
        return [
            PlatformIdentityResponse.model_validate(identity)
            for identity in db_identities
        ]


# Dependency Provider Function
def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """FastAPI dependency provider for UserService."""
    return UserService(repository=repository)
