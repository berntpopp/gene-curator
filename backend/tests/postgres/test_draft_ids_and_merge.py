"""Draft merge patch, ID warnings and submit validation as app_user (MCP study round 2)."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.security import create_access_token
from app.schemas.validation import PMIDValidationResult, PublicationData
from app.services import evidence_ids, publication_service
from app.services.publication_service import PublicationService
from tests.postgres.test_submit_unknown_pmids import (
    W,
    _owner,
    _stage,
    client as client,
    w as w,
)

pytestmark = pytest.mark.postgres
MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "database/sql/063_evidence_category_length.sql"
)
ROWS = "genetic_evidence.case_control.single_variant_analysis"


def _rows(pmid: str) -> dict[str, Any]:
    return {"case_control": {"single_variant_analysis": [{"points": 2, "pmid": pmid}]}}


def test_patch_warns_scores_zero_409s_when_stale_and_submit_names_the_path(
    client: TestClient, w: W, monkeypatch: MonkeyPatch
) -> None:
    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        return PMIDValidationResult(
            pmid=pmid, is_valid=False, error=f"Publication not found: {pmid}"
        )

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    monkeypatch.setattr(evidence_ids, "lookup_pmids", publication_service.lookup_pmids)
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    entity = {
        "mondo_id": "MONDO:0000001",
        "disease_name": "d",
        "mode_of_inheritance": "AD",
    }
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": {"entity_definition": entity},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid, version = r.json()["id"], r.json()["lock_version"]

    patch = {"evidence_data": {"genetic_evidence": _rows("99999999")}, "merge": True}
    r = client.patch(
        f"/api/v1/curations/{cid}/draft?detail=true",
        json={**patch, "lock_version": version},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_data"]["entity_definition"] == entity
    assert r.json()["warnings"] == [
        {
            "path": f"{ROWS}[0].pmid",
            "message": "PMID 99999999 not found in PubMed: this row scores 0 and "
            "submit will refuse it; fix or remove the PMID",
        }
    ]
    assert r.json()["computed_scores"]["total_score"] == 0
    after = _stage(cid)

    stale = client.patch(
        f"/api/v1/curations/{cid}/draft?detail=true",
        json={**patch, "lock_version": version},
        headers=h,
    )
    assert stale.status_code == 409, stale.text
    assert _stage(cid) == after

    bad = {"evidence_data": {"genetic_evidence": _rows("PMID12x")}, "merge": True}
    r = client.patch(
        f"/api/v1/curations/{cid}/draft?detail=true",
        json={**bad, "lock_version": after[2]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    before = _stage(cid)
    refused = client.post(
        f"/api/v1/curations/{cid}/submit", json={"lock_version": before[2]}, headers=h
    )
    assert refused.status_code == 422, refused.text
    assert f"{ROWS}[0].pmid" in [e["path"] for e in refused.json()["detail"]["errors"]]
    assert _stage(cid) == before


def test_migration_063_widens_the_category_idempotently() -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(MIGRATION.read_text())
        cur.execute(MIGRATION.read_text())
        cur.execute(
            "SELECT character_maximum_length FROM information_schema.columns "
            "WHERE table_name = 'evidence_items' AND column_name = 'evidence_category'"
        )
        assert cur.fetchone() == (255,)
        cur.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = '063_evidence_category_length.sql'"
        )
        assert cur.fetchone() == (1,)


def test_app_user_caches_found_pmids(
    client: TestClient, w: W, monkeypatch: MonkeyPatch
) -> None:
    fetched: list[str] = []

    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        fetched.append(pmid)
        data = PublicationData(pmid=pmid, title="T", journal="J")
        return PMIDValidationResult(pmid=pmid, is_valid=True, publication=data)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    monkeypatch.setattr(evidence_ids, "lookup_pmids", publication_service.lookup_pmids)
    pmid = str(800000000 + w.scope.int % 10**8)
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": {},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid, version = r.json()["id"], r.json()["lock_version"]
    try:
        for _ in range(2):
            r = client.patch(
                f"/api/v1/curations/{cid}/draft?detail=true",
                json={
                    "evidence_data": {"genetic_evidence": _rows(pmid)},
                    "lock_version": version,
                },
                headers=h,
            )
            assert r.status_code == 200, r.text
            version = r.json()["lock_version"]
        assert fetched == [pmid]
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM publications WHERE pmid = %s", (pmid,))


def test_a_failed_cache_insert_never_fails_the_save(
    client: TestClient, w: W, monkeypatch: MonkeyPatch
) -> None:
    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        data = PublicationData(pmid=pmid, title="T", journal="J", pages="1-" + "9" * 80)
        return PMIDValidationResult(pmid=pmid, is_valid=True, publication=data)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    monkeypatch.setattr(evidence_ids, "lookup_pmids", publication_service.lookup_pmids)
    long_pmid, broken_pmid = (str(700000000 + w.scope.int % 10**8 + i) for i in (0, 1))
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": {},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid, version = r.json()["id"], r.json()["lock_version"]

    def save(pmid: str) -> Any:
        body = {
            "evidence_data": {"genetic_evidence": _rows(pmid)},
            "lock_version": version,
        }
        return client.patch(
            f"/api/v1/curations/{cid}/draft?detail=true", json=body, headers=h
        )

    try:
        r = save(long_pmid)  # pages longer than VARCHAR(50): cached cut to fit
        assert r.status_code == 200, r.text
        version = r.json()["lock_version"]
        real_row = publication_service.publication_row
        monkeypatch.setattr(
            publication_service,
            "publication_row",
            lambda data: {
                **real_row(data),
                "title": None,
            },  # NOT NULL: the insert fails
        )
        r = save(broken_pmid)
        assert r.status_code == 200, r.text
        assert r.json()["evidence_data"]["genetic_evidence"] == _rows(broken_pmid)
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pmid, length(pages) FROM publications WHERE pmid IN (%s, %s)",
                (long_pmid, broken_pmid),
            )
            assert cur.fetchall() == [(long_pmid, 50)]
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM publications WHERE pmid IN (%s, %s)",
                (long_pmid, broken_pmid),
            )
