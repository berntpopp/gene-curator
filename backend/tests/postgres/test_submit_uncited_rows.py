"""Submit refuses scored case rows without a PMID or a real variant, as app_user through the
real API (owner decisions 2026-10-27/28); Europe PMC mocked; nothing changes."""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.schemas.validation import PMIDValidationResult
from app.services.publication_service import PublicationService

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator
    gene: UUID = field(default_factory=uuid4)
    pre: UUID = field(default_factory=uuid4)  # approved precuration of the gene
    pair: str = ""
    extra_genes: list[UUID] = field(default_factory=list)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'alice', 'user')",
            (str(x.alice), f"alice-{tag}@uncited.org", get_password_hash("pw")),
        )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'GC', false, %s)",
            (str(x.scope), f"uc-{x.scope}", str(x.alice)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
        cur.execute(
            "SELECT id, precuration_schema_id FROM workflow_pairs WHERE is_active LIMIT 1"
        )
        pair, schema = cur.fetchone()
        x.pair = str(pair)
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"UC{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
            "status, workflow_stage, is_draft, created_by) VALUES "
            "(%s, %s, %s, %s, 'approved', 'curation', false, %s)",
            (str(x.pre), str(x.gene), str(x.scope), str(schema), str(x.alice)),
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM genes WHERE id = ANY(%s::uuid[])",
            ([str(g) for g in [x.gene, *x.extra_genes]],),
        )
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = %s OR scope_id = %s",
            (str(x.alice), str(x.scope)),
        )
        cur.execute("DELETE FROM users WHERE id = %s", (str(x.alice),))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _stage(cid: str) -> tuple[str, str, int]:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, workflow_stage, lock_version FROM curations WHERE id = %s",
            (cid,),
        )
        row = cur.fetchone()
        assert row
        return row[0], row[1], row[2]


ROWS = "genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null"


def _evidence(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "entity_definition": {
            "mondo_id": "MONDO:0000001",
            "disease_name": "disease",
            "mode_of_inheritance": "AD",
        },
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": rows}
            }
        },
    }


def test_submit_refuses_uncited_scored_case_rows_until_fixed(
    client: TestClient, w: W, monkeypatch: MonkeyPatch
) -> None:
    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        return PMIDValidationResult(pmid=pmid, is_valid=True, error=None)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    h = {"Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"}
    row = {"proband_label": "P1", "variant_type": "nonsense", "pmid": "31558469"}
    rows = [
        {
            **row,
            "variant": "truncating variant (as reported)",
            "proband_counted_points": 2,
        },
        {**row, "pmid": "", "variant": "c.1A>T", "proband_counted_points": 2},
    ]
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": _evidence(rows),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text  # drafts never block
    cid = r.json()["id"]
    before = _stage(cid)

    refused = client.post(
        f"/api/v1/curations/{cid}/submit", json={"lock_version": before[2]}, headers=h
    )
    assert refused.status_code == 422, refused.text
    paths = [e["path"] for e in refused.json()["detail"]["errors"]]
    assert paths == [f"{ROWS}[0].variant", f"{ROWS}[1].pmid"]
    assert _stage(cid) == before

    rows[0]["variant"] = "NM_000001.1:c.100C>T (p.Arg34Ter)"
    rows[1]["pmid"] = "31558469"
    r = client.put(
        f"/api/v1/curations/{cid}",
        json={"evidence_data": _evidence(rows), "lock_version": before[2]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    lock = r.json()["lock_version"]
    ok = client.post(
        f"/api/v1/curations/{cid}/submit", json={"lock_version": lock}, headers=h
    )
    assert ok.status_code == 200, ok.text
    assert _stage(cid)[1] == "review"
