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


# Shape of the seeded "ClinGen Precuration" schema (016_seed_precuration_schema.sql)
SEEDED_SECTIONS = {
    "sections": [
        {
            "id": "disease_entity",
            "label": "Disease Entity Definition",
            "fields": [
                {"id": "mondo_id", "label": "Mondo Disease ID", "required": True},
                {"id": "disease_name", "label": "Disease Name", "required": True},
                {"id": "notes", "label": "Notes", "required": False},
            ],
        },
        {
            "id": "metadata",
            "label": "Precuration Metadata",
            "fields": [{"id": "affiliation", "label": "Affiliation", "required": True}],
        },
    ]
}
SEEDED_RULES = {"required_fields": ["mondo_id", "disease_name", "mode_of_inheritance"]}


def _precuration(
    db_session, scope, gene, user, evidence, fields=None, rules=None
) -> PrecurationNew:
    schema = CurationSchema(
        id=uuid4(),
        name=f"Req {uuid4()}",
        version="1.0",
        schema_type="precuration",
        is_active=True,
        field_definitions=FIELDS if fields is None else fields,
        validation_rules=rules or {},
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


def test_seeded_sections_schema_blocks_an_empty_submit(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
):
    p = _precuration(
        db_session,
        test_scope,
        test_gene,
        test_user_admin,
        {"mondo_id": "MONDO:0000001"},
        SEEDED_SECTIONS,
        SEEDED_RULES,
    )

    response = _submit(client, admin_token, p)

    assert response.status_code == 422
    assert set(response.json()["detail"]["fields"]) == {
        "disease_name",
        "affiliation",
        "mode_of_inheritance",
    }


def test_list_reads_disease_from_nested_entity_definition(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
):
    evidence = {
        "entity_definition": {
            "disease_name": "Nested disease",
            "mondo_id": "MONDO:0000009",
            "mode_of_inheritance": "autosomal_dominant",
        }
    }
    _precuration(db_session, test_scope, test_gene, test_user_admin, evidence)

    response = client.get(
        "/api/v1/precurations/", headers={"Authorization": f"Bearer {admin_token}"}
    )

    row = response.json()["precurations"][0]
    assert row["disease_name"] == "Nested disease"
    assert row["mondo_id"] == "MONDO:0000009"
    assert row["mode_of_inheritance"] == "autosomal_dominant"
