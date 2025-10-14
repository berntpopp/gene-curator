"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.
"""

import enum
import uuid

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    institution = Column(String(255), index=True)
    is_public = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    default_workflow_pair_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_pairs.id")
    )

    # Configuration
    scope_config = Column(JSONB, default={})

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Relationships
    creator = relationship("UserNew", foreign_keys=[created_by])
    default_workflow_pair = relationship(
        "WorkflowPair", foreign_keys=[default_workflow_pair_id]
    )
    gene_assignments = relationship("GeneScopeAssignment", back_populates="scope")
    scope_memberships = relationship("ScopeMembership", back_populates="scope")
    precurations = relationship("PrecurationNew", back_populates="scope")
    curations = relationship("CurationNew", back_populates="scope")
    active_curations = relationship("ActiveCuration", back_populates="scope")


class UserNew(Base):
    """Enhanced users with scope assignments and scientific attribution."""

    __tablename__ = "users_new"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="viewer",
        index=True,
    )
    institution = Column(String(255), index=True)
    assigned_scopes = Column(ARRAY(UUID(as_uuid=True)), default=[])

    # Enhanced profile
    orcid_id = Column(String(50))
    expertise_areas = Column(ARRAY(Text), default=[])

    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    created_scopes = relationship("Scope", foreign_keys="[Scope.created_by]")
    created_schemas = relationship(
        "CurationSchema", foreign_keys="[CurationSchema.created_by]"
    )
    created_workflow_pairs = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.created_by]"
    )
    curator_assignments = relationship(
        "GeneScopeAssignment", foreign_keys="[GeneScopeAssignment.assigned_curator_id]"
    )
    created_genes = relationship("GeneNew", foreign_keys="[GeneNew.created_by]")
    created_precurations = relationship(
        "PrecurationNew", foreign_keys="[PrecurationNew.created_by]"
    )
    created_curations = relationship(
        "CurationNew", foreign_keys="[CurationNew.created_by]"
    )
    reviews_assigned = relationship("Review", foreign_keys="[Review.reviewer_id]")
    approved_curations = relationship(
        "CurationNew", foreign_keys="[CurationNew.approved_by]"
    )
    scope_memberships = relationship(
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role within scope (uses scope_role enum from database)
    role = Column(
        String(50), nullable=False, index=True
    )  # admin, curator, reviewer, viewer

    # Invitation workflow
    invited_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    invited_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at = Column(DateTime(timezone=True))  # NULL = pending invitation

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Team support (future feature for group-based permissions)
    team_id = Column(UUID(as_uuid=True))

    # Notes
    notes = Column(Text)

    # Metadata
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    scope = relationship("Scope", back_populates="scope_memberships")
    user = relationship(
        "UserNew", foreign_keys=[user_id], back_populates="scope_memberships"
    )
    inviter = relationship("UserNew", foreign_keys=[invited_by])

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    schema_type = Column(
        Enum(SchemaType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )

    # Complete schema definition
    field_definitions = Column(JSONB, nullable=False)
    validation_rules = Column(JSONB, nullable=False, default={})
    scoring_configuration = Column(JSONB)
    workflow_states = Column(JSONB, nullable=False)
    ui_configuration = Column(JSONB, nullable=False)

    # Inheritance support
    based_on_schema_id = Column(UUID(as_uuid=True), ForeignKey("curation_schemas.id"))

    # Metadata
    description = Column(Text)
    institution = Column(String(255), index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users_new.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)

    # Schema validation checksum
    schema_hash = Column(String(64), nullable=False)

    # Relationships
    creator = relationship("UserNew", foreign_keys=[created_by])
    based_on_schema = relationship("CurationSchema", remote_side=[id])
    precuration_workflow_pairs = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.precuration_schema_id]"
    )
    curation_workflow_pairs = relationship(
        "WorkflowPair", foreign_keys="[WorkflowPair.curation_schema_id]"
    )
    precurations = relationship("PrecurationNew", back_populates="precuration_schema")

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)

    precuration_schema_id = Column(
        UUID(as_uuid=True), ForeignKey("curation_schemas.id")
    )
    curation_schema_id = Column(UUID(as_uuid=True), ForeignKey("curation_schemas.id"))

    # How data flows between stages
    data_mapping = Column(JSONB, nullable=False, default={})

    # Workflow configuration
    workflow_config = Column(JSONB, default={})

    # Metadata
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users_new.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    creator = relationship("UserNew", foreign_keys=[created_by])
    precuration_schema = relationship(
        "CurationSchema", foreign_keys=[precuration_schema_id]
    )
    curation_schema = relationship("CurationSchema", foreign_keys=[curation_schema_id])
    scope_defaults = relationship(
        "Scope", foreign_keys="[Scope.default_workflow_pair_id]"
    )
    gene_assignments = relationship(
        "GeneScopeAssignment", back_populates="workflow_pair"
    )
    curations = relationship("CurationNew", back_populates="workflow_pair")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_workflow_pair_name_version"),
    )


class GeneNew(Base):
    """Enhanced genes table for scope assignment."""

    __tablename__ = "genes_new"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hgnc_id = Column(String(50), unique=True, nullable=False, index=True)
    approved_symbol = Column(String(100), nullable=False, index=True)
    previous_symbols = Column(ARRAY(Text))
    alias_symbols = Column(ARRAY(Text))
    chromosome = Column(String(10), index=True)
    location = Column(String(50))

    # Gene details (preserves current flexibility)
    details = Column(JSONB, default={})

    # Provenance tracking
    record_hash = Column(String(64), nullable=False, unique=True)
    previous_hash = Column(String(64))

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    updated_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Relationships
    creator = relationship("UserNew", foreign_keys=[created_by])
    updater = relationship("UserNew", foreign_keys=[updated_by])
    scope_assignments = relationship("GeneScopeAssignment", back_populates="gene")
    precurations = relationship("PrecurationNew", back_populates="gene")
    curations = relationship("CurationNew", back_populates="gene")
    active_curations = relationship("ActiveCuration", back_populates="gene")

    __table_args__ = (
        Index("idx_genes_new_details_gin", "details", postgresql_using="gin"),
    )


class GeneScopeAssignment(Base):
    """Many-to-many relationship between genes and clinical scopes."""

    __tablename__ = "gene_scope_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id = Column(
        UUID(as_uuid=True),
        ForeignKey("genes_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_curator_id = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL"), index=True
    )
    workflow_pair_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_pairs.id"), index=True
    )

    # Assignment details
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(String(20), default="normal")  # high, normal, low
    due_date = Column(Date)
    assignment_notes = Column(Text)

    # Metadata
    assigned_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    gene = relationship("GeneNew", back_populates="scope_assignments")
    scope = relationship("Scope", back_populates="gene_assignments")
    assigned_curator = relationship("UserNew", foreign_keys=[assigned_curator_id])
    assigner = relationship("UserNew", foreign_keys=[assigned_by])
    workflow_pair = relationship("WorkflowPair", back_populates="gene_assignments")

    __table_args__ = (
        UniqueConstraint("gene_id", "scope_id", name="uq_gene_scope_assignment"),
    )


# ========================================
# MULTI-STAGE WORKFLOW MODELS
# ========================================


class PrecurationNew(Base):
    """Multiple precurations per gene-scope with schema-driven fields."""

    __tablename__ = "precurations_new"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id = Column(
        UUID(as_uuid=True),
        ForeignKey("genes_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    precuration_schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curation_schemas.id"),
        nullable=False,
        index=True,
    )

    # Status and workflow
    status = Column(
        Enum(CurationStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="draft",
        index=True,
    )
    workflow_stage = Column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="precuration",
        index=True,
    )
    is_draft = Column(Boolean, default=True, index=True)

    # Evidence data (schema-agnostic)
    evidence_data = Column(JSONB, nullable=False, default={})

    # Computed results from schema
    computed_scores = Column(JSONB, default={})
    computed_fields = Column(JSONB, default={})

    # Auto-save functionality
    auto_saved_at = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    updated_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Provenance tracking
    version_number = Column(Integer, default=1)
    record_hash = Column(String(64), unique=True)
    previous_hash = Column(String(64))

    # Relationships
    gene = relationship("GeneNew", back_populates="precurations")
    scope = relationship("Scope", back_populates="precurations")
    precuration_schema = relationship("CurationSchema", back_populates="precurations")
    creator = relationship("UserNew", foreign_keys=[created_by])
    updater = relationship("UserNew", foreign_keys=[updated_by])
    curations = relationship("CurationNew", back_populates="precuration")

    __table_args__ = (
        Index("idx_precurations_new_gene_scope", "gene_id", "scope_id"),
        Index(
            "idx_precurations_new_evidence_gin", "evidence_data", postgresql_using="gin"
        ),
    )


class CurationNew(Base):
    """Multiple curations per gene-scope with scoring engine integration."""

    __tablename__ = "curations_new"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id = Column(
        UUID(as_uuid=True),
        ForeignKey("genes_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    precuration_id = Column(
        UUID(as_uuid=True), ForeignKey("precurations_new.id", ondelete="SET NULL")
    )
    workflow_pair_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_pairs.id"), nullable=False, index=True
    )

    # Status and workflow
    status = Column(
        Enum(CurationStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="draft",
        index=True,
    )
    workflow_stage = Column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="curation",
        index=True,
    )
    is_draft = Column(Boolean, default=True, index=True)

    # Evidence data (schema-agnostic)
    evidence_data = Column(JSONB, nullable=False, default={})

    # Computed results (updated by scoring engines)
    computed_scores = Column(JSONB, default={})
    computed_verdict = Column(String(100), index=True)
    computed_summary = Column(Text)
    computed_fields = Column(JSONB, default={})

    # Auto-save functionality
    auto_saved_at = Column(DateTime(timezone=True))

    # Submission and approval
    submitted_at = Column(DateTime(timezone=True))
    submitted_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    approved_at = Column(DateTime(timezone=True), index=True)
    approved_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    updated_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Provenance tracking
    version_number = Column(Integer, default=1)
    record_hash = Column(String(64), unique=True)
    previous_hash = Column(String(64))

    # Relationships
    gene = relationship("GeneNew", back_populates="curations")
    scope = relationship("Scope", back_populates="curations")
    precuration = relationship("PrecurationNew", back_populates="curations")
    workflow_pair = relationship("WorkflowPair", back_populates="curations")
    creator = relationship("UserNew", foreign_keys=[created_by])
    updater = relationship("UserNew", foreign_keys=[updated_by])
    submitter = relationship("UserNew", foreign_keys=[submitted_by])
    approver = relationship("UserNew", foreign_keys=[approved_by])
    reviews = relationship("Review", back_populates="curation")
    active_curation = relationship(
        "ActiveCuration",
        back_populates="curation",
        foreign_keys="[ActiveCuration.curation_id]",
    )

    __table_args__ = (
        Index("idx_curations_new_gene_scope", "gene_id", "scope_id"),
        Index(
            "idx_curations_new_evidence_gin", "evidence_data", postgresql_using="gin"
        ),
        Index(
            "idx_curations_new_scores_gin", "computed_scores", postgresql_using="gin"
        ),
    )


class Review(Base):
    """4-eyes principle implementation with mandatory independent review."""

    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    curation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curations_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_new.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(ReviewStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="pending",
        index=True,
    )

    # Review content
    comments = Column(Text)
    feedback_data = Column(JSONB, default={})
    recommendation = Column(String(50))  # approve, reject, needs_revision

    # Review actions
    reviewed_at = Column(DateTime(timezone=True), index=True)

    # Metadata
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    assigned_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    due_date = Column(Date)

    # Version tracking for iterative reviews
    review_round = Column(Integer, default=1)

    # Relationships
    curation = relationship("CurationNew", back_populates="reviews")
    reviewer = relationship("UserNew", foreign_keys=[reviewer_id])
    assigner = relationship("UserNew", foreign_keys=[assigned_by])


class ActiveCuration(Base):
    """One active curation per gene-scope with archive management."""

    __tablename__ = "active_curations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gene_id = Column(
        UUID(as_uuid=True),
        ForeignKey("genes_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    curation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curations_new.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Activation details
    activated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    activated_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )

    # Previous active curation (for audit trail)
    replaced_curation_id = Column(
        UUID(as_uuid=True), ForeignKey("curations_new.id", ondelete="SET NULL")
    )

    # Archive information
    archived_at = Column(DateTime(timezone=True), index=True)
    archived_by = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    archive_reason = Column(Text)

    # Relationships
    gene = relationship("GeneNew", back_populates="active_curations")
    scope = relationship("Scope", back_populates="active_curations")
    curation = relationship(
        "CurationNew", back_populates="active_curation", foreign_keys=[curation_id]
    )
    activator = relationship("UserNew", foreign_keys=[activated_by])
    archiver = relationship("UserNew", foreign_keys=[archived_by])
    replaced_curation = relationship("CurationNew", foreign_keys=[replaced_curation_id])

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

    __tablename__ = "audit_log_new"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    entity_type = Column(Text, nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id"))
    operation = Column(Text, nullable=False, index=True)
    changes = Column(JSONB)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Additional context
    ip_address = Column(INET)
    user_agent = Column(Text)
    session_id = Column(UUID(as_uuid=True))

    # Multi-stage workflow context
    workflow_stage = Column(
        Enum(WorkflowStage, values_callable=lambda obj: [e.value for e in obj]),
        index=True,
    )
    review_action = Column(
        Enum(ReviewStatus, values_callable=lambda obj: [e.value for e in obj])
    )
    previous_status = Column(Text)
    new_status = Column(Text)

    # Schema context
    schema_id = Column(UUID(as_uuid=True), ForeignKey("curation_schemas.id"))
    workflow_pair_id = Column(UUID(as_uuid=True), ForeignKey("workflow_pairs.id"))

    # Relationships
    scope = relationship("Scope")
    user = relationship("UserNew")
    schema = relationship("CurationSchema")
    workflow_pair = relationship("WorkflowPair")

    __table_args__ = (Index("idx_audit_log_new_entity", "entity_type", "entity_id"),)


class SchemaSelection(Base):
    """User and institutional preferences for schema selection."""

    __tablename__ = "schema_selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="CASCADE"))
    scope_id = Column(UUID(as_uuid=True), ForeignKey("scopes.id"), nullable=False)
    institution = Column(String(255))

    # Preferred schemas
    preferred_workflow_pair_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_pairs.id")
    )
    preferred_precuration_schema_id = Column(
        UUID(as_uuid=True), ForeignKey("curation_schemas.id")
    )
    preferred_curation_schema_id = Column(
        UUID(as_uuid=True), ForeignKey("curation_schemas.id")
    )

    # Selection metadata
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("UserNew")
    scope = relationship("Scope")
    preferred_workflow_pair = relationship("WorkflowPair")
    preferred_precuration_schema = relationship(
        "CurationSchema", foreign_keys=[preferred_precuration_schema_id]
    )
    preferred_curation_schema = relationship(
        "CurationSchema", foreign_keys=[preferred_curation_schema_id]
    )

    __table_args__ = (
        Index("idx_schema_selections_user_scope", "user_id", "scope_id"),
        Index("idx_schema_selections_institution_scope", "institution", "scope_id"),
    )


class SystemLog(Base):
    """Persistent log storage with request correlation and monthly partitioning."""

    __tablename__ = "system_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    level = Column(Text, nullable=False, index=True)
    logger = Column(Text, nullable=False, index=True)
    message = Column(Text, nullable=False)
    context = Column(JSONB, default={}, nullable=False)

    # Request correlation
    request_id = Column(Text, index=True)

    # User context
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users_new.id", ondelete="SET NULL")
    )
    ip_address = Column(Text)
    user_agent = Column(Text)

    # HTTP context
    path = Column(Text, index=True)
    method = Column(Text)
    status_code = Column(Integer)
    duration_ms = Column(BigInteger)

    # Error context
    error_type = Column(Text)
    error_message = Column(Text)
    stack_trace = Column(Text)

    # Relationships
    user = relationship("UserNew")

    __table_args__ = (
        Index("idx_system_logs_level_timestamp", "level", timestamp.desc()),
        Index("idx_system_logs_context_gin", "context", postgresql_using="gin"),
    )
