"""API tests for /genes endpoints: CRUD, bulk create, scope access and admin-only actions.

PostgreSQL-only paths (free-text search, /genes/statistics) are not exercised here
because they use jsonb/array operators that SQLite cannot run.
"""

import hashlib
from typing import ClassVar
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Gene, GeneScopeAssignment, Scope, UserNew
from app.schemas.validation import HGNCGeneSearchResult

pytestmark = pytest.mark.unit

BASE = "/api/v1/genes"


class _FakeHGNC:
    """Echo a deterministic record for any id; the real service is never called."""

    SYMBOLS: ClassVar[dict[str, str]] = {"HGNC:2001": "NEWG", "HGNC:1100": "BRCA1"}

    async def fetch_gene_by_id(self, hgnc_id: str) -> HGNCGeneSearchResult:
        symbol = self.SYMBOLS.get(hgnc_id, f"G{hgnc_id[5:]}")
        return HGNCGeneSearchResult(hgnc_id=hgnc_id, symbol=symbol, chromosome="1")

    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _hgnc():
    with patch("app.services.gene_verification.HGNCValidator", _FakeHGNC):
        yield


@pytest.fixture
def test_gene(db_session: Session, test_user_admin: UserNew) -> Gene:
    """Owned BRCA1 record: the Gene response schema requires created_by/updated_by."""
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:1100",
        approved_symbol="BRCA1",
        record_hash=hashlib.sha256(b"HGNC:1100").hexdigest(),
        previous_symbols=["BRCC1"],
        alias_symbols=["FANCS", "RNF53"],
        chromosome="17",
        location="17q21.31",
        details={"approved_name": "BRCA1 DNA repair associated"},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    db_session.add(gene)
    db_session.commit()
    db_session.refresh(gene)
    return gene


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _gene(
    db: Session,
    owner: UserNew,
    hgnc_id: str,
    symbol: str,
    *,
    chromosome: str | None = "17",
    location: str | None = "17q21.31",
) -> Gene:
    gene = Gene(
        id=uuid4(),
        hgnc_id=hgnc_id,
        approved_symbol=symbol,
        record_hash=hashlib.sha256(hgnc_id.encode()).hexdigest(),
        previous_symbols=[],
        alias_symbols=[],
        chromosome=chromosome,
        location=location,
        details={},
        created_by=owner.id,
        updated_by=owner.id,
    )
    db.add(gene)
    db.commit()
    db.refresh(gene)
    return gene


def _assign(db: Session, gene: Gene, scope: Scope) -> GeneScopeAssignment:
    assignment = GeneScopeAssignment(gene_id=gene.id, scope_id=scope.id, is_active=True)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _create_payload(
    hgnc_id: str = "HGNC:2001", symbol: str = "NEWG"
) -> dict[str, object]:
    return {
        "hgnc_id": hgnc_id,
        "approved_symbol": symbol,
        "chromosome": "1",
        "location": "1p36.1",
        "previous_symbols": [],
        "alias_symbols": [],
        "details": {},
    }


def test_gene_list_requires_authentication_but_single_gene_is_public(
    client: TestClient,
) -> None:
    assert client.get(f"{BASE}/").status_code in (401, 403)
    # public reference data: unauthenticated lookups reach the handler (404, not 401)
    assert client.get(f"{BASE}/{uuid4()}").status_code == 404


def test_create_gene_then_duplicate_is_rejected(
    client: TestClient, curator_token: str
) -> None:
    created = client.post(
        f"{BASE}/", json=_create_payload(), headers=_auth(curator_token)
    )
    assert created.status_code == 200
    assert created.json()["approved_symbol"] == "NEWG"

    duplicate = client.post(
        f"{BASE}/", json=_create_payload(), headers=_auth(curator_token)
    )
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.json()["detail"]


def test_create_gene_validates_hgnc_format(
    client: TestClient, curator_token: str
) -> None:
    response = client.post(
        f"{BASE}/", json=_create_payload(hgnc_id="1100"), headers=_auth(curator_token)
    )
    assert response.status_code == 422


def test_get_gene_by_id_includes_assignment_info(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    _assign(db_session, test_gene, test_scope)

    response = client.get(f"{BASE}/{test_gene.id}", headers=_auth(curator_token))

    assert response.status_code == 200
    body = response.json()
    assert body["approved_symbol"] == "BRCA1"
    assert body["total_scope_assignments"] == 1
    assert body["is_assigned_to_any_scope"] is True
    assert str(test_scope.id) in body["scope_assignments"]


def test_get_gene_is_public_and_hides_assignments_when_anonymous(
    client: TestClient, db_session: Session, test_gene: Gene, test_scope: Scope
) -> None:
    _assign(db_session, test_gene, test_scope)

    response = client.get(f"{BASE}/{test_gene.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["approved_symbol"] == "BRCA1"
    assert body["total_scope_assignments"] == 0
    assert body["scope_assignments"] == {}
    assert body["is_assigned_to_any_scope"] is False


def test_get_unknown_gene_is_404(client: TestClient, curator_token: str) -> None:
    response = client.get(f"{BASE}/{uuid4()}", headers=_auth(curator_token))
    assert response.status_code == 404
    assert response.json()["detail"] == "Gene not found"


def test_list_genes_with_pagination_and_summary_flags(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_user_admin: UserNew,
) -> None:
    _gene(db_session, test_user_admin, "HGNC:3000", "ZZZ1")

    response = client.get(f"{BASE}/?limit=1&skip=0", headers=_auth(curator_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["has_next"] is True
    assert body["has_prev"] is False
    assert body["genes"][0]["is_assigned"] is False


def test_list_genes_scope_filter_requires_membership(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    viewer_token: str,
    test_scope: Scope,
    test_public_scope: Scope,
    test_gene: Gene,
) -> None:
    _assign(db_session, test_gene, test_scope)

    member = client.get(
        f"{BASE}/?scope_id={test_scope.id}&assigned_only=true",
        headers=_auth(curator_token),
    )
    assert member.status_code == 200
    assert [g["approved_symbol"] for g in member.json()["genes"]] == ["BRCA1"]

    outsider = client.get(
        f"{BASE}/?scope_id={test_public_scope.id}", headers=_auth(viewer_token)
    )
    assert outsider.status_code == 403


def test_search_genes_without_text_query(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
) -> None:
    response = client.get(
        f"{BASE}/search?chromosome=17&hgnc_id=HGNC:1100", headers=_auth(curator_token)
    )

    assert response.status_code == 200
    assert [g["hgnc_id"] for g in response.json()] == ["HGNC:1100"]


def test_search_genes_scope_forbidden_for_non_member(
    client: TestClient, viewer_token: str, test_public_scope: Scope
) -> None:
    response = client.get(
        f"{BASE}/search?scope_id={test_public_scope.id}", headers=_auth(viewer_token)
    )
    assert response.status_code == 403


def test_update_gene_applies_changes(
    client: TestClient, curator_token: str, test_gene: Gene
) -> None:
    response = client.put(
        f"{BASE}/{test_gene.id}",
        json={"details": {"note": "x"}},
        headers=_auth(curator_token),
    )

    assert response.status_code == 200
    assert response.json()["details"] == {"note": "x"}


def test_update_gene_hgnc_conflict_and_missing(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_user_admin: UserNew,
) -> None:
    _gene(db_session, test_user_admin, "HGNC:4000", "OTHER")

    conflict = client.put(
        f"{BASE}/{test_gene.id}",
        json={"hgnc_id": "HGNC:4000"},
        headers=_auth(curator_token),
    )
    assert conflict.status_code == 400

    missing = client.put(
        f"{BASE}/{uuid4()}", json={"location": "x"}, headers=_auth(curator_token)
    )
    assert missing.status_code == 404


def test_delete_gene_requires_admin(
    client: TestClient, curator_token: str, test_gene: Gene
) -> None:
    response = client.delete(f"{BASE}/{test_gene.id}", headers=_auth(curator_token))
    assert response.status_code == 403


def test_delete_gene_unknown_is_404(client: TestClient, admin_token: str) -> None:
    assert (
        client.delete(f"{BASE}/{uuid4()}", headers=_auth(admin_token)).status_code
        == 404
    )


def test_delete_gene_blocked_by_assignment(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_gene: Gene,
    test_scope: Scope,
) -> None:
    _assign(db_session, test_gene, test_scope)

    response = client.delete(f"{BASE}/{test_gene.id}", headers=_auth(admin_token))

    assert response.status_code == 400
    assert "assignments" in response.json()["detail"]


def test_delete_unassigned_gene_as_admin(
    client: TestClient, db_session: Session, admin_token: str, test_user_admin: UserNew
) -> None:
    gene = _gene(db_session, test_user_admin, "HGNC:5000", "DELME")

    response = client.delete(f"{BASE}/{gene.id}", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["message"] == "Gene deleted successfully"
    assert db_session.get(Gene, gene.id) is None


def test_assignments_and_progress_endpoints(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    viewer_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
) -> None:
    _assign(db_session, test_gene, test_scope)

    assignments = client.get(
        f"{BASE}/{test_gene.id}/assignments", headers=_auth(curator_token)
    )
    assert assignments.status_code == 200
    assert assignments.json()["total_scope_assignments"] == 1

    progress = client.get(
        f"{BASE}/{test_gene.id}/progress", headers=_auth(curator_token)
    )
    assert progress.status_code == 200
    assert progress.json()["has_active_work"] is False

    forbidden = client.get(
        f"{BASE}/{test_gene.id}/progress?scope_id={test_public_scope.id}",
        headers=_auth(viewer_token),
    )
    assert forbidden.status_code == 403

    missing = client.get(f"{BASE}/{uuid4()}/progress", headers=_auth(curator_token))
    assert missing.status_code == 404
    assert (
        client.get(
            f"{BASE}/{uuid4()}/assignments", headers=_auth(curator_token)
        ).status_code
        == 404
    )


def test_bulk_create_reports_created_skipped_and_errors(
    client: TestClient, db_session: Session, curator_token: str, test_gene: Gene
) -> None:
    payload = {
        "genes": [
            _create_payload("HGNC:6001", "BULK1"),
            _create_payload("HGNC:6002", "BULK2"),
            _create_payload("HGNC:1100", "BRCA1"),  # already exists -> skipped
        ],
        "skip_duplicates": True,
    }

    response = client.post(f"{BASE}/bulk", json=payload, headers=_auth(curator_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_processed"] == 3
    assert body["total_created"] == 2
    assert body["total_skipped"] == 1
    assert body["total_errors"] == 0


def test_bulk_create_duplicates_become_errors_when_not_skipping(
    client: TestClient, curator_token: str, test_gene: Gene
) -> None:
    payload = {
        "genes": [_create_payload("HGNC:1100", "BRCA1")],
        "skip_duplicates": False,
    }

    response = client.post(f"{BASE}/bulk", json=payload, headers=_auth(curator_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_errors"] == 1
    assert body["errors"][0]["hgnc_id"] == "HGNC:1100"


def test_bulk_create_requires_at_least_one_gene(
    client: TestClient, curator_token: str
) -> None:
    response = client.post(
        f"{BASE}/bulk", json={"genes": []}, headers=_auth(curator_token)
    )
    assert response.status_code == 422


def test_scope_genes_requires_membership(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
) -> None:
    _assign(db_session, test_gene, test_scope)

    response = client.get(f"{BASE}/scope/{test_scope.id}", headers=_auth(curator_token))
    assert response.status_code == 200
    body = response.json()
    assert body["assigned"] == 1
    assert body["unassigned"] == 0
    assert body["genes"][0]["is_assigned"] is True

    forbidden = client.get(
        f"{BASE}/scope/{test_public_scope.id}", headers=_auth(curator_token)
    )
    assert forbidden.status_code == 403


def test_validate_gene_flags_format_problems(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_user_admin: UserNew,
) -> None:
    ok = client.post(f"{BASE}/{test_gene.id}/validate", headers=_auth(curator_token))
    assert ok.status_code == 200
    assert ok.json()["is_valid"] is True

    bad = _gene(
        db_session, test_user_admin, "HGNC:7001", "BADG", chromosome="ZZ", location=None
    )
    bad.hgnc_id = "NOPREFIX"
    db_session.commit()

    report = client.post(f"{BASE}/{bad.id}/validate", headers=_auth(curator_token))
    body = report.json()
    assert body["is_valid"] is False
    assert "Invalid HGNC ID format" in body["errors"]
    assert any("ZZ" in w for w in body["warnings"])
    assert body["suggestions"]

    assert (
        client.post(
            f"{BASE}/{uuid4()}/validate", headers=_auth(curator_token)
        ).status_code
        == 404
    )


def test_lookup_by_hgnc_id(
    client: TestClient, curator_token: str, test_gene: Gene
) -> None:
    found = client.get(f"{BASE}/hgnc/HGNC:1100", headers=_auth(curator_token))
    assert found.status_code == 200
    assert found.json()["approved_symbol"] == "BRCA1"

    missing = client.get(f"{BASE}/hgnc/HGNC:9999999", headers=_auth(curator_token))
    assert missing.status_code == 404


def test_merge_requires_admin_and_known_primary(
    client: TestClient,
    admin_token: str,
    curator_token: str,
    test_gene: Gene,
) -> None:
    body = {
        "primary_gene_id": str(test_gene.id),
        "duplicate_gene_ids": [str(uuid4())],
        "merge_strategy": "keep_primary",
        "preserve_history": True,
    }
    assert (
        client.post(
            f"{BASE}/merge", json=body, headers=_auth(curator_token)
        ).status_code
        == 403
    )

    ok = client.post(f"{BASE}/merge", json=body, headers=_auth(admin_token))
    assert ok.status_code == 200
    result = ok.json()
    assert result["duplicate_genes_processed"] == 1
    assert result["warnings"]

    body["primary_gene_id"] = str(UUID(int=1))
    missing = client.post(f"{BASE}/merge", json=body, headers=_auth(admin_token))
    assert missing.status_code == 404


def test_delete_blocked_by_active_curation_work(
    client: TestClient, admin_token: str, test_curation: object, test_gene: Gene
) -> None:
    response = client.delete(f"{BASE}/{test_gene.id}", headers=_auth(admin_token))

    assert response.status_code == 400
    assert "curation work" in response.json()["detail"]


def test_progress_reports_curation_status_counts(
    client: TestClient, curator_token: str, test_curation: object, test_gene: Gene
) -> None:
    response = client.get(
        f"{BASE}/{test_gene.id}/progress", headers=_auth(curator_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_curations"] == 1
    assert body["has_active_work"] is True
    assert sum(body["curation_status_counts"].values()) == 1


def test_list_genes_sorted_descending(
    client: TestClient,
    db_session: Session,
    curator_token: str,
    test_gene: Gene,
    test_user_admin: UserNew,
) -> None:
    _gene(db_session, test_user_admin, "HGNC:3100", "AAA1")

    response = client.get(
        f"{BASE}/?sort_by=approved_symbol&sort_order=desc", headers=_auth(curator_token)
    )

    assert response.status_code == 200
    assert [g["approved_symbol"] for g in response.json()["genes"]] == ["BRCA1", "AAA1"]
