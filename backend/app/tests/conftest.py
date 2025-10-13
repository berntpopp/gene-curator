"""
Pytest configuration and shared fixtures for Gene Curator tests.

Provides database session fixtures and common test utilities.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Provide a database session for tests.

    Creates a fresh database session for each test. Tests can commit
    within the session, but should use unique identifiers to avoid
    conflicts between tests.

    Note: This fixture does NOT automatically rollback changes.
    Tests should use unique email addresses and names to avoid conflicts.

    Yields:
        Session: SQLAlchemy database session
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session(db: Session) -> Session:
    """
    Alias for db fixture for compatibility.

    Some tests may use db_session instead of db.
    """
    return db
