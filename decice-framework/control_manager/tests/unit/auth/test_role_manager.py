import uuid

import pytest
from fastapi import HTTPException

from auth.role_manager import RoleManager
from domain.user_schemas import PlatformIdentityResponse, User, UserRole

DUMMY_USER_DATA = {
    "full_name": "Test User",
    "active": True,
    "project": "test-project",
}


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
def admin_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    """Provides a mock User object with the ADMIN role."""

    admin_id = uuid.uuid4()
    admin_identity = mock_platform_identity.model_copy(
        update={
            "id": uuid.uuid4(),
            "user_id": admin_id,
            "platform_username": "adminuser",
            "default_working_dir": "/home/adminuser",
        }
    )

    return User(
        **DUMMY_USER_DATA,
        id=admin_id,
        username="adminuser",
        email="admin@example.com",
        role=UserRole.ADMIN,
        platform_identity=admin_identity,
    )


@pytest.fixture
def standard_user(mock_platform_identity: PlatformIdentityResponse) -> User:
    """Provides a mock User object with the USER role."""

    user_id = uuid.uuid4()
    identity_copy = mock_platform_identity.model_copy(
        update={"id": uuid.uuid4(), "user_id": user_id}
    )

    return User(
        **DUMMY_USER_DATA,
        id=user_id,
        username="testuser",
        email="test@example.com",
        role=UserRole.USER,
        platform_identity=identity_copy,
    )


class TestRoleManager:
    """A test suite for the RoleManager dependency."""

    def test_initialization_fails_with_empty_roles(self):
        """
        GIVEN an attempt to initialize RoleManager
        WHEN the list of allowed_roles is empty
        THEN a ValueError must be raised.
        """
        with pytest.raises(ValueError, match="allowed_roles cannot be empty"):
            RoleManager(allowed_roles=[])

    @pytest.mark.asyncio
    async def test_access_granted_for_allowed_role(self, admin_user: User):
        """
        GIVEN a RoleManager configured to allow ADMINs
        WHEN it is called with a user who is an ADMIN
        THEN the call should complete successfully without raising an exception.
        """
        admin_only_guard = RoleManager(allowed_roles=[UserRole.ADMIN])

        try:
            await admin_only_guard(current_user=admin_user)
        except HTTPException:
            pytest.fail("HTTPException was raised unexpectedly for an authorized user.")

    @pytest.mark.asyncio
    async def test_access_denied_for_disallowed_role(self, standard_user: User):
        """
        GIVEN a RoleManager configured to allow only ADMINs
        WHEN it is called with a user who has the USER role
        THEN it must raise an HTTPException with a 403 Forbidden status.
        """
        admin_only_guard = RoleManager(allowed_roles=[UserRole.ADMIN])

        with pytest.raises(HTTPException) as exc_info:
            await admin_only_guard(current_user=standard_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Insufficient permissions."

    @pytest.mark.asyncio
    async def test_multiple_allowed_roles_logic(
        self, admin_user: User, standard_user: User
    ):
        """
        GIVEN a RoleManager configured to allow both ADMINs and USERs
        WHEN it is called with either an ADMIN or a USER
        THEN the call should complete successfully in both cases.
        """
        multi_role_guard = RoleManager(allowed_roles=[UserRole.ADMIN, UserRole.USER])

        try:
            await multi_role_guard(current_user=admin_user)
            await multi_role_guard(current_user=standard_user)
        except HTTPException:
            pytest.fail(
                "HTTPException was raised unexpectedly when multiple roles were allowed."
            )
