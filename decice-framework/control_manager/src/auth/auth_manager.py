import logging

from fastapi import HTTPException, status
from fastapi.params import Depends

from auth.security import AuthService, get_auth_service
from domain.token_schemas import Token
from domain.user_schemas import User, UserCreate, UserResponse
from services.user_service import UserService, get_user_service
from session.session_management import UserSession, get_user_session

logger = logging.getLogger(__name__)


class AuthManager:
    def __init__(
        self,
        auth_service: AuthService,
        user_service: UserService,
        user_session: UserSession,
    ):
        self.auth_service = auth_service
        self.user_service = user_service
        self.user_session = user_session

    async def login_user(self, username: str, password: str) -> Token:
        """
        Authenticates a user, creates a session, and returns an access token.
        """
        try:
            user = await self.user_service.get_userdb_by_name(username)
        except ValueError:
            # User not found
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # If user was found, now verify the password
        if not self.auth_service.verify_password(password, user.hashed_password):
            # Incorrect password
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # If username found and password verified
        # Create session (using User schema representation)
        # Ensure User schema can be created from DBUser correctly
        try:
            user_schema = User.model_validate(user)
        except Exception as e:
            logger.error(
                f"Error converting DBUser to User schema for user {username}: {e}"
            )
            raise HTTPException(
                status_code=500, detail="Internal server error during login process."
            )

        session_id = await self.user_session.create_session(user_schema)

        # Generate access token
        access_token = self.auth_service.generate_access_token(
            username=username, session_id=session_id
        )
        return access_token

    async def register_user(self, user_create: UserCreate) -> UserResponse:
        """
        Registers a new user if username and email are available.
        """
        # Check if user or email already exists
        if await self.user_service.check_if_user_exists(user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered.",
            )
        if await self.user_service.check_if_email_exists(user_create.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered.",
            )

        # Hash the user's password and create the user
        hashed_password = self.auth_service.get_password_hash(user_create.password)
        created_user = await self.user_service.create_user(user_create, hashed_password)

        return UserResponse(**created_user.model_dump())


async def get_auth_manager(
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
    user_session: UserSession = Depends(get_user_session),
) -> AuthManager:
    return AuthManager(auth_service, user_service, user_session)
