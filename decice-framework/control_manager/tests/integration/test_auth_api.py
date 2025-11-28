import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth.security import AuthService
from db.models import PlatformIdentity, User


@pytest.mark.asyncio
class TestAuthAPI:
    async def test_register_user_success(
        self, test_client: TestClient, test_db_session: AsyncSession
    ):
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "a-very-secure-password",
            "project": "decice",
            "platform_username": "testuser_slurm",
            "default_working_dir": "/home/testuser",
        }

        response = test_client.post("/v1/register", json=user_data)

        assert response.status_code == 201, response.json()

        query = select(User).where(User.username == "testuser")
        result = await test_db_session.execute(query)
        created_user = result.scalar_one_or_none()

        assert created_user is not None
        assert created_user.email == "test@example.com"

    async def test_register_user_username_exists(self, test_client: TestClient):
        user_data = {
            "username": "existinguser",
            "email": "first@example.com",
            "full_name": "First User",
            "password": "password123",
            "project": "decice",
            "platform_username": "existinguser_slurm",
            "default_working_dir": "/home/existinguser",
        }
        test_client.post("/v1/register", json=user_data)

        conflicting_user_data = {
            "username": "existinguser",
            "email": "second@example.com",
            "full_name": "Second User",
            "password": "password456",
            "project": "decice",
            "platform_username": "other_user_slurm",
            "default_working_dir": "/home/other_user",
        }
        response = test_client.post("/v1/register", json=conflicting_user_data)

        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    async def test_login_for_access_token_success(
        self, test_client: TestClient, test_db_session: AsyncSession
    ):
        plain_password = "my-login-password"

        temp_auth_service = AuthService(
            secret_key="dummy-key-for-testing", algorithm="HS256", expire_minutes=30
        )
        hashed_password = temp_auth_service.get_password_hash(plain_password)
        db_identity = PlatformIdentity(
            platform="slurm",
            platform_username="loginuser_slurm",
            default_working_dir="/home/loginuser",
        )
        db_user = User(
            username="loginuser",
            email="login@example.com",
            hashed_password=hashed_password,
            project="decice",
            active=True,
            platform_identity=db_identity,
        )
        test_db_session.add(db_user)
        await test_db_session.commit()

        login_data = {"username": "loginuser", "password": plain_password}
        response = test_client.post("/v1/token", data=login_data)

        assert response.status_code == 200, response.json()
        response_data = response.json()
        assert "access_token" in response_data
