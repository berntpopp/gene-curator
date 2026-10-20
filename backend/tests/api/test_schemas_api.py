"""API tests for curation schema endpoints (/api/v1/schemas/curation-schemas).

Covers authentication, owner/admin permission checks, duplicate and in-use guards,
validation and compatible-engine lookup. Fixtures insert schema rows directly so
tests do not depend on the create endpoint unless they exercise it.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationSchema, Scope, UserNew
from tests.api.schema_api_support import (
    auth,
    insert_pair,
    insert_schema,
    schema_payload,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas"


@pytest.fixture
def owned_schema(db_session: Session, test_user_curator: UserNew) -> CurationSchema:
    return insert_schema(db_session, name="Owned", created_by=test_user_curator.id)


# =============================================================================
# Authentication
# =============================================================================


class TestAuthentication:
    def test_list_requires_token(self, client: TestClient):
        response = client.get(f"{BASE}/curation-schemas")

        assert response.status_code in (401, 403)

    def test_scoring_engines_requires_token(self, client: TestClient):
        response = client.get(f"{BASE}/scoring-engines")

        assert response.status_code in (401, 403)


# =============================================================================
# Curation schemas: read
# =============================================================================


class TestCurationSchemaRead:
    def test_list_returns_active_schemas_for_any_user(
        self, client: TestClient, db_session: Session, viewer_token: str
    ):
        insert_schema(db_session, name="Active One")
        insert_schema(db_session, name="Inactive One", is_active=False)

        response = client.get(f"{BASE}/curation-schemas", headers=auth(viewer_token))

        assert response.status_code == 200
        names = [s["name"] for s in response.json()]
        assert names == ["Active One"]

    def test_list_active_only_false_includes_inactive(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        insert_schema(db_session, name="Inactive Two", is_active=False)

        response = client.get(
            f"{BASE}/curation-schemas",
            params={"active_only": False},
            headers=auth(admin_token),
        )

        assert response.status_code == 200
        assert "Inactive Two" in [s["name"] for s in response.json()]

    def test_list_filters_by_type_and_institution(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        insert_schema(db_session, name="A", schema_type="precuration", institution="X")
        insert_schema(db_session, name="B", schema_type="curation", institution="X")
        insert_schema(db_session, name="C", schema_type="curation", institution="Y")

        response = client.get(
            f"{BASE}/curation-schemas",
            params={"schema_type": "curation", "institution": "X"},
            headers=auth(admin_token),
        )

        assert [s["name"] for s in response.json()] == ["B"]

    def test_list_pagination(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        for i in range(3):
            insert_schema(db_session, name=f"Page {i}", version=f"{i}.0")

        response = client.get(
            f"{BASE}/curation-schemas",
            params={"skip": 1, "limit": 1},
            headers=auth(admin_token),
        )

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_by_id(
        self, client: TestClient, owned_schema: CurationSchema, viewer_token: str
    ):
        response = client.get(
            f"{BASE}/curation-schemas/{owned_schema.id}", headers=auth(viewer_token)
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Owned"

    def test_get_unknown_id_is_404(self, client: TestClient, viewer_token: str):
        response = client.get(
            f"{BASE}/curation-schemas/{uuid4()}", headers=auth(viewer_token)
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Schema not found"


# =============================================================================
# Curation schemas: create / update / delete
# =============================================================================


class TestCurationSchemaWrite:
    def test_create_accepts_seeded_workflow_states_format(
        self, client: TestClient, curator_token: str
    ):
        """Regression: the seeded {"states": [...]} shape must be accepted on create."""
        response = client.post(
            f"{BASE}/curation-schemas",
            json=schema_payload(name="Seeded Shape"),
            headers=auth(curator_token),
        )

        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Seeded Shape"

    def test_create_duplicate_name_version_rejected(
        self, client: TestClient, db_session: Session, curator_token: str
    ):
        insert_schema(db_session, name="Dup", version="2.0")

        response = client.post(
            f"{BASE}/curation-schemas",
            json=schema_payload(name="Dup", version="2.0"),
            headers=auth(curator_token),
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_missing_required_fields_is_422(
        self, client: TestClient, curator_token: str
    ):
        response = client.post(
            f"{BASE}/curation-schemas",
            json={"name": "No body"},
            headers=auth(curator_token),
        )

        assert response.status_code == 422

    def test_update_by_owner(
        self, client: TestClient, owned_schema: CurationSchema, curator_token: str
    ):
        response = client.put(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            json={"description": "updated"},
            headers=auth(curator_token),
        )

        assert response.status_code == 200
        assert response.json()["description"] == "updated"

    def test_update_by_other_user_forbidden(
        self, client: TestClient, owned_schema: CurationSchema, other_token: str
    ):
        response = client.put(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            json={"description": "hijack"},
            headers=auth(other_token),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Can only update own schemas"

    def test_update_by_admin_allowed(
        self, client: TestClient, owned_schema: CurationSchema, admin_token: str
    ):
        response = client.put(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            json={"is_active": False},
            headers=auth(admin_token),
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_update_unknown_is_404(self, client: TestClient, admin_token: str):
        response = client.put(
            f"{BASE}/curation-schemas/{uuid4()}",
            json={"description": "x"},
            headers=auth(admin_token),
        )

        assert response.status_code == 404

    def test_delete_requires_admin(
        self, client: TestClient, owned_schema: CurationSchema, curator_token: str
    ):
        response = client.delete(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            headers=auth(curator_token),
        )

        assert response.status_code == 403

    def test_delete_by_admin(
        self, client: TestClient, owned_schema: CurationSchema, admin_token: str
    ):
        response = client.delete(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            headers=auth(admin_token),
        )

        assert response.status_code == 200
        gone = client.get(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            headers=auth(admin_token),
        )
        assert gone.status_code == 404

    def test_delete_refused_when_in_use(
        self,
        client: TestClient,
        db_session: Session,
        admin_token: str,
    ):
        precur = insert_schema(db_session, name="P", schema_type="precuration")
        cur = insert_schema(db_session, name="C", schema_type="curation")
        insert_pair(db_session, precur, cur, name="in-use")

        response = client.delete(
            f"{BASE}/curation-schemas/{cur.id}", headers=auth(admin_token)
        )

        assert response.status_code == 400
        assert "in use" in response.json()["detail"]


# =============================================================================
# Curation schemas: validate and compatible engines
# =============================================================================


class TestCurationSchemaValidateAndEngines:
    def test_validate_seeded_shape_is_valid(
        self, client: TestClient, db_session: Session, viewer_token: str
    ):
        schema = insert_schema(db_session, name="Valid Shape")

        response = client.post(
            f"{BASE}/curation-schemas/{schema.id}/validate",
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is True, body
        assert body["field_count"] == 1

    def test_validate_reports_missing_states(
        self, client: TestClient, db_session: Session, viewer_token: str
    ):
        schema = insert_schema(
            db_session,
            name="No Submitted",
            workflow_states={"states": [{"name": "draft"}]},
        )

        response = client.post(
            f"{BASE}/curation-schemas/{schema.id}/validate",
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        assert response.json()["is_valid"] is False

    def test_compatible_engines_for_clingen_schema(
        self, client: TestClient, db_session: Session, viewer_token: str
    ):
        schema = insert_schema(db_session, name="ClinGen_SOP_11.0", version="11.0")

        response = client.get(
            f"{BASE}/curation-schemas/{schema.id}/compatible-engines",
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        assert response.json() == ["clingen_sop_v11"]

    def test_compatible_engines_empty_for_unknown_schema(
        self, client: TestClient, db_session: Session, viewer_token: str
    ):
        schema = insert_schema(db_session, name="Homegrown")

        response = client.get(
            f"{BASE}/curation-schemas/{schema.id}/compatible-engines",
            headers=auth(viewer_token),
        )

        assert response.json() == []


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
