import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status

from auth.auth import get_token
from auth.security import AuthService, get_auth_service
from domain.user_schemas import User
from session.session_management import UserSession, get_user_session

logger = logging.getLogger(__name__)


async def get_current_active_user(
    token: Annotated[str, Depends(get_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_session: Annotated[UserSession, Depends(get_user_session)],
) -> User:
    """
    FastAPI dependency: Decodes JWT, retrieves user from session, checks activity.

    Raises HTTPException(401) if token invalid/expired or session not found.
    Raises HTTPException(403) if user is inactive.

    Returns:
        The active User object associated with the valid session.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    inactive_user_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Inactive user",
    )

    try:
        # Decode Token (AuthService handles JWTError, ExpiredSignatureError -> HTTPException)
        logger.debug("Decoding authentication token.")
        decoded_token = auth_service.decode_token(token)

        # Extract Session ID (assuming 'id' claim holds the session identifier)
        session_id = decoded_token.id
        if not session_id:
            logger.warning("Token valid but missing 'id' (session ID) claim.")
            raise credentials_exception

        # Retrieve User from Session Cache
        logger.debug(f"Retrieving user for session ID: {session_id}")
        try:
            user = await user_session.get_user(session_id)
        except ValueError:
            # Session ID not found in cache
            logger.warning(f"Session ID '{session_id}' not found in session cache.")
            raise credentials_exception

        # Check if User is Active
        if not getattr(user, "active", False):  # Safely check for 'active' attribute
            logger.warning(
                f"User '{user.username}' (Session: {session_id}) attempted access but is inactive."
            )
            raise inactive_user_exception

        logger.debug(f"Authenticated active user: {user.username}")

        # Return validated, active user
        return user

    except HTTPException as e:
        # Re-raise specific HTTPExceptions from decode_token or checks above
        raise e
    except Exception as e:
        # Catch-all for unexpected errors during the process
        logger.exception(f"Unexpected error during user authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during authentication.",
        ) from e
