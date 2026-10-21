"""A curation created with a precuration link shows that precuration's disease (#409)."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.models import Gene, PrecurationNew, Scope, UserNew, WorkflowPair
from tests.api.scopes.factories import auth_headers

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite() -> Iterator[None]:
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


def test_linked_curation_shows_the_precuration_disease(
    client: TestClient,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    approved_precuration: PrecurationNew,
) -> None:
    headers = auth_headers(test_user_admin)
    created = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "workflow_pair_id": str(test_workflow_pair.id),
            "precuration_id": str(approved_precuration.id),
            "evidence_data": {"genetic_evidence": {}},
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    curation_id = created.json()["id"]

    detail = client.get(f"/api/v1/curations/{curation_id}", headers=headers).json()
    assert detail["precuration_id"] == str(approved_precuration.id)
    assert detail["disease_name"] == "Test Disease"

    listing = client.get(
        "/api/v1/curations/", params={"scope_id": str(test_scope.id)}, headers=headers
    ).json()
    row = next(c for c in listing["curations"] if c["id"] == curation_id)
    assert row["disease_name"] == "Test Disease"
