"""#484: the Scopes page lists active public scopes for a logged-in non-member (no role),
next to the user's own scopes; private and inactive scopes stay hidden."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.scope import ScopeStatistics
from tests.api.scopes.factories import auth_headers, make_member, make_scope, make_user


def test_lists_own_and_active_public_scopes(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    own = make_scope(db_session)
    make_member(db_session, own, user, "viewer")
    public = make_scope(db_session)
    hidden = make_scope(db_session)  # private
    gone = make_scope(db_session, is_active=False)
    for scope in (public, gone):
        scope.is_public = True
    db_session.commit()

    r = client.get("/api/v1/scopes/", headers=auth_headers(user))
    assert r.status_code == 200, r.text
    roles = {item["id"]: item["user_role"] for item in r.json()}
    assert roles == {str(own.id): "viewer", str(public.id): None}
    assert str(hidden.id) not in roles


def test_single_scope_get_carries_user_role(
    client: TestClient, db_session: Session
) -> None:
    """GET /scopes/{id} reports the caller's role like the list does; null for outsiders."""
    member, outsider = make_user(db_session), make_user(db_session)
    scope = make_scope(db_session)
    make_member(db_session, scope, member, "reviewer")
    scope.is_public = True
    db_session.commit()

    # Detailed statistics need PostgreSQL (EXTRACT days); zero them on SQLite
    zeros = {
        name: 0 for name, f in ScopeStatistics.model_fields.items() if f.is_required()
    }
    for user, role in ((member, "reviewer"), (outsider, None)):
        with patch(
            "app.crud.scope.scope_crud.get_detailed_statistics", return_value=zeros
        ):
            r = client.get(f"/api/v1/scopes/{scope.id}", headers=auth_headers(user))
        assert r.status_code == 200, r.text
        assert r.json()["user_role"] == role
