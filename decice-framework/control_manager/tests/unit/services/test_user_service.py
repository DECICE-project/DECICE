import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from db.models import PlatformIdentity
from db.models import User as DBUser
from domain.user_schemas import User, UserCreate, UserRole, UserUpdate
from repositories.user_repository import UserRepository
from services.user_service import UserService


@pytest.fixture
def mock_db_user() -> DBUser:
    """Provides a consistent, mock SQLAlchemy User model instance."""

    user_id = uuid.uuid4()

    identity = PlatformIdentity(
        id=uuid.uuid4(),
        platform="slurm",
        platform_username="testuser_slurm",
        default_working_dir="/home/testuser",
        user_id=user_id,
    )

    db_user = DBUser(
        id=user_id,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_abc",
        active=True,
        project="decice",
        role=UserRole.USER,
        platform_identity=identity,
    )

    identity.user = db_user
    return db_user


@pytest.fixture
def user_create_data() -> UserCreate:
    """Provides a consistent Pydantic UserCreate model instance."""
    return UserCreate(
        username="newuser",
        email="new@example.com",
        full_name="New User",
        password="plain_password",
        project="decice",
        platform_username="newuser_slurm",
        default_working_dir="/home/newuser",
    )


@pytest.fixture
def user_update_data() -> UserUpdate:
    """Provides a consistent Pydantic UserUpdate model instance."""
    return UserUpdate(email="updated@example.com", full_name="Updated Name")


@pytest.fixture
def mock_user_repository() -> MagicMock:
    """
    Provides a mock of the UserRepository with awaitable async methods.
    """
    repo = MagicMock(spec=UserRepository)
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_name = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.mark.asyncio
class TestUserService:
    """Test suite for the UserService."""

    async def test_create_user_success(
        self,
        mock_user_repository: MagicMock,
        mock_db_user: DBUser,
        user_create_data: UserCreate,
    ):
        mock_user_repository.get_by_name.side_effect = [None, mock_db_user]
        mock_user_repository.get_by_email.return_value = None
        user_service = UserService(repository=mock_user_repository)
        new_user = await user_service.create_user(user_create_data, "hashed_password")

        mock_user_repository.get_by_name.assert_any_call(user_create_data.username)
        mock_user_repository.get_by_email.assert_awaited_once_with(
            user_create_data.email
        )
        mock_user_repository.create.assert_awaited_once()
        assert isinstance(new_user, User)
        assert new_user.username == mock_db_user.username
        assert (
            new_user.platform_identity.platform_username
            == mock_db_user.platform_identity.platform_username
        )

        created_db_user_arg = mock_user_repository.create.call_args[0][0]
        assert isinstance(created_db_user_arg, DBUser)
        assert created_db_user_arg.platform_identity is not None
        assert (
            created_db_user_arg.platform_identity.platform_username
            == user_create_data.platform_username
        )

        assert isinstance(new_user, User)
        assert new_user.username == mock_db_user.username

    async def test_create_user_raises_error_if_username_exists(
        self,
        mock_user_repository: MagicMock,
        mock_db_user: DBUser,
        user_create_data: UserCreate,
    ):
        mock_user_repository.get_by_name.return_value = mock_db_user
        user_service = UserService(repository=mock_user_repository)
        with pytest.raises(ValueError, match="User with this username already exists"):
            await user_service.create_user(user_create_data, "hashed_password")
        mock_user_repository.create.assert_not_awaited()

    async def test_get_user_by_id_success(
        self, mock_user_repository: MagicMock, mock_db_user: DBUser
    ):
        mock_user_repository.get_by_id.return_value = mock_db_user
        user_service = UserService(repository=mock_user_repository)
        user = await user_service.get_user_by_id(str(mock_db_user.id))
        mock_user_repository.get_by_id.assert_awaited_once_with(str(mock_db_user.id))
        assert user.id == mock_db_user.id

    async def test_get_user_by_id_not_found(self, mock_user_repository: MagicMock):
        mock_user_repository.get_by_id.return_value = None
        user_service = UserService(repository=mock_user_repository)
        with pytest.raises(ValueError, match="User not found"):
            await user_service.get_user_by_id("non-existent-id")

    async def test_update_user_success(
        self,
        mock_user_repository: MagicMock,
        mock_db_user: DBUser,
        user_update_data: UserUpdate,
    ):
        """
        GIVEN valid update data for an existing user
        WHEN update_user is called
        THEN the repository's get_by_name is called twice and update is called once.
        """

        mock_user_repository.get_by_name.side_effect = [mock_db_user, mock_db_user]

        user_service = UserService(repository=mock_user_repository)

        updated_user = await user_service.update_user(
            mock_db_user.username, user_update_data
        )

        assert mock_user_repository.get_by_name.await_count == 2
        mock_user_repository.get_by_name.assert_has_awaits(
            [
                call(mock_db_user.username),
                call(mock_db_user.username),
            ]
        )

        mock_user_repository.update.assert_awaited_once_with(mock_db_user)

        assert updated_user.email == user_update_data.email
        assert updated_user.full_name == user_update_data.full_name

        assert (
            updated_user.platform_identity.platform_username
            == mock_db_user.platform_identity.platform_username
        )

    async def test_delete_user_success(
        self, mock_user_repository: MagicMock, mock_db_user: DBUser
    ):
        mock_user_repository.get_by_id.return_value = mock_db_user
        user_service = UserService(repository=mock_user_repository)
        await user_service.delete_user(mock_db_user.id)
        mock_user_repository.delete.assert_awaited_once_with(mock_db_user.id)

    async def test_delete_user_not_found_raises_error(
        self, mock_user_repository: MagicMock
    ):
        mock_user_repository.get_by_id.return_value = None
        user_service = UserService(repository=mock_user_repository)
        with pytest.raises(ValueError, match="User not found"):
            await user_service.delete_user("non-existent-id")
        mock_user_repository.delete.assert_not_awaited()
