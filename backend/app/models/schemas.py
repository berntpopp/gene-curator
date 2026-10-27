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
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import (
    compatible_jsonb,
    compatible_uuid,
)
from app.models.model_enums import SchemaType

if TYPE_CHECKING:
    from app.models.curation import CurationNew, PrecurationNew
    from app.models.genes import GeneScopeAssignment
    from app.models.identity import Scope, UserNew


class CurationSchema(Base):
    """Repository of methodology definitions (ClinGen, GenCC, custom)."""

    __tablename__ = "curation_schemas"

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
    use_dynamic_form: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="When true, use DynamicForm instead of legacy ClinGen form",
    )

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
    # create_scope uses it when no pair is given; at most one (062)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

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
        Index(
            "uq_workflow_pairs_single_default",
            text("(true)"),
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default"),
        ),
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
