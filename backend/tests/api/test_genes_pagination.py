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
