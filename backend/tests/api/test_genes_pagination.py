"""Gene list totals come from a count query, not the size of the current page."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Scope, UserNew
from tests.api.test_genes_api import BASE, _assign, _auth, _gene


def test_gene_list_total_counts_all_pages(
    client: TestClient, db_session: Session, test_user_admin: UserNew, admin_token: str
) -> None:
    for i in range(3):
        _gene(db_session, test_user_admin, f"HGNC:9{i}", f"GENE{i}")

    body = client.get(f"{BASE}/?skip=0&limit=2", headers=_auth(admin_token)).json()

    assert len(body["genes"]) == 2
    assert body["total"] == 3
    assert body["has_next"] is True


def test_scope_gene_counts_cover_all_pages(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_scope: Scope,
    admin_token: str,
) -> None:
    genes = [
        _gene(db_session, test_user_admin, f"HGNC:8{i}", f"SG{i}") for i in range(3)
    ]
    _assign(db_session, genes[0], test_scope)

    body = client.get(
        f"{BASE}/scope/{test_scope.id}?skip=0&limit=1", headers=_auth(admin_token)
    ).json()

    assert body["total"] == 3
    assert body["assigned"] == 1
    assert body["unassigned"] == 2


def test_search_count_ignores_paging_and_matches_filters(
    client: TestClient, db_session: Session, test_user_admin: UserNew, admin_token: str
) -> None:
    for i in range(3):
        g = _gene(db_session, test_user_admin, f"HGNC:7{i}", f"CNT{i}")
        g.chromosome = "X" if i else "1"
    db_session.commit()

    def count(qs: str) -> int:
        r = client.get(f"{BASE}/search/count{qs}", headers=_auth(admin_token))
        assert r.status_code == 200
        return int(r.json())

    assert count("") == 3
    assert count("?chromosome=X") == 2
    assert count("?hgnc_id=HGNC:70") == 1
    page = client.get(f"{BASE}/search?limit=1", headers=_auth(admin_token)).json()
    assert len(page) == 1
