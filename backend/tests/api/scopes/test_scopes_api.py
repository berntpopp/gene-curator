"""API tests for /api/v1/scopes (creation, listing, detail, update, delete)."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    GeneScopeAssignment,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_gene,
    make_member,
    make_scope,
    make_user,
    make_workflow_pair,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/scopes"


def _create_payload(db: Session, name: str | None = None) -> dict[str, object]:
    return {
        "default_workflow_pair_id": str(make_workflow_pair(db).id),
        "name": name or f"new-scope-{uuid4().hex[:8]}",
        "display_name": "New Scope",
        "description": "Created in a test",
    }


# -----------------------------------------------------------------------------
# Creation and creator membership (regression)
# -----------------------------------------------------------------------------


def test_create_scope_makes_creator_an_accepted_active_admin(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    """Regression: the creator must get an accepted admin membership at once.

    Without accepted_at the membership is a pending invitation and grants no
    access, so the creator would be locked out of their own scope.
    """
    response = client.post(
        f"{BASE}/", json=_create_payload(db_session), headers=auth_headers(owner)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created_by"] == str(owner.id)

    membership = (
        db_session.query(ScopeMembership)
        .filter(
            ScopeMembership.scope_id == body["id"],
            ScopeMembership.user_id == owner.id,
        )
        .one()
    )
    assert membership.role == "admin"
    assert membership.accepted_at is not None
    assert membership.is_active is True


def test_creator_can_use_new_scope_immediately(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    """The creator's accepted membership must pass scope-gated endpoints."""
    created = client.post(
        f"{BASE}/", json=_create_payload(db_session), headers=auth_headers(owner)
    ).json()

    members = client.get(f"{BASE}/{created['id']}/members", headers=auth_headers(owner))

    assert members.status_code == 200
    body = members.json()
    assert body["active_count"] == 1
    assert body["pending_count"] == 0
    assert body["members"][0]["user_id"] == str(owner.id)
    assert body["members"][0]["role"] == "admin"


def test_create_scope_rejects_duplicate_name(
    client: TestClient, db_session: Session, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.post(
        f"{BASE}/",
        json=_create_payload(db_session, name=scope_with_admin.name),
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_scope_requires_authentication(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(f"{BASE}/", json=_create_payload(db_session))

    assert response.status_code in (401, 403)


def test_create_scope_without_methodology_or_default_is_400(
    client: TestClient, owner: UserNew
) -> None:
    payload = {"name": "no-method", "display_name": "X", "description": "y"}

    response = client.post(f"{BASE}/", json=payload, headers=auth_headers(owner))

    assert response.status_code == 400
    assert "Workflow pair" in response.json()["detail"]


def test_create_scope_rejects_unknown_or_inactive_methodology(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    unknown = _create_payload(db_session)
    unknown["default_workflow_pair_id"] = str(uuid4())
    inactive = _create_payload(db_session)
    pair = db_session.get(WorkflowPair, UUID(str(inactive["default_workflow_pair_id"])))
    assert pair is not None
    pair.is_active = False
    db_session.commit()

    for payload in (unknown, inactive):
        response = client.post(f"{BASE}/", json=payload, headers=auth_headers(owner))
        assert response.status_code == 400
        assert "Workflow pair" in response.json()["detail"]


def test_create_scope_validates_name(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    payload = _create_payload(db_session)
    payload["name"] = "Bad Name With Spaces"

    response = client.post(f"{BASE}/", json=payload, headers=auth_headers(owner))

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# Listing
# -----------------------------------------------------------------------------


def test_list_scopes_returns_only_member_scopes_with_counts(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    scope_with_admin: Scope,
    viewer: UserNew,
) -> None:
    other = make_scope(db_session)
    make_member(db_session, other, viewer, "viewer")
    gene = make_gene(db_session)
    db_session.add(
        GeneScopeAssignment(
            gene_id=gene.id, scope_id=scope_with_admin.id, is_active=True
        )
    )
    db_session.commit()

    response = client.get(f"{BASE}/", headers=auth_headers(owner))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(scope_with_admin.id) in ids
    assert str(other.id) not in ids
    item = next(i for i in response.json() if i["id"] == str(scope_with_admin.id))
    # owner (admin) and viewer are both accepted members of scope_with_admin
    assert item["stats"] == {"total_genes": 1, "completed_genes": 0, "member_count": 2}


def test_list_scopes_carries_the_callers_scope_role(
    client: TestClient,
    db_session: Session,
    scope_with_admin: Scope,
    curator: UserNew,
    app_admin: UserNew,
) -> None:
    curator_item = next(
        i
        for i in client.get(f"{BASE}/", headers=auth_headers(curator)).json()
        if i["id"] == str(scope_with_admin.id)
    )
    assert curator_item["user_role"] == "curator"

    # an application admin without a membership sees the scope but has no scope role
    admin_item = next(
        i
        for i in client.get(f"{BASE}/", headers=auth_headers(app_admin)).json()
        if i["id"] == str(scope_with_admin.id)
    )
    assert admin_item["user_role"] is None


def test_list_scopes_says_whether_the_ai_second_view_is_on(
    client: TestClient, db_session: Session, scope_with_admin: Scope, curator: UserNew
) -> None:
    """B20: the review queue hides the AI second view link when the scope has it off."""
    from app.models.llm import ScopeLLMSettings

    def on() -> bool:
        rows = client.get(f"{BASE}/", headers=auth_headers(curator)).json()
        return next(i for i in rows if i["id"] == str(scope_with_admin.id))[
            "llm_second_view"
        ]

    assert on() is False
    db_session.add(ScopeLLMSettings(scope_id=scope_with_admin.id, enabled=True))
    db_session.commit()
    assert on() is True


def test_list_scopes_hides_inactive_scopes_by_default(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    inactive = make_scope(db_session, is_active=False)
    make_member(db_session, inactive, owner, "admin")

    hidden = client.get(f"{BASE}/", headers=auth_headers(owner)).json()
    shown = client.get(
        f"{BASE}/", params={"active_only": False}, headers=auth_headers(owner)
    ).json()

    assert str(inactive.id) not in [s["id"] for s in hidden]
    assert str(inactive.id) in [s["id"] for s in shown]


def test_list_scopes_application_admin_sees_all_scopes(
    client: TestClient,
    db_session: Session,
    app_admin: UserNew,
    scope_with_admin: Scope,
) -> None:
    response = client.get(f"{BASE}/", headers=auth_headers(app_admin))

    assert response.status_code == 200
    assert str(scope_with_admin.id) in [s["id"] for s in response.json()]


def test_list_scopes_pagination_applies_to_member_scopes(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    for _ in range(3):
        make_member(db_session, make_scope(db_session), owner, "viewer")

    page = client.get(
        f"{BASE}/", params={"skip": 1, "limit": 1}, headers=auth_headers(owner)
    ).json()

    assert len(page) == 1


# -----------------------------------------------------------------------------
# Detail
# -----------------------------------------------------------------------------


def test_get_scope_details_unknown_scope_returns_404(
    client: TestClient, owner: UserNew
) -> None:
    response = client.get(f"{BASE}/{uuid4()}", headers=auth_headers(owner))

    assert response.status_code == 404


# -----------------------------------------------------------------------------
# Update
# -----------------------------------------------------------------------------


def test_update_scope_allowed_for_scope_admin(
    client: TestClient, owner: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}",
        json={"display_name": "Renamed"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Renamed"


def test_update_scope_forbidden_for_curator(
    client: TestClient, curator: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}",
        json={"display_name": "Nope"},
        headers=auth_headers(curator),
    )

    assert response.status_code == 403


def test_update_scope_forbidden_for_non_member(
    client: TestClient, outsider: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}",
        json={"display_name": "Nope"},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 403


def test_update_scope_allowed_for_application_admin(
    client: TestClient, app_admin: UserNew, scope_with_admin: Scope
) -> None:
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}",
        json={"description": "Changed by app admin"},
        headers=auth_headers(app_admin),
    )

    assert response.status_code == 200


# -----------------------------------------------------------------------------
# Delete
# -----------------------------------------------------------------------------


def test_delete_scope_by_creator_without_assignments(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    scope = make_scope(db_session, created_by=owner.id)
    make_member(db_session, scope, owner, "admin")

    response = client.delete(f"{BASE}/{scope.id}", headers=auth_headers(owner))

    assert response.status_code == 204
    assert db_session.get(Scope, scope.id) is None


def test_delete_scope_by_non_owner_is_forbidden(
    client: TestClient, db_session: Session, owner: UserNew, curator: UserNew
) -> None:
    scope = make_scope(db_session, created_by=owner.id)
    make_member(db_session, scope, owner, "admin")
    make_member(db_session, scope, curator, "admin")

    response = client.delete(f"{BASE}/{scope.id}", headers=auth_headers(curator))

    assert response.status_code == 403
    assert db_session.get(Scope, scope.id) is not None


def test_delete_scope_with_assignments_requires_force(
    client: TestClient, db_session: Session, owner: UserNew
) -> None:
    scope = make_scope(db_session, created_by=owner.id)
    make_member(db_session, scope, owner, "admin")
    gene = make_gene(db_session)
    db_session.add(
        GeneScopeAssignment(gene_id=gene.id, scope_id=scope.id, is_active=True)
    )
    db_session.commit()

    refused = client.delete(f"{BASE}/{scope.id}", headers=auth_headers(owner))
    forced = client.delete(
        f"{BASE}/{scope.id}", params={"force": True}, headers=auth_headers(owner)
    )

    assert refused.status_code == 400
    assert forced.status_code == 204


def test_delete_unknown_scope_returns_404(
    client: TestClient, app_admin: UserNew
) -> None:
    response = client.delete(f"{BASE}/{uuid4()}", headers=auth_headers(app_admin))

    assert response.status_code == 404


def test_delete_scope_by_application_admin_succeeds(
    client: TestClient, db_session: Session, app_admin: UserNew
) -> None:
    scope = make_scope(db_session, created_by=make_user(db_session).id)

    response = client.delete(f"{BASE}/{scope.id}", headers=auth_headers(app_admin))

    assert response.status_code == 204


# -----------------------------------------------------------------------------
# Statistics
# -----------------------------------------------------------------------------


def test_statistics_forbidden_for_non_member(
    client: TestClient, outsider: UserNew, scope_with_admin: Scope
) -> None:
    response = client.get(
        f"{BASE}/{scope_with_admin.id}/statistics", headers=auth_headers(outsider)
    )

    assert response.status_code == 403


@pytest.mark.parametrize("field", ["display_name", "institution"])
def test_overlong_string_fields_are_422_not_500(
    client: TestClient,
    db_session: Session,
    owner: UserNew,
    app_admin: UserNew,
    scope_with_admin: Scope,
    field: str,
) -> None:
    """varchar(255) columns: an overlong value is a validation error, not a DB 500."""
    response = client.patch(
        f"{BASE}/{scope_with_admin.id}",
        json={field: "x" * 256},
        headers=auth_headers(owner),
    )
    assert response.status_code == 422
    payload = {**_create_payload(db_session), field: "x" * 256}
    response = client.post(f"{BASE}/", json=payload, headers=auth_headers(app_admin))
    assert response.status_code == 422


def test_overlong_scope_name_is_422(
    client: TestClient, db_session: Session, app_admin: UserNew
) -> None:
    payload = _create_payload(db_session, name="a" * 256)
    response = client.post(f"{BASE}/", json=payload, headers=auth_headers(app_admin))
    assert response.status_code == 422
