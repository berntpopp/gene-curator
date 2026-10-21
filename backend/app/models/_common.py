"""
SQLAlchemy models for schema-agnostic Gene Curator architecture.
Supports scope-based organization, multi-stage workflow, and pluggable methodologies.

Modern SQLAlchemy 2.0 patterns with full type safety.
"""

from typing import Any

from sqlalchemy import (
    ForeignKey,
)
from sqlalchemy.orm import mapped_column

from app.core.db_types import (
    compatible_uuid,
)


def _user_fk() -> Any:
    """Nullable audit FK to users (created_by/updated_by)."""
    return mapped_column(compatible_uuid(), ForeignKey("users.id", ondelete="SET NULL"))
