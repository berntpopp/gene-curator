"""API tests for bulk curator assignment on /gene-assignments/bulk."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, GeneScopeAssignment, Scope, UserNew
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
            "assignment_notes": "bulk note",
        },
        headers=_auth(curator_token),
    )

    assert response.status_code == 200
    assert response.json()["total_created"] == 2
    for row in (first, second):
        db_session.refresh(row)
        assert row.assignment_notes == "bulk note"
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


def test_bulk_assign_rejects_viewer_assignee_and_non_member_admin(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_viewer: UserNew,
    test_user_admin: UserNew,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)
    for assignee in (test_user_viewer, test_user_admin):
        response = client.post(
            f"{BASE}/bulk",
            json={
                "gene_ids": [str(test_gene.id)],
                "scope_id": str(test_scope.id),
                "assigned_curator_id": str(assignee.id),
            },
            headers=_auth(curator_token),
        )
        assert response.status_code == 400
    db_session.refresh(row)
    assert row.assigned_curator_id is None


def test_bulk_assign_failure_on_later_gene_leaves_earlier_unassigned(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    response = client.post(
        f"{BASE}/bulk",
        json={
            "gene_ids": [str(test_gene.id), str(uuid4())],
            "scope_id": str(test_scope.id),
        },
        headers=_auth(curator_token),
    )

    assert response.status_code == 400
    db_session.expire_all()
    assert (
        db_session.query(GeneScopeAssignment).filter_by(scope_id=test_scope.id).count()
        == 0
    )


def test_bulk_assign_requires_edit_rights_in_scope(
    client: TestClient,
    db_session: Session,
    viewer_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)
    response = client.post(
        f"{BASE}/bulk",
        json={
            "gene_ids": [str(test_gene.id)],
            "scope_id": str(test_scope.id),
            "assigned_curator_id": str(test_user_curator.id),
        },
        headers=_auth(viewer_token),
    )
    assert response.status_code == 403
    db_session.refresh(row)
    assert row.assigned_curator_id is None
