"""Immutable methodology versions: numbered snapshots of a curation schema (migration 042)."""

import uuid
from datetime import datetime as dt
from typing import Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import compatible_jsonb, compatible_uuid


class MethodologyVersion(Base):
    """A schema snapshot; once published, the database refuses any UPDATE or DELETE."""

    __tablename__ = "methodology_versions"

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )
    schema_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curation_schemas.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(compatible_jsonb(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id")
    )
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    derived_from_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("methodology_versions.id")
    )

    __table_args__ = (
        UniqueConstraint(
            "schema_id", "version", name="uq_methodology_versions_schema_version"
        ),
        CheckConstraint("version > 0"),
        CheckConstraint("status IN ('draft', 'published')"),
    )
