"""MCP OAuth clients and grants (migration 064, #462)."""

import uuid
from datetime import datetime as dt
from typing import Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_jsonb, compatible_uuid


class OAuthClient(Base):
    """A dynamically registered client (RFC 7591); only its secret's sha256 is kept."""

    __tablename__ = "oauth_clients"

    client_id: Mapped[str] = mapped_column(Text, primary_key=True)
    client_secret_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", compatible_jsonb(), nullable=False
    )
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OAuthGrant(Base):
    """One authorization: pending, then a hashed code, then a hashed refresh token."""

    __tablename__ = "oauth_grants"
    __table_args__ = (Index("idx_oauth_grants_user", "user_id"),)

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[str] = mapped_column(
        Text, ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="CASCADE")
    )
    params: Mapped[dict[str, Any]] = mapped_column(compatible_jsonb(), nullable=False)
    code_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    access_token_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(),
        ForeignKey("personal_access_tokens.id", ondelete="CASCADE"),
    )
    expires_at: Mapped[dt] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
