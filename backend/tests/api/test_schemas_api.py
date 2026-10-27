"""API tests for curation schema endpoints (/api/v1/schemas/curation-schemas).

Covers authentication, owner/admin permission checks, duplicate and in-use guards,
validation and compatible-engine lookup. Fixtures insert schema rows directly so
tests do not depend on the create endpoint unless they exercise it.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.schema_repository import schema_crud
from app.models.models import CurationSchema, Scope, UserNew
from tests.api.schema_api_support import (
    auth,
    insert_pair,
    insert_schema,
    schema_payload,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas"
DUPLICATE = "Schema with this name and version already exists"


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
        assert "field_definitions" not in response.json()[0]  # summary rows by default
        full = client.get(
            f"{BASE}/curation-schemas?detail=true", headers=auth(viewer_token)
        ).json()
        assert "field_definitions" in full[0]

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

    def test_get_compact_keeps_field_contract_and_drops_layout(
        self,
        client: TestClient,
        db_session: Session,
        owned_schema: CurationSchema,
        viewer_token: str,
    ):
        """MCP study finding 6: compact read for agents (types, required, values)."""
        option = {"value": "score", "label": "Score"}
        option = {"value": "score", "label": "Score"}
        default_by = {"field": "status", "values": {"score": 1.5}}
        owned_schema.field_definitions = {
            "summary": {"type": "string", "label": "S", "ui_component": "RichText"},
            "cases": {
                "type": "array",
                "label": "Cases",
                "items": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "select", "options": [option, "review"]},
                        "points": {
                            "type": "number",
                            "min": 0,
                            "default_by": default_by,
                        },
                    },
                },
            },
            "table": {
                "type": "evidence_table",
                "required_when": {"field": "moi", "equals": "AD"},
                "columns": [{"key": "pmid", "type": "string", "order": 1}],
            },
            "sections": [
                {
                    "id": "s",
                    "fields": [
                        {"id": "moi", "type": "text", "required": True, "default": "AD"}
                    ],
                }
            ],
        }
        owned_schema.scoring_configuration = {"engine": "x"}
        db_session.commit()

        response = client.get(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            params={"compact": True},
            headers=auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ui_configuration"] == {}
        assert body["scoring_configuration"] is None
        assert body["field_definitions"] == {
            "summary": {"type": "string"},
            "cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "select", "options": ["score", "review"]},
                        "points": {
                            "type": "number",
                            "min": 0,
                            "default_by": default_by,
                        },
                    },
                },
            },
            "table": {
                "type": "evidence_table",
                "required_when": {"field": "moi", "equals": "AD"},
                "columns": [{"key": "pmid", "type": "string"}],
            },
            "moi": {"id": "moi", "type": "text", "required": True, "default": "AD"},
        }

    def test_get_path_returns_only_that_field(
        self,
        client: TestClient,
        db_session: Session,
        owned_schema: CurationSchema,
        viewer_token: str,
    ):
        """Round 3: agents asked 4 times to read one evidence table, not the schema."""
        row = {"pmid": {"type": "string", "label": "PMID"}}
        table = {"type": "array", "items": {"type": "object", "properties": row}}
        owned_schema.field_definitions = {
            "genetic_evidence": {
                "type": "object",
                "properties": {"segregation": table},
            },
            "other": {"type": "string"},
        }
        db_session.commit()

        def get(**params: object) -> Any:
            return client.get(
                f"{BASE}/curation-schemas/{owned_schema.id}",
                params=params,
                headers=auth(viewer_token),
            )

        path = "genetic_evidence.segregation"
        assert get(path=path).json()["field_definitions"] == {path: table}
        compact = get(path=f"{path}.pmid", compact=True).json()
        assert compact["field_definitions"] == {f"{path}.pmid": {"type": "string"}}
        missing = get(path="genetic_evidence.case_level")
        assert missing.status_code == 400
        assert (
            "no 'case_level' here; choose from segregation" in missing.json()["detail"]
        )
        assert "single field" in get(path="other.x").json()["detail"]

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
        self, client: TestClient, admin_token: str
    ):
        """Regression: the seeded {"states": [...]} shape must be accepted on create."""
        response = client.post(
            f"{BASE}/curation-schemas",
            json=schema_payload(name="Seeded Shape"),
            headers=auth(admin_token),
        )

        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Seeded Shape"

    def test_create_duplicate_name_version_rejected(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        insert_schema(db_session, name="Dup", version="2.0")

        response = client.post(
            f"{BASE}/curation-schemas",
            json=schema_payload(name="Dup", version="2.0"),
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_losing_a_race_gets_the_same_400(
        self,
        client: TestClient,
        db_session: Session,
        admin_token: str,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """#432: the check passed, a concurrent create took the name; the constraint decides."""
        insert_schema(db_session, name="Race", version="1.0")
        monkeypatch.setattr(
            schema_crud, "get_by_name_and_version", lambda *a, **k: None
        )

        response = client.post(
            f"{BASE}/curation-schemas",
            json=schema_payload(name="Race", version="1.0"),
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == DUPLICATE

    def test_rename_to_taken_name_version_rejected(
        self, client: TestClient, db_session: Session, admin_token: str
    ):
        insert_schema(db_session, name="Taken", version="2.0")
        other = insert_schema(db_session, name="Other", version="2.0")

        response = client.put(
            f"{BASE}/curation-schemas/{other.id}",
            json={"name": "Taken"},
            headers=auth(admin_token),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == DUPLICATE
        kept = client.get(
            f"{BASE}/curation-schemas/{other.id}", headers=auth(admin_token)
        )
        assert kept.json()["name"] == "Other"

    @pytest.mark.parametrize(
        "field",
        [
            "name",
            "version",
            "field_definitions",
            "validation_rules",
            "workflow_states",
            "ui_configuration",
            "is_active",
            "use_dynamic_form",
        ],
    )
    def test_update_explicit_null_is_422_and_changes_nothing(
        self,
        client: TestClient,
        owned_schema: CurationSchema,
        admin_token: str,
        field: str,
    ):
        """Required response fields: omitting keeps the value, explicit null is invalid."""
        response = client.put(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            json={field: None},
            headers=auth(admin_token),
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", field]
        kept = client.get(
            f"{BASE}/curation-schemas/{owned_schema.id}", headers=auth(admin_token)
        )
        assert kept.json()["name"] == "Owned"

    def test_other_integrity_errors_are_not_reported_as_duplicates(
        self,
        client: TestClient,
        admin_token: str,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Only the name/version clash becomes the 400; anything else propagates as before."""

        def fail(*args: object, **kwargs: object) -> None:
            raise IntegrityError(
                "INSERT", {}, Exception("NOT NULL constraint failed: x.schema_hash")
            )

        monkeypatch.setattr(schema_crud, "create_with_owner", fail)

        with pytest.raises(IntegrityError, match="schema_hash"):
            client.post(
                f"{BASE}/curation-schemas",
                json=schema_payload(name="Other error"),
                headers=auth(admin_token),
            )

    def test_create_missing_required_fields_is_422(
        self, client: TestClient, admin_token: str
    ):
        response = client.post(
            f"{BASE}/curation-schemas",
            json={"name": "No body"},
            headers=auth(admin_token),
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("who", ["viewer_token", "curator_token", "other_token"])
    def test_non_admin_cannot_create_or_update(
        self,
        client: TestClient,
        owned_schema: CurationSchema,
        request: pytest.FixtureRequest,
        who: str,
    ):
        """#212: schema writes need platform admin, even for the schema's creator."""
        headers = auth(request.getfixturevalue(who))

        created = client.post(
            f"{BASE}/curation-schemas", json=schema_payload(), headers=headers
        )
        updated = client.put(
            f"{BASE}/curation-schemas/{owned_schema.id}",
            json={"description": "hijack"},
            headers=headers,
        )

        assert created.status_code == 403
        assert updated.status_code == 403

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
