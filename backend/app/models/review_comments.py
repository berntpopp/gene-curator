"""Per-item review comments (migration 037)."""

import uuid
from datetime import datetime as dt
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_uuid


class ReviewItemComment(Base):
    """A comment anchored to one evidence item (`item_path`) of a curation."""

    __tablename__ = "review_item_comments"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'resolved')"),
        Index("idx_review_item_comments_curation", "curation_id", "created_at"),
    )

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )
    curation_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curations.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("reviews.id", ondelete="SET NULL")
    )
    item_path: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
