"""MCP study round 6, T2: create and the submit 422 name the required fields and their
allowed values, so agents do not guess the precuration schema."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope, UserNew
from tests.api.test_precuration_submit_required import _no_rls, _precuration  # noqa: F401

FIELDS = {
    "entity_definition": {
        "type": "object",
        "properties": {
            "disease_name": {"type": "string", "required": True},
            "mode_of_inheritance": {
                "type": "enum",
                "required": True,
                "options": [{"value": "AD", "label": "Dominant"}, "AR"],
            },
        },
    },
    "optional": {"type": "string"},
}
MOI = {
    "path": "entity_definition.mode_of_inheritance",
    "type": "enum",
    "allowed": ["AD", "AR"],
}


def test_create_lists_required_fields_and_submit_422_names_them(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
) -> None:
    h = {"Authorization": f"Bearer {admin_token}"}
    p = _precuration(
        db_session,
        test_scope,
        test_gene,
        test_user_admin,
        {"entity_definition": {"disease_name": "X"}},
        fields=FIELDS,
    )
    created = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "precuration_schema_id": str(p.precuration_schema_id),
        },
        headers=h,
    )
    assert created.status_code == 200, created.text  # the open draft is returned
    assert created.json()["required_fields"] == [MOI]

    r = client.post(
        f"/api/v1/precurations/{p.id}/submit",
        json={"lock_version": p.lock_version},
        headers=h,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["required"] == [MOI]
    assert detail["schema"] == (
        f"get_curation_schema(schema_id={p.precuration_schema_id}, compact=true)"
    )
