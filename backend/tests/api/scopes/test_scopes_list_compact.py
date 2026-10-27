"""MCP study F4: list_scopes returns compact rows by default, full rows on detail=true, and
filters by name (case-insensitive substring of name or display_name)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.api.scopes.factories import auth_headers, make_member, make_scope, make_user

COMPACT = {
    "id",
    "name",
    "display_name",
    "default_workflow_pair_id",
    "user_role",
    "stats",
}


def test_list_is_compact_by_default_and_full_on_detail(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    make_member(db_session, make_scope(db_session), user, "curator")

    compact = client.get("/api/v1/scopes/", headers=auth_headers(user)).json()
    assert [set(row) for row in compact] == [COMPACT]
    assert compact[0]["user_role"] == "curator"

    full = client.get("/api/v1/scopes/?detail=true", headers=auth_headers(user)).json()
    assert {"scope_config", "description", "created_at", "is_public"} <= set(full[0])


def test_name_filter_for_members_and_admins(
    client: TestClient, db_session: Session
) -> None:
    user, admin = make_user(db_session), make_user(db_session, role="admin")
    kidney, heart = make_scope(db_session), make_scope(db_session)
    kidney.display_name = "Kidney Genetics"
    db_session.commit()
    for scope in (kidney, heart):
        make_member(db_session, scope, user, "viewer")

    for caller in (user, admin):
        rows = client.get(
            "/api/v1/scopes/?name=kidney", headers=auth_headers(caller)
        ).json()
        assert [r["id"] for r in rows] == [str(kidney.id)]
        by_name = client.get(
            f"/api/v1/scopes/?name={heart.name.upper()}", headers=auth_headers(caller)
        ).json()
        assert [r["id"] for r in by_name] == [str(heart.id)]
