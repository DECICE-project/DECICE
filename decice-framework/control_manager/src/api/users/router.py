import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auth.auth import get_token
from auth.dependencies import get_current_active_user
from auth.role_manager import RoleManager
from auth.security import AuthService, get_auth_service
from domain.token_schemas import Token
from domain.user_schemas import (
    PlatformIdentityCreate,
    PlatformIdentityResponse,
    User,
    UserResponse,
    UserResponseAndToken,
    UserRole,
    UserUpdate,
)
from services.user_service import UserService, get_user_service
from session.session_management import UserSession, get_user_session

logger = logging.getLogger(__name__)

user_router = APIRouter(prefix="/user")


@user_router.get(
    "/me/",
    description="Get current user",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user(user: Annotated[User, Depends(get_current_active_user)]):
    """API Endpoint to retrieve the current authenticated user's profile."""

    logger.info(
        f"Request received for /users/me/ endpoint by user '{user.username}' (ID: {user.id})."
    )
    return UserResponse(**user.model_dump())


@user_router.patch(
    "/me/",
    response_model=UserResponseAndToken,
    summary="Update Current User",
    description="Updates the profile data for the currently authenticated user. "
    "This operation invalidates the user's current session and issues a "
    "new access token linked to a new session with the updated data.",
)
async def update_current_user(
    user_update_payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    user_session: UserSession = Depends(get_user_session),
    auth_service: AuthService = Depends(get_auth_service),
    token: str = Depends(get_token),
):
    """Updates the current user's profile, invalidates old session, issues new token."""
    logger.info(
        f"User '{current_user.username}' (ID: {current_user.id}) attempting profile update."
    )

    # Update User Data
    try:
        # Call the service to update user data in the database.
        # Pass current username to ensure user updates their own record.
        updated_user: User = await user_service.update_user(
            username=current_user.username, user_update=user_update_payload
        )
        logger.info(
            f"User profile data updated successfully for '{current_user.username}' in service layer."
        )
    except ValueError as e:
        logger.warning(f"Update failed for user '{current_user.username}': {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception(
            f"Unexpected error during user update for '{current_user.username}'"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile.",
        )

    # Invalidate Old Session
    old_session_id: Optional[str] = None
    try:
        # Decode the original token again *only* to get the associated session ID
        decoded_token_payload = auth_service.decode_token(token)
        old_session_id = decoded_token_payload.id
        if old_session_id:
            logger.debug(
                f"Invalidating old session '{old_session_id}' for user '{current_user.username}'."
            )
            # Delete the old session from storage
            await user_session.delete_session(old_session_id)
        else:
            logger.warning(
                f"Could not find session ID in token claim for user '{current_user.username}' during update; old session not invalidated."
            )
    except HTTPException as e:
        logger.warning(
            f"Error decoding token during session invalidation for user '{current_user.username}': {e.detail}. Old session may persist."
        )
    except Exception as e:
        logger.error(
            f"Error deleting old session '{old_session_id}' for user '{current_user.username}': {e}",
            exc_info=True,
        )

    # Create New Session & Token
    try:
        # Create a new session using the updated user data
        new_session_id = await user_session.create_session(updated_user)
        logger.debug(
            f"Created new session '{new_session_id}' for user '{updated_user.username}'."
        )

        # Generate a new JWT linked to the new session ID
        new_token: Token = auth_service.generate_access_token(
            username=updated_user.username, session_id=new_session_id
        )
        logger.info(
            f"Generated new access token for user '{updated_user.username}' after profile update."
        )

    except Exception:
        logger.exception(
            f"FATAL: Failed to create new session or token for user '{updated_user.username}' after update."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User profile updated, but failed to finalize the new session. Please log in again.",
        )

    # Prepare and Return Response
    updated_user_response = UserResponse(**updated_user.model_dump())

    return UserResponseAndToken(
        user=updated_user_response,
        token=new_token,
    )


@user_router.post(
    "/me/identities",
    summary="Create a Platform Identity",
    description="Create a new platform identity (e.g., HPC account) for the current user.",
    response_model=PlatformIdentityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_platform_identity(
    identity_create: PlatformIdentityCreate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Creates a new PlatformIdentity record and associates it with the
    currently authenticated user.
    """
    logger.info(
        f"User '{current_user.username}' creating new platform identity for platform '{identity_create.platform}'."
    )
    try:
        new_identity = await user_service.create_platform_identity_for_user(
            identity_create=identity_create, user_id=current_user.id
        )
        return new_identity
    except ValueError as e:
        logger.warning(
            f"Failed to create platform identity for user '{current_user.username}': {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception(
            f"Unexpected error creating platform identity for user '{current_user.username}'"
        )
        raise HTTPException(
            status_code=500, detail="Internal error creating platform identity."
        )


@user_router.get(
    "/me/identities",
    summary="Get My Platform Identities",
    description="Retrieves all platform identities associated with the current user.",
    response_model=list[PlatformIdentityResponse],
)
async def get_my_platform_identities(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Retrieves all PlatformIdentity records for the currently authenticated user.
    """
    logger.info(f"User '{current_user.username}' retrieving their platform identities.")
    identities = await user_service.get_platform_identities_for_user(
        user_id=current_user.id
    )
    return identities


# Admin Routes for Managing Users
@user_router.get(
    "/",
    summary="Get All Users (Admin)",
    description="Retrieves a list of all registered users. Requires ADMIN privileges.",
    response_model=list[UserResponse],
    dependencies=[Depends(RoleManager([UserRole.ADMIN]))],
)
async def get_all_users(service: UserService = Depends(get_user_service)):
    """Admin endpoint to retrieve all users."""
    logger.info("Admin request received for get_all_users.")
    users = await service.get_all_users()

    return [UserResponse(**user.model_dump()) for user in users]


@user_router.patch(
    "/{user_id}",
    summary="Update User by ID (Admin)",
    description="Updates specific fields for a user identified by their ID. Requires ADMIN privileges.",
    response_model=UserResponse,
    dependencies=[Depends(RoleManager([UserRole.ADMIN]))],
)
async def update_user_by_id(
    user_id: UUID,
    update_payload: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    """Admin endpoint to update user details by ID."""
    logger.info(f"Admin request received to update user ID: {user_id}")
    try:
        user_to_update = await service.get_user_by_id(user_id)
        updated_user = await service.update_user(
            username=user_to_update.username, user_update=update_payload
        )
        return UserResponse(**updated_user.model_dump())
    except ValueError as e:
        logger.warning(f"Update failed, user ID {user_id} not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.exception(f"Unexpected error updating user ID {user_id}")
        raise HTTPException(status_code=500, detail="Internal error updating user.")


@user_router.delete(
    "/{user_id}",
    summary="Delete User by ID (Admin)",
    description="Deletes a user identified by their ID. Requires ADMIN privileges.",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleManager([UserRole.ADMIN]))],
)
async def delete_user_by_id(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    """Admin endpoint to delete a user by ID."""
    logger.info(f"Admin request received to delete user ID: {user_id}")
    try:
        await service.delete_user(user_id=user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        logger.warning(f"Delete failed, user ID {user_id} not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.exception(f"Unexpected error deleting user ID {user_id}")
        raise HTTPException(status_code=500, detail="Internal error deleting user.")
