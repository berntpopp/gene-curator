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
    Enum,
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
from app.models.model_enums import UserRoleNew

if TYPE_CHECKING:
    from app.models.curation import ActiveCuration, CurationNew, PrecurationNew, Review
    from app.models.genes import Gene, GeneScopeAssignment
    from app.models.schemas import CurationSchema, SchemaSelection, WorkflowPair
    from app.models.system import AuditLogNew


class SchemaMigration(Base):
    """Applied SQL migrations; written only by the migration owner."""

    __tablename__ = "schema_migrations"
    filename: Mapped[str] = mapped_column(Text, primary_key=True)
    applied_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Scope(Base):
    """Clinical specialties as first-class entities."""

    __tablename__ = "scopes"

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
    # 074 (#560): approvals need a signed-in person, not a token or MCP call
    approvals_require_session: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # 076 (#558): export evidence, scores and summary to non-members of a public scope
    export_evidence_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
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
    # 082 (#284): pairs the scope may use besides its default pair
    allowed_workflow_pairs: Mapped[list["WorkflowPair"]] = relationship(
        "WorkflowPair", secondary="scope_workflow_pairs", passive_deletes=True
    )

    @property
    def allowed_workflow_pair_ids(self) -> list[PyUUID]:
        return [pair.id for pair in self.allowed_workflow_pairs]


class UserNew(Base):
    """Enhanced users with scope assignments and scientific attribution."""

    __tablename__ = "users"

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
    expires_at: Mapped[dt | None] = mapped_column(
        DateTime(timezone=True)
    )  # Invitation expiry (GitHub-style)

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
