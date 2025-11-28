import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from auth.auth_manager import AuthManager
from auth.security import AuthService
from db.models import PlatformIdentity
from db.models import User as DBUser
from domain.token_schemas import Token
from domain.user_schemas import User, UserCreate, UserResponse, UserRole
from services.user_service import UserService
from session.session_management import UserSession


@pytest.fixture
def mock_user_db() -> DBUser:
    """Provides a database User object linked to a real PlatformIdentity."""

    user_id = uuid.uuid4()

    identity = PlatformIdentity(
        id=uuid.uuid4(),
        user_id=user_id,
        platform="slurm",
        platform_username="testuser_slurm",
        default_working_dir="/home/testuser",
    )

    user = DBUser(
        id=user_id,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="a_very_hashed_password",
        active=True,
        project="test-project",
        role=UserRole.USER,
        platform_identity=identity,
    )

    identity.user = user
    return user


@pytest.fixture
def user_create_data() -> UserCreate:
    """Provides a Pydantic model for creating a new user."""
    return UserCreate(
        username="newuser",
        email="new@example.com",
        full_name="New User",
        password="a_plain_password",
        project="new-project",
        platform_username="newuser_slurm",
        default_working_dir="/home/newuser",
    )


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Provides a mock of AuthService."""
    service = MagicMock(spec=AuthService)
    service.verify_password = MagicMock(return_value=True)
    service.get_password_hash = MagicMock(return_value="new_hashed_password")
    service.generate_access_token = MagicMock(
        return_value=Token(access_token="fake-access-token", token_type="bearer")
    )
    return service


@pytest.fixture
def mock_user_service() -> MagicMock:
    """Provides a mock of UserService."""
    service = MagicMock(spec=UserService)

    service.get_userdb_by_name = AsyncMock()
    service.check_if_user_exists = AsyncMock(return_value=False)
    service.check_if_email_exists = AsyncMock(return_value=False)
    service.create_user = AsyncMock()
    return service


@pytest.fixture
def mock_user_session() -> MagicMock:
    """Provides a mock of UserSession."""
    session = MagicMock(spec=UserSession)
    session.create_session = AsyncMock(return_value="new-session-id-123")
    return session


@pytest.mark.asyncio
class TestAuthManager:
    """Test suite for the AuthManager class."""

    async def test_login_user_success(
        self, mock_auth_service, mock_user_service, mock_user_session, mock_user_db
    ):
        """
        GIVEN correct username and password
        WHEN login_user is called
        THEN it should return a valid Token.
        """
        mock_pydantic_user = MagicMock(spec=User)
        mock_pydantic_user.username = mock_user_db.username

        mock_user_service.get_userdb_by_name.return_value = mock_user_db
        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )

        token = await auth_manager.login_user("testuser", "correct_password")

        mock_user_service.get_userdb_by_name.assert_awaited_once_with("testuser")
        mock_auth_service.verify_password.assert_called_once_with(
            "correct_password", mock_user_db.hashed_password
        )

        mock_user_session.create_session.assert_awaited_once()
        user_arg = mock_user_session.create_session.call_args[0][0]
        assert isinstance(user_arg, User)
        assert user_arg.username == mock_user_db.username

        mock_auth_service.generate_access_token.assert_called_once_with(
            username="testuser", session_id="new-session-id-123"
        )
        assert token.access_token == "fake-access-token"

    async def test_login_user_not_found(
        self, mock_auth_service, mock_user_service, mock_user_session
    ):
        """
        GIVEN a username that does not exist
        WHEN login_user is called
        THEN it must raise a 401 HTTPException.
        """
        mock_user_service.get_userdb_by_name.side_effect = ValueError("User not found")
        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.login_user("unknown_user", "any_password")

        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in exc_info.value.detail
        mock_auth_service.verify_password.assert_not_called()

    async def test_login_user_incorrect_password(
        self, mock_auth_service, mock_user_service, mock_user_session, mock_user_db
    ):
        """
        GIVEN a correct username but an incorrect password
        WHEN login_user is called
        THEN it must raise a 401 HTTPException.
        """
        mock_user_service.get_userdb_by_name.return_value = mock_user_db
        mock_auth_service.verify_password.return_value = False
        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.login_user("testuser", "wrong_password")

        assert exc_info.value.status_code == 401
        mock_user_session.create_session.assert_not_awaited()

    async def test_register_user_success(
        self, mock_auth_service, mock_user_service, mock_user_session, user_create_data
    ):
        mock_created_user = MagicMock(spec=User)
        mock_identity_dict = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "platform": "slurm",
            "platform_username": "newuser",
            "default_working_dir": "/home/newuser",
        }
        mock_created_user.model_dump.return_value = {
            "id": uuid.uuid4(),
            "username": user_create_data.username,
            "email": user_create_data.email,
            "full_name": user_create_data.full_name,
            "active": True,
            "role": "user",
            "project": user_create_data.project,
            "platform_identity": mock_identity_dict,  # 👈 ADD THIS
        }
        mock_user_service.create_user.return_value = mock_created_user

        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )
        response = await auth_manager.register_user(user_create_data)

        mock_user_service.create_user.assert_awaited_once()
        assert isinstance(response, UserResponse)
        assert response.username == user_create_data.username

    async def test_register_user_username_exists(
        self, mock_auth_service, mock_user_service, mock_user_session, user_create_data
    ):
        """
        GIVEN user data with an already registered username
        WHEN register_user is called
        THEN it must raise a 400 HTTPException.
        """
        mock_user_service.check_if_user_exists.return_value = True
        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.register_user(user_create_data)

        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail
        mock_user_service.create_user.assert_not_awaited()

    async def test_register_user_email_exists(
        self, mock_auth_service, mock_user_service, mock_user_session, user_create_data
    ):
        """
        GGIVEN user data with an already registered email
        WHEN register_user is called
        THEN it must raise a 400 HTTPException.
        """
        mock_user_service.check_if_email_exists.return_value = True
        auth_manager = AuthManager(
            mock_auth_service, mock_user_service, mock_user_session
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.register_user(user_create_data)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail
        mock_user_service.create_user.assert_not_awaited()
