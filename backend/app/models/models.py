"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.

Modern SQLAlchemy 2.0 patterns with full type safety.
"""

import enum
import uuid
from datetime import datetime as dt
from typing import Any
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
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
    compatible_array_uuid,
    compatible_inet,
    compatible_jsonb,
    compatible_uuid,
)

# ========================================
# ENHANCED ENUM DEFINITIONS
# ========================================


class UserRoleNew(str, enum.Enum):
    """
    Application-level user roles (NOT scope-specific).

    - ADMIN: Platform administrator with full access
    - USER: Standard user (scope-specific roles assigned via scope_memberships)

    Note: Scope-specific roles (curator, reviewer, viewer, admin) are managed
    in the scope_memberships table, not at the application level.
    """

    ADMIN = "admin"
    USER = "user"


class WorkflowStage(str, enum.Enum):
    ENTRY = "entry"
    PRECURATION = "precuration"
    CURATION = "curation"
    REVIEW = "review"
    ACTIVE = "active"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class CurationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SchemaType(str, enum.Enum):
    PRECURATION = "precuration"
    CURATION = "curation"
    COMBINED = "combined"


# ========================================
# CORE SCHEMA-AGNOSTIC MODELS
# ========================================


class Scope(Base):
    """Clinical specialties as first-class entities."""

    __tablename__ = "scopes"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Nullable fields
    description: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(String(255), index=True)
    default_workflow_pair_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("workflow_pairs.id")
    )

    # Status
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Configuration
    scope_config: Mapped[dict[str, Any]] = mapped_column(compatible_jsonb(), default={})

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
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by]
    )
    default_workflow_pair: Mapped["WorkflowPair | None"] = relationship(
        "WorkflowPair", foreign_keys=[default_workflow_pair_id]
    )
    gene_assignments: Mapped[list["GeneScopeAssignment"]] = relationship(
        "GeneScopeAssignment", back_populates="scope", passive_deletes=True
    )
    scope_memberships: Mapped[list["ScopeMembership"]] = relationship(
        "ScopeMembership", back_populates="scope", passive_deletes=True
    )
    precurations: Mapped[list["PrecurationNew"]] = relationship(
        "PrecurationNew", back_populates="scope", passive_deletes=True
    )
    curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", back_populates="scope", passive_deletes=True
    )
    active_curations: Mapped[list["ActiveCuration"]] = relationship(
        "ActiveCuration", back_populates="scope", passive_deletes=True
    )
    audit_logs: Mapped[list["AuditLogNew"]] = relationship(
        "AuditLogNew", back_populates="scope", passive_deletes=True
    )
    schema_selections: Mapped[list["SchemaSelection"]] = relationship(
        "SchemaSelection", back_populates="scope", passive_deletes=True
    )


class UserNew(Base):
    """Enhanced users with scope assignments and scientific attribution."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleNew] = mapped_column(
        Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="viewer",
        index=True,
    )

    # Nullable fields
    institution: Mapped[str | None] = mapped_column(String(255), index=True)
    assigned_scopes: Mapped[list[PyUUID]] = mapped_column(
        compatible_array_uuid(), default=[]
    )

    # Enhanced profile (nullable)
    orcid_id: Mapped[str | None] = mapped_column(String(50))
    expertise_areas: Mapped[list[str]] = mapped_column(
        compatible_array_text(), default=[]
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login: Mapped[dt | None] = mapped_column(DateTime(timezone=True))

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

    # Relationships
    created_scopes: Mapped[list["Scope"]] = relationship(
        "Scope", foreign_keys="[Scope.created_by]", overlaps="creator"
    )
    created_schemas: Mapped[list["CurationSchema"]] = relationship(
        "CurationSchema", foreign_keys="[CurationSchema.created_by]"
    )
    created_workflow_pairs: Mapped[list["WorkflowPair"]] = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.created_by]"
    )
    curator_assignments: Mapped[list["GeneScopeAssignment"]] = relationship(
        "GeneScopeAssignment", foreign_keys="[GeneScopeAssignment.assigned_curator_id]"
    )
    created_genes: Mapped[list["Gene"]] = relationship(
        "Gene", foreign_keys="[Gene.created_by]"
    )
    created_precurations: Mapped[list["PrecurationNew"]] = relationship(
        "PrecurationNew", foreign_keys="[PrecurationNew.created_by]"
    )
    created_curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", foreign_keys="[CurationNew.created_by]"
    )
    reviews_assigned: Mapped[list["Review"]] = relationship(
        "Review", foreign_keys="[Review.reviewer_id]"
    )
    approved_curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", foreign_keys="[CurationNew.approved_by]"
    )
    scope_memberships: Mapped[list["ScopeMembership"]] = relationship(
        "ScopeMembership",
        foreign_keys="[ScopeMembership.user_id]",
        back_populates="user",
    )


class ScopeMembership(Base):
    """
    Scope membership table for multi-tenant user-scope relationships.

    This is the core table for multi-tenancy. It defines which users belong to
    which scopes and what role they have within each scope.

    Key Features:
    - Many-to-many relationship between users and scopes with roles
    - Invitation workflow support (invited_at, accepted_at)
    - Soft delete support (is_active)
    - Team support for future group-based permissions
    """

    __tablename__ = "scope_memberships"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role within scope (uses scope_role enum from database)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # admin, curator, reviewer, viewer

    # Invitation workflow (nullable fields)
    invited_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    invited_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True)
    )  # NULL = pending invitation

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    # Team support (future feature for group-based permissions)
    team_id: Mapped[PyUUID | None] = mapped_column(compatible_uuid())

    # Notes (nullable)
    notes: Mapped[str | None] = mapped_column(Text)

    # Metadata
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    scope: Mapped["Scope"] = relationship("Scope", back_populates="scope_memberships")
    user: Mapped["UserNew"] = relationship(
        "UserNew", foreign_keys=[user_id], back_populates="scope_memberships"
    )
    inviter: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[invited_by]
    )

    __table_args__ = (
        UniqueConstraint("scope_id", "user_id", name="uq_scope_membership_scope_user"),
        Index(
            "idx_scope_memberships_user_scope_active",
            "user_id",
            "scope_id",
            "role",
            postgresql_where="is_active = TRUE AND accepted_at IS NOT NULL",
        ),
        Index(
            "idx_scope_memberships_pending",
            "user_id",
            postgresql_where="accepted_at IS NULL",
        ),
    )


class CurationSchema(Base):
    """Repository of methodology definitions (ClinGen, GenCC, custom)."""

    __tablename__ = "curation_schemas"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_type: Mapped[SchemaType] = mapped_column(
        Enum(SchemaType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )

    # Complete schema definition (required)
    field_definitions: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False
    )
    validation_rules: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default={}
    )
    workflow_states: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False
    )
    ui_configuration: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False
    )

    # Complete schema definition (nullable)
    scoring_configuration: Mapped[dict[str, Any] | None] = mapped_column(
        compatible_jsonb()
    )

    # Inheritance support (nullable)
    based_on_schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )

    # Metadata (nullable)
    description: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(String(255), index=True)
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id")
    )
    created_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Schema validation checksum
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by], overlaps="created_schemas"
    )
    based_on_schema: Mapped["CurationSchema | None"] = relationship(
        "CurationSchema", remote_side=[id]
    )
    precuration_workflow_pairs: Mapped[list["WorkflowPair"]] = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.precuration_schema_id]"
    )
    curation_workflow_pairs: Mapped[list["WorkflowPair"]] = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.curation_schema_id]"
    )
    precurations: Mapped[list["PrecurationNew"]] = relationship(
        "PrecurationNew", back_populates="precuration_schema"
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_schema_name_version"),
        Index(
            "idx_curation_schemas_field_definitions",
            "field_definitions",
            postgresql_using="gin",
        ),
        Index(
            "idx_curation_schemas_scoring_config",
            "scoring_configuration",
            postgresql_using="gin",
        ),
    )


class WorkflowPair(Base):
    """Precuration + curation schema combinations for complete workflows."""

    __tablename__ = "workflow_pairs"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Schema references (nullable)
    precuration_schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )
    curation_schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )

    # How data flows between stages
    data_mapping: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False, default={}
    )

    # Workflow configuration
    workflow_config: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )

    # Metadata (nullable)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id")
    )
    created_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    creator: Mapped["UserNew | None"] = relationship(
        "UserNew", foreign_keys=[created_by], overlaps="created_workflow_pairs"
    )
    precuration_schema: Mapped["CurationSchema | None"] = relationship(
        "CurationSchema",
        foreign_keys=[precuration_schema_id],
        overlaps="precuration_workflow_pairs",
    )
    curation_schema: Mapped["CurationSchema | None"] = relationship(
        "CurationSchema",
        foreign_keys=[curation_schema_id],
        overlaps="curation_workflow_pairs",
    )
    scope_defaults: Mapped[list["Scope"]] = relationship(
        "Scope",
        foreign_keys="[Scope.default_workflow_pair_id]",
        overlaps="default_workflow_pair",
    )
    gene_assignments: Mapped[list["GeneScopeAssignment"]] = relationship(
        "GeneScopeAssignment", back_populates="workflow_pair"
    )
    curations: Mapped[list["CurationNew"]] = relationship(
        "CurationNew", back_populates="workflow_pair"
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_workflow_pair_name_version"),
    )


class Gene(Base):
    """Genes table for scope assignment."""

    __tablename__ = "genes"

    # Primary key
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
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

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

    # Primary key
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
        String(20), default="normal"
    )  # high, normal, low
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


# ========================================
# MULTI-STAGE WORKFLOW MODELS
# ========================================


class PrecurationNew(Base):
    """Multiple precurations per gene-scope with schema-driven fields."""

    __tablename__ = "precurations"

    # Primary key
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
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

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
        Index("idx_precurations_evidence_gin", "evidence_data", postgresql_using="gin"),
    )


class CurationNew(Base):
    """Multiple curations per gene-scope with scoring engine integration."""

    __tablename__ = "curations"

    # Primary key
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

    # Computed results (updated by scoring engines)
    computed_scores: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )
    computed_verdict: Mapped[str | None] = mapped_column(String(100), index=True)
    computed_summary: Mapped[str | None] = mapped_column(Text)
    computed_fields: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), default={}
    )

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
    created_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

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
    )


class Review(Base):
    """4-eyes principle implementation with mandatory independent review."""

    __tablename__ = "reviews"

    # Primary key
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
    due_date: Mapped[dt | None] = mapped_column(Date)

    # Version tracking for iterative reviews
    review_round: Mapped[int] = mapped_column(Integer, default=1)

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

    # Primary key
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
        UniqueConstraint("gene_id", "scope_id", name="uq_active_curation_gene_scope"),
        Index("idx_active_curations_gene_scope", "gene_id", "scope_id"),
        Index(
            "idx_active_curations_current",
            "archived_at",
            postgresql_where="archived_at IS NULL",
        ),
    )


# ========================================
# AUDIT AND TRACKING MODELS
# ========================================


class AuditLogNew(Base):
    """Enhanced audit log for multi-stage workflow with scope context."""

    __tablename__ = "audit_log"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Required fields
    entity_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    entity_id: Mapped[PyUUID] = mapped_column(compatible_uuid(), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    timestamp: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Nullable fields
    scope_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("scopes.id", ondelete="SET NULL")
    )
    changes: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())
    user_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Additional context (nullable)
    ip_address: Mapped[str | None] = mapped_column(compatible_inet())
    user_agent: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[PyUUID | None] = mapped_column(compatible_uuid())

    # Multi-stage workflow context (nullable)
    workflow_stage: Mapped[WorkflowStage | None] = mapped_column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        index=True,
    )
    review_action: Mapped[ReviewStatus | None] = mapped_column(
        Enum(ReviewStatus, values_callable=lambda obj: [e.value for e in obj])
    )
    previous_status: Mapped[str | None] = mapped_column(Text)
    new_status: Mapped[str | None] = mapped_column(Text)

    # Schema context (nullable)
    schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )
    workflow_pair_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("workflow_pairs.id")
    )

    # Enhanced tracking fields (ClinGen SOP v11 - ALCOA+ compliance)
    change_type: Mapped[str | None] = mapped_column(
        String(50), index=True
    )  # 'evidence_added', 'score_updated', 'status_changed'
    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        compatible_jsonb()
    )  # Previous state snapshot
    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        compatible_jsonb()
    )  # New state snapshot
    change_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        compatible_jsonb()
    )  # User agent, IP, client info
    alcoa_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        compatible_jsonb()
    )  # ALCOA+ compliance fields

    # Relationships
    scope: Mapped["Scope | None"] = relationship("Scope", back_populates="audit_logs")
    user: Mapped["UserNew | None"] = relationship("UserNew")
    schema: Mapped["CurationSchema | None"] = relationship("CurationSchema")
    workflow_pair: Mapped["WorkflowPair | None"] = relationship("WorkflowPair")

    __table_args__ = (
        Index("idx_audit_log_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_change_type", "change_type"),
        Index("idx_audit_logs_user_action", "user_id", "change_type", "timestamp"),
        Index("idx_audit_logs_old_values", "old_values", postgresql_using="gin"),
        Index("idx_audit_logs_new_values", "new_values", postgresql_using="gin"),
    )


class SchemaSelection(Base):
    """User and institutional preferences for schema selection."""

    __tablename__ = "schema_selections"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    scope_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )

    # Nullable fields
    user_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="CASCADE")
    )
    institution: Mapped[str | None] = mapped_column(String(255))

    # Preferred schemas (nullable)
    preferred_workflow_pair_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("workflow_pairs.id")
    )
    preferred_precuration_schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )
    preferred_curation_schema_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("curation_schemas.id")
    )

    # Selection metadata
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["UserNew | None"] = relationship("UserNew")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="schema_selections")
    preferred_workflow_pair: Mapped["WorkflowPair | None"] = relationship(
        "WorkflowPair"
    )
    preferred_precuration_schema: Mapped["CurationSchema | None"] = relationship(
        "CurationSchema", foreign_keys=[preferred_precuration_schema_id]
    )
    preferred_curation_schema: Mapped["CurationSchema | None"] = relationship(
        "CurationSchema", foreign_keys=[preferred_curation_schema_id]
    )

    __table_args__ = (
        Index("idx_schema_selections_user_scope", "user_id", "scope_id"),
        Index("idx_schema_selections_institution_scope", "institution", "scope_id"),
    )


class SystemLog(Base):
    """Persistent log storage with request correlation and monthly partitioning."""

    __tablename__ = "system_logs"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Required fields
    timestamp: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    level: Mapped[str] = mapped_column(Text, index=True)
    logger: Mapped[str] = mapped_column(Text, index=True)
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(compatible_jsonb(), default={})

    # Request correlation (nullable)
    request_id: Mapped[str | None] = mapped_column(Text, index=True)

    # User context (nullable)
    user_id: Mapped[PyUUID | None] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL")
    )
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)

    # HTTP context (nullable)
    path: Mapped[str | None] = mapped_column(Text, index=True)
    method: Mapped[str | None] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    # Error context (nullable)
    error_type: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped["UserNew | None"] = relationship("UserNew")

    __table_args__ = (
        Index("idx_system_logs_level_timestamp", "level", timestamp.desc()),
        Index("idx_system_logs_context_gin", "context", postgresql_using="gin"),
    )


# ========================================
# CLINGEN SOP V11 MODELS
# ========================================


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


class ValidationCache(Base):
    """
    Cache for external validator results (HGNC, PubMed, HPO).
    Reduces API calls and improves performance.
    """

    __tablename__ = "validation_cache"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    validator_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'hgnc', 'pubmed', 'hpo'
    input_value: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # Gene symbol, PMID, HPO term
    validator_input_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )  # SHA256(validator_name + input_value)

    # Validation result
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'valid', 'invalid', 'error', 'not_found'
    validation_response: Mapped[dict[str, Any]] = mapped_column(
        compatible_jsonb(), nullable=False
    )

    # Suggestions for invalid inputs
    suggestions: Mapped[dict[str, Any] | None] = mapped_column(compatible_jsonb())

    # Error information
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(50))

    # Cache control
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_accessed_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_validation_cache_validator", "validator_name", "input_value"),
        Index("idx_validation_cache_valid", "validator_name", "is_valid"),
        Index(
            "idx_validation_cache_cleanup",
            "expires_at",
            postgresql_where="expires_at < NOW()",
        ),
    )
