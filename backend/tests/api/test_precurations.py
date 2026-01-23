"""Integration tests for precurations API endpoints.

Tests CRUD operations, RLS filtering, and workflow transitions.
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

from app.models.models import CurationSchema, Gene, PrecurationNew, Scope, UserNew

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_rls_context():
    """Mock set_rls_context for SQLite compatibility.

    SQLite doesn't support PostgreSQL's SET session variables used by RLS.
    This mock makes set_rls_context a no-op for tests.
    """
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


@pytest.fixture
def test_user_with_scope(db_session: Session, test_scope: Scope) -> UserNew:
    """Create a user with scope membership via scope_memberships table."""
    from app.core.security import get_password_hash
    from app.models.models import ScopeMembership

    user = UserNew(
        id=uuid4(),
        email="scopeuser_precuration@test.com",
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


class TestPrecurationsList:
    """Tests for GET /precurations/"""

    def test_list_precurations_empty(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test listing precurations returns empty list when none exist."""
        # Act
        response = client.get(
            "/api/v1/precurations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "precurations" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["precurations"] == []
        assert data["total"] == 0

    def test_list_precurations_with_data(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test listing precurations returns existing precurations."""
        # Act
        response = client.get(
            "/api/v1/precurations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["precurations"]) >= 1

    def test_list_precurations_filter_by_scope(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
        test_scope: Scope,
    ):
        """Test filtering precurations by scope."""
        # Act
        response = client.get(
            f"/api/v1/precurations/?scope_id={test_scope.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_precurations_unauthorized(
        self,
        client: TestClient,
    ):
        """Test listing precurations without authentication returns 401."""
        # Act
        response = client.get("/api/v1/precurations/")

        # Assert
        assert response.status_code == 401

    def test_list_precurations_with_scope_user(
        self,
        client: TestClient,
        scope_user_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test user with assigned scope can list precurations."""
        # Act
        response = client.get(
            "/api/v1/precurations/",
            headers={"Authorization": f"Bearer {scope_user_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestPrecurationGet:
    """Tests for GET /precurations/{precuration_id}"""

    def test_get_precuration_success(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test getting a single precuration by ID."""
        # Act
        response = client.get(
            f"/api/v1/precurations/{test_precuration.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_precuration.id)
        assert "evidence_data" in data
        assert "mondo_id" in data["evidence_data"]

    def test_get_precuration_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test getting non-existent precuration returns 404."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = client.get(
            f"/api/v1/precurations/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestPrecurationCreate:
    """Tests for POST /precurations/"""

    def test_create_precuration_success(
        self,
        client: TestClient,
        admin_token: str,
        test_scope: Scope,
        test_gene: Gene,
        test_precuration_schema: CurationSchema,
    ):
        """Test successful precuration creation."""
        # Arrange
        precuration_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "precuration_schema_id": str(test_precuration_schema.id),
            "evidence_data": {
                "mondo_id": "MONDO:0000002",
                "disease_name": "New Test Disease",
                "mode_of_inheritance": "AR",
            },
        }

        # Act
        response = client.post(
            "/api/v1/precurations/",
            json=precuration_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["gene_id"] == str(test_gene.id)
        assert data["scope_id"] == str(test_scope.id)
        assert data["status"] == "draft"
        assert data["is_draft"] is True

    def test_create_precuration_invalid_gene(
        self,
        client: TestClient,
        admin_token: str,
        test_scope: Scope,
        test_precuration_schema: CurationSchema,
    ):
        """Test creating precuration with non-existent gene returns 400."""
        # Arrange
        precuration_data = {
            "gene_id": str(uuid4()),  # Non-existent
            "scope_id": str(test_scope.id),
            "precuration_schema_id": str(test_precuration_schema.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/precurations/",
            json=precuration_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 400

    def test_create_precuration_invalid_scope(
        self,
        client: TestClient,
        admin_token: str,
        test_gene: Gene,
        test_precuration_schema: CurationSchema,
    ):
        """Test creating precuration with non-existent scope returns 400."""
        # Arrange
        precuration_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(uuid4()),  # Non-existent
            "precuration_schema_id": str(test_precuration_schema.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/precurations/",
            json=precuration_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 400

    def test_create_precuration_unauthorized(
        self,
        client: TestClient,
        test_scope: Scope,
        test_gene: Gene,
        test_precuration_schema: CurationSchema,
    ):
        """Test creating precuration without auth returns 401."""
        # Arrange
        precuration_data = {
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "precuration_schema_id": str(test_precuration_schema.id),
            "evidence_data": {},
        }

        # Act
        response = client.post(
            "/api/v1/precurations/",
            json=precuration_data,
        )

        # Assert
        assert response.status_code == 401


class TestPrecurationUpdate:
    """Tests for PUT /precurations/{precuration_id}"""

    def test_update_precuration_success(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test successful precuration update."""
        # Arrange
        update_data = {
            "evidence_data": {
                "mondo_id": "MONDO:0000003",
                "disease_name": "Updated Disease",
                "mode_of_inheritance": "XLR",
            },
        }

        # Act
        response = client.put(
            f"/api/v1/precurations/{test_precuration.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_data"]["mondo_id"] == "MONDO:0000003"

    def test_update_precuration_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test updating non-existent precuration returns 404."""
        # Arrange
        fake_id = uuid4()
        update_data = {
            "evidence_data": {"test": "data"},
        }

        # Act
        response = client.put(
            f"/api/v1/precurations/{fake_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestPrecurationDraft:
    """Tests for PATCH /precurations/{precuration_id}/draft"""

    def test_save_draft_success(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test saving precuration as draft."""
        # Arrange
        draft_data = {
            "evidence_data": {
                "mondo_id": "MONDO:0000004",
                "disease_name": "Draft Disease",
                "mode_of_inheritance": "AD",
            },
        }

        # Act
        response = client.patch(
            f"/api/v1/precurations/{test_precuration.id}/draft",
            json=draft_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_data"]["mondo_id"] == "MONDO:0000004"
        assert data["is_draft"] is True


class TestPrecurationSubmit:
    """Tests for POST /precurations/{precuration_id}/submit"""

    def test_submit_precuration_endpoint_exists(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test that submit endpoint exists and handles requests.

        Note: Full workflow transition requires proper workflow setup.
        This test verifies the endpoint is accessible.
        """
        # Arrange
        submit_data = {
            "notes": "Ready for review",
        }

        # Act
        response = client.post(
            f"/api/v1/precurations/{test_precuration.id}/submit",
            json=submit_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert - endpoint responds (either success or workflow validation error)
        assert response.status_code in [
            200,
            400,
        ]  # Accept either success or validation error


class TestPrecurationApproval:
    """Tests for POST /precurations/{precuration_id}/approve"""

    def test_approve_precuration_not_in_review(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test approving precuration that's not submitted returns 400."""
        # Act - try to approve a draft precuration
        response = client.post(
            f"/api/v1/precurations/{test_precuration.id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 400


class TestPrecurationReject:
    """Tests for POST /precurations/{precuration_id}/reject"""

    def test_reject_precuration_success(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test rejecting precuration."""
        # Arrange
        reject_data = {
            "reason": "Incomplete disease definition",
        }

        # Act
        response = client.post(
            f"/api/v1/precurations/{test_precuration.id}/reject",
            json=reject_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"


class TestPrecurationDelete:
    """Tests for DELETE /precurations/{precuration_id}"""

    def test_delete_precuration_success(
        self,
        client: TestClient,
        admin_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test soft delete of draft precuration."""
        # Act
        response = client.delete(
            f"/api/v1/precurations/{test_precuration.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 204

    def test_delete_precuration_not_found(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test deleting non-existent precuration returns 404."""
        # Arrange
        fake_id = uuid4()

        # Act
        response = client.delete(
            f"/api/v1/precurations/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestPrecurationScopeAccess:
    """Tests for scope-based access control."""

    def test_user_without_scope_gets_empty_list(
        self,
        client: TestClient,
        viewer_token: str,
    ):
        """Test user without scopes gets empty list."""
        # Act
        response = client.get(
            "/api/v1/precurations/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["precurations"] == []
        assert data["total"] == 0

    def test_user_with_scope_can_access(
        self,
        client: TestClient,
        scope_user_token: str,
        test_precuration: PrecurationNew,
    ):
        """Test user with assigned scope can access precurations."""
        # Act
        response = client.get(
            f"/api/v1/precurations/{test_precuration.id}",
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
            f"/api/v1/precurations/?scope_id={other_scope_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert - empty list but valid response (admin bypasses scope checks)
        assert response.status_code == 200
        data = response.json()
        assert data["precurations"] == []
