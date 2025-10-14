"""
Pytest configuration and shared fixtures for Gene Curator tests.

Provides database session fixtures with proper transaction isolation using
nested transactions (savepoints). This allows tests to call commit() freely
while maintaining complete isolation and automatic rollback.

Key Features:
- Nested transactions via SAVEPOINT
- commit() calls only commit the savepoint, not the outer transaction
- SET LOCAL variables persist across savepoints within the transaction
- Complete rollback after each test for isolation
- No test data pollution between tests
- Uses non-superuser role for RLS testing (bypasses RLS bypass privilege)
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Provide a database session with proper nested transaction support.

    This fixture creates a connection using a NON-SUPERUSER role to ensure
    RLS policies are properly enforced. The dev_user is a superuser with
    BYPASSRLS privilege, which causes RLS to be bypassed even with FORCE RLS.

    Benefits:
    1. Tests can call db.commit() freely - it only commits the savepoint
    2. SET LOCAL variables persist throughout the test (not cleared by commit)
    3. All changes are rolled back at the end of the test
    4. Complete test isolation with no data pollution
    5. RLS policies are properly enforced (non-superuser connection)

    Technical Details:
    - Uses test_rls_user (non-superuser, no BYPASSRLS privilege)
    - Outer transaction: Never committed, always rolled back
    - Nested transaction: Created via SAVEPOINT, can be committed/rolled back
    - commit() override: Commits savepoint and creates a new one
    - SET LOCAL scope: Persists within outer transaction across savepoints

    Yields:
        Session: SQLAlchemy database session with nested transaction support
    """
    # Create engine with non-superuser role for RLS testing
    # Replace dev_user with test_rls_user in the DATABASE_URL
    test_db_url = settings.DATABASE_URL.replace(
        "dev_user:dev_password",
        "test_rls_user:test_password"
    )

    test_engine = create_engine(test_db_url, echo=True)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)  # noqa: N806

    # Create a connection from the test engine
    connection = test_engine.connect()

    # Begin an outer transaction (never committed)
    transaction = connection.begin()

    # Bind the session to this connection
    session = TestSessionLocal(bind=connection)

    # Begin a nested transaction (SAVEPOINT)
    connection.begin_nested()

    # When the application code calls session.commit(), we want it to only
    # commit the savepoint, not the outer transaction. This keeps SET LOCAL
    # variables alive.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        """Automatically restart savepoint after each commit."""
        if transaction.nested and not transaction._parent.nested:
            # We're ending a savepoint - start a new one
            session.expire_all()
            connection.begin_nested()

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
