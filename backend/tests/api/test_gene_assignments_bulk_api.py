"""API tests for bulk curator assignment on /gene-assignments/bulk."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope, UserNew
from tests.api.test_gene_assignments_api import BASE, _assignment, _auth, _outsider

pytestmark = pytest.mark.unit


def test_bulk_assign_curator_to_existing_unassigned_assignments(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    other = Gene(
        hgnc_id="HGNC:9999",
        approved_symbol="ZZZ1",
        record_hash="x" * 64,
        previous_symbols=[],
        alias_symbols=[],
    )
    db_session.add(other)
    db_session.commit()
    first = _assignment(db_session, test_gene, test_scope)
    second = _assignment(db_session, other, test_scope)

    response = client.post(
        f"{BASE}/bulk",
        json={
            "gene_ids": [str(test_gene.id), str(other.id)],
            "scope_id": str(test_scope.id),
            "assigned_curator_id": str(test_user_curator.id),
            "priority_level": "high",
        },
        headers=_auth(curator_token),
    )

    assert response.status_code == 200
    assert response.json()["total_created"] == 2
    for row in (first, second):
        db_session.refresh(row)
        assert row.assigned_curator_id == test_user_curator.id
        assert row.priority == "high"


def test_bulk_assign_invalid_curator_changes_nothing(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)
    outsider = _outsider(db_session)

    response = client.post(
        f"{BASE}/bulk",
        json={
            "gene_ids": [str(test_gene.id)],
            "scope_id": str(test_scope.id),
            "assigned_curator_id": str(outsider.id),
        },
        headers=_auth(curator_token),
    )

    assert response.status_code == 400
    db_session.refresh(row)
    assert row.assigned_curator_id is None
