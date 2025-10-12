"""
Database configuration and session management.

Provides both synchronous and asynchronous database sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create synchronous database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and settings.LOG_LEVEL.lower() == "debug",
)

# Create synchronous session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

# Create declarative base
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    """
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database error", error=e)
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database by creating all tables."""
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete.")


def check_db_connection():
    """Check database connection health."""
    # Lazy import to avoid circular dependency
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    try:
        from sqlalchemy import text

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.fetchone()[0] == 1
    except Exception as e:
        logger.error("Database connection check failed", error=e)
        return False
