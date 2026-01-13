"""
Database configuration and session management.

Provides both synchronous and asynchronous database sessions.
Uses modern SQLAlchemy 2.0 patterns with full type safety.
"""

from collections.abc import Generator
from typing import Annotated, Any, ClassVar
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import String, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column

from app.core.config import settings

# Create synchronous database engine
engine = create_engine(
    settings.DATABASE_URL,
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


def init_db() -> None:
    """Initialize database by creating all tables."""
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete.")


def check_db_connection() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    try:
        from sqlalchemy import text

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            return row is not None and row[0] == 1
    except Exception as e:
        logger.error("Database connection check failed", error=e)
        return False
