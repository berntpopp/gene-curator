"""API tests for workflow pair and scoring engine endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationSchema, Scope, UserNew
from tests.api.schema_api_support import (
    auth,
    insert_pair,
    insert_schema,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas"


# =============================================================================
# Workflow pairs
# =============================================================================


@pytest.fixture
def schema_pair(db_session: Session) -> tuple[CurationSchema, CurationSchema]:
    precur = insert_schema(db_session, name="Precur", schema_type="precuration")
    cur = insert_schema(db_session, name="Cur", schema_type="curation")
    return precur, cur


class TestWorkflowPairs:
    def test_create_pair(
        self,
        client: TestClient,
        schema_pair,
        curator_token: str,
    ):
        precur, cur = schema_pair

        response = client.post(
            f"{BASE}/workflow-pairs",
            json={
                "name": "clingen",
                "version": "1.0",
                "precuration_schema_id": str(precur.id),
                "curation_schema_id": str(cur.id),
            },
            headers=auth(curator_token),
        )

        assert response.status_code == 200, response.text
        assert response.json()["name"] == "clingen"

    def test_create_rejects_wrong_schema_types(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        cur_a = insert_schema(db_session, name="CurA", schema_type="curation")
        cur_b = insert_schema(db_session, name="CurB", schema_type="curation")

        response = client.post(
            f"{BASE}/workflow-pairs",
            json={
                "name": "bad",
                "version": "1.0",
                "precuration_schema_id": str(cur_a.id),
                "curation_schema_id": str(cur_b.id),
            },
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert "Precuration schema must be" in response.json()["detail"]

    def test_create_rejects_missing_schema(
        self, client: TestClient, schema_pair, admin_token: str
    ):
        precur, _ = schema_pair

        response = client.post(
            f"{BASE}/workflow-pairs",
            json={
                "name": "ghost",
                "version": "1.0",
                "precuration_schema_id": str(precur.id),
                "curation_schema_id": str(uuid4()),
            },
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Curation schema not found"

    def test_create_rejects_duplicate(
        self,
        client: TestClient,
        db_session: Session,
        schema_pair,
        admin_token: str,
    ):
        precur, cur = schema_pair
        insert_pair(db_session, precur, cur, name="dup", version="9.0")

        response = client.post(
            f"{BASE}/workflow-pairs",
            json={
                "name": "dup",
                "version": "9.0",
                "precuration_schema_id": str(precur.id),
                "curation_schema_id": str(cur.id),
            },
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_list_and_get(
        self,
        client: TestClient,
        db_session: Session,
        schema_pair,
        viewer_token: str,
    ):
        precur, cur = schema_pair
        pair = insert_pair(db_session, precur, cur, name="listed")

        listing = client.get(f"{BASE}/workflow-pairs", headers=auth(viewer_token))
        single = client.get(
            f"{BASE}/workflow-pairs/{pair.id}", headers=auth(viewer_token)
        )
        missing = client.get(
            f"{BASE}/workflow-pairs/{uuid4()}", headers=auth(viewer_token)
        )

        assert [p["name"] for p in listing.json()] == ["listed"]
        assert single.json()["id"] == str(pair.id)
        assert missing.status_code == 404

    def test_update_permissions(
        self,
        client: TestClient,
        db_session: Session,
        schema_pair,
        curator_token: str,
        other_token: str,
        test_user_curator: UserNew,
    ):
        precur, cur = schema_pair
        pair = insert_pair(
            db_session, precur, cur, name="owned", created_by=test_user_curator.id
        )
        url = f"{BASE}/workflow-pairs/{pair.id}"

        forbidden = client.put(
            url, json={"description": "x"}, headers=auth(other_token)
        )
        allowed = client.put(
            url, json={"description": "mine"}, headers=auth(curator_token)
        )

        assert forbidden.status_code == 403
        assert allowed.status_code == 200
        assert allowed.json()["description"] == "mine"

    def test_delete_requires_admin(
        self,
        client: TestClient,
        db_session: Session,
        schema_pair,
        curator_token: str,
        admin_token: str,
    ):
        precur, cur = schema_pair
        pair = insert_pair(db_session, precur, cur, name="deletable")
        url = f"{BASE}/workflow-pairs/{pair.id}"

        forbidden = client.delete(url, headers=auth(curator_token))
        allowed = client.delete(url, headers=auth(admin_token))

        assert forbidden.status_code == 403
        assert allowed.status_code == 200
        assert allowed.json() == {"message": "Workflow pair deleted successfully"}

    def test_delete_refused_when_default_for_scope(
        self,
        client: TestClient,
        db_session: Session,
        schema_pair,
        admin_token: str,
        test_scope: Scope,
    ):
        precur, cur = schema_pair
        pair = insert_pair(db_session, precur, cur, name="scope-default")
        test_scope.default_workflow_pair_id = pair.id
        db_session.commit()

        response = client.delete(
            f"{BASE}/workflow-pairs/{pair.id}", headers=auth(admin_token)
        )

        assert response.status_code == 400
        assert "in use" in response.json()["detail"]

    def test_update_and_delete_unknown_are_404(
        self, client: TestClient, admin_token: str
    ):
        url = f"{BASE}/workflow-pairs/{uuid4()}"

        assert client.put(url, json={}, headers=auth(admin_token)).status_code == 404
        assert client.delete(url, headers=auth(admin_token)).status_code == 404


# =============================================================================
# Scoring engines
# =============================================================================


class TestScoringEngines:
    def test_list_engines(self, client: TestClient, viewer_token: str):
        response = client.get(f"{BASE}/scoring-engines", headers=auth(viewer_token))

        assert response.status_code == 200
        names = {e["name"] for e in response.json()}
        assert {"clingen_sop_v11", "gencc_based", "qualitative_assessment"} <= names

    def test_engine_info(self, client: TestClient, viewer_token: str):
        response = client.get(
            f"{BASE}/scoring-engines/clingen_sop_v11", headers=auth(viewer_token)
        )

        assert response.status_code == 200
        assert response.json()["version"] == "11.0.0"

    def test_unknown_engine_info_is_404(self, client: TestClient, viewer_token: str):
        response = client.get(
            f"{BASE}/scoring-engines/nope", headers=auth(viewer_token)
        )

        assert response.status_code == 404

    def test_validate_with_engine_reports_errors(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/scoring-engines/clingen_sop_v11/validate",
            json={"evidence_data": {"genetic_evidence": []}, "schema_config": {}},
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is False
        assert "At least one genetic evidence item is required" in body["errors"]

    def test_validate_unknown_engine_is_reported_not_raised(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/scoring-engines/nope/validate",
            json={"evidence_data": {}, "schema_config": {}},
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        assert response.json()["is_valid"] is False

    def test_calculate_nested_clingen_evidence(
        self, client: TestClient, viewer_token: str
    ):
        """Regression: nested SOP v11 evidence used to crash the calculate endpoint."""
        evidence = {
            "genetic_evidence": {
                "case_level": {
                    "autosomal_dominant_or_x_linked": {
                        "predicted_or_proven_null": [
                            {"pmid": "12345678", "proband_counted_points": 1.5},
                            {"pmid": "23456789", "proband_counted_points": 1.5},
                        ]
                    }
                }
            },
            "experimental_evidence": {},
        }

        response = client.post(
            f"{BASE}/scoring-engines/clingen_sop_v11/calculate",
            json={"evidence_data": evidence, "schema_config": {}},
            headers=auth(viewer_token),
        )

        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert result["total_score"] == pytest.approx(3.0)
        assert result["verdict"] == "limited"

    def test_calculate_qualitative(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/scoring-engines/qualitative_assessment/calculate",
            json={
                "evidence_data": {
                    "clinical_assessment": {
                        "phenotype_match": "excellent",
                        "inheritance_consistency": "consistent",
                    }
                },
                "schema_config": {},
                "scope_context": {"scope": "x"},
            },
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["engine_name"] == "qualitative_assessment"
        assert body["result"]["total_score"] == pytest.approx(5.0)
        assert body["result"]["verdict"] == "Moderate Association"

    def test_calculate_unknown_engine_is_404(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/scoring-engines/nope/calculate",
            json={"evidence_data": {}, "schema_config": {}},
            headers=auth(viewer_token),
        )

        assert response.status_code == 404


@pytest.fixture
def other_curator(db_session: Session, test_scope: Scope) -> UserNew:
    """A second non-admin user, used to prove ownership checks."""
    from app.core.security import get_password_hash
    from app.models.models import ScopeMembership

    user = UserNew(
        id=uuid4(),
        email="other_curator@test.com",
        hashed_password=get_password_hash("other123"),
        name="Other Curator",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.add(
        ScopeMembership(scope_id=test_scope.id, user_id=user.id, role="curator")
    )
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_token(other_curator: UserNew) -> str:
    from app.core.security import create_access_token

    return create_access_token(
        data={
            "sub": str(other_curator.id),
            "email": other_curator.email,
            "role": "user",
        }
    )
