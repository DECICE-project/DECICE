import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from auth.dependencies import get_current_active_user
from auth.security import AuthService
from domain.token_schemas import TokenData
from domain.user_schemas import PlatformIdentityResponse, User, UserRole
from session.session_management import UserSession

DUMMY_TOKEN = "this.is.a.dummy.token"


@pytest.fixture
def mock_platform_identity() -> PlatformIdentityResponse:
    """Provides a mock Pydantic PlatformIdentityResponse schema."""
    return PlatformIdentityResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        platform="slurm",
        platform_username="testuser",
        default_working_dir="/home/testuser",
    )


@pytest.fixture
def active_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    """Provides a valid, active User model instance."""
    user_id = uuid.uuid4()
    mock_platform_identity.user_id = user_id

    return User(
        id=user_id,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        active=True,
        role=UserRole.USER,
        project="test-project",
        platform_identity=mock_platform_identity,
    )


@pytest.fixture
def inactive_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    """Provides a valid, but inactive, User model instance."""

    user_id = uuid.uuid4()
    identity_copy = mock_platform_identity.model_copy(
        update={"user_id": user_id, "platform_username": "inactiveuser"}
    )

    return User(
        id=user_id,
        username="inactiveuser",
        email="inactive@example.com",
        full_name="Inactive User",
        active=False,
        role=UserRole.USER,
        project="test-project",
        platform_identity=identity_copy,
    )


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Provides a mock AuthService with an async 'decode_token' method."""
    service = MagicMock(spec=AuthService)
    service.decode_token = AsyncMock()
    service.decode_token = MagicMock()
    return service


@pytest.fixture
def mock_user_session() -> MagicMock:
    """Provides a mock UserSession with an async 'get_user' method."""
    session = MagicMock(spec=UserSession)
    session.get_user = AsyncMock()
    return session


@pytest.fixture
def valid_token_data(active_user: User) -> TokenData:
    """Provides a valid TokenData object linked to the active_user fixture."""
    return TokenData(
        sub=active_user.username,
        id=str(uuid.uuid4()),
        exp=int(time.time() + 3600),
    )


@pytest.mark.asyncio
class TestGetCurrentActiveUser:
    """A test suite for the get_current_active_user dependency."""

    async def test_success_path(
        self,
        mock_auth_service: MagicMock,
        mock_user_session: MagicMock,
        active_user: User,
        valid_token_data: TokenData,
    ):
        """
        GIVEN a valid token, a valid session, and an active user
        WHEN get_current_active_user is called
        THEN it should return the correct User object.
        """

        mock_auth_service.decode_token.return_value = valid_token_data
        mock_user_session.get_user.return_value = active_user

        result_user = await get_current_active_user(
            token=DUMMY_TOKEN,
            auth_service=mock_auth_service,
            user_session=mock_user_session,
        )

        mock_auth_service.decode_token.assert_called_once_with(DUMMY_TOKEN)
        mock_user_session.get_user.assert_awaited_once_with(valid_token_data.id)
        assert result_user == active_user

    async def test_inactive_user_raises_forbidden(
        self,
        mock_auth_service: MagicMock,
        mock_user_session: MagicMock,
        inactive_user: User,
        valid_token_data: TokenData,
    ):
        """
        GIVEN a valid token and session
        WHEN the user retrieved from the session is inactive
        THEN a 403 Forbidden HTTPException must be raised.
        """

        valid_token_data.sub = inactive_user.username
        mock_auth_service.decode_token.return_value = valid_token_data
        mock_user_session.get_user.return_value = inactive_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(
                token=DUMMY_TOKEN,
                auth_service=mock_auth_service,
                user_session=mock_user_session,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Inactive user"
        mock_user_session.get_user.assert_awaited_once_with(valid_token_data.id)

    async def test_session_not_found_raises_unauthorized(
        self,
        mock_auth_service: MagicMock,
        mock_user_session: MagicMock,
        valid_token_data: TokenData,
    ):
        """
        GIVEN a valid token
        WHEN the session ID from the token does not exist in the session store (raises ValueError)
        THEN a 401 Unauthorized HTTPException must be raised.
        """
        mock_auth_service.decode_token.return_value = valid_token_data
        mock_user_session.get_user.side_effect = ValueError("Session not found")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(
                token=DUMMY_TOKEN,
                auth_service=mock_auth_service,
                user_session=mock_user_session,
            )

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    async def test_invalid_token_raises_unauthorized(
        self, mock_auth_service: MagicMock, mock_user_session: MagicMock
    ):
        """
        GIVEN an invalid token that causes auth_service to raise an exception
        WHEN get_current_active_user is called
        THEN it should propagate the 401 Unauthorized HTTPException.
        """
        credentials_exception = HTTPException(status_code=401, detail="Invalid token")
        mock_auth_service.decode_token.side_effect = credentials_exception

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(
                token=DUMMY_TOKEN,
                auth_service=mock_auth_service,
                user_session=mock_user_session,
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"
        mock_user_session.get_user.assert_not_awaited()

    async def test_token_missing_session_id_claim(
        self,
        mock_auth_service: MagicMock,
        mock_user_session: MagicMock,
        valid_token_data: TokenData,
    ):
        """
        GIVEN a token that decodes successfully but is missing the 'id' claim
        WHEN get_current_active_user is called
        THEN a 401 Unauthorized HTTPException must be raised.
        """
        valid_token_data.id = None
        mock_auth_service.decode_token.return_value = valid_token_data

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(
                token=DUMMY_TOKEN,
                auth_service=mock_auth_service,
                user_session=mock_user_session,
            )

        assert exc_info.value.status_code == 401
        mock_user_session.get_user.assert_not_awaited()
