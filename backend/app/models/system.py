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
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.db_types import (
    compatible_inet,
    compatible_jsonb,
    compatible_uuid,
)
from app.models.model_enums import NotificationType, ReviewStatus, WorkflowStage

if TYPE_CHECKING:
    from app.models.identity import Scope, UserNew
    from app.models.schemas import CurationSchema, WorkflowPair


class AuditLogNew(Base):
    """Enhanced audit log for multi-stage workflow with scope context."""

    __tablename__ = "audit_log"

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


# CLINGEN SOP V11 MODELS


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


# PUBLICATION CACHE


class NotificationNew(Base):
    """User notifications for workflow events."""

    __tablename__ = "notifications"

    # Primary key
    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )

    # Recipient
    user_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Notification content
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["UserNew"] = relationship("UserNew", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_notifications_user_unread", "user_id", "is_read"),
        Index("idx_notifications_created", "created_at"),
    )
    # No INSERT..RETURNING: RLS would require the sender to read the recipient's row
    __mapper_args__ = {"eager_defaults": False}  # noqa: RUF012
