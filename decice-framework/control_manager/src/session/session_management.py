import logging
import secrets

import redis.asyncio as redis
from fastapi import Depends
from pydantic import ValidationError

from config.config import get_settings
from core.dependencies import get_redis_client
from domain.user_schemas import User

logger = logging.getLogger(__name__)


class UserSession:
    """Manages user sessions using Redis as the backend."""

    def __init__(self, redis_client: redis.Redis = Depends(get_redis_client)):
        """Initializes UserSession with an injected Redis client instance."""
        settings = get_settings()
        self.redis: redis.Redis = redis_client
        # Get session expiry from settings
        self.expire_seconds: int = settings.SESSION_EXPIRE_SECONDS
        if self.expire_seconds <= 0:
            # Default to 30 mins if config is invalid
            logger.warning(
                f"Invalid SESSION_EXPIRE_SECONDS ({self.expire_seconds}), defaulting to 1800."
            )
            self.expire_seconds = 1800
        logger.info(
            f"UserSession initialized with Redis. Session Expiry: {self.expire_seconds}s"
        )

    def _generate_session_id(self) -> str:
        """Generates a secure random session ID string."""
        return secrets.token_urlsafe(32)

    async def create_session(self, user: User) -> str:
        """
        Creates a new session ID, stores serialized user data in Redis with expiry.

        Args:
            user: The User object (Pydantic model) to store.

        Returns:
            The generated session ID string.
        """
        session_id = self._generate_session_id()
        logger.debug(
            f"Creating session for user '{user.username}' with session ID: {session_id}"
        )
        try:
            user_json = user.model_dump_json()

            # Store in Redis using session_id as key, user_json as value, with expiration
            # 'ex' sets the expiry time in seconds
            await self.redis.set(
                name=session_id, value=user_json, ex=self.expire_seconds
            )
            logger.info(
                f"Session created successfully in Redis for user '{user.username}' (ID: {session_id})"
            )
            return session_id
        except Exception as e:
            logger.exception(
                f"Failed to create session in Redis for user {user.username}: {e}"
            )
            raise RuntimeError(
                "Failed to create user session due to storage error."
            ) from e

    async def get_user(self, session_id: str) -> User:
        """
        Retrieves user data from Redis using session ID and deserializes it.

        Args:
            session_id: The session ID to look up.

        Returns:
            The deserialized User object.

        Raises:
            ValueError: If the session ID is not found, expired, or data is invalid/corrupt.
        """
        if not session_id:
            raise ValueError("Session ID cannot be empty.")
        logger.debug(f"Attempting to retrieve session data for ID: {session_id}")
        try:
            # Get the JSON string value from Redis associated with the session_id key
            user_json = await self.redis.get(
                session_id
            )  # Returns string due to decode_responses=True

            if user_json is None:
                # Key doesn't exist or has expired
                logger.warning(
                    f"Session ID not found in Redis (likely expired or invalid): {session_id}"
                )
                raise ValueError("Session not found or expired.")

            # Deserialize JSON string back into a User Pydantic model
            user = User.model_validate_json(user_json)
            logger.debug(
                f"Successfully retrieved and deserialized user '{user.username}' from session {session_id}"
            )
            # Optional: Extend session expiry on access? (Touch operation)
            # await self.redis.expire(session_id, self.expire_seconds)
            return user

        except ValidationError:
            logger.warning(
                f"Invalid or corrupt session data for session ID {session_id}."
            )
            raise ValueError("Invalid or corrupt session data.")
        except ValueError:
            # Catch "Session not found" error and re-raise it as intended.
            raise
        except Exception as e:
            # Catch all other exceptions
            logger.exception(
                f"Failed to get or parse session data from Redis for session ID {session_id}: {e}"
            )
            raise ValueError("Invalid or corrupt session data.")

    async def delete_session(self, session_id: str) -> None:
        """Deletes a session from Redis."""
        if not session_id:
            logger.warning("Attempted to delete session with empty ID.")
            return  # Or raise error? Silently ignore is okay here maybe.
        logger.info(f"Deleting session ID from Redis: {session_id}")
        try:
            # Delete the key from Redis. Returns num keys deleted (0 or 1).
            await self.redis.delete(session_id)
            logger.debug(f"Session delete command executed for ID: {session_id}")
        except Exception as e:
            logger.exception(f"Failed to delete session {session_id} from Redis: {e}")
            raise RuntimeError("Failed to delete session.") from e


# Dependency Provider Function
def get_user_session(
    session_manager: UserSession = Depends(UserSession),
) -> UserSession:
    """FastAPI dependency provider for UserSession."""
    return session_manager
