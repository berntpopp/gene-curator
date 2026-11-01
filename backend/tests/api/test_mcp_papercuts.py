"""#640: scope names resolve for platform admins as list_scopes shows them, and creating a
precuration warns when nobody but its author can review it."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationSchema, Gene, UserNew
from tests.api.scopes.factories import auth_headers, make_member, make_scope, make_user

pytestmark = pytest.mark.unit


def test_a_platform_admin_resolves_a_scope_name_without_membership(
    client: TestClient, db_session: Session, test_user_admin: UserNew
) -> None:
    scope = make_scope(db_session)  # private, no members
    url, query = "/api/v1/curations/", {"scope_name": scope.name}
    r = client.get(url, params=query, headers=auth_headers(test_user_admin))
    assert r.status_code == 200, r.text
    outsider = make_user(db_session)
    assert (
        client.get(url, params=query, headers=auth_headers(outsider)).status_code == 404
    )


def test_create_warns_when_no_other_reviewer_exists(
    client: TestClient,
    db_session: Session,
    test_gene: Gene,
    test_precuration_schema: CurationSchema,
) -> None:
    scope = make_scope(db_session)
    author = make_user(db_session)
    make_member(db_session, scope, author, "admin")  # may review, but not its own work

    def create(mondo: str) -> list[str]:
        r = client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(test_gene.id),
                "scope_id": str(scope.id),
                "precuration_schema_id": str(test_precuration_schema.id),
                "evidence_data": {"mondo_id": mondo, "mode_of_inheritance": "AR"},
            },
            headers=auth_headers(author),
        )
        assert r.status_code == 201, r.text
        return r.json()["warnings"]  # type: ignore[no-any-return]

    [warning] = create("MONDO:0000002")
    assert "no eligible reviewer" in warning
    make_member(db_session, scope, make_user(db_session), "reviewer")
    assert create("MONDO:0000003") == []
