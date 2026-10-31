"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.

Modern SQLAlchemy 2.0 patterns with full type safety.
"""

import uuid
from datetime import date, datetime as dt
from typing import TYPE_CHECKING, Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import (
    compatible_array_text,
    compatible_jsonb,
    compatible_uuid,
)
from app.models._common import _user_fk

if TYPE_CHECKING:
    from app.models.curation import ActiveCuration, CurationNew, PrecurationNew
    from app.models.identity import Scope, UserNew
    from app.models.schemas import WorkflowPair


class Gene(Base):
    """Genes table for scope assignment."""

    __tablename__ = "genes"

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    hgnc_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    approved_symbol: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Nullable fields
    previous_symbols: Mapped[list[str]] = mapped_column(compatible_array_text())
    alias_symbols: Mapped[list[str]] = mapped_column(compatible_array_text())
    chromosome: Mapped[str | None] = mapped_column(String(10), index=True)
    location: Mapped[str | None] = mapped_column(String(50))

    # Gene details (preserves current flexibility)
    details: Mapped[dict[str, Any]] = mapped_column(compatible_jsonb(), default={})

    # Provenance tracking
    previous_hash: Mapped[str | None] = mapped_column(String(64))

    # Metadata
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[PyUUID | None] = _user_fk()
    updated_by: Mapped[PyUUID | None] = _user_fk()

    # Relationships
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by], overlaps="created_genes"
    )
    updater: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[updated_by]
    )
    scope_assignments: Mapped[list["GeneScopeAssignment"]] = relationship(
        "GeneScopeAssignment", back_populates="gene"
    )
    precurations: Mapped[list["PrecurationNew"]] = relationship(
        "PrecurationNew", back_populates="gene"
    )
    curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", back_populates="gene"
    )
    active_curations: Mapped[list["ActiveCuration"]] = relationship(
        "ActiveCuration", back_populates="gene"
    )

    __table_args__ = (
        Index("idx_genes_details_gin", "details", postgresql_using="gin"),
    )


# Gene resolver lookup (052, #379). The GIN pair uses upper_text_array, a Postgres function.
Index("idx_genes_upper_symbol", func.upper(Gene.approved_symbol))
Index("idx_genes_upper_hgnc_id", func.upper(Gene.hgnc_id))
for _col in (Gene.previous_symbols, Gene.alias_symbols):
    Index(
        f"idx_genes_upper_{_col.key}",
        func.upper_text_array(_col),
        postgresql_using="gin",
    ).ddl_if(dialect="postgresql")


class GeneScopeAssignment(Base):
    """Many-to-many relationship between genes and clinical scopes."""

    __tablename__ = "gene_scope_assignments"

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    gene_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("genes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Nullable fields
    assigned_curator_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    workflow_pair_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("workflow_pairs.id"), index=True
    )

    # Assignment details
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[str] = mapped_column(
        String(20), default="medium"
    )  # high, medium, low
    due_date: Mapped[date | None] = mapped_column(Date)
    assignment_notes: Mapped[str | None] = mapped_column(Text)

    # Metadata
    assigned_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    gene: Mapped["Gene"] = relationship("Gene", back_populates="scope_assignments")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="gene_assignments")
    assigned_curator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[assigned_curator_id], overlaps="curator_assignments"
    )
    assigner: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[assigned_by]
    )
    workflow_pair: Mapped["WorkflowPair | None"] = relationship(
        "WorkflowPair", back_populates="gene_assignments"
    )

    __table_args__ = (
        UniqueConstraint("gene_id", "scope_id", name="uq_gene_scope_assignment"),
    )
