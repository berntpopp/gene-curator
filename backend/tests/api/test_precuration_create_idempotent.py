"""POST /precurations/ is idempotent per creator while a draft is open."""

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    CurationSchema,
    CurationStatus,
    Gene,
    PrecurationNew,
    Scope,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_rls_context():
    with patch("app.api.v1.endpoints.precurations.set_rls_context"):
        yield


def test_create_returns_existing_draft_for_same_gene_scope_and_creator(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_precuration_schema: CurationSchema,
):
    """A repeated create (lost response) returns the open draft, not a second row."""
    body = {
        "gene_id": str(test_gene.id),
        "scope_id": str(test_scope.id),
        "precuration_schema_id": str(test_precuration_schema.id),
        "evidence_data": {"mondo_id": "MONDO:0000002"},
    }
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = client.post("/api/v1/precurations/", json=body, headers=headers)
    second = client.post("/api/v1/precurations/", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    # An archived draft no longer blocks a new one.
    row = db_session.get(PrecurationNew, UUID(first.json()["id"]))
    row.status = CurationStatus.ARCHIVED
    db_session.commit()
    third = client.post("/api/v1/precurations/", json=body, headers=headers)
    assert third.status_code == 201
    assert third.json()["id"] != first.json()["id"]
