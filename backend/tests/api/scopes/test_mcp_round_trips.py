"""MCP study round trips agents named (token-efficiency plan item 2)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, PrecurationNew, Scope, UserNew
from tests.api.scopes.factories import (
    auth_headers,
    make_gene,
    make_precuration,
    make_scope,
)


def test_list_rows_carry_lock_version(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    """A save needs lock_version; the list row has it, so no GET just for it."""
    h = {"Authorization": f"Bearer {curator_token}"}
    (c,) = client.get("/api/v1/curations/", headers=h).json()["curations"]
    (p,) = client.get("/api/v1/precurations/", headers=h).json()["precurations"]
    assert c["lock_version"] == test_curation.lock_version
    assert p["lock_version"] == test_precuration.lock_version


def test_scope_name_replaces_scope_id(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    """List, create and reviewer lookups take the scope name; no list_scopes first."""
    h = auth_headers(curator)
    name = scope_with_admin.name.upper()  # any case
    gene = make_gene(db_session)
    created = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(gene.id),
            "scope_name": name,
            "precuration_schema_id": None,
        },
        headers=h,
    )
    # the scope has no workflow pair: the scope resolved, the default schema did not
    assert created.status_code == 400, created.text
    assert "precuration_schema_id" in created.text
    make_precuration(db_session, scope=scope_with_admin, gene=gene, creator=curator)

    listed = client.get("/api/v1/precurations/", params={"scope_name": name}, headers=h)
    reviewers = client.get(
        "/api/v1/workflow/peer-reviewers", params={"scope_name": name}, headers=h
    )
    assert listed.json()["total"] == 1
    assert str(reviewer.id) in {r["id"] for r in reviewers.json()}


def test_unknown_or_hidden_scope_name_is_404_with_suggestions(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    hidden = make_scope(db_session, name="hidden-team")  # curator is no member
    h = auth_headers(curator)
    typo = client.get(
        "/api/v1/curations/",
        params={"scope_name": scope_with_admin.name[:-1]},
        headers=h,
    )
    assert typo.status_code == 404
    assert typo.json()["detail"]["suggestions"] == [scope_with_admin.name]

    secret = client.get(
        "/api/v1/precurations/", params={"scope_name": hidden.name}, headers=h
    )
    assert secret.status_code == 404
    assert secret.json()["detail"]["suggestions"] == []  # hidden scopes never leak

    clash = client.get(
        "/api/v1/curations/",
        params={"scope_name": scope_with_admin.name, "scope_id": str(hidden.id)},
        headers=h,
    )
    assert clash.status_code == 404
    missing = client.post(
        "/api/v1/precurations/",
        json={"gene_id": str(make_gene(db_session).id)},
        headers=h,
    )
    assert missing.status_code == 422
