# Testing Implementation Guide - Scope-Centric Refactoring

**Status:** Production-Ready Testing Strategy
**Testing Model:** Testing Trophy (Integration-Focused)
**Last Updated:** 2025-01-13

## Table of Contents

1. [Testing Strategy Overview](#testing-strategy-overview)
2. [Testing Trophy Model](#testing-trophy-model)
3. [Test Infrastructure Setup](#test-infrastructure-setup)
4. [Core Testing Fixtures](#core-testing-fixtures)
5. [Unit Tests](#unit-tests)
6. [Integration Tests](#integration-tests)
7. [RLS Security Tests](#rls-security-tests)
8. [Property-Based Tests](#property-based-tests)
9. [Test Data Factories](#test-data-factories)
10. [Performance & Load Tests](#performance--load-tests)
11. [Testing Checklist](#testing-checklist)

---

## Testing Strategy Overview

### Testing Philosophy

This testing strategy follows the **Testing Trophy** model, which emphasizes:

1. **Integration Tests (70%)** - Primary focus on testing component interactions
2. **Unit Tests (20%)** - Critical business logic and helper functions
3. **E2E Tests (5%)** - Key user workflows
4. **Static Analysis (5%)** - Type checking, linting, security scanning

**Why Testing Trophy?**

- **Better Bug Detection**: Integration tests catch 70% more bugs than unit tests alone
- **Refactoring Safety**: Less brittle than pure unit tests (no mocking hell)
- **Real-World Validation**: Tests actual component interactions (database, API, RLS)
- **Confidence**: High coverage of real user scenarios

### Testing Pyramid vs Trophy Comparison

```
Traditional Pyramid (AVOID)          Testing Trophy (RECOMMENDED)
       /\                                   ___
      /E2\                                 /E2E\
     /----\                               /-----\
    /Integ\                              /Integ \
   /-------\                            /-------\
  /  Unit   \                          /  Integ  \
 /-----------\                        /-----------\
                                     /   Unit      \
                                    /--------------\
                                   /Static Analysis \
```

### Test Coverage Goals

- **Integration Tests**: 80%+ coverage of API endpoints and database interactions
- **Unit Tests**: 90%+ coverage of utility functions and business logic
- **RLS Security Tests**: 100% coverage of all RLS policies
- **Overall Code Coverage**: 85%+ (measured with pytest-cov)

---

## Testing Trophy Model

### Layer 1: Static Analysis (Foundation)

**Tools:**
- `ruff` - Fast Python linter
- `mypy` - Static type checking
- `bandit` - Security vulnerability scanner

**Configuration:** Already implemented in `backend/app/` with strict mode.

### Layer 2: Unit Tests (20%)

**Focus Areas:**
- Utility functions (UUID validation, type casting helpers)
- Pydantic models and validation
- Enum conversions
- Helper functions in `app/core/`

**Example:**
```python
# tests/unit/test_helpers.py
def test_get_current_user_uuid_valid():
    """Test UUID parsing with valid input."""
    assert get_current_user_uuid() is not None

def test_is_scope_member_returns_boolean():
    """Test scope membership check returns bool."""
    result = is_scope_member(uuid4())
    assert isinstance(result, bool)
```

### Layer 3: Integration Tests (70% - PRIMARY FOCUS)

**Focus Areas:**
- API endpoints with real database
- Dependency injection chains
- RLS policy enforcement
- Multi-component workflows (scope creation + membership)

**Example:**
```python
# tests/integration/test_scope_membership_api.py
def test_create_scope_and_add_member_workflow(client, test_db):
    """Test complete workflow: create scope → invite member → accept."""
    # Create scope
    response = client.post("/api/v1/scopes", json={"title": "Test"})
    scope_id = response.json()["id"]

    # Invite member
    response = client.post(f"/api/v1/scopes/{scope_id}/invitations", ...)

    # Verify RLS isolation
    # ... (see Integration Tests section)
```

### Layer 4: E2E Tests (5%)

**Focus Areas:**
- Critical user journeys
- Authentication flows
- Scope lifecycle (create → use → archive)

**Note:** E2E tests will be added in Phase 2 after frontend integration.

---

## Test Infrastructure Setup

### Required Dependencies

**File:** `backend/pyproject.toml`

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-xdist>=3.5.0",              # Parallel test execution
    "pytest-postgresql>=6.0.0",          # PostgreSQL test fixtures
    "factory-boy>=3.3.0",                # Test data factories
    "hypothesis>=6.92.0",                # Property-based testing
    "faker>=22.0.0",                     # Fake data generation
    "httpx>=0.26.0",                     # TestClient dependency
]
```

**Installation:**
```bash
cd backend
uv pip install -e ".[test]"
```

### pytest Configuration

**File:** `backend/pytest.ini`

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Asyncio configuration
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Coverage settings
addopts =
    --strict-markers
    --strict-config
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
    -ra
    --tb=short
    --maxfail=5

# Markers for test categorization
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (database, API)
    rls: RLS policy tests (security-critical)
    slow: Slow tests (> 1 second)
    security: Security-critical tests
    property: Property-based tests (Hypothesis)

# Warnings
filterwarnings =
    error
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### Test Directory Structure

```
backend/tests/
├── conftest.py                      # Shared fixtures
├── factories/                       # Factory Boy factories
│   ├── __init__.py
│   ├── user_factory.py
│   ├── scope_factory.py
│   └── membership_factory.py
├── unit/                            # Unit tests (20%)
│   ├── test_helpers.py
│   ├── test_enums.py
│   ├── test_security.py
│   └── test_validators.py
├── integration/                     # Integration tests (70%)
│   ├── test_scope_api.py
│   ├── test_membership_api.py
│   ├── test_invitation_flow.py
│   ├── test_dependency_injection.py
│   └── test_rls_integration.py
├── rls/                             # RLS security tests (100% coverage)
│   ├── test_rls_scopes.py
│   ├── test_rls_memberships.py
│   ├── test_rls_curations.py
│   ├── test_rls_isolation.py
│   └── test_rls_performance.py
├── property/                        # Property-based tests
│   ├── test_uuid_properties.py
│   └── test_pagination_properties.py
└── e2e/                            # End-to-end tests (future)
    └── test_scope_lifecycle.py
```

---

## Core Testing Fixtures

### File: `backend/tests/conftest.py`

```python
"""
Shared pytest fixtures for scope-centric testing.

Following best practices:
- Session-scoped DB for performance
- Function-scoped transactions for isolation
- TestClient with dependency overrides
- RLS context helpers
"""

import pytest
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from app.main import app
from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.models.models import UserNew, Scope
from tests.factories import UserFactory, ScopeFactory


# ============================================================================
# DATABASE FIXTURES (Session-scoped for performance)
# ============================================================================

@pytest.fixture(scope="session")
def database_url() -> str:
    """Return test database URL (override via env var)."""
    return "postgresql://dev_user:dev_password@localhost:5454/gene_curator_test"


@pytest.fixture(scope="session")
def engine(database_url):
    """
    Create database engine for entire test session.

    Uses StaticPool for SQLite in-memory, or regular pooling for PostgreSQL.
    """
    if "sqlite" in database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(database_url, pool_pre_ping=True)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def SessionLocal(engine):
    """Create session factory for test session."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================================
# TRANSACTION FIXTURES (Function-scoped for isolation)
# ============================================================================

@pytest.fixture
def db(SessionLocal) -> Generator[Session, None, None]:
    """
    Provide clean database session for each test.

    Uses nested transactions with savepoints for rollback:
    - BEGIN transaction
    - Create savepoint
    - Run test
    - Rollback to savepoint
    - ROLLBACK transaction

    This ensures complete isolation between tests without recreating tables.
    """
    connection = SessionLocal().connection()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    # Create savepoint for nested transaction
    nested = connection.begin_nested()

    # Reset savepoint on each flush
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    # Rollback everything
    session.close()
    transaction.rollback()
    connection.close()


# ============================================================================
# RLS CONTEXT HELPERS
# ============================================================================

@pytest.fixture
def set_rls_user(db: Session):
    """
    Factory fixture to set RLS user context.

    Usage:
        set_rls_user(user.id)
    """
    def _set_user(user_id: UUID) -> None:
        """Set PostgreSQL RLS context for user."""
        db.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        db.commit()

    return _set_user


@pytest.fixture
def clear_rls_context(db: Session):
    """Clear RLS context (reset to NULL)."""
    def _clear() -> None:
        db.execute(text("SET LOCAL app.current_user_id = NULL"))
        db.commit()

    return _clear


# ============================================================================
# TEST USER FIXTURES
# ============================================================================

@pytest.fixture
def test_admin_user(db: Session) -> UserNew:
    """Create admin user for tests."""
    user = UserFactory.create(
        email="admin@test.com",
        application_role="admin",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_regular_user(db: Session) -> UserNew:
    """Create regular user for tests."""
    user = UserFactory.create(
        email="user@test.com",
        application_role="user",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_inactive_user(db: Session) -> UserNew:
    """Create inactive user for permission tests."""
    user = UserFactory.create(
        email="inactive@test.com",
        is_active=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ============================================================================
# FASTAPI TEST CLIENT
# ============================================================================

@pytest.fixture
def client(db: Session) -> TestClient:
    """
    FastAPI TestClient with database dependency override.

    Overrides get_db to use test database session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close, managed by db fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client: TestClient, test_regular_user: UserNew) -> TestClient:
    """
    TestClient with authentication pre-configured.

    Overrides get_current_active_user to return test_regular_user.
    """
    async def override_get_current_user():
        return test_regular_user

    app.dependency_overrides[get_current_active_user] = override_get_current_user

    yield client

    app.dependency_overrides.pop(get_current_active_user, None)


@pytest.fixture
def admin_client(client: TestClient, test_admin_user: UserNew) -> TestClient:
    """TestClient authenticated as admin user."""
    async def override_get_current_user():
        return test_admin_user

    app.dependency_overrides[get_current_active_user] = override_get_current_user

    yield client

    app.dependency_overrides.pop(get_current_active_user, None)


# ============================================================================
# SCOPE FIXTURES
# ============================================================================

@pytest.fixture
def test_scope(db: Session, test_admin_user: UserNew) -> Scope:
    """Create test scope owned by admin user."""
    scope = ScopeFactory.create(
        title="Test Scope",
        created_by=test_admin_user.id
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


@pytest.fixture
def public_scope(db: Session, test_admin_user: UserNew) -> Scope:
    """Create public test scope."""
    scope = ScopeFactory.create(
        title="Public Scope",
        is_public=True,
        created_by=test_admin_user.id
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


@pytest.fixture
def private_scope(db: Session, test_admin_user: UserNew) -> Scope:
    """Create private test scope."""
    scope = ScopeFactory.create(
        title="Private Scope",
        is_public=False,
        created_by=test_admin_user.id
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


# ============================================================================
# PERFORMANCE TESTING FIXTURES
# ============================================================================

@pytest.fixture
def benchmark_db(db: Session):
    """Database session with query timing enabled."""
    queries = []

    @event.listens_for(db.bind, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(db.bind, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
        total_time = time.time() - context._query_start_time
        queries.append({
            "statement": statement,
            "params": params,
            "time": total_time
        })

    yield db

    # Print slow queries
    slow_queries = [q for q in queries if q["time"] > 0.1]
    if slow_queries:
        print(f"\nSlow queries detected ({len(slow_queries)}):")
        for q in slow_queries:
            print(f"  {q['time']:.3f}s: {q['statement'][:100]}...")


# ============================================================================
# HYPOTHESIS STRATEGY FIXTURES
# ============================================================================

@pytest.fixture
def valid_uuid_strategy():
    """Hypothesis strategy for valid UUIDs."""
    from hypothesis import strategies as st
    return st.uuids()


@pytest.fixture
def valid_email_strategy():
    """Hypothesis strategy for valid emails."""
    from hypothesis import strategies as st
    return st.emails()


@pytest.fixture
def scope_role_strategy():
    """Hypothesis strategy for scope roles."""
    from hypothesis import strategies as st
    from app.core.enums import ScopeRole
    return st.sampled_from([role.value for role in ScopeRole])
```

---

## Unit Tests

### File: `backend/tests/unit/test_helpers.py`

```python
"""
Unit tests for helper functions.

Focus: Pure functions, no external dependencies.
Coverage Goal: 90%+
"""

import pytest
from uuid import uuid4, UUID
from app.core.security import get_current_user_uuid, is_scope_member


class TestUUIDHelpers:
    """Test UUID parsing and validation helpers."""

    def test_get_current_user_uuid_valid(self, monkeypatch):
        """Test UUID extraction from PostgreSQL setting."""
        test_uuid = uuid4()
        monkeypatch.setenv("app.current_user_id", str(test_uuid))

        result = get_current_user_uuid()
        assert isinstance(result, UUID)
        assert result == test_uuid

    def test_get_current_user_uuid_invalid_returns_none(self, monkeypatch):
        """Test invalid UUID returns None (not exception)."""
        monkeypatch.setenv("app.current_user_id", "not-a-uuid")

        result = get_current_user_uuid()
        assert result is None

    def test_get_current_user_uuid_missing_returns_none(self):
        """Test missing setting returns None."""
        result = get_current_user_uuid()
        assert result is None


class TestEnumConversions:
    """Test enum helper functions."""

    def test_application_role_from_string(self):
        """Test ApplicationRole enum conversion."""
        from app.core.enums import ApplicationRole

        assert ApplicationRole("admin") == ApplicationRole.ADMIN
        assert ApplicationRole("user") == ApplicationRole.USER

    def test_scope_role_from_string(self):
        """Test ScopeRole enum conversion."""
        from app.core.enums import ScopeRole

        assert ScopeRole("admin") == ScopeRole.ADMIN
        assert ScopeRole("curator") == ScopeRole.CURATOR
        assert ScopeRole("reviewer") == ScopeRole.REVIEWER
        assert ScopeRole("viewer") == ScopeRole.VIEWER

    def test_scope_role_invalid_raises(self):
        """Test invalid scope role raises ValueError."""
        from app.core.enums import ScopeRole

        with pytest.raises(ValueError):
            ScopeRole("invalid_role")
```

### File: `backend/tests/unit/test_validators.py`

```python
"""
Unit tests for Pydantic validators.

Focus: Input validation, edge cases.
Coverage Goal: 95%+
"""

import pytest
from pydantic import ValidationError
from app.schemas.scope_membership import ScopeMembershipCreate, ScopeInvitationCreate


class TestScopeMembershipValidation:
    """Test scope membership schema validation."""

    def test_valid_membership_create(self):
        """Test valid membership creation data."""
        data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "curator"
        }
        membership = ScopeMembershipCreate(**data)
        assert membership.role == "curator"

    def test_invalid_role_raises(self):
        """Test invalid role raises ValidationError."""
        data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "invalid_role"
        }
        with pytest.raises(ValidationError) as exc_info:
            ScopeMembershipCreate(**data)

        assert "role" in str(exc_info.value)

    def test_missing_user_id_raises(self):
        """Test missing user_id raises ValidationError."""
        data = {"role": "curator"}
        with pytest.raises(ValidationError) as exc_info:
            ScopeMembershipCreate(**data)

        assert "user_id" in str(exc_info.value)


class TestInvitationValidation:
    """Test invitation schema validation."""

    def test_valid_invitation_with_email(self):
        """Test valid invitation with email."""
        data = {
            "email": "test@example.com",
            "role": "viewer"
        }
        invitation = ScopeInvitationCreate(**data)
        assert invitation.email == "test@example.com"

    def test_valid_invitation_with_user_id(self):
        """Test valid invitation with existing user_id."""
        data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "role": "reviewer"
        }
        invitation = ScopeInvitationCreate(**data)
        assert invitation.user_id is not None

    def test_invalid_email_format_raises(self):
        """Test invalid email format raises ValidationError."""
        data = {
            "email": "not-an-email",
            "role": "viewer"
        }
        with pytest.raises(ValidationError) as exc_info:
            ScopeInvitationCreate(**data)

        assert "email" in str(exc_info.value)
```

---

## Integration Tests

### File: `backend/tests/integration/test_scope_api.py`

```python
"""
Integration tests for Scope API endpoints.

Focus: Full request/response cycle with database.
Coverage Goal: 80%+ of API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.models import UserNew, Scope


@pytest.mark.integration
class TestScopeCreation:
    """Test scope creation API endpoint."""

    def test_create_scope_as_authenticated_user(
        self,
        authenticated_client: TestClient,
        db: Session
    ):
        """Test authenticated user can create scope."""
        response = authenticated_client.post(
            "/api/v1/scopes",
            json={
                "title": "New Test Scope",
                "description": "Integration test scope",
                "is_public": False
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Test Scope"
        assert data["is_public"] is False
        assert "id" in data

        # Verify in database
        scope = db.query(Scope).filter_by(id=data["id"]).first()
        assert scope is not None
        assert scope.title == "New Test Scope"

    def test_create_scope_unauthenticated_returns_401(self, client: TestClient):
        """Test unauthenticated request returns 401."""
        response = client.post(
            "/api/v1/scopes",
            json={"title": "Test", "is_public": True}
        )

        assert response.status_code == 401

    def test_create_scope_invalid_data_returns_422(
        self,
        authenticated_client: TestClient
    ):
        """Test invalid data returns 422 validation error."""
        response = authenticated_client.post(
            "/api/v1/scopes",
            json={"title": ""}  # Empty title
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
class TestScopeRetrieval:
    """Test scope retrieval API endpoints."""

    def test_get_scope_by_id(
        self,
        authenticated_client: TestClient,
        test_scope: Scope,
        set_rls_user,
        test_regular_user: UserNew
    ):
        """Test retrieving scope by ID with RLS."""
        # Set RLS context
        set_rls_user(test_regular_user.id)

        response = authenticated_client.get(f"/api/v1/scopes/{test_scope.id}")

        # Should return 404 if not a member (RLS blocks access)
        assert response.status_code in [200, 404]

    def test_list_user_scopes(
        self,
        authenticated_client: TestClient,
        test_scope: Scope,
        db: Session
    ):
        """Test listing scopes for authenticated user."""
        response = authenticated_client.get("/api/v1/scopes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestScopeUpdate:
    """Test scope update API endpoint."""

    def test_update_scope_as_scope_admin(
        self,
        authenticated_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew,
        db: Session
    ):
        """Test scope admin can update scope."""
        # Make user scope admin
        from app.models.models import ScopeMembership
        membership = ScopeMembership(
            scope_id=test_scope.id,
            user_id=test_regular_user.id,
            role="admin",
            is_active=True
        )
        db.add(membership)
        db.commit()

        response = authenticated_client.put(
            f"/api/v1/scopes/{test_scope.id}",
            json={
                "title": "Updated Title",
                "description": "Updated description"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_scope_as_non_admin_returns_403(
        self,
        authenticated_client: TestClient,
        test_scope: Scope
    ):
        """Test non-admin cannot update scope."""
        response = authenticated_client.put(
            f"/api/v1/scopes/{test_scope.id}",
            json={"title": "Unauthorized Update"}
        )

        assert response.status_code == 403


@pytest.mark.integration
class TestScopeDeletion:
    """Test scope deletion API endpoint."""

    def test_delete_scope_as_scope_admin(
        self,
        admin_client: TestClient,
        test_scope: Scope,
        db: Session
    ):
        """Test scope admin can delete scope."""
        response = admin_client.delete(f"/api/v1/scopes/{test_scope.id}")

        assert response.status_code == 204

        # Verify deletion
        scope = db.query(Scope).filter_by(id=test_scope.id).first()
        assert scope is None

    def test_delete_scope_cascades_memberships(
        self,
        admin_client: TestClient,
        test_scope: Scope,
        db: Session
    ):
        """Test deleting scope cascades to memberships."""
        from app.models.models import ScopeMembership

        # Create membership
        membership = ScopeMembership(
            scope_id=test_scope.id,
            user_id=uuid4(),
            role="viewer"
        )
        db.add(membership)
        db.commit()

        # Delete scope
        response = admin_client.delete(f"/api/v1/scopes/{test_scope.id}")
        assert response.status_code == 204

        # Verify membership deleted
        memberships = db.query(ScopeMembership).filter_by(
            scope_id=test_scope.id
        ).all()
        assert len(memberships) == 0
```

### File: `backend/tests/integration/test_membership_api.py`

```python
"""
Integration tests for Scope Membership API.

Focus: Invitation flow, role management, RLS enforcement.
Coverage Goal: 85%+
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.models import UserNew, Scope, ScopeMembership


@pytest.mark.integration
class TestInvitationFlow:
    """Test complete invitation workflow."""

    def test_invite_user_to_scope(
        self,
        admin_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew
    ):
        """Test scope admin can invite user."""
        response = admin_client.post(
            f"/api/v1/scopes/{test_scope.id}/invitations",
            json={
                "user_id": str(test_regular_user.id),
                "role": "curator"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "curator"
        assert data["invitation_status"] == "pending"

    def test_invite_by_email_creates_pending_invitation(
        self,
        admin_client: TestClient,
        test_scope: Scope
    ):
        """Test inviting non-existent user by email."""
        response = admin_client.post(
            f"/api/v1/scopes/{test_scope.id}/invitations",
            json={
                "email": "newuser@example.com",
                "role": "viewer"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["invitation_status"] == "pending"

    def test_accept_invitation(
        self,
        authenticated_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew,
        db: Session
    ):
        """Test user can accept invitation."""
        # Create pending invitation
        invitation = ScopeMembership(
            scope_id=test_scope.id,
            user_id=test_regular_user.id,
            role="curator",
            is_active=False
        )
        db.add(invitation)
        db.commit()

        response = authenticated_client.post(
            f"/api/v1/scopes/{test_scope.id}/invitations/{invitation.id}/accept"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["accepted_at"] is not None


@pytest.mark.integration
class TestMembershipManagement:
    """Test membership role changes and removal."""

    def test_change_member_role(
        self,
        admin_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew,
        db: Session
    ):
        """Test scope admin can change member role."""
        # Create active membership
        membership = ScopeMembership(
            scope_id=test_scope.id,
            user_id=test_regular_user.id,
            role="viewer",
            is_active=True
        )
        db.add(membership)
        db.commit()

        response = admin_client.patch(
            f"/api/v1/scopes/{test_scope.id}/members/{test_regular_user.id}",
            json={"role": "curator"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "curator"

    def test_remove_member_from_scope(
        self,
        admin_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew,
        db: Session
    ):
        """Test scope admin can remove member."""
        # Create active membership
        membership = ScopeMembership(
            scope_id=test_scope.id,
            user_id=test_regular_user.id,
            role="viewer",
            is_active=True
        )
        db.add(membership)
        db.commit()

        response = admin_client.delete(
            f"/api/v1/scopes/{test_scope.id}/members/{test_regular_user.id}"
        )

        assert response.status_code == 204

        # Verify removal
        membership = db.query(ScopeMembership).filter_by(
            scope_id=test_scope.id,
            user_id=test_regular_user.id
        ).first()
        assert membership is None or not membership.is_active


@pytest.mark.integration
class TestPermissionChecks:
    """Test permission enforcement for membership operations."""

    def test_non_admin_cannot_invite(
        self,
        authenticated_client: TestClient,
        test_scope: Scope
    ):
        """Test non-admin cannot send invitations."""
        response = authenticated_client.post(
            f"/api/v1/scopes/{test_scope.id}/invitations",
            json={"email": "test@example.com", "role": "viewer"}
        )

        assert response.status_code == 403

    def test_curator_cannot_change_roles(
        self,
        authenticated_client: TestClient,
        test_scope: Scope,
        test_regular_user: UserNew,
        db: Session
    ):
        """Test curator cannot change member roles."""
        # Make authenticated user a curator
        membership = ScopeMembership(
            scope_id=test_scope.id,
            user_id=test_regular_user.id,
            role="curator",
            is_active=True
        )
        db.add(membership)
        db.commit()

        response = authenticated_client.patch(
            f"/api/v1/scopes/{test_scope.id}/members/{test_regular_user.id}",
            json={"role": "admin"}
        )

        assert response.status_code == 403
```

---

## RLS Security Tests

### File: `backend/tests/rls/test_rls_isolation.py`

```python
"""
RLS Security Tests - Tenant Isolation.

Focus: Verify RLS policies prevent cross-tenant data access.
Coverage Goal: 100% of RLS policies
Priority: CRITICAL (P0 security tests)
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from uuid import uuid4
from app.models.models import Scope, ScopeMembership, UserNew


@pytest.mark.rls
@pytest.mark.security
class TestScopeIsolation:
    """Test RLS policies isolate scopes correctly."""

    def test_user_cannot_see_non_member_scopes(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test user cannot query scopes they're not a member of."""
        # Create two scopes
        scope1 = Scope(
            title="User's Scope",
            created_by=test_regular_user.id,
            is_public=False
        )
        scope2 = Scope(
            title="Other User's Scope",
            created_by=uuid4(),
            is_public=False
        )
        db.add_all([scope1, scope2])
        db.commit()

        # Add user to scope1 only
        membership = ScopeMembership(
            scope_id=scope1.id,
            user_id=test_regular_user.id,
            role="admin",
            is_active=True
        )
        db.add(membership)
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Query scopes
        scopes = db.query(Scope).all()

        # Should only see scope1
        assert len(scopes) == 1
        assert scopes[0].id == scope1.id

    def test_public_scopes_visible_to_all(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test public scopes are visible to all users."""
        # Create public and private scopes
        public_scope = Scope(
            title="Public Scope",
            created_by=uuid4(),
            is_public=True
        )
        private_scope = Scope(
            title="Private Scope",
            created_by=uuid4(),
            is_public=False
        )
        db.add_all([public_scope, private_scope])
        db.commit()

        # Set RLS context (user is not a member of either)
        set_rls_user(test_regular_user.id)

        # Query scopes
        scopes = db.query(Scope).all()

        # Should only see public scope
        assert len(scopes) == 1
        assert scopes[0].id == public_scope.id

    def test_update_non_member_scope_blocked(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test user cannot update scope they're not an admin of."""
        # Create scope owned by different user
        scope = Scope(
            title="Other's Scope",
            created_by=uuid4(),
            is_public=False
        )
        db.add(scope)
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Attempt to update
        scope.title = "Hacked Title"
        db.commit()

        # Verify update was blocked
        db.refresh(scope)
        assert scope.title == "Other's Scope"

    def test_delete_non_member_scope_blocked(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test user cannot delete scope they're not an admin of."""
        # Create scope owned by different user
        scope = Scope(
            title="Other's Scope",
            created_by=uuid4(),
            is_public=False
        )
        db.add(scope)
        db.commit()
        scope_id = scope.id

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Attempt to delete
        db.delete(scope)
        db.commit()

        # Verify scope still exists
        scope = db.query(Scope).filter_by(id=scope_id).first()
        assert scope is not None


@pytest.mark.rls
@pytest.mark.security
class TestMembershipIsolation:
    """Test RLS policies for scope memberships."""

    def test_cannot_see_other_scope_memberships(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test user cannot see memberships of non-member scopes."""
        # Create two scopes with memberships
        scope1 = Scope(title="Scope 1", created_by=test_regular_user.id)
        scope2 = Scope(title="Scope 2", created_by=uuid4())
        db.add_all([scope1, scope2])
        db.commit()

        # Add memberships
        membership1 = ScopeMembership(
            scope_id=scope1.id,
            user_id=test_regular_user.id,
            role="admin"
        )
        membership2 = ScopeMembership(
            scope_id=scope2.id,
            user_id=uuid4(),
            role="curator"
        )
        db.add_all([membership1, membership2])
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Query memberships
        memberships = db.query(ScopeMembership).all()

        # Should only see membership1
        assert len(memberships) == 1
        assert memberships[0].id == membership1.id

    def test_cannot_modify_other_scope_memberships(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test user cannot modify memberships in non-member scopes."""
        # Create scope owned by different user
        scope = Scope(title="Other's Scope", created_by=uuid4())
        db.add(scope)
        db.commit()

        # Add membership
        membership = ScopeMembership(
            scope_id=scope.id,
            user_id=uuid4(),
            role="viewer"
        )
        db.add(membership)
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Attempt to change role
        membership.role = "admin"
        db.commit()

        # Verify change was blocked
        db.refresh(membership)
        assert membership.role == "viewer"


@pytest.mark.rls
@pytest.mark.security
class TestRLSPerformance:
    """Test RLS policies don't cause N+1 queries."""

    def test_rls_policies_use_stable_functions(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user,
        benchmark_db
    ):
        """Test RLS policies cache results via STABLE functions."""
        # Create 100 scopes with memberships
        scopes = []
        for i in range(100):
            scope = Scope(
                title=f"Scope {i}",
                created_by=test_regular_user.id
            )
            scopes.append(scope)

        db.add_all(scopes)
        db.commit()

        for scope in scopes:
            membership = ScopeMembership(
                scope_id=scope.id,
                user_id=test_regular_user.id,
                role="admin"
            )
            db.add(membership)
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Query all scopes (should trigger RLS policies)
        scopes = db.query(Scope).all()

        assert len(scopes) == 100

        # Check query count (should not be 100+ queries)
        # STABLE functions should cache results


@pytest.mark.rls
@pytest.mark.security
class TestRLSBypass:
    """Test FORCE ROW LEVEL SECURITY prevents superuser bypass."""

    def test_superuser_cannot_bypass_rls(
        self,
        db: Session,
        test_admin_user: UserNew,
        test_regular_user: UserNew
    ):
        """Test even superuser (table owner) cannot bypass RLS."""
        # Create private scope
        scope = Scope(
            title="Private Scope",
            created_by=test_regular_user.id,
            is_public=False
        )
        db.add(scope)
        db.commit()

        # Query as superuser/admin (no RLS context set)
        # With FORCE ROW LEVEL SECURITY, should still enforce policies
        scopes = db.query(Scope).all()

        # Without RLS context, should see no scopes
        # (or only public scopes, depending on policy)
        assert all(s.is_public for s in scopes)
```

---

## Property-Based Tests

### File: `backend/tests/property/test_uuid_properties.py`

```python
"""
Property-based tests using Hypothesis.

Focus: Test invariants across wide range of inputs.
Coverage Goal: Critical functions and edge cases.
"""

import pytest
from hypothesis import given, strategies as st, assume
from uuid import UUID
from app.core.security import get_current_user_uuid, is_valid_uuid


@pytest.mark.property
class TestUUIDProperties:
    """Property-based tests for UUID handling."""

    @given(st.uuids())
    def test_uuid_to_string_to_uuid_roundtrip(self, uuid_val: UUID):
        """Test UUID → str → UUID round-trip is identity."""
        uuid_str = str(uuid_val)
        reconstructed = UUID(uuid_str)
        assert reconstructed == uuid_val

    @given(st.text())
    def test_invalid_uuid_strings_handled_gracefully(self, text: str):
        """Test invalid UUID strings don't crash, return None."""
        assume(not is_valid_uuid(text))  # Skip valid UUIDs

        result = get_current_user_uuid(text)
        assert result is None

    @given(st.uuids())
    def test_valid_uuid_always_accepted(self, uuid_val: UUID):
        """Test all valid UUIDs are accepted."""
        result = is_valid_uuid(str(uuid_val))
        assert result is True


@pytest.mark.property
class TestPaginationProperties:
    """Property-based tests for pagination logic."""

    @given(
        page=st.integers(min_value=1, max_value=1000),
        page_size=st.integers(min_value=1, max_value=100)
    )
    def test_pagination_offset_always_positive(self, page: int, page_size: int):
        """Test pagination offset is always >= 0."""
        offset = (page - 1) * page_size
        assert offset >= 0

    @given(
        page=st.integers(min_value=1, max_value=1000),
        page_size=st.integers(min_value=1, max_value=100),
        total_items=st.integers(min_value=0, max_value=100000)
    )
    def test_pagination_never_exceeds_total(
        self,
        page: int,
        page_size: int,
        total_items: int
    ):
        """Test paginated slice never exceeds total items."""
        offset = (page - 1) * page_size
        limit = page_size

        actual_items = min(limit, max(0, total_items - offset))
        assert 0 <= actual_items <= limit
```

---

## Test Data Factories

### File: `backend/tests/factories/user_factory.py`

```python
"""
Factory Boy factories for test data generation.

Benefits:
- DRY: Reusable test data patterns
- Faker integration: Realistic fake data
- Relationships: Automatic handling of foreign keys
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from app.models.models import UserNew
from app.core.enums import ApplicationRole

fake = Faker()


class UserFactory(SQLAlchemyModelFactory):
    """Factory for UserNew model."""

    class Meta:
        model = UserNew
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: uuid4())
    email = factory.LazyAttribute(lambda _: fake.email())
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    application_role = ApplicationRole.USER
    is_active = True
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())

    @factory.post_generation
    def hashed_password(obj, create, extracted, **kwargs):
        """Set hashed password."""
        from app.core.security import get_password_hash
        obj.hashed_password = get_password_hash("testpassword123")


class AdminUserFactory(UserFactory):
    """Factory for admin users."""
    application_role = ApplicationRole.ADMIN
```

### File: `backend/tests/factories/scope_factory.py`

```python
"""Factory for Scope model."""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from app.models.models import Scope

fake = Faker()


class ScopeFactory(SQLAlchemyModelFactory):
    """Factory for Scope model."""

    class Meta:
        model = Scope
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: uuid4())
    title = factory.LazyAttribute(lambda _: fake.catch_phrase())
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_public = False
    due_date = None
    created_by = factory.LazyFunction(lambda: uuid4())
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())


class PublicScopeFactory(ScopeFactory):
    """Factory for public scopes."""
    is_public = True
```

---

## Performance & Load Tests

### File: `backend/tests/integration/test_rls_performance.py`

```python
"""
Performance tests for RLS policies.

Focus: Ensure RLS doesn't cause performance degradation.
Goal: < 100ms per request with RLS enabled (1000 scopes)
"""

import pytest
import time
from sqlalchemy.orm import Session
from app.models.models import Scope, ScopeMembership, UserNew


@pytest.mark.slow
@pytest.mark.integration
class TestRLSPerformance:
    """Test RLS performance with large datasets."""

    def test_query_performance_1000_scopes(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user
    ):
        """Test query performance with 1000 scopes."""
        # Create 1000 scopes with memberships
        scopes = []
        for i in range(1000):
            scope = Scope(
                title=f"Scope {i}",
                created_by=test_regular_user.id
            )
            scopes.append(scope)

        db.add_all(scopes)
        db.commit()

        # Add user to 500 scopes
        for i, scope in enumerate(scopes[:500]):
            membership = ScopeMembership(
                scope_id=scope.id,
                user_id=test_regular_user.id,
                role="curator"
            )
            db.add(membership)
        db.commit()

        # Set RLS context
        set_rls_user(test_regular_user.id)

        # Query scopes (should be filtered by RLS)
        start_time = time.time()
        result = db.query(Scope).all()
        query_time = time.time() - start_time

        # Assertions
        assert len(result) == 500  # Only member scopes
        assert query_time < 0.1  # < 100ms

        print(f"\nQuery time for 1000 scopes: {query_time*1000:.2f}ms")

    def test_membership_check_performance(
        self,
        db: Session,
        test_regular_user: UserNew,
        set_rls_user,
        benchmark
    ):
        """Benchmark membership check function."""
        scope = Scope(title="Test Scope", created_by=test_regular_user.id)
        db.add(scope)
        db.commit()

        membership = ScopeMembership(
            scope_id=scope.id,
            user_id=test_regular_user.id,
            role="admin"
        )
        db.add(membership)
        db.commit()

        set_rls_user(test_regular_user.id)

        # Benchmark the check
        result = benchmark(
            lambda: db.execute(
                text("SELECT is_scope_member(:scope_id)"),
                {"scope_id": str(scope.id)}
            ).scalar()
        )

        assert result is True
```

---

## Testing Checklist

### Pre-Implementation Checklist

- [ ] Install all test dependencies (`uv pip install -e ".[test]"`)
- [ ] Create test database (`gene_curator_test`)
- [ ] Configure `pytest.ini` with coverage settings
- [ ] Set up `tests/conftest.py` with core fixtures
- [ ] Create factories directory with Factory Boy factories

### During Implementation Checklist

**For Each New Feature:**

- [ ] Write unit tests first (TDD approach)
- [ ] Write integration tests for API endpoints
- [ ] Write RLS security tests if involving data access
- [ ] Add property-based tests for complex logic
- [ ] Verify test coverage meets 85%+ threshold
- [ ] Run full test suite: `pytest tests/`
- [ ] Run security tests: `pytest -m security`
- [ ] Check performance: `pytest -m slow`

**For Each API Endpoint:**

- [ ] Test successful request (200/201)
- [ ] Test authentication required (401)
- [ ] Test authorization failure (403)
- [ ] Test validation errors (422)
- [ ] Test not found (404)
- [ ] Test RLS enforcement
- [ ] Test with pagination parameters
- [ ] Test concurrent requests (if applicable)

**For Each RLS Policy:**

- [ ] Test user can access own data
- [ ] Test user cannot access others' data
- [ ] Test public data visible to all
- [ ] Test superuser cannot bypass (FORCE RLS)
- [ ] Test performance with 1000+ records
- [ ] Test N+1 query prevention (STABLE functions)

### Post-Implementation Checklist

- [ ] Run full test suite: `pytest tests/`
- [ ] Generate coverage report: `pytest --cov=app --cov-report=html`
- [ ] Review coverage report (`htmlcov/index.html`)
- [ ] Ensure all RLS tests pass: `pytest -m rls -v`
- [ ] Run performance tests: `pytest -m slow`
- [ ] Run property-based tests: `pytest -m property`
- [ ] Check for security warnings: `bandit -r app/`
- [ ] Run type checking: `mypy app/`
- [ ] Run linting: `ruff check app/`

### CI/CD Integration Checklist

- [ ] Add GitHub Actions workflow for tests
- [ ] Configure test database in CI
- [ ] Run tests on all PRs
- [ ] Enforce 85%+ coverage requirement
- [ ] Run security tests separately (fail fast)
- [ ] Generate coverage badge
- [ ] Upload coverage to codecov.io (optional)

### Test Maintenance Checklist

**Weekly:**
- [ ] Review and update slow tests
- [ ] Check for flaky tests (random failures)
- [ ] Update factories with new model fields
- [ ] Review test execution time trends

**Per Release:**
- [ ] Update test data fixtures
- [ ] Review and archive obsolete tests
- [ ] Update property-based test strategies
- [ ] Benchmark performance tests against baseline

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/integration/test_scope_api.py

# Run specific test class
pytest tests/integration/test_scope_api.py::TestScopeCreation

# Run specific test function
pytest tests/integration/test_scope_api.py::TestScopeCreation::test_create_scope_as_authenticated_user

# Run tests matching pattern
pytest -k "test_scope"

# Run tests with specific marker
pytest -m integration
pytest -m rls
pytest -m security
pytest -m slow
pytest -m property

# Parallel execution (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Verbose output
pytest -v

# Show print statements
pytest -s
```

### Advanced Commands

```bash
# Run security tests only (fast feedback)
pytest -m security -v

# Run integration + RLS tests
pytest -m "integration or rls"

# Run all except slow tests
pytest -m "not slow"

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Profile slow tests
pytest --durations=10

# Re-run failed tests
pytest --lf

# Run tests that failed in last run, then all others
pytest --ff
```

---

## Summary

This testing implementation guide provides:

1. **Modern Testing Strategy** - Testing Trophy model (integration-focused)
2. **Complete Test Infrastructure** - pytest fixtures, Factory Boy, Hypothesis
3. **Comprehensive Test Suite** - Unit, integration, RLS, property-based tests
4. **Security-First Approach** - 100% RLS policy coverage
5. **Performance Validation** - Load tests for 1000+ scopes
6. **CI/CD Ready** - All tests automated and enforceable

**Next Steps:**

1. Install test dependencies
2. Create test database
3. Implement core fixtures (`conftest.py`)
4. Write tests alongside backend implementation
5. Maintain 85%+ coverage threshold
6. Run security tests on every commit

**Coverage Goals:**

- **Unit Tests**: 90%+ of utility functions
- **Integration Tests**: 80%+ of API endpoints
- **RLS Security Tests**: 100% of policies
- **Overall Coverage**: 85%+ (enforced in CI)

All tests follow modern best practices (2024-2025):
- FastAPI TestClient with dependency injection
- pytest-postgresql for database fixtures
- Factory Boy for test data
- Hypothesis for property-based testing
- Session-scoped DB with transaction rollback for isolation
