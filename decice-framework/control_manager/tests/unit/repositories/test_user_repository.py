import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.models import User as DBUser
from repositories.user_repository import UserRepository, get_user_repository


@pytest.fixture
def mock_session() -> MagicMock:
    """Provides a fully configured mock for SQLAlchemy's AsyncSession."""
    session = MagicMock()
    session.commit = AsyncMock(name="commit")
    session.refresh = AsyncMock(name="refresh")
    session.execute = AsyncMock(name="execute")
    session.rollback = AsyncMock(name="rollback")
    session.delete = AsyncMock(name="delete")
    session.add = MagicMock(name="add")

    mock_execute_result = MagicMock()
    mock_scalars_result = MagicMock()
    session.execute.return_value = mock_execute_result
    mock_execute_result.scalars.return_value = mock_scalars_result

    return session


class TestUserRepository:
    """Test suite for the UserRepository."""

    @pytest.mark.asyncio
    async def test_create_success(self, mock_session: MagicMock):
        """Tests the successful creation of a user."""
        mock_user = MagicMock(spec=DBUser)
        repo = UserRepository(session=mock_session)

        await repo.create(mock_user)

        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_create_raises_exception(self, mock_session: MagicMock):
        """Tests that an exception during commit triggers a rollback."""
        mock_user = MagicMock(spec=DBUser)
        mock_session.commit.side_effect = Exception("Database connection failed")
        repo = UserRepository(session=mock_session)

        with pytest.raises(Exception):
            await repo.create(mock_user)

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session: MagicMock):
        """Tests fetching a user by ID when the user is found."""
        user_id = uuid.uuid4()
        expected_user = MagicMock(spec=DBUser)
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            expected_user
        )
        repo = UserRepository(session=mock_session)

        result = await repo.get_by_id(str(user_id))

        mock_session.execute.assert_awaited_once()
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session: MagicMock):
        """Tests fetching a user by ID when the user is not found."""
        user_id = uuid.uuid4()
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        repo = UserRepository(session=mock_session)

        result = await repo.get_by_id(str(user_id))

        mock_session.execute.assert_awaited_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, mock_session: MagicMock):
        """Tests fetching all users."""
        expected_users = [MagicMock(spec=DBUser), MagicMock(spec=DBUser)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            expected_users
        )
        repo = UserRepository(session=mock_session)

        result = await repo.get_all()

        mock_session.execute.assert_awaited_once()
        assert result == expected_users

    @pytest.mark.asyncio
    async def test_update_success(self, mock_session: MagicMock):
        """Tests the successful update of a user."""
        mock_user = MagicMock(spec=DBUser)
        repo = UserRepository(session=mock_session)

        await repo.update(mock_user)

        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_update_raises_exception(self, mock_session: MagicMock):
        """Tests that an exception during update triggers a rollback."""
        mock_user = MagicMock(spec=DBUser)
        mock_session.commit.side_effect = Exception("Update failed")
        repo = UserRepository(session=mock_session)

        with pytest.raises(Exception):
            await repo.update(mock_user)

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session: MagicMock):
        """Tests the successful deletion of a user."""
        user_id = uuid.uuid4()
        mock_user_to_delete = MagicMock(spec=DBUser)
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_user_to_delete
        )
        repo = UserRepository(session=mock_session)

        await repo.delete(str(user_id))

        mock_session.execute.assert_awaited_once()
        mock_session.delete.assert_awaited_once_with(mock_user_to_delete)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_raises_exception(self, mock_session: MagicMock):
        """Tests that an exception during delete triggers a rollback."""
        user_id = uuid.uuid4()
        mock_session.delete.side_effect = Exception("Deletion failed")
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            MagicMock(spec=DBUser)
        )
        repo = UserRepository(session=mock_session)

        with pytest.raises(Exception):
            await repo.delete(str(user_id))

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session: MagicMock):
        """Tests that deleting a non-existent user raises a ValueError."""
        user_id = uuid.uuid4()
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        repo = UserRepository(session=mock_session)

        with pytest.raises(ValueError, match=f"User with ID {user_id} not found."):
            await repo.delete(str(user_id))

        mock_session.execute.assert_awaited_once()
        mock_session.delete.assert_not_awaited()
        mock_session.commit.assert_not_awaited()
        mock_session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_by_name(self, mock_session: MagicMock):
        """Tests fetching a user by username."""
        username = "testuser"
        expected_user = MagicMock(spec=DBUser)
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            expected_user
        )
        repo = UserRepository(session=mock_session)

        result = await repo.get_by_name(username)

        mock_session.execute.assert_awaited_once()
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_get_by_email(self, mock_session: MagicMock):
        """Tests fetching a user by email."""
        email = "test@example.com"
        expected_user = MagicMock(spec=DBUser)
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            expected_user
        )
        repo = UserRepository(session=mock_session)

        result = await repo.get_by_email(email)

        mock_session.execute.assert_awaited_once()
        assert result == expected_user


def test_get_user_repository():
    """Tests the dependency provider function for UserRepository."""
    mock_session_instance = MagicMock()

    repo_instance = get_user_repository(session=mock_session_instance)

    assert isinstance(repo_instance, UserRepository)
    assert repo_instance.session == mock_session_instance
