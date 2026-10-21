"""
Database configuration and session management.

Provides both synchronous and asynchronous database sessions.
Uses modern SQLAlchemy 2.0 patterns with full type safety.
"""

from collections.abc import Generator
from typing import Annotated, Any, ClassVar
from uuid import UUID as PyUUID  # noqa: N811

from fastapi import HTTPException, status
from sqlalchemy import Connection, String, create_engine, event, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction, mapped_column

from app.core.config import settings

# Create synchronous database engine
# SQLAlchemy 2.1 defaults postgresql:// to psycopg 3, whose typed parameters break the
# enum columns mapped as strings; stay on psycopg2 explicitly.
engine = create_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and settings.LOG_LEVEL.lower() == "debug",
)

# Create asynchronous database engine
# Convert postgresql:// to postgresql+asyncpg://
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and settings.LOG_LEVEL.lower() == "debug",
)

# Create asynchronous session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# Row-level security context
# ============================================================================

RLS_USER_KEY = "rls_user_id"


def apply_rls_user(connection: Connection, user_id: str) -> None:
    """Set app.current_user_id for the current transaction only (set_config(..., true)).

    Transaction-local, so a pooled connection never carries one request's user into
    the next; `_reapply_rls_user` restores it after every commit within a session.
    """
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": user_id},
        )


@event.listens_for(Session, "after_begin")
def _reapply_rls_user(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    user_id = session.info.get(RLS_USER_KEY)
    if user_id:
        apply_rls_user(connection, user_id)


# ============================================================================
# Modern SQLAlchemy 2.0 Declarative Base
# ============================================================================

# Custom type annotations for common column patterns
# These provide reusable, type-safe column definitions
uuid_pk = Annotated[PyUUID, mapped_column(UUID(as_uuid=True), primary_key=True)]
str_50 = Annotated[str, mapped_column(String(50))]
str_100 = Annotated[str, mapped_column(String(100))]
str_255 = Annotated[str, mapped_column(String(255))]
str_500 = Annotated[str, mapped_column(String(500))]


class Base(DeclarativeBase):
    """
    Modern SQLAlchemy 2.0 declarative base.

    Provides:
    - Full type safety with mypy through Mapped[] annotations
    - Custom type annotation mappings for common patterns
    - Shared metadata configuration across all models

    Benefits over legacy declarative_base():
    - Better IDE autocomplete and type inference
    - Compile-time type checking with mypy
    - More explicit and maintainable model definitions
    """

    # Global type mappings (fallback when no annotation provided)
    # These apply when using Mapped[type] without explicit column definition
    type_annotation_map: ClassVar[dict[type, Any]] = {
        str: String(255),  # Default string length for unspecified str columns
        PyUUID: UUID(as_uuid=True),  # Default UUID configuration
    }


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session (modern SQLAlchemy 2.0 pattern).

    Yields a database session using context manager pattern.
    Automatically commits on success and rolls back on exceptions.
    Session is automatically closed after use.

    Benefits:
    - Context manager ensures proper cleanup
    - No need for explicit close() call
    - Cleaner error handling

    Yields:
        Session: SQLAlchemy database session
    """
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception as e:
            # HTTPExceptions (401/403/400...) are API outcomes, not database errors
            if not isinstance(e, HTTPException):
                logger.error("Database error", error=e)
            session.rollback()
            raise


async def get_async_db() -> AsyncSession:  # type: ignore[misc]
    """
    Async dependency function to get database session.

    Yields an async database session using context manager pattern.
    Automatically commits on success and rolls back on exceptions.
    Session is automatically closed after use.

    This is the async equivalent of get_db() for use in async endpoints.

    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error("Async database error", error=e)
            await session.rollback()
            raise


def raise_if_rls_denied(error: Exception, detail: str) -> None:
    """Turn an RLS denial into 403: an UPDATE filtered to zero rows (StaleDataError) or
    insufficient_privilege (42501, a WITH CHECK or guard trigger). Other errors fall through."""
    if getattr(getattr(error, "orig", None), "pgcode", "42501") == "42501":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=detail
        ) from None
