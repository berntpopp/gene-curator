"""Old catalogue and GET /genes/{id}/scopes under real RLS: same rule as the matrix (#367)."""

import os
from collections.abc import Generator
from uuid import UUID

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token
from app.main import app
from tests.postgres.test_catalogue_matrix_visibility import W, w  # noqa: F401

pytestmark = pytest.mark.postgres

WHO = ["anonymous", "member", "pending", "outsider", "root"]


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _headers(w: W, who: str) -> dict[str, str]:  # noqa: F811
    uid: UUID | None = {
        "anonymous": None,
        "member": w.member,
        "pending": w.pending,
        "outsider": w.outsider,
        "root": w.root,
    }[who]
    if uid is None:
        return {}
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def _expected(w: W, who: str) -> set[str]:  # noqa: F811
    return {str(w.pub), str(w.priv)} if who == "member" else {str(w.pub)}


@pytest.mark.parametrize("who", WHO)
def test_catalogue_entries_and_scope_filter(client: TestClient, w: W, who: str) -> None:  # noqa: F811
    headers = _headers(w, who)
    entries = client.get(
        "/api/v1/gene-catalogue/",
        params={"search": "MXA", "limit": 100},
        headers=headers,
    ).json()["entries"]
    mine = [e for e in entries if e["gene_id"] == str(w.active_gene)]
    assert {sc["scope_id"] for sc in mine[0]["scope_curations"]} == _expected(w, who)

    options = client.get(
        "/api/v1/gene-catalogue/filters/scopes", headers=headers
    ).json()
    ids = {o["id"] for o in options}
    assert (str(w.priv) in ids) == (who == "member")
    assert str(w.pub) in ids


@pytest.mark.parametrize("who", WHO)
def test_gene_scopes_and_draft_counts(client: TestClient, w: W, who: str) -> None:  # noqa: F811
    headers = _headers(w, who)
    active = client.get(f"/api/v1/genes/{w.active_gene}/scopes", headers=headers).json()
    assert {s["scope_id"] for s in active} == _expected(w, who)
    drafts = client.get(f"/api/v1/genes/{w.draft_gene}/scopes", headers=headers).json()
    # the only curation of draft_gene is a draft in the private scope: members only
    assert [s["scope_id"] for s in drafts] == ([str(w.priv)] if who == "member" else [])


def test_wildcard_and_nul_search(client: TestClient, w: W) -> None:  # noqa: F811
    for text in ("%", "_"):
        body = client.get("/api/v1/gene-catalogue/", params={"search": text}).json()
        assert body["entries"] == []
    assert (
        client.get("/api/v1/gene-catalogue/", params={"search": "a\x00"}).status_code
        == 422
    )


@pytest.mark.parametrize("who", WHO)
def test_filter_lists_hide_private_scope_disease_and_classification(
    client: TestClient,
    w: W,  # noqa: F811
    who: str,
) -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        for scope, disease in ((w.pub, "Public disease"), (w.priv, "Secret disease")):
            cur.execute(
                "UPDATE curations SET evidence_data = jsonb_build_object('disease_name', %s::text) "
                "WHERE scope_id = %s AND status = 'active'",
                (disease, str(scope)),
            )
    headers = _headers(w, who)
    diseases = set(
        client.get("/api/v1/gene-catalogue/filters/diseases", headers=headers).json()
    )
    classes = set(
        client.get(
            "/api/v1/gene-catalogue/filters/classifications", headers=headers
        ).json()
    )
    assert "Public disease" in diseases and "strong" in classes
    assert ("Secret disease" in diseases) == (who == "member")
    assert ("refuted" in classes) == (who == "member")
