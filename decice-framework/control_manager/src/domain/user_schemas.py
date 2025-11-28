from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from .token_schemas import Token


class PlatformIdentityBase(BaseModel):
    """Base schema for platform identity properties."""

    platform: str = Field(
        ...,
        description="Key identifying the platform.",
    )
    platform_username: str = Field(
        ..., description="The username specific to that platform, e.g., 'alice92'."
    )
    default_working_dir: str = Field(
        None, description="Default working directory on the platform."
    )


class PlatformIdentityCreate(PlatformIdentityBase):
    """Schema for creating a new platform identity via the API."""

    pass


class PlatformIdentityResponse(PlatformIdentityBase):
    """Schema for returning a platform identity via the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


# properties to create database model
class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str | None = None
    active: bool = False
    role: UserRole = UserRole.USER
    project: str | None

    platform_identity: PlatformIdentityResponse

    @field_serializer("id")
    def serialize_id(self, value: UUID) -> str:
        return str(value)


# properties to receive via API on creation
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    project: str
    platform: str = Field(
        default="slurm",
        description="The platform identifier (e.g., 'slurm', 'openstack').",
    )
    platform_username: str = Field(
        ..., description="The username for the HPC platform."
    )
    default_working_dir: str = Field(
        ..., description="Default working directory on the platform."
    )


# properties to send via API on querying user information
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    active: bool = False
    platform_identity: PlatformIdentityResponse


# properties to send via API on login
class UserLogin(BaseModel):
    username: str
    password: str


# properties to receive via API on update
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None


class UserResponseAndToken(BaseModel):
    user: UserResponse
    token: Token


class UserSession(BaseModel):
    session_id: str
    user: User


# properties to receive via API on update
# class UserOptional(User):
#     __annotations__ = {k: Optional[v] for k, v in User.__annotations__.items()}
