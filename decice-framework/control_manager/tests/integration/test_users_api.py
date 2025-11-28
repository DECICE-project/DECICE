import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.security import AuthService
from db.models import PlatformIdentity, User
from domain.user_schemas import User as UserSchema


@pytest.mark.asyncio
class TestUsersAPI:
    """
    Integration test suite for the /user API endpoints.
    This suite tests both standard user and admin-only functionality.
    """

    @pytest_asyncio.fixture(autouse=True)
    async def setup_users(self, test_db_session: AsyncSession):
        """
        Auto-running fixture that creates a baseline set of users
        in the database before each test function in this class.
        """
        temp_auth_service = AuthService(
            secret_key="dummy-key-for-hashing-should-have-at-least-64-chars",
            algorithm="HS256",
            expire_minutes=30,
        )

        id1 = PlatformIdentity(
            platform="slurm",
            platform_username="user1",
            default_working_dir="/home/user1",
        )
        user1 = User(
            username="user1",
            email="user1@example.com",
            full_name="User One",
            hashed_password=temp_auth_service.get_password_hash("pass1"),
            project="decice",
            platform_identity=id1,
        )
        id2 = PlatformIdentity(
            platform="slurm",
            platform_username="user2",
            default_working_dir="/home/user2",
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            full_name="User Two",
            hashed_password=temp_auth_service.get_password_hash("pass2"),
            project="decice",
            platform_identity=id2,
        )
        test_db_session.add_all([user1, user2])
        await test_db_session.commit()

        await test_db_session.refresh(user1)
        await test_db_session.refresh(user2)

        self.user1_id = user1.id
        self.user2_id = user2.id

    async def test_get_me_success(
        self, authenticated_client: TestClient, mock_user: UserSchema
    ):
        """
        GIVEN an authenticated user
        WHEN a GET request is made to /user/me/
        THEN the response should be 200 OK with the user's own data.
        """
        response = authenticated_client.get("/v1/user/me/")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["username"] == mock_user.username
        assert response_data["email"] == mock_user.email
        assert response_data["full_name"] == mock_user.full_name

    async def test_get_all_users_as_admin(self, admin_authenticated_client: TestClient):
        """
        GIVEN an admin user
        WHEN a GET request is made to /user/
        THEN the response should be 200 OK and contain all users.
        """
        response = admin_authenticated_client.get("/v1/user/")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) >= 2
        usernames = {u["username"] for u in response_data}
        assert "user1" in usernames
        assert "user2" in usernames

    async def test_get_all_users_as_regular_user(
        self, authenticated_client: TestClient
    ):
        """
        GIVEN a regular (non-admin) user
        WHEN a GET request is made to /user/
        THEN the response should be 403 Forbidden.
        """
        response = authenticated_client.get("/v1/user/")
        assert response.status_code == 403

    async def test_delete_user_as_admin(
        self, admin_authenticated_client: TestClient, test_db_session: AsyncSession
    ):
        """
        GIVEN an admin user
        WHEN a DELETE request is made to /user/{user_id}
        THEN the response should be 204 No Content and the user should be deleted.
        """
        response = admin_authenticated_client.delete(f"/v1/user/{self.user1_id}")
        assert response.status_code == 204
        user_in_db = await test_db_session.get(User, self.user1_id)
        assert user_in_db is None

    async def test_delete_user_as_regular_user(self, authenticated_client: TestClient):
        """
        GIVEN a regular user
        WHEN a DELETE request is made to /user/{user_id}
        THEN the response should be 403 Forbidden.
        """
        response = authenticated_client.delete(f"/v1/user/{self.user1_id}")
        assert response.status_code == 403
