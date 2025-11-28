import logging

from fastapi import Depends, HTTPException, status

from auth.dependencies import get_current_active_user
from domain.user_schemas import User, UserRole

logger = logging.getLogger(__name__)


class RoleManager:
    """
    FastAPI dependency class to verify if the current active user has one of the allowed roles.

    Usage:
        admin_only = RoleManager([UserRole.ADMIN])
        ...
        @router.get("/admin", dependencies=[Depends(admin_only)])
        async def admin_route(): ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        """
        Args:
            allowed_roles: A list of UserRole enum members that are permitted access.
        """
        if not allowed_roles:
            raise ValueError("allowed_roles cannot be empty")
        self.allowed_roles = allowed_roles
        # Store as a set for efficient 'in' check
        self._allowed_roles_set = set(allowed_roles)
        logger.debug(f"RoleManager initialized for roles: {self._allowed_roles_set}")

    async def __call__(
        self,
        # Step 1: Depend directly on the output of get_current_active_user
        current_user: User = Depends(get_current_active_user),
    ):
        """
        This method is called by FastAPI's dependency injection system.
        It checks if the injected current_user's role is in the allowed list.

        Raises:
            HTTPException(403): If the user's role is not permitted.
        """
        logger.debug(
            f"Checking role for user '{current_user.username}'. Required: {self._allowed_roles_set}, User has: {current_user.role}"
        )

        # Step 2: Perform the role check directly on the injected user object
        # Assumes 'current_user.role' holds the UserRole enum member
        if current_user.role not in self._allowed_roles_set:
            logger.warning(
                f"Role check FAILED for user '{current_user.username}'. "
                f"Required: {self._allowed_roles_set}, User has: {current_user.role}"
            )
            # Step 3: Raise 403 Forbidden if the role is not allowed
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        # If the role check passes, the dependency resolves successfully,
        # and request processing continues. No return value is needed.
        logger.debug(f"Role check PASSED for user '{current_user.username}'.")
