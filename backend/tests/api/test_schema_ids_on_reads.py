"""MCP study round 2 finding 4: curation and scope reads carry the workflow pair's schema
ids, and create_precuration takes its schema from the scope's pair when none is given."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    CurationNew,
    CurationSchema,
    Gene,
    Scope,
    WorkflowPair,
)
from app.schemas.scope import ScopeStatistics

pytestmark = pytest.mark.unit


@pytest.fixture
def paired(
    db_session: Session,
    test_scope: Scope,
    test_workflow_pair: WorkflowPair,
    test_precuration_schema: CurationSchema,
) -> WorkflowPair:
    test_workflow_pair.precuration_schema_id = test_precuration_schema.id
    test_scope.default_workflow_pair_id = test_workflow_pair.id
    db_session.commit()
    return test_workflow_pair


def test_curation_and_scope_reads_carry_schema_ids(
    client: TestClient,
    admin_token: str,
    paired: WorkflowPair,
    test_scope: Scope,
    test_curation: CurationNew,
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    curation = client.get(f"/api/v1/curations/{test_curation.id}", headers=headers)
    assert curation.json()["precuration_schema_id"] == str(paired.precuration_schema_id)
    assert curation.json()["curation_schema_id"] is None

    zeros = {n: 0 for n, f in ScopeStatistics.model_fields.items() if f.is_required()}
    with patch("app.crud.scope.scope_crud.get_detailed_statistics", return_value=zeros):
        scope = client.get(f"/api/v1/scopes/{test_scope.id}", headers=headers).json()
    assert scope["default_workflow_pair_id"] == str(paired.id)
    assert scope["precuration_schema_id"] == str(paired.precuration_schema_id)


def test_create_precuration_defaults_its_schema_from_the_scope_pair(
    client: TestClient,
    admin_token: str,
    paired: WorkflowPair,
    test_scope: Scope,
    test_gene: Gene,
) -> None:
    response = client.post(
        "/api/v1/precurations/",
        json={"gene_id": str(test_gene.id), "scope_id": str(test_scope.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["precuration_schema_id"] == str(paired.precuration_schema_id)


def test_create_precuration_without_any_schema_is_a_400(
    client: TestClient, admin_token: str, test_scope: Scope, test_gene: Gene
) -> None:
    response = client.post(
        "/api/v1/precurations/",
        json={"gene_id": str(test_gene.id), "scope_id": str(test_scope.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "precuration_schema_id" in response.json()["detail"]
