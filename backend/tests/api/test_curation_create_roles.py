"""Only scope curators/admins (and platform admins) may create curations (#196)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope, WorkflowPair
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


@pytest.mark.parametrize(
    ("scope_role", "expected"),
    [("curator", 201), ("admin", 201), ("reviewer", 403), ("viewer", 403)],
)
def test_create_curation_by_scope_role(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    scope_role: str,
    expected: int,
):
    user = make_user(db_session)
    make_member(db_session, test_scope, user, scope_role)
    response = client.post(
        "/api/v1/curations/",
        headers=auth_headers(user),
        json={
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "workflow_pair_id": str(test_workflow_pair.id),
            "evidence_data": {},
        },
    )
    assert response.status_code == expected, response.text
