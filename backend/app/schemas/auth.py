"""
Authentication-related Pydantic schemas.
"""

import uuid
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: Literal["admin", "user"] = "user"  # Mirrors UserRoleNew
    is_active: bool = True
    is_agent: bool = Field(
        False, description="AI agent account (#639): token sign-in only, never an admin"
    )

    @model_validator(mode="after")
    def _agent_is_no_admin(self) -> "UserBase":
        if self.is_agent and self.role == "admin":
            raise ValueError("An agent account cannot be a platform admin")
        return self


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)
    institution: str | None = None
    orcid_id: str | None = None
    expertise_areas: list[str] | None = None


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


class PasswordChange(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
