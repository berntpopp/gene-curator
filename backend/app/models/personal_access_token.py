"""Personal access tokens (migration 056, #462)."""

import uuid
from datetime import datetime as dt
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_array_text, compatible_uuid


class PersonalAccessToken(Base):
    """A per-user API token; only the sha256 hash of the plaintext is stored."""

    __tablename__ = "personal_access_tokens"
    __table_args__ = (
        Index("idx_personal_access_tokens_user", "user_id", "created_at"),
    )

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        compatible_array_text(), nullable=False, default=lambda: ["read", "write"]
    )
    expires_at: Mapped[dt] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
