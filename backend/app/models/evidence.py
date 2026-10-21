"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.

Modern SQLAlchemy 2.0 patterns with full type safety.
"""

import uuid
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import (
    compatible_array_text,
    compatible_jsonb,
    compatible_uuid,
)

if TYPE_CHECKING:
    from app.models.curation import CurationNew
    from app.models.identity import UserNew


class EvidenceItem(Base):
    """
    Individual evidence items extracted from JSONB arrays.
    Provides better data integrity, validation, and queryability for evidence.
    """

    __tablename__ = "evidence_items"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required foreign keys
    curation_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Evidence classification
    evidence_category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'case_level', 'segregation', 'case_control', etc.
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'genetic', 'experimental'

    # Evidence data (JSONB for flexibility)
    evidence_data: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False
    )

    # Scoring results
    computed_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    score_metadata: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())

    # Validation status
    validation_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # 'pending', 'valid', 'invalid'
    validation_errors: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())
    validated_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))

    # Audit fields
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="RESTRICT")
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    curation: Mapped["CurationNew"] = relationship("CurationNew")
    creator: Mapped["UserNew"] = relationship("UserNew", foreign_keys=[created_by])
    updater: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[updated_by]
    )
    deleter: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[deleted_by]
    )

    __table_args__ = (
        Index(
            "idx_evidence_items_curation",
            "curation_id",
            postgresql_where="is_deleted = FALSE",
        ),
        Index(
            "idx_evidence_items_category",
            "evidence_category",
            postgresql_where="is_deleted = FALSE",
        ),
        Index(
            "idx_evidence_items_type",
            "evidence_type",
            postgresql_where="is_deleted = FALSE",
        ),
        Index(
            "idx_evidence_items_curation_category",
            "curation_id",
            "evidence_category",
            postgresql_where="is_deleted = FALSE",
        ),
        Index(
            "idx_evidence_items_display",
            "curation_id",
            "evidence_category",
            "created_at",
            postgresql_where="is_deleted = FALSE",
        ),
    )


class Publication(Base):
    """
    Cached publication data from PubMed/Europe PMC.
    Stores validated publication metadata for association with curations
    and evidence items without repeated API calls.
    """

    __tablename__ = "publications"

    # Primary key - using PMID as natural key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # PubMed identifier (unique)
    pmid: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )

    # Core publication data
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list[str]] = mapped_column(
        compatible_array_text(), nullable=False, default=[]
    )
    author_string: Mapped[str | None] = mapped_column(Text)  # Formatted author list

    # Journal information
    journal: Mapped[str] = mapped_column(String(500), nullable=False)
    journal_abbrev: Mapped[str | None] = mapped_column(String(100))
    volume: Mapped[str | None] = mapped_column(String(50))
    issue: Mapped[str | None] = mapped_column(String(50))
    pages: Mapped[str | None] = mapped_column(String(50))

    # Date information
    pub_year: Mapped[int | None] = mapped_column(Integer, index=True)
    pub_date: Mapped[str | None] = mapped_column(String(50))  # Full date string

    # External identifiers
    doi: Mapped[str | None] = mapped_column(String(200), index=True)
    pmcid: Mapped[str | None] = mapped_column(String(20), index=True)

    # Extended metadata
    abstract: Mapped[str | None] = mapped_column(Text)
    pub_type: Mapped[str | None] = mapped_column(String(100))
    is_open_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cited_by_count: Mapped[int | None] = mapped_column(Integer)

    # Raw API response for reference
    api_response: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())

    # Cache control
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_fetched_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Track who first added this publication
    added_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    adder: Mapped["UserNew | None"] = relationship("UserNew", foreign_keys=[added_by])

    __table_args__ = (
        Index("idx_publications_year", "pub_year"),
        Index("idx_publications_journal", "journal"),
        Index(
            "idx_publications_search",
            "pmid",
            "doi",
            "title",
        ),
    )


# Notifications
