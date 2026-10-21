"""Curators may not reassign or edit gene assignments (scope admins only)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope, UserNew
from tests.api.test_gene_assignments_api import BASE, _assignment, _auth

pytestmark = pytest.mark.unit


def test_curator_cannot_reassign_or_unassign_curator(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)

    assigned = client.post(
        f"{BASE}/{row.id}/assign-curator",
        json={"curator_id": str(test_user_curator.id)},
        headers=_auth(curator_token),
    )
    cleared = client.post(
        f"{BASE}/{row.id}/unassign-curator", headers=_auth(curator_token)
    )

    assert assigned.status_code == 403
    assert cleared.status_code == 403


def test_curator_cannot_update_assignment_changes_priority_and_notes(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)

    response = client.put(
        f"{BASE}/{row.id}",
        json={"priority_level": "low", "assignment_notes": "later"},
        headers=_auth(curator_token),
    )

    assert response.status_code == 403
