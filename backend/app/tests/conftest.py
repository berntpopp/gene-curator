"""
Pytest configuration and shared fixtures for Gene Curator tests.

Provides database session fixtures with proper transaction isolation using
SQLAlchemy 2.0's join_transaction_mode="create_savepoint" pattern. This allows
tests to call commit() freely while maintaining complete isolation and automatic
rollback. FORCE ROW LEVEL SECURITY on tables ensures RLS policies apply even to
superuser connections.

Key Features (SQLAlchemy 2.0 Pattern):
- Automatic savepoint management via join_transaction_mode="create_savepoint"
- commit() calls only commit the savepoint, not the outer transaction
- SET LOCAL variables persist across savepoints within the transaction
- Complete rollback after each test for isolation
- No test data pollution between tests
- RLS policies enforced via FORCE ROW LEVEL SECURITY
"""

from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Provide a database session with proper nested transaction support.

    Uses SQLAlchemy 2.0's join_transaction_mode="create_savepoint" pattern for
    clean transaction management in tests. Uses test_user (non-BYPASSRLS) to
    ensure RLS policies are properly enforced.

    Benefits:
    1. Tests can call db.commit() freely - it only commits the savepoint
    2. SET LOCAL variables persist throughout the test (not cleared by commit)
    3. All changes are rolled back at the end of the test
    4. Complete test isolation with no data pollution
    5. RLS policies properly enforced (test_user lacks BYPASSRLS privilege)

    Technical Details (SQLAlchemy 2.0 Pattern):
    - Uses test_user (no BYPASSRLS privilege)
    - FORCE RLS + non-BYPASSRLS user = RLS fully enforced
    - Outer transaction: Never committed, always rolled back
    - join_transaction_mode="create_savepoint": Automatic savepoint management
    - Session.commit(): Only commits savepoint, not outer transaction
    - SET LOCAL scope: Persists within outer transaction across savepoints

    Reference:
        https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
        Section: "Joining a Session into an External Transaction"

    Yields:
        Session: SQLAlchemy database session with nested transaction support
    """
    # Create engine using test_user (no BYPASSRLS privilege)
    # This ensures RLS policies are properly enforced in tests
    from sqlalchemy import create_engine

    test_db_url = settings.DATABASE_URL.replace(
        "dev_user:dev_password", "test_user:test_password"
    )
    test_engine = create_engine(test_db_url, pool_pre_ping=True)

    # Create a connection from the test engine
    connection = test_engine.connect()

    # Begin an outer transaction (never committed, always rolled back)
    transaction = connection.begin()

    # Create session bound to this connection with create_savepoint mode
    # This automatically manages savepoints on commit/rollback
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        # Clean up
        session.close()

        # Rollback the outer transaction (undoes all changes)
        transaction.rollback()

        # Close the connection
        connection.close()

        # Dispose of the test engine
        test_engine.dispose()


@pytest.fixture
def db_session(db: Session) -> Session:
    """
    Alias for db fixture for compatibility.

    Some tests may use db_session instead of db.
    """
    return db


def set_test_user_context(db: Session, user_id: str) -> None:
    """
    Set RLS context for test user using session-level SET (not LOCAL).

    In test fixtures with savepoints, SET LOCAL can be unreliable across
    savepoint boundaries. Using session-level SET ensures the context persists
    throughout the test transaction.

    This function sets the app.current_user_id session variable that is used by RLS
    policies to identify the current user. Must be called before creating any objects
    that are protected by RLS policies.

    Args:
        db: Database session
        user_id: UUID of the user (as string)

    Example:
        from app.tests.conftest import set_test_user_context
        from uuid import UUID

        # In test fixture or test function:
        admin = UserNew(id=uuid4(), ...)
        db.add(admin)
        db.commit()

        # Set RLS context before creating scopes
        set_test_user_context(db, str(admin.id))

        # Now scope creation will work with RLS
        scope = scope_crud.create_scope(db, scope_data, admin.id)
    """
    from sqlalchemy import text

    # Use SET (session-level) instead of SET LOCAL for tests
    # This persists across savepoint boundaries
    db.execute(text(f"SET app.current_user_id = '{user_id}'"))
