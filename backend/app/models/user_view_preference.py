"""Per-user saved views (migration 084, #276)."""

from datetime import datetime as dt
from typing import Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_jsonb, compatible_uuid


class UserViewPreference(Base):
    """One user's saved state of one view, such as the catalogue's scope columns."""

    __tablename__ = "user_view_preferences"

    user_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    view: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default=dict
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
