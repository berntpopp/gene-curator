"""
Cross-database compatible types for SQLAlchemy.

Provides types that work across both PostgreSQL (production) and SQLite (testing).
Uses SQLAlchemy's TypeDecorator pattern with dialect-specific implementations.

Solution based on SQLAlchemy best practices:
- https://docs.sqlalchemy.org/en/20/core/custom_types.html
- https://docs.sqlalchemy.org/en/20/core/type_api.html#sqlalchemy.types.TypeEngine.with_variant
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import (
    ARRAY as PG_ARRAY,
    JSONB as PG_JSONB,
    UUID as PG_UUID,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.types import CHAR, TypeDecorator, TypeEngine


class JSONEncodedList(TypeDecorator[list[Any]]):
    """
    Stores a Python list as a JSON-encoded string.
    Used as SQLite fallback for PostgreSQL ARRAY type.

    Example:
        ["item1", "item2"] <-> '["item1", "item2"]'
    """

    impl = Text
    cache_ok = True

    def process_bind_param(
        self, value: list[Any] | None, dialect: Dialect
    ) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> list[Any] | None:
        if value is None:
            return None
        return list(json.loads(value))


class UUIDEncodedList(TypeDecorator[list[UUID]]):
    """
    Stores a Python list of UUIDs as a JSON-encoded string.
    Used as SQLite fallback for PostgreSQL ARRAY(UUID) type.

    Example:
        [UUID(...), UUID(...)] <-> '["uuid-string-1", "uuid-string-2"]'
    """

    impl = Text
    cache_ok = True

    def process_bind_param(
        self, value: list[UUID] | None, dialect: Dialect
    ) -> str | None:
        if value is None:
            return None
        return json.dumps([str(u) for u in value])

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> list[UUID] | None:
        if value is None:
            return None
        return [UUID(u) for u in json.loads(value)]


class CompatibleUUID(TypeDecorator[UUID]):
    """
    Platform-independent UUID type.
    Uses CHAR(36) for SQLite, native UUID for PostgreSQL.

    Based on SQLAlchemy backend-agnostic GUID recipe.
    """

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(
        self, value: UUID | None, dialect: Dialect
    ) -> str | UUID | None:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        return UUID(value)


def compatible_array(item_type: type) -> TypeEngine[Any]:
    """
    Factory function for cross-database compatible array types.

    Uses PostgreSQL's native ARRAY type in production, falls back to
    JSON-encoded storage in SQLite for testing.

    Args:
        item_type: The type of items in the array (e.g., Text, UUID)

    Returns:
        A type that works across both databases.

    Example:
        # In model definition:
        tags: Mapped[list[str]] = mapped_column(compatible_array(Text))
        scope_ids: Mapped[list[UUID]] = mapped_column(compatible_array_uuid())
    """
    # For UUID arrays, use the specialized type
    if item_type == PG_UUID or str(item_type) == "UUID":
        pg_type = PG_ARRAY(PG_UUID(as_uuid=True))
        return pg_type.with_variant(UUIDEncodedList(), "sqlite")

    # For other types, use JSON-encoded list in SQLite
    pg_type = PG_ARRAY(item_type)
    return pg_type.with_variant(JSONEncodedList(), "sqlite")


def compatible_array_uuid() -> TypeEngine[Any]:
    """
    Shorthand for compatible_array(UUID).
    Creates a cross-database compatible array of UUIDs.
    """
    pg_type = PG_ARRAY(PG_UUID(as_uuid=True))
    return pg_type.with_variant(UUIDEncodedList(), "sqlite")


def compatible_array_text() -> TypeEngine[Any]:
    """
    Shorthand for compatible_array(Text).
    Creates a cross-database compatible array of text strings.
    """
    pg_type = PG_ARRAY(Text)
    return pg_type.with_variant(JSONEncodedList(), "sqlite")


def compatible_jsonb() -> TypeEngine[Any]:
    """
    Cross-database compatible JSONB type.
    Uses PostgreSQL's native JSONB in production, falls back to JSON in SQLite.

    JSONB offers better performance and indexing in PostgreSQL, while
    SQLite's JSON type provides equivalent functionality for testing.
    """
    return PG_JSONB().with_variant(JSON(), "sqlite")


def compatible_uuid() -> CompatibleUUID:
    """
    Cross-database compatible UUID type.
    Uses PostgreSQL's native UUID in production, falls back to CHAR(36) in SQLite.

    Returns:
        CompatibleUUID instance that handles both dialects.

    Example:
        # In model definition:
        id: Mapped[PyUUID] = mapped_column(compatible_uuid(), primary_key=True)
        user_id: Mapped[PyUUID] = mapped_column(
            compatible_uuid(), ForeignKey("users.id")
        )
    """
    return CompatibleUUID()


def compatible_inet() -> TypeEngine[Any]:
    """
    Cross-database compatible INET type.
    Uses PostgreSQL's native INET in production, falls back to String in SQLite.

    INET is used for storing IP addresses (IPv4 or IPv6).
    SQLite stores as plain string for testing.
    """
    from sqlalchemy import String
    from sqlalchemy.dialects.postgresql import INET as PG_INET

    return PG_INET().with_variant(String(45), "sqlite")  # 45 chars for IPv6
