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
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
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
    due_date: Mapped[dt | None] = mapped_column(Date)
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


# Multi-stage workflow models


class GeneSummary(Base):
    """
    Pre-computed aggregations of gene curations across scopes.
    Enables fast public queries without real-time aggregation overhead.
    """

    __tablename__ = "gene_summaries"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required foreign key
    gene_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("genes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Aggregated counts
    total_scopes_curated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    public_scopes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    private_scopes_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Classification summary (JSONB with counts by classification)
    classification_summary: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default={}
    )

    # Consensus information
    consensus_classification: Mapped[str | None] = mapped_column(String(50))
    consensus_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    has_conflicts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Per-scope details (array of scope summary objects)
    scope_summaries: Mapped[list[dict[str, Any]]] = mapped_column(
        compatible_jsonb(), nullable=False, default=[]
    )

    # Metadata
    last_computed_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    computation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Cache control
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    gene: Mapped["Gene"] = relationship("Gene")

    __table_args__ = (
        Index(
            "idx_gene_summaries_public",
            "public_scopes_count",
            postgresql_where="public_scopes_count > 0",
        ),
        Index(
            "idx_gene_summaries_stale", "is_stale", postgresql_where="is_stale = TRUE"
        ),
        Index(
            "idx_gene_summaries_classification",
            "classification_summary",
            postgresql_using="gin",
        ),
        Index("idx_gene_summaries_scopes", "scope_summaries", postgresql_using="gin"),
    )
