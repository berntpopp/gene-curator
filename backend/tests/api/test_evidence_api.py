"""API tests for evidence endpoints

Tests CRUD operations, permissions, and error handling for evidence items.
Following Arrange-Act-Assert pattern with comprehensive coverage.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, EvidenceItem

pytestmark = pytest.mark.unit


class TestEvidenceCreate:
    """Tests for POST /curations/{curation_id}/evidence"""

    def test_create_evidence_success(
        self,
        client: TestClient,
        curator_token: str,
        test_curation: CurationNew,
    ):
        """Test successful evidence item creation"""
        # Arrange
        evidence_data = {
            "evidence_category": "case_level",
            "evidence_type": "genetic",
            "evidence_data": {
                "proband_count": 5,
                "phenotype_specificity": "high",
            },
        }

        # Act
        response = client.post(
            f"/api/v1/curations/{test_curation.id}/evidence",
            json=evidence_data,
            headers={"Authorization": f"Bearer {curator_token}"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["evidence_category"] == "case_level"
        assert data["evidence_type"] == "genetic"
        assert "id" in data
        assert data["validation_status"] == "pending"

    def test_create_evidence_unauthorized(
        self,
        client: TestClient,
        test_curation: CurationNew,
    ):
        """Test evidence creation without authentication

        Note: FastAPI's HTTPBearer returns 403 (not 401) when no credentials
        are provided, per OAuth 2.0 Bearer Token spec (RFC 6750).
        """
        # Arrange
        evidence_data = {
            "evidence_category": "case_level",
            "evidence_type": "genetic",
            "evidence_data": {},
        }

        # Act
        response = client.post(
            f"/api/v1/curations/{test_curation.id}/evidence",
            json=evidence_data,
        )

        # Assert - HTTPBearer returns 403 for missing credentials
        assert response.status_code == 403

    def test_create_evidence_forbidden_viewer(
        self,
        client: TestClient,
        viewer_token: str,
        test_curation: CurationNew,
    ):
        """Test viewers cannot create evidence"""
        # Arrange
        evidence_data = {
            "evidence_category": "case_level",
            "evidence_type": "genetic",
            "evidence_data": {},
        }

        # Act
        response = client.post(
            f"/api/v1/curations/{test_curation.id}/evidence",
            json=evidence_data,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 403

    def test_create_evidence_curation_not_found(
        self,
        client: TestClient,
        curator_token: str,
    ):
        """Test evidence creation for non-existent curation"""
        # Arrange
        import uuid
        fake_id = uuid.uuid4()
        evidence_data = {
            "evidence_category": "case_level",
            "evidence_type": "genetic",
            "evidence_data": {},
        }

        # Act
        response = client.post(
            f"/api/v1/curations/{fake_id}/evidence",
            json=evidence_data,
            headers={"Authorization": f"Bearer {curator_token}"},
        )

        # Assert
        assert response.status_code == 404


class TestEvidenceList:
    """Tests for GET /curations/{curation_id}/evidence"""

    def test_list_evidence_success(
        self,
        client: TestClient,
        curator_token: str,
        test_curation: CurationNew,
        test_evidence_item: EvidenceItem,
    ):
        """Test successful evidence listing"""
        # Act
        response = client.get(
            f"/api/v1/curations/{test_curation.id}/evidence",
            headers={"Authorization": f"Bearer {curator_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == str(test_evidence_item.id)

    def test_list_evidence_viewer_allowed(
        self,
        client: TestClient,
        viewer_token: str,
        test_curation: CurationNew,
    ):
        """Test viewers can list evidence"""
        # Act
        response = client.get(
            f"/api/v1/curations/{test_curation.id}/evidence",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 200


class TestEvidenceUpdate:
    """Tests for PUT /curations/{curation_id}/evidence/{item_id}"""

    def test_update_evidence_success(
        self,
        client: TestClient,
        curator_token: str,
        test_curation: CurationNew,
        test_evidence_item: EvidenceItem,
    ):
        """Test successful evidence update"""
        # Arrange
        update_data = {
            "evidence_data": {
                "proband_count": 15,
                "phenotype_specificity": "very_high",
            },
        }

        # Act
        response = client.put(
            f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {curator_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_data"]["proband_count"] == 15

    def test_update_evidence_viewer_forbidden(
        self,
        client: TestClient,
        viewer_token: str,
        test_curation: CurationNew,
        test_evidence_item: EvidenceItem,
    ):
        """Test viewers cannot update evidence"""
        # Arrange
        update_data = {"evidence_data": {}}

        # Act
        response = client.put(
            f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 403


class TestEvidenceDelete:
    """Tests for DELETE /curations/{curation_id}/evidence/{item_id}"""

    def test_delete_evidence_success(
        self,
        client: TestClient,
        db_session: Session,
        curator_token: str,
        test_curation: CurationNew,
        test_evidence_item: EvidenceItem,
    ):
        """Test successful evidence deletion (soft delete)"""
        # Act
        response = client.delete(
            f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}",
            headers={"Authorization": f"Bearer {curator_token}"},
        )

        # Assert
        assert response.status_code == 204

        # Verify soft delete
        db_session.refresh(test_evidence_item)
        assert test_evidence_item.is_deleted is True

    def test_delete_evidence_viewer_forbidden(
        self,
        client: TestClient,
        viewer_token: str,
        test_curation: CurationNew,
        test_evidence_item: EvidenceItem,
    ):
        """Test viewers cannot delete evidence"""
        # Act
        response = client.delete(
            f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 403
