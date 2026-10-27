"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.

Modern SQLAlchemy 2.0 patterns with full type safety.
"""

import enum


class UserRoleNew(str, enum.Enum):
    """Application-level roles (admin/user); scope roles live in scope_memberships."""

    ADMIN = "admin"
    USER = "user"


class WorkflowStage(str, enum.Enum):
    ENTRY = "entry"
    PRECURATION = "precuration"
    CURATION = "curation"
    REVIEW = "review"
    ACTIVE = "active"
    ARCHIVED = "archived"  # terminal: superseded or deleted


class NotificationType(str, enum.Enum):
    REVIEW_ASSIGNED = "review_assigned"
    REVIEW_COMPLETED = "review_completed"
    REVISION_REQUESTED = "revision_requested"
    CURATION_APPROVED = "curation_approved"
    CURATION_REJECTED = "curation_rejected"
    SCOPE_MEMBERSHIP_ADDED = "scope_membership_added"


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


# Core schema-agnostic models
