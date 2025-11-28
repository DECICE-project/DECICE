from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.auth_manager import AuthManager, get_auth_manager
from domain.token_schemas import Token
from domain.user_schemas import UserCreate, UserResponse

auth_router = APIRouter()


@auth_router.post(
    "/token",
    response_model=Token,
    description="Get access token",
    summary="Get access token",
    status_code=status.HTTP_200_OK,
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> Token:
    """
    Obtain access token upon login.
    """
    return await auth_manager.login_user(form_data.username, form_data.password)


@auth_router.post(
    "/register",
    response_model=UserResponse,
    description="Register a new user",
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_create: UserCreate, auth_manager: AuthManager = Depends(get_auth_manager)
) -> UserResponse:
    """
    Register a new user.
    """
    return await auth_manager.register_user(user_create)
