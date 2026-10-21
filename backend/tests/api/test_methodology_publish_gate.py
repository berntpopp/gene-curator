"""Publish gate (#269): an invalid definition is refused and inserts no version."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationSchema
from tests.api.schema_api_support import auth, insert_schema

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas/curation-schemas"
STAGES = {
    "entry": {"allowed_transitions": ["precuration"]},
    "precuration": {"allowed_transitions": ["curation", "review"]},
    "curation": {"allowed_transitions": ["review"]},
    "review": {"allowed_transitions": ["active", "curation"], "reviewers_required": 1},
    "active": {"allowed_transitions": ["review"]},
}
CLINGEN = {"engine": "clingen_sop_v11"}


def _publish(client: TestClient, token: str, schema: CurationSchema) -> Any:
    return client.post(f"{BASE}/{schema.id}/versions", headers=auth(token))


def _versions(client: TestClient, token: str, schema: CurationSchema) -> list[Any]:
    listed = client.get(f"{BASE}/{schema.id}/versions", headers=auth(token)).json()
    assert isinstance(listed, list)
    return listed


@pytest.mark.parametrize(
    ("workflow_states", "scoring", "error"),
    [
        # monkey bug 6: only review left, reviewers out of range
        ({"review": {"reviewers_required": 9}}, CLINGEN, "reviewers_required"),
        ({"review": {"reviewers_required": 2}}, CLINGEN, "required stage: entry"),
        (
            STAGES,
            {**CLINGEN, "point_model": {"sections": [{"key": "g"}]}},
            "point_model",
        ),
    ],
)
def test_invalid_definition_is_refused_and_inserts_no_version(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    workflow_states: dict[str, Any],
    scoring: dict[str, Any],
    error: str,
) -> None:
    schema = insert_schema(
        db_session, workflow_states=workflow_states, scoring_configuration=scoring
    )
    r = _publish(client, admin_token, schema)
    assert r.status_code == 422, r.text
    assert any(error in e for e in r.json()["detail"]["errors"]), r.text
    assert _versions(client, admin_token, schema) == []
