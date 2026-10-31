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
    Computed,
    Date,
    DateTime,
    Enum,
    FetchedValue,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_types import (
    compatible_jsonb,
    compatible_uuid,
)
from app.models._common import _user_fk
from app.models.model_enums import CurationStatus, ReviewStatus, WorkflowStage

if TYPE_CHECKING:
    from app.models.genes import Gene
    from app.models.identity import Scope, UserNew
    from app.models.schemas import CurationSchema, WorkflowPair


def _field(key: str) -> str:
    """A disease field, flat or under entity_definition (as schemas.curation.disease_fields)."""
    return (
        f"trim(COALESCE(NULLIF(trim(evidence_data ->> '{key}'), ''), "
        f"evidence_data -> 'entity_definition' ->> '{key}', ''))"
    )


_MONDO = f"upper(replace({_field('mondo_id')}, '_', ':'))"
# Squashed: no case, spaces, '_' or '-', and no "inheritance" (HPO labels)
_MOI = (
    "replace(replace(replace(replace(lower("
    f"{_field('mode_of_inheritance')}"
    "), ' ', ''), '_', ''), '-', ''), 'inheritance', '')"
)
# HPO label, HPO id and code map to one canonical MOI (codes pass through as-is)
_MOI_SYNONYMS = {
    "ad": ("autosomaldominant", "hp:0000006"),
    "ar": ("autosomalrecessive", "hp:0000007"),
    "xl": ("xlinked", "hp:0001417"),
    "xld": ("xlinkeddominant", "hp:0001423"),
    "xlr": ("xlinkedrecessive", "hp:0001419"),
    "yl": ("ylinked", "hp:0001450"),
    "sd": ("semidominant", "hp:0032113"),
    "mt": ("mitochondrial", "hp:0001427"),
}
_MOI_CASE = (
    f"upper(CASE {_MOI} "
    + " ".join(
        f"WHEN '{s}' THEN '{abbr}'"
        for abbr, syns in _MOI_SYNONYMS.items()
        for s in syns
    )
    + f" ELSE {_MOI} END)"
)
# Only non-Mendelian relationships are suffixed (#539), so Mendelian keys stay as 067 made them
_RELATIONSHIP = (
    f"CASE WHEN lower({_field('relationship_type')}) = 'susceptibility' "
    "THEN '|SUSCEPTIBILITY' ELSE '' END"
)
# The gene-disease-MOI entity (#530): normalised MONDO id | MOI [| SUSCEPTIBILITY]; ''
# without a MONDO id. Portable SQL (PostgreSQL jsonb and SQLite JSON ->/->>); 072 holds
# the same expression.
ENTITY_KEY_SQL = (
    f"CASE WHEN {_MONDO} = '' THEN '' "
    f"ELSE {_MONDO} || '|' || {_MOI_CASE} || {_RELATIONSHIP} END"
)
# Open precurations, one per disease entity (077 holds the same predicate)
_OPEN_ENTITY = (
    "entity_key <> '' AND status IN ('draft', 'submitted', 'in_review', 'rejected')"
)


class PrecurationNew(Base):
    """Multiple precurations per gene-scope with schema-driven fields."""

    __tablename__ = "precurations"

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
    precuration_schema_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curation_schemas.id"),
        nullable=False,
        index=True,
    )
    # Pinned at creation by a DB trigger (042); NOT NULL; only an admin move to a later
    # version of the same schema re-pins it in PostgreSQL (078)
    methodology_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(),
        ForeignKey("methodology_versions.id"),
        server_default=FetchedValue(),
    )

    # Status and workflow
    status: Mapped[CurationStatus] = mapped_column(
        Enum(CurationStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="draft",
        index=True,
    )
    workflow_stage: Mapped[WorkflowStage] = mapped_column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="precuration",
        index=True,
    )
    # Optimistic locking: saves compare-and-increment this (migration 040)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Evidence data (schema-agnostic)
    evidence_data: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default={}
    )

    # Computed results from schema
    computed_scores: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )
    computed_fields: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )

    # Disease entity of the draft, derived from evidence_data (migration 067)
    entity_key: Mapped[str] = mapped_column(
        Text, Computed(ENTITY_KEY_SQL, persisted=True)
    )

    # Auto-save functionality (nullable)
    auto_saved_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))

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

    # Provenance tracking
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    record_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64))

    # Relationships
    gene: Mapped["Gene"] = relationship("Gene", back_populates="precurations")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="precurations")
    precuration_schema: Mapped["CurationSchema"] = relationship(
        "CurationSchema", back_populates="precurations"
    )
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by], overlaps="created_precurations"
    )
    updater: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[updated_by]
    )
    curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", back_populates="precuration"
    )

    __table_args__ = (
        Index("idx_precurations_gene_scope", "gene_id", "scope_id"),
        Index(
            "uq_precurations_open_draft",
            "gene_id",
            "scope_id",
            "created_by",
            "entity_key",
            unique=True,
            postgresql_where=text("status = 'draft'"),
            sqlite_where=text("status = 'draft'"),
        ),
        Index(  # one open precuration per disease entity (077)
            "uq_precurations_open_entity",
            "gene_id",
            "scope_id",
            "entity_key",
            unique=True,
            postgresql_where=text(_OPEN_ENTITY),
            sqlite_where=text(_OPEN_ENTITY),
        ),
        Index("idx_precurations_evidence_gin", "evidence_data", postgresql_using="gin"),
    )


class CurationNew(Base):
    """Multiple curations per gene-scope with scoring engine integration."""

    __tablename__ = "curations"

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
    workflow_pair_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("workflow_pairs.id"), nullable=False, index=True
    )

    # Nullable fields
    precuration_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("precurations.id", ondelete="SET NULL")
    )
    # Copied once from the precuration at creation (067); '' = lumped/legacy, one per gene
    entity_key: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    # Pinned at creation by a DB trigger (042); NOT NULL; only an admin move to a later
    # version of the same schema re-pins it in PostgreSQL (078)
    methodology_version_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(),
        ForeignKey("methodology_versions.id"),
        server_default=FetchedValue(),
    )

    # Status and workflow
    status: Mapped[CurationStatus] = mapped_column(
        Enum(CurationStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="draft",
        index=True,
    )
    workflow_stage: Mapped[WorkflowStage] = mapped_column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="curation",
        index=True,
    )
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Evidence data (schema-agnostic)
    evidence_data: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default={}
    )

    # #593 (080): who added and last changed each evidence table row, by row key
    row_provenance: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())
    # Computed results (updated by scoring engines)
    computed_scores: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )
    computed_verdict: Mapped[str | None] = mapped_column(String(100), index=True)
    computed_summary: Mapped[str | None] = mapped_column(Text)
    computed_fields: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )

    # Curator's call (#533): overrides the computed verdict; rationale required if it differs
    curator_classification: Mapped[str | None] = mapped_column(String(100))
    curator_classification_rationale: Mapped[str | None] = mapped_column(Text)
    # Adopted ClinGen record, verbatim from GeneFoundry (#105, migration 079)
    clingen_adoption: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())

    @hybrid_property
    def final_classification(self) -> str | None:
        return self.curator_classification or self.computed_verdict

    @final_classification.inplace.expression
    @classmethod
    def _final_classification_expression(cls) -> ColumnElement[str | None]:
        return func.coalesce(cls.curator_classification, cls.computed_verdict)

    # Auto-save functionality (nullable)
    auto_saved_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))

    # Submission and approval (nullable)
    submitted_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), index=True)
    approved_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Optimistic locking (ClinGen SOP v11)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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

    # Provenance tracking
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    record_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64))

    # Relationships
    gene: Mapped["Gene"] = relationship("Gene", back_populates="curations")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="curations")
    precuration: Mapped["PrecurationNew | None"] = relationship(
        "PrecurationNew", back_populates="curations"
    )
    workflow_pair: Mapped["WorkflowPair"] = relationship(
        "WorkflowPair", back_populates="curations"
    )

    @property
    def curation_schema_id(self) -> PyUUID | None:
        """The pair's curation schema: the field contract a client reads (round 5)."""
        return self.workflow_pair.curation_schema_id if self.workflow_pair else None

    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by], overlaps="created_curations"
    )
    updater: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[updated_by]
    )
    submitter: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[submitted_by]
    )
    approver: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[approved_by], overlaps="approved_curations"
    )
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="curation")
    active_curation: Mapped["ActiveCuration | None"] = relationship(
        "ActiveCuration",
        back_populates="curation",
        foreign_keys="[ActiveCuration.curation_id]",
    )

    __table_args__ = (
        Index("idx_curations_gene_scope", "gene_id", "scope_id"),
        Index("idx_curations_evidence_gin", "evidence_data", postgresql_using="gin"),
        Index("idx_curations_scores_gin", "computed_scores", postgresql_using="gin"),
        Index("idx_curations_lock_version", "id", "lock_version"),
        # Mirrors database/sql/067: one active and one open curation per disease entity
        Index(
            "uq_curations_one_active",
            "gene_id",
            "scope_id",
            "entity_key",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_curations_one_open",
            "gene_id",
            "scope_id",
            "entity_key",
            unique=True,
            postgresql_where=text("status NOT IN ('active', 'archived')"),
            sqlite_where=text("status NOT IN ('active', 'archived')"),
        ),
    )


class Review(Base):
    """4-eyes principle implementation with mandatory independent review."""

    __tablename__ = "reviews"

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    curation_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="pending",
        index=True,
    )

    # Review content (nullable)
    comments: Mapped[str | None] = mapped_column(Text)
    feedback_data: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )
    recommendation: Mapped[str | None] = mapped_column(
        String(50)
    )  # approve, reject, needs_revision

    # Review actions (nullable)
    reviewed_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), index=True)

    # Metadata
    assigned_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    assigned_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    due_date: Mapped[date | None] = mapped_column(Date)

    # Version tracking for iterative reviews
    review_round: Mapped[int] = mapped_column(Integer, default=1)

    # Read by the audit trigger (migration 035)
    created_by: Mapped[PyUUID | None] = _user_fk()
    updated_by: Mapped[PyUUID | None] = _user_fk()

    # Relationships
    curation: Mapped["CurationNew"] = relationship(
        "CurationNew", back_populates="reviews"
    )
    reviewer: Mapped["UserNew"] = relationship(
        "UserNew", foreign_keys=[reviewer_id], overlaps="reviews_assigned"
    )
    assigner: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[assigned_by]
    )


class ActiveCuration(Base):
    """One active curation per gene-scope with archive management."""

    __tablename__ = "active_curations"

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
    curation_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("curations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_key: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )

    # Activation details
    activated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    activated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Previous active curation (for audit trail)
    replaced_curation_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curations.id", ondelete="SET NULL")
    )

    # Archive information (nullable)
    archived_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    archive_reason: Mapped[str | None] = mapped_column(Text)

    # Audit fields (required by audit trigger)
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
    gene: Mapped["Gene"] = relationship("Gene", back_populates="active_curations")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="active_curations")
    curation: Mapped["CurationNew"] = relationship(
        "CurationNew", back_populates="active_curation", foreign_keys=[curation_id]
    )
    activator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[activated_by]
    )
    archiver: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[archived_by]
    )
    replaced_curation: Mapped["CurationNew | None"] = relationship(
        "CurationNew", foreign_keys=[replaced_curation_id]
    )

    __table_args__ = (
        # Only one non-archived row per disease entity; archived history may repeat
        Index(
            "uq_active_curation_gene_scope_current",
            "gene_id",
            "scope_id",
            "entity_key",
            unique=True,
            postgresql_where="archived_at IS NULL",
            sqlite_where=text("archived_at IS NULL"),
        ),
        Index(
            "idx_active_curations_current",
            "archived_at",
            postgresql_where="archived_at IS NULL",
        ),
    )


# AUDIT AND TRACKING MODELS
