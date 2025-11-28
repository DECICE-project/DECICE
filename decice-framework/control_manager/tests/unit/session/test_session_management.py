import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.user_schemas import PlatformIdentityResponse, User, UserRole
from session.session_management import UserSession


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Provides a mock Redis client with awaitable async methods."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def valid_user() -> User:
    """Provides a standard, valid User Pydantic model for tests."""

    user_id = uuid.uuid4()
    identity = PlatformIdentityResponse(
        id=uuid.uuid4(),
        user_id=user_id,
        platform="slurm",
        platform_username="sessionuser",
        default_working_dir="/home/sessionuser",
    )
    return User(
        id=user_id,
        username="sessionuser",
        email="session@example.com",
        full_name="Session User",
        active=True,
        role=UserRole.USER,
        project="decice",
        platform_identity=identity,
    )


@pytest.fixture(autouse=True)
def mock_settings_for_session(monkeypatch):
    """
    This is an auto-running fixture. For every test in this file, it will
    automatically mock the get_settings() function *specifically where it's
    used in the session.session_management module*.

    It returns a simple mock object with only the one attribute that the
    UserSession class actually needs, perfectly isolating the test.
    """
    mock_settings = MagicMock()
    mock_settings.SESSION_EXPIRE_SECONDS = 1800

    monkeypatch.setattr(
        "session.session_management.get_settings", lambda: mock_settings
    )

    yield mock_settings


class TestUserSession:
    """Test suite for the UserSession manager."""

    def test_init_with_valid_settings(
        self, mock_redis_client: MagicMock, mock_settings_for_session: MagicMock
    ):
        """
        Tests that UserSession correctly initializes with a valid expiration setting.
        """
        mock_settings_for_session.SESSION_EXPIRE_SECONDS = 3600

        session_manager = UserSession(redis_client=mock_redis_client)

        assert session_manager.expire_seconds == 3600

    def test_init_with_invalid_settings_defaults_correctly(
        self, mock_redis_client: MagicMock, mock_settings_for_session: MagicMock
    ):
        """
        Tests that UserSession falls back to a default expiration if the setting is invalid.
        """
        mock_settings_for_session.SESSION_EXPIRE_SECONDS = 0

        session_manager = UserSession(redis_client=mock_redis_client)

        assert session_manager.expire_seconds == 1800

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, mock_redis_client: MagicMock, valid_user: User
    ):
        """
        Tests that create_session correctly calls the redis client's 'set' method.
        """
        session_manager = UserSession(redis_client=mock_redis_client)
        session_id = await session_manager.create_session(valid_user)

        assert isinstance(session_id, str)
        mock_redis_client.set.assert_awaited_once()

        call_args, call_kwargs = mock_redis_client.set.call_args
        assert call_kwargs["name"] == session_id
        assert call_kwargs["value"] == valid_user.model_dump_json()
        assert call_kwargs["ex"] == 1800

    @pytest.mark.asyncio
    async def test_get_user_success(
        self, mock_redis_client: MagicMock, valid_user: User
    ):
        """
        Tests that get_user correctly deserializes a valid user from Redis.
        """
        session_id = "valid-session-id"
        user_json = valid_user.model_dump_json()
        mock_redis_client.get.return_value = user_json

        session_manager = UserSession(redis_client=mock_redis_client)
        retrieved_user = await session_manager.get_user(session_id)

        mock_redis_client.get.assert_awaited_once_with(session_id)
        assert retrieved_user == valid_user

    @pytest.mark.asyncio
    async def test_get_user_not_found_raises_error(self, mock_redis_client: MagicMock):
        """
        Tests that get_user raises a ValueError if the session ID is not in Redis.
        """
        mock_redis_client.get.return_value = None
        session_manager = UserSession(redis_client=mock_redis_client)

        with pytest.raises(ValueError, match="Session not found or expired"):
            await session_manager.get_user("non-existent-id")

    @pytest.mark.asyncio
    async def test_get_user_invalid_data_raises_error(
        self, mock_redis_client: MagicMock
    ):
        """
        Tests that get_user raises a ValueError if the data in Redis is corrupt/invalid JSON.
        """
        mock_redis_client.get.return_value = '{"id": "123", "username": "bad-data"'
        session_manager = UserSession(redis_client=mock_redis_client)

        with pytest.raises(ValueError, match="Invalid or corrupt session data"):
            await session_manager.get_user("corrupted-id")

    @pytest.mark.asyncio
    async def test_delete_session_success(self, mock_redis_client: MagicMock):
        """
        Tests that delete_session correctly calls the redis client's 'delete' method.
        """
        session_id = "session-to-delete"
        session_manager = UserSession(redis_client=mock_redis_client)

        await session_manager.delete_session(session_id)

        mock_redis_client.delete.assert_awaited_once_with(session_id)
