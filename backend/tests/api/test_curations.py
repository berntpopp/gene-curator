"""Integration tests for curations API endpoints.

Tests CRUD operations, optimistic locking, RLS filtering, and permissions.
Following Arrange-Act-Assert pattern with comprehensive coverage.

NOTE: These tests mock set_rls_context because SQLite (used in tests) doesn't
support PostgreSQL's Row-Level Security features. Admin tokens are used for
most tests since admins bypass scope checks.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, Gene, Scope, UserNew, WorkflowPair

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_rls_context():
    """Mock set_rls_context for SQLite compatibility.

    SQLite doesn't support PostgreSQL's SET session variables used by RLS.
    This mock makes set_rls_context a no-op for tests.
    """
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


@pytest.fixture
def test_user_with_scope(db_session: Session, test_scope: Scope) -> UserNew:
    """Create a user with scope membership via scope_memberships table."""
    from app.core.security import get_password_hash
    from app.models.models import ScopeMembership

    user = UserNew(
        id=uuid4(),
        email="scopeuser@test.com",
        hashed_password=get_password_hash("test123"),
        name="Scope User",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()  # Get user ID

    # Create scope membership
    membership = ScopeMembership(
        user_id=user.id,
        scope_id=test_scope.id,
        role="curator",
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def scope_user_token(test_user_with_scope: UserNew) -> str:
    """JWT token for user with scope access."""
    from app.core.security import create_access_token

    return create_access_token(
        data={
            "sub": str(test_user_with_scope.id),
            "email": test_user_with_scope.email,
            "role": test_user_with_scope.role.value,
        }
    )


class TestCurationsList:
    """Tests for GET /curations/"""

    def test_list_curations_empty(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test listing curations returns empty list when none exist."""
        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "curations" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["curations"] == []
        assert data["total"] == 0

    def test_list_curations_with_data(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test listing curations returns existing curations."""
        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["curations"]) >= 1

    def test_list_curations_filter_by_scope(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
        test_scope: Scope,
    ):
        """Test filtering curations by scope."""
        # Act
        response = client.get(
            f"/api/v1/curations/?scope_id={test_scope.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_curations_unauthorized(
        self,
        client: TestClient,
    ):
        """Test listing curations without authentication returns 403.

        Note: FastAPI's HTTPBearer returns 403 (not 401) when no credentials
        are provided, per OAuth 2.0 Bearer Token spec (RFC 6750).
        """
        # Act
        response = client.get("/api/v1/curations/")

        # Assert
        assert response.status_code == 403

    def test_list_curations_with_scope_user(
        self,
        client: TestClient,
        scope_user_token: str,
        test_curation: CurationNew,
    ):
        """Test user with assigned scope can list curations."""
        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {scope_user_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestCurationGet:
    """Tests for GET /curations/{curation_id}"""

    def test_get_curation_success(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test getting a single curation by ID."""
        # Act
        response = client.get(
            f"/api/v1/curations/{test_curation.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_curation.id)
        assert "evidence_data" in data
        assert "lock_version" in data

    def test_get_curation_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test getting non-existent curation returns 404."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = client.get(
            f"/api/v1/curations/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestCurationCreate:
    """Tests for POST /curations/"""

    def test_create_curation_success(
        self,
        client: TestClient,
        admin_token: str,
        test_scope: Scope,
        test_gene: Gene,
        test_workflow_pair: WorkflowPair,
    ):
        """Test successful curation creation."""
        # Arrange
        curation_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "workflow_pair_id": str(test_workflow_pair.id),
            "evidence_data": {"test": "data"},
        }

        # Act
        response = client.post(
            "/api/v1/curations/",
            json=curation_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["gene_id"] == str(test_gene.id)
        assert data["scope_id"] == str(test_scope.id)
        assert data["status"] == "draft"
        assert data["is_draft"] is True
        assert data["lock_version"] == 0

    def test_create_curation_invalid_gene(
        self,
        client: TestClient,
        admin_token: str,
        test_scope: Scope,
        test_workflow_pair: WorkflowPair,
    ):
        """Test creating curation with non-existent gene returns 400."""
        # Arrange
        curation_data = {
            "gene_id": str(uuid4()),  # Non-existent
            "scope_id": str(test_scope.id),
            "workflow_pair_id": str(test_workflow_pair.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/curations/",
            json=curation_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 400

    def test_create_curation_invalid_scope(
        self,
        client: TestClient,
        admin_token: str,
        test_gene: Gene,
        test_workflow_pair: WorkflowPair,
    ):
        """Test creating curation with non-existent scope returns 400."""
        # Arrange
        curation_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(uuid4()),  # Non-existent
            "workflow_pair_id": str(test_workflow_pair.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/curations/",
            json=curation_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 400

    def test_create_curation_unauthorized(
        self,
        client: TestClient,
        test_scope: Scope,
        test_gene: Gene,
        test_workflow_pair: WorkflowPair,
    ):
        """Test creating curation without auth returns 403."""
        # Arrange
        curation_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "workflow_pair_id": str(test_workflow_pair.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/curations/",
            json=curation_data,
        )

        # Assert
        assert response.status_code == 403


class TestCurationUpdate:
    """Tests for PUT /curations/{curation_id}"""

    def test_update_curation_success(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test successful curation update with correct lock version."""
        # Arrange - get fresh lock version
        initial_lock_version = test_curation.lock_version
        update_data = {
            "evidence_data": {"updated": True, "new_field": "value"},
            "lock_version": initial_lock_version,
        }

        # Act
        response = client.put(
            f"/api/v1/curations/{test_curation.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_data"]["updated"] is True
        # Lock version should increment by 1 from what we sent
        assert data["lock_version"] == initial_lock_version + 1

    def test_update_curation_conflict(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test optimistic locking returns 409 on version mismatch."""
        # Arrange
        update_data = {
            "evidence_data": {"updated": True},
            "lock_version": 999,  # Wrong version
        }

        # Act
        response = client.put(
            f"/api/v1/curations/{test_curation.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 409
        data = response.json()
        assert "current_lock_version" in data["detail"]

    def test_update_curation_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test updating non-existent curation returns 404."""
        # Arrange
        fake_id = uuid4()
        update_data = {
            "evidence_data": {"test": "data"},
            "lock_version": 0,
        }

        # Act
        response = client.put(
            f"/api/v1/curations/{fake_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestCurationDraft:
    """Tests for PATCH /curations/{curation_id}/draft"""

    def test_save_draft_success(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test saving curation as draft."""
        # Arrange
        draft_data = {
            "evidence_data": {"draft_field": "draft_value"},
        }

        # Act
        response = client.patch(
            f"/api/v1/curations/{test_curation.id}/draft",
            json=draft_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_data"]["draft_field"] == "draft_value"
        assert data["is_draft"] is True

    def test_save_draft_without_lock_version(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test draft save works without lock_version."""
        # Arrange
        draft_data = {
            "evidence_data": {"auto_saved": True},
        }

        # Act
        response = client.patch(
            f"/api/v1/curations/{test_curation.id}/draft",
            json=draft_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200


class TestCurationSubmit:
    """Tests for POST /curations/{curation_id}/submit"""

    def test_submit_curation_requires_lock_version(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test submission requires lock_version."""
        # Arrange - no lock_version
        submit_data = {
            "notes": "Ready for review",
        }

        # Act
        response = client.post(
            f"/api/v1/curations/{test_curation.id}/submit",
            json=submit_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert - should fail validation
        assert response.status_code == 422


class TestCurationScore:
    """Tests for GET /curations/{curation_id}/score"""

    def test_calculate_score_success(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test score calculation endpoint."""
        # Act
        response = client.get(
            f"/api/v1/curations/{test_curation.id}/score",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "curation_id" in data
        assert "total_score" in data
        assert "classification" in data


class TestCurationDelete:
    """Tests for DELETE /curations/{curation_id}"""

    def test_delete_curation_success(
        self,
        client: TestClient,
        admin_token: str,
        test_curation: CurationNew,
    ):
        """Test soft delete of draft curation."""
        # Act
        response = client.delete(
            f"/api/v1/curations/{test_curation.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 204

    def test_delete_curation_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test deleting non-existent curation returns 404."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = client.delete(
            f"/api/v1/curations/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestCurationScopeAccess:
    """Tests for scope-based access control."""

    def test_user_without_scope_gets_empty_list(
        self,
        client: TestClient,
        viewer_token: str,
    ):
        """Test user without scopes gets empty list.

        Note: viewer_token user doesn't have assigned_scopes populated
        in the base fixture, so they should get an empty result.
        """
        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["curations"] == []
        assert data["total"] == 0

    def test_user_with_scope_can_access(
        self,
        client: TestClient,
        scope_user_token: str,
        test_curation: CurationNew,
    ):
        """Test user with assigned scope can access curations."""
        # Act
        response = client.get(
            f"/api/v1/curations/{test_curation.id}",
            headers={"Authorization": f"Bearer {scope_user_token}"},
        )

        # Assert
        assert response.status_code == 200

    def test_scope_filter_admin_access(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test admin can filter by any scope."""
        # Arrange - use a non-existent scope
        other_scope_id = uuid4()

        # Act
        response = client.get(
            f"/api/v1/curations/?scope_id={other_scope_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert - empty list but valid response (admin bypasses scope checks)
        assert response.status_code == 200
        data = response.json()
        assert data["curations"] == []
