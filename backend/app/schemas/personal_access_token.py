"""Pydantic schemas for personal access tokens (#462)."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

TokenScope = Literal["read", "write"]


class PersonalAccessTokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_at: AwareDatetime = Field(
        ..., description="Required; must be in the future"
    )
    scopes: list[TokenScope] = Field(
        default=["read", "write"],
        min_length=1,
        description="'read' alone makes the token read-only; scopes never add rights",
    )

    @field_validator("expires_at")
    @classmethod
    def _in_future(cls, value: datetime) -> datetime:
        if value <= datetime.now(UTC):
            raise ValueError("expires_at must be in the future")
        return value


class PersonalAccessTokenResponse(BaseModel):
    """A token as listed: never contains the plaintext or its hash."""

    id: UUID
    name: str
    token_prefix: str
    scopes: list[str]
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonalAccessTokenCreated(PersonalAccessTokenResponse):
    """Creation response: the only time the plaintext token is returned."""

    token: str
