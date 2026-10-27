"""POST /genes and /genes/bulk: who may create global gene rows, and from what data (#363)."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, Scope
from app.schemas.validation import HGNCGeneSearchResult
from tests.api.scopes.factories import auth_headers, make_member, make_user

pytestmark = pytest.mark.unit

RECORDS = {
    "HGNC:9008": HGNCGeneSearchResult(
        hgnc_id="HGNC:9008",
        symbol="PKD1",
        name="polycystin 1",
        alias_symbols=["PBP"],
        previous_symbols=["PKD"],
        chromosome="16",
        location="16p13.3",
    ),
    "HGNC:9009": HGNCGeneSearchResult(
        hgnc_id="HGNC:9009", symbol="PKD2", name="polycystin 2", location="4q22.1"
    ),
}


class FakeHGNC:
    async def fetch_gene_by_id(self, hgnc_id: str):
        return RECORDS.get(hgnc_id)

    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def hgnc():
    with patch("app.services.gene_verification.HGNCValidator", FakeHGNC):
        yield


def _row(hgnc_id="HGNC:9008", symbol="PKD1", **over):
    return {"hgnc_id": hgnc_id, "approved_symbol": symbol, **over}


def _user(db: Session, scope: Scope, who: str):
    user = make_user(db, role="admin" if who == "platform_admin" else "user")
    if who in ("viewer", "reviewer", "curator", "admin"):
        make_member(db, scope, user, who)
    elif who == "pending":
        make_member(db, scope, user, "curator", accepted=False)
    return user


ALLOWED = {"curator", "admin", "platform_admin"}
ROLES = [
    "viewer",
    "reviewer",
    "curator",
    "admin",
    "pending",
    "outsider",
    "platform_admin",
]


@pytest.mark.parametrize("who", ROLES)
def test_single_create_by_role(
    client: TestClient, db_session: Session, test_scope, who
):
    user = _user(db_session, test_scope, who)
    response = client.post("/api/v1/genes/", json=_row(), headers=auth_headers(user))
    assert response.status_code == (200 if who in ALLOWED else 403), response.text


@pytest.mark.parametrize("who", ROLES)
def test_bulk_create_by_role(client: TestClient, db_session: Session, test_scope, who):
    user = _user(db_session, test_scope, who)
    response = client.post(
        "/api/v1/genes/bulk", json={"genes": [_row()]}, headers=auth_headers(user)
    )
    assert response.status_code == (200 if who in ALLOWED else 403), response.text
    if who in ALLOWED:
        assert response.json()["total_created"] == 1


def test_inactive_scope_curator_cannot_create(client, db_session, test_scope):
    test_scope.is_active = False
    db_session.commit()
    user = _user(db_session, test_scope, "curator")
    response = client.post("/api/v1/genes/", json=_row(), headers=auth_headers(user))
    assert response.status_code == 403


def test_client_data_is_replaced_by_hgnc_record(client, db_session, test_scope):
    user = _user(db_session, test_scope, "curator")
    fabricated = _row(
        symbol="EVIL",
        chromosome="X",
        location="Xq99",
        previous_symbols=["FAKE"],
        details={"approved_name": "made up", "gene_description": "<script>"},
    )
    body = client.post(
        "/api/v1/genes/", json=fabricated, headers=auth_headers(user)
    ).json()
    assert body["approved_symbol"] == "PKD1"
    assert body["chromosome"] == "16"
    assert body["location"] == "16p13.3"
    assert body["previous_symbols"] == ["PKD"]
    assert body["alias_symbols"] == ["PBP"]
    assert body["details"] == {"approved_name": "polycystin 1"}


def test_unknown_hgnc_id_is_rejected_and_nothing_stored(client, db_session, test_scope):
    user = _user(db_session, test_scope, "curator")
    response = client.post(
        "/api/v1/genes/", json=_row("HGNC:99999999", "NOPE"), headers=auth_headers(user)
    )
    assert response.status_code == 422
    assert db_session.query(Gene).filter(Gene.hgnc_id == "HGNC:99999999").count() == 0


def test_bulk_verifies_every_row_and_reports_unverifiable_ones(
    client, db_session, test_scope
):
    user = _user(db_session, test_scope, "curator")
    body = client.post(
        "/api/v1/genes/bulk",
        json={
            "genes": [
                _row(),
                _row("HGNC:9009", "WRONG"),
                _row("HGNC:99999999", "NOPE"),
            ],
            "validate_hgnc": False,  # the client cannot opt out
        },
        headers=auth_headers(user),
    ).json()
    assert body["total_processed"] == 3
    assert body["total_created"] == 2
    assert body["total_errors"] == 1
    assert body["errors"][0]["hgnc_id"] == "HGNC:99999999"
    assert sorted(g["approved_symbol"] for g in body["created_genes"]) == [
        "PKD1",
        "PKD2",
    ]


# --- PUT /genes/{id} (#363 review) ---------------------------------------------


@pytest.mark.parametrize("who", ROLES)
def test_update_by_role(client, db_session, test_scope, who):
    admin = _user(db_session, test_scope, "platform_admin")
    gid = client.post(
        "/api/v1/genes/", json=_row(), headers=auth_headers(admin)
    ).json()["id"]
    user = _user(db_session, test_scope, who)
    response = client.put(
        f"/api/v1/genes/{gid}",
        json={"details": {"note": "x"}},
        headers=auth_headers(user),
    )
    assert response.status_code == (200 if who in ALLOWED else 403), response.text


def test_update_replaces_fabricated_reference_fields(client, db_session, test_scope):
    user = _user(db_session, test_scope, "curator")
    gid = client.post("/api/v1/genes/", json=_row(), headers=auth_headers(user)).json()[
        "id"
    ]
    body = client.put(
        f"/api/v1/genes/{gid}",
        json={"approved_symbol": "EVIL", "location": "Xq99", "alias_symbols": ["FAKE"]},
        headers=auth_headers(user),
    ).json()
    assert body["approved_symbol"] == "PKD1"
    assert body["location"] == "16p13.3"
    assert body["alias_symbols"] == ["PBP"]


def test_update_to_unknown_hgnc_id_is_rejected(client, db_session, test_scope):
    user = _user(db_session, test_scope, "platform_admin")
    gid = client.post("/api/v1/genes/", json=_row(), headers=auth_headers(user)).json()[
        "id"
    ]
    response = client.put(
        f"/api/v1/genes/{gid}",
        json={"hgnc_id": "HGNC:99999999"},
        headers=auth_headers(user),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("who", ["curator", "admin", "platform_admin"])
def test_hgnc_repoint_is_platform_admin_only(client, db_session, test_scope, who):
    """#478: repointing a gene to another HGNC record rewrites it for every scope."""
    user = _user(db_session, test_scope, who)
    gid = client.post("/api/v1/genes/", json=_row(), headers=auth_headers(user)).json()[
        "id"
    ]
    response = client.put(
        f"/api/v1/genes/{gid}",
        json={"hgnc_id": "HGNC:9009"},
        headers=auth_headers(user),
    )
    if who == "platform_admin":
        assert response.status_code == 200, response.text
        assert response.json()["approved_symbol"] == "PKD2"
    else:
        assert response.status_code == 403, response.text
    same = client.put(
        f"/api/v1/genes/{gid}",
        json={
            "hgnc_id": client.get(
                f"/api/v1/genes/{gid}", headers=auth_headers(user)
            ).json()["hgnc_id"]
        },
        headers=auth_headers(user),
    )
    assert same.status_code == 200, same.text


# --- total HGNC budget -----------------------------------------------------------


class SlowHGNC(FakeHGNC):
    async def fetch_gene_by_id(self, hgnc_id: str):
        if hgnc_id == "HGNC:9009":
            await asyncio.sleep(5)
        return RECORDS.get(hgnc_id)


def test_slow_hgnc_rows_reported_as_timeout_errors(client, db_session, test_scope):
    user = _user(db_session, test_scope, "curator")
    with (
        patch("app.services.gene_verification.HGNCValidator", SlowHGNC),
        patch("app.services.gene_verification._BUDGET_S", 0.1),
    ):
        body = client.post(
            "/api/v1/genes/bulk",
            json={"genes": [_row(), _row("HGNC:9009", "PKD2")]},
            headers=auth_headers(user),
        ).json()
        single = client.post(
            "/api/v1/genes/", json=_row("HGNC:9009", "PKD2"), headers=auth_headers(user)
        )
    assert body["total_created"] == 1
    assert body["errors"] == [
        {"hgnc_id": "HGNC:9009", "error": "HGNC lookup timed out"}
    ]
    assert single.status_code == 504
