"""API tests for /gene-assignments endpoints: scope access, admin-only actions and curator assignment."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.models import (
    CurationNew,
    Gene,
    GeneScopeAssignment,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/gene-assignments"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _outsider(db: Session) -> UserNew:
    """Active user with no scope membership."""
    user = UserNew(
        id=uuid4(),
        email="outsider@test.com",
        hashed_password=get_password_hash("outsider123"),
        name="Outsider",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _assignment(
    db: Session, gene: Gene, scope: Scope, **fields: object
) -> GeneScopeAssignment:
    values: dict[str, object] = {"is_active": True, **fields}
    row = GeneScopeAssignment(gene_id=gene.id, scope_id=scope.id, **values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_assignment_routes_require_authentication(client: TestClient) -> None:
    assert client.get(f"{BASE}/").status_code in (401, 403)
    assert client.get(f"{BASE}/{uuid4()}").status_code in (401, 403)


def test_create_assignment_defaults_priority_to_medium(
    client: TestClient,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    response = client.post(
        f"{BASE}/",
        json={"gene_id": str(test_gene.id), "scope_id": str(test_scope.id)},
        headers=_auth(curator_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is True
    assert body["priority"] == "medium"


def test_create_assignment_outside_scope_is_forbidden(
    client: TestClient,
    viewer_token: str,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    response = client.post(
        f"{BASE}/",
        json={"gene_id": str(test_gene.id), "scope_id": str(test_public_scope.id)},
        headers=_auth(viewer_token),
    )
    assert response.status_code == 403


def test_create_duplicate_active_assignment_is_rejected(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    _assignment(db_session, test_gene, test_scope)

    response = client.post(
        f"{BASE}/",
        json={"gene_id": str(test_gene.id), "scope_id": str(test_scope.id)},
        headers=_auth(curator_token),
    )

    assert response.status_code == 400
    assert "already assigned" in response.json()["detail"]


def test_create_after_deactivation_reuses_row(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    # Regression: the (gene, scope) pair is unique, so re-assigning a deactivated
    # gene must reactivate the existing row rather than insert a second one.
    old = _assignment(db_session, test_gene, test_scope, is_active=False)

    response = client.post(
        f"{BASE}/",
        json={
            "gene_id": str(test_gene.id),
            "scope_id": str(test_scope.id),
            "priority_level": "high",
        },
        headers=_auth(curator_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(old.id)
    assert response.json()["is_active"] is True
    assert response.json()["priority"] == "high"


def test_list_assignments_scope_filter(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    viewer_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
) -> None:
    _assignment(db_session, test_gene, test_scope)

    listed = client.get(
        f"{BASE}/?scope_id={test_scope.id}", headers=_auth(curator_token)
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    forbidden = client.get(
        f"{BASE}/?scope_id={test_public_scope.id}", headers=_auth(viewer_token)
    )
    assert forbidden.status_code == 403


def test_get_assignment_details_and_access(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    row = _assignment(
        db_session, test_gene, test_scope, assigned_curator_id=test_user_curator.id
    )

    found = client.get(f"{BASE}/{row.id}", headers=_auth(curator_token))
    assert found.status_code == 200
    body = found.json()
    assert body["gene_symbol"] == "BRCA1"
    assert body["scope_name"] == "test-scope"
    assert body["curator_email"] == "curator@test.com"

    assert (
        client.get(f"{BASE}/{uuid4()}", headers=_auth(curator_token)).status_code == 404
    )


def test_get_assignment_forbidden_for_non_member(
    client: TestClient,
    db_session: Session,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    from app.core.security import create_access_token

    outsider = _outsider(db_session)
    row = _assignment(db_session, test_gene, test_public_scope)
    token = create_access_token(
        data={"sub": str(outsider.id), "email": outsider.email, "role": "user"}
    )

    response = client.get(f"{BASE}/{row.id}", headers=_auth(token))
    assert response.status_code == 403


def test_update_assignment_changes_priority_and_notes(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)

    response = client.put(
        f"{BASE}/{row.id}",
        json={"priority_level": "low", "assignment_notes": "later"},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "low"
    assert response.json()["assignment_notes"] == "later"


def test_update_unknown_assignment_is_404(
    client: TestClient, curator_token: str
) -> None:
    response = client.put(
        f"{BASE}/{uuid4()}",
        json={"assignment_notes": "x"},
        headers=_auth(curator_token),
    )
    assert response.status_code == 404


def test_deactivate_requires_admin_and_no_active_work(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_workflow_pair: WorkflowPair,
    test_user_curator: UserNew,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)

    non_admin = client.request(
        "DELETE", f"{BASE}/{row.id}", json={"reason": "t"}, headers=_auth(curator_token)
    )
    assert non_admin.status_code == 403

    ok = client.request(
        "DELETE", f"{BASE}/{row.id}", json={"reason": "t"}, headers=_auth(admin_token)
    )
    assert ok.status_code == 200
    db_session.refresh(row)
    assert row.is_active is False

    # Re-open the assignment and attach a curation to make it busy.
    row.is_active = True
    db_session.add(
        CurationNew(
            id=uuid4(),
            scope_id=test_scope.id,
            gene_id=test_gene.id,
            workflow_pair_id=test_workflow_pair.id,
            workflow_stage="curation",
            evidence_data={},
            created_by=test_user_curator.id,
        )
    )
    db_session.commit()

    busy = client.request(
        "DELETE", f"{BASE}/{row.id}", json={"reason": "t"}, headers=_auth(admin_token)
    )
    assert busy.status_code == 400


def test_deactivate_and_reactivate_unknown_are_404(
    client: TestClient, admin_token: str
) -> None:
    assert (
        client.request(
            "DELETE",
            f"{BASE}/{uuid4()}",
            json={"reason": "t"},
            headers=_auth(admin_token),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{BASE}/{uuid4()}/reactivate", headers=_auth(admin_token)
        ).status_code
        == 404
    )


def test_reactivate_requires_admin(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope, is_active=False)

    assert (
        client.post(
            f"{BASE}/{row.id}/reactivate", headers=_auth(curator_token)
        ).status_code
        == 403
    )
    ok = client.post(f"{BASE}/{row.id}/reactivate", headers=_auth(admin_token))
    assert ok.status_code == 200
    db_session.refresh(row)
    assert row.is_active is True


def test_assignment_statistics_access_rules(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)
    assert (
        client.get(
            f"{BASE}/{row.id}/statistics", headers=_auth(curator_token)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{BASE}/{uuid4()}/statistics", headers=_auth(curator_token)
        ).status_code
        == 404
    )


def test_assignment_statistics_count_curations_by_status(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_curation: CurationNew,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    """#403: status counts were keyed by the enum's repr and always read 0."""
    row = _assignment(db_session, test_gene, test_scope)
    response = client.get(f"{BASE}/{row.id}/statistics", headers=_auth(curator_token))
    assert response.status_code == 200, response.text
    assert response.json()["draft_curations"] == 1


def test_bulk_create_assignments(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    _assignment(db_session, test_gene, test_scope)

    response = client.post(
        f"{BASE}/bulk",
        json={"gene_ids": [str(test_gene.id)], "scope_id": str(test_scope.id)},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_processed"] == 1
    assert body["total_created"] == 0
    assert body["total_skipped"] + body["total_errors"] == 1


def test_bulk_create_forbidden_outside_scope(
    client: TestClient,
    viewer_token: str,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    response = client.post(
        f"{BASE}/bulk",
        json={"gene_ids": [str(test_gene.id)], "scope_id": str(test_public_scope.id)},
        headers=_auth(viewer_token),
    )
    assert response.status_code == 403


def test_assign_and_unassign_curator(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    admin_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)

    assigned = client.post(
        f"{BASE}/{row.id}/assign-curator",
        json={"curator_id": str(test_user_curator.id)},
        headers=_auth(admin_token),
    )
    assert assigned.status_code == 200
    db_session.refresh(row)
    assert row.assigned_curator_id == test_user_curator.id

    cleared = client.post(
        f"{BASE}/{row.id}/unassign-curator", headers=_auth(admin_token)
    )
    assert cleared.status_code == 200
    db_session.refresh(row)
    assert row.assigned_curator_id is None


def test_assign_curator_rejects_unknown_or_non_member_curator(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    row = _assignment(db_session, test_gene, test_scope)
    outsider = _outsider(db_session)

    non_member = client.post(
        f"{BASE}/{row.id}/assign-curator",
        json={"curator_id": str(outsider.id)},
        headers=_auth(admin_token),
    )
    assert non_member.status_code == 400
    assert "does not have access" in non_member.json()["detail"]

    unknown = client.post(
        f"{BASE}/{row.id}/assign-curator",
        json={"curator_id": str(uuid4())},
        headers=_auth(admin_token),
    )
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "Curator not found"


def test_assign_and_unassign_unknown_assignment_is_404(
    client: TestClient, curator_token: str
) -> None:
    body = {"curator_id": str(uuid4())}
    assert (
        client.post(
            f"{BASE}/{uuid4()}/assign-curator", json=body, headers=_auth(curator_token)
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{BASE}/{uuid4()}/unassign-curator", headers=_auth(curator_token)
        ).status_code
        == 404
    )


def test_curator_workload_access_rules(
    client: TestClient,
    admin_token: str,
    curator_token: str,
    test_user_curator: UserNew,
    test_user_viewer: UserNew,
) -> None:
    own = client.get(
        f"{BASE}/curator/{test_user_curator.id}/workload", headers=_auth(curator_token)
    )
    assert own.status_code == 200

    other = client.get(
        f"{BASE}/curator/{test_user_viewer.id}/workload", headers=_auth(curator_token)
    )
    assert other.status_code == 403

    admin_view = client.get(
        f"{BASE}/curator/{test_user_curator.id}/workload", headers=_auth(admin_token)
    )
    assert admin_view.status_code == 200


def test_curator_assignments_access_rules(
    client: TestClient,
    admin_token: str,
    curator_token: str,
    test_user_curator: UserNew,
    test_user_viewer: UserNew,
) -> None:
    assert (
        client.get(
            f"{BASE}/curator/{test_user_curator.id}/assignments",
            headers=_auth(curator_token),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{BASE}/curator/{test_user_viewer.id}/assignments",
            headers=_auth(curator_token),
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"{BASE}/curator/{test_user_curator.id}/assignments",
            headers=_auth(admin_token),
        ).status_code
        == 200
    )


def test_scope_assignment_views_require_membership(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
) -> None:
    _assignment(db_session, test_gene, test_scope)

    listed = client.get(f"{BASE}/scope/{test_scope.id}", headers=_auth(curator_token))
    assert listed.status_code == 200
    assert listed.json()[0]["gene_symbol"] == "BRCA1"

    assert (
        client.get(
            f"{BASE}/scope/{test_public_scope.id}", headers=_auth(curator_token)
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"{BASE}/scope/{test_public_scope.id}/available-genes",
            headers=_auth(curator_token),
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"{BASE}/scope/{test_public_scope.id}/overview",
            headers=_auth(curator_token),
        ).status_code
        == 403
    )


def test_available_genes_and_overview_for_member_scope(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    available = client.get(
        f"{BASE}/scope/{test_scope.id}/available-genes", headers=_auth(curator_token)
    )
    assert available.status_code == 200
    assert str(test_gene.id) in [g["gene_id"] for g in available.json()]

    _assignment(db_session, test_gene, test_scope)
    overview = client.get(
        f"{BASE}/scope/{test_scope.id}/overview", headers=_auth(curator_token)
    )
    assert overview.status_code == 200
    assert overview.json()["total_assignments"] == 1


def test_available_genes_excludes_every_active_assignment(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_user_admin: UserNew,
) -> None:
    # Regression: with several active assignments in a scope, only the unassigned
    # gene may be listed (the old scalar subquery broke for >1 row).
    taken_a = Gene(
        id=uuid4(),
        hgnc_id="HGNC:8001",
        approved_symbol="TAKENA",
        record_hash="a" * 64,
        previous_symbols=[],
        alias_symbols=[],
        details={},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    taken_b = Gene(
        id=uuid4(),
        hgnc_id="HGNC:8002",
        approved_symbol="TAKENB",
        record_hash="b" * 64,
        previous_symbols=[],
        alias_symbols=[],
        details={},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    db_session.add_all([taken_a, taken_b])
    db_session.commit()
    _assignment(db_session, test_gene, test_scope)
    _assignment(db_session, taken_a, test_scope)
    _assignment(db_session, taken_b, test_scope)

    free = Gene(
        id=uuid4(),
        hgnc_id="HGNC:8003",
        approved_symbol="FREEG",
        record_hash="c" * 64,
        previous_symbols=[],
        alias_symbols=[],
        details={},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    db_session.add(free)
    db_session.commit()

    response = client.get(
        f"{BASE}/scope/{test_scope.id}/available-genes", headers=_auth(curator_token)
    )

    assert response.status_code == 200
    assert [g["approved_symbol"] for g in response.json()] == ["FREEG"]
