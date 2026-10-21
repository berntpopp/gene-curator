"""Submitting a precuration rejects missing required schema fields with 422."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationSchema, Gene, PrecurationNew, Scope, UserNew

pytestmark = pytest.mark.unit

FIELDS = {
    "entity_definition": {
        "type": "object",
        "properties": {
            "disease_name": {"type": "string", "required": True},
            "mode_of_inheritance": {"type": "enum", "required": True},
        },
    },
    "notes": {"type": "string", "required": True},
    "optional": {"type": "string"},
}


@pytest.fixture(autouse=True)
def _no_rls():
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


def _precuration(db_session, scope, gene, user, evidence) -> PrecurationNew:
    schema = CurationSchema(
        id=uuid4(),
        name=f"Req {uuid4()}",
        version="1.0",
        schema_type="precuration",
        is_active=True,
        field_definitions=FIELDS,
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex,
    )
    db_session.add(schema)
    db_session.flush()
    p = PrecurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        precuration_schema_id=schema.id,
        workflow_stage="precuration",
        evidence_data=evidence,
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(p)
    db_session.commit()
    return p


def _submit(client: TestClient, token: str, p: PrecurationNew):
    return client.post(
        f"/api/v1/precurations/{p.id}/submit",
        json={"notes": "go"},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_empty_precuration_cannot_be_submitted(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
):
    p = _precuration(db_session, test_scope, test_gene, test_user_admin, {})

    response = _submit(client, admin_token, p)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert set(detail["fields"]) == {
        "entity_definition.disease_name",
        "entity_definition.mode_of_inheritance",
        "notes",
    }


def test_partially_filled_lists_only_the_missing_fields(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
):
    evidence = {"entity_definition": {"disease_name": "X", "mode_of_inheritance": " "}}
    p = _precuration(db_session, test_scope, test_gene, test_user_admin, evidence)

    response = _submit(client, admin_token, p)

    assert response.status_code == 422
    assert set(response.json()["detail"]["fields"]) == {
        "entity_definition.mode_of_inheritance",
        "notes",
    }
