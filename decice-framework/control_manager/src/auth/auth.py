import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt

from config.config import get_settings
from services.user_service import UserService, get_user_service
from session.session_management import UserSession, get_user_session

from .security import AuthService, get_auth_service

API_KEY_HEADER_NAME = "X-Internal-Api-Key"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/token/")
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def get_token(token: Annotated[str, Depends(oauth2_scheme)]):
    return token


async def verify_internal_traffic(
    api_key_header: str = Security(api_key_header),
):
    """
    Verifies that the request comes from a trusted internal service
    by checking the shared secret.
    """
    settings = get_settings()

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing internal authentication credentials",
        )

    # secrets.compare_digest prevents timing attacks
    if not secrets.compare_digest(api_key_header, settings.INTERNAL_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal authentication credentials",
        )

    return True


async def auth_required(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_session: Annotated[UserSession, Depends(get_user_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """
    Middleware function for authentication enforcement.

    This function is a middleware used to enforce authentication on routes that require it.
    It checks the provided JWT token and verifies its validity, ensuring the user is authenticated.
    If the token is valid, it extracts the username from the token's payload.
    If the token has expired, it invalidates the user's session and raises a 401 Unauthorized error.
    If the token is invalid for any other reason, it raises a 401 Unauthorized error.
    If the user does not exist, it raises a 401 Unauthorized error.

    Parameters:
    - token (str): JWT token obtained from the request header.
    - request (Request): The FastAPI request object.

    Returns:
    - None: This function does not return any value. It raises exceptions if authentication fails.

    Raises:
    - HTTPException: If authentication fails for any reason, raises HTTP 401 Unauthorized error.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: dict = jwt.decode(
            token, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

    except ExpiredSignatureError:
        # if token has expired, invalidate the user's session
        payload = jwt.get_unverified_claims(token)
        session_id = payload.get("id")
        user_session.delete_session(session_id)

        raise credentials_exception

    except JWTError:
        # if token is invalid for any other reason, raise an exception
        raise credentials_exception

    if not await user_service.check_if_user_exists(username):
        raise credentials_exception
