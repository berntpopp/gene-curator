"""
Authentication-related Pydantic schemas.
"""

import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: str = "viewer"  # Use string directly, validated by enum constraint in DB
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)
    institution: str | None = None
    orcid_id: str | None = None
    expertise_areas: list[str] | None = None
    assigned_scopes: list[str] | None = None


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema for user responses (excludes sensitive data)."""

    id: str | uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
        json_encoders={uuid.UUID: str},  # Convert UUID to string in JSON
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # user ID
    email: str
    role: str
    exp: int
    iat: int | None = None
    type: str | None = "access"  # access or refresh


class PasswordChange(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
