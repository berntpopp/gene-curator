"""The KGDB bundle end to end as app_user on PostgreSQL: a platform admin imports it, a
curator precurates and curates CLDN16 in the seeded kidney-genetics scope, it scores
Definitive (16 points), another reviewer approves both steps (D1) and a viewer member
exports it with its evidence, diagnostics included."""

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.schemas.validation import PMIDValidationResult
from app.services import evidence_ids
from app.services.publication_service import PublicationService
from tests.postgres.test_methodology_versions import _h, _owner, client
from tests.unit.test_kgdb_methodology import BUNDLE, SCHEMAS

pytestmark = pytest.mark.postgres
__all__ = ["client"]

SCOPE = "kidney-genetics"
TESTS = SCHEMAS["KGDB Mendelian Curation"]["scoring_configuration"]["tests"]
CLDN16 = next(t for t in TESTS if t["name"].startswith("CLDN16"))["evidence_data"]
DIAGNOSTICS = {
    "recommended_transcript": {"refseq": "NM_006580.4", "mane_status": "select"},
    "detectability": [],
    "resources": [
        {
            "type": "other",
            "name": "ERKNet",
            "url": "https://www.erknet.org",
            "audiences": ["patients", "clinicians"],
            "verified_method": "fetched",
            "verified_date": "2026-10-30",
        }
    ],
}
NOTES = {"detectability_note": "standard short-read testing adequate"}
ENTITY = {
    "clingen_curated": False,
    "mondo_id": "MONDO:0009633",
    "disease_name": "familial hypomagnesemia with hypercalciuria and nephrocalcinosis",
    "mode_of_inheritance": "HP:0000007",
    "relationship_type": "mendelian",
    "lumping_splitting_applicable": False,
    "binning": "isolated",
    "mechanism": "lof",
}


@dataclass
class W:
    admin: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author
    bob: UUID = field(default_factory=uuid4)  # independent reviewer
    carol: UUID = field(default_factory=uuid4)  # viewer member, export reader
    gene: UUID = field(default_factory=uuid4)
    scope: str = ""


@pytest.fixture
def w(monkeypatch: pytest.MonkeyPatch) -> Generator[W, None, None]:
    # PubMed and the ontologies are offline: every ID is known
    monkeypatch.setattr(evidence_ids, "lookup_pmids", lambda db, ids: ([], []))
    monkeypatch.setattr(evidence_ids, "lookup_terms", lambda ids: ([], []))

    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    x = W()
    tag = x.gene.hex[:8]
    users = [(x.admin, "admin"), (x.alice, "user"), (x.bob, "user"), (x.carol, "user")]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, default_workflow_pair_id FROM scopes WHERE name = %s", (SCOPE,)
        )
        scope, default = cur.fetchone()
        x.scope = str(scope)
        for uid, role in users:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'kgdb', %s)",
                (str(uid), f"{uid.hex[:8]}@kgdb.org", get_password_hash("pw"), role),
            )
        for uid, role in (
            (x.alice, "curator"),
            (x.bob, "reviewer"),
            (x.carol, "viewer"),
        ):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (x.scope, str(uid), role, str(x.admin)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"KG{tag}", x.gene.hex * 2),
        )
    yield x
    ids = [str(uid) for uid, _ in users]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        # Other lanes look these PMIDs up again: drop what the export path cached
        cur.execute("DELETE FROM publications WHERE pmid LIKE '310000__'")
        cur.execute(
            "UPDATE scopes SET default_workflow_pair_id = %s WHERE id = %s",
            (default, x.scope),
        )
        cur.execute("SELECT id FROM workflow_pairs WHERE name LIKE 'KGDB %'")
        pairs = [str(r[0]) for r in cur.fetchall()]
        cur.execute("SELECT id FROM curation_schemas WHERE name LIKE 'KGDB %'")
        schemas = [str(r[0]) for r in cur.fetchall()]
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) "
            "OR workflow_pair_id = ANY(%s::uuid[]) OR schema_id = ANY(%s::uuid[])",
            (ids, pairs, schemas),
        )
        cur.execute("DELETE FROM workflow_pairs WHERE id = ANY(%s::uuid[])", (pairs,))
        cur.execute(
            "DELETE FROM curation_schemas WHERE id = ANY(%s::uuid[])", (schemas,)
        )
        cur.execute(
            "DELETE FROM scope_memberships WHERE user_id = ANY(%s::uuid[])", (ids,)
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (ids,))


def _ok(r: Any) -> dict[str, Any]:
    assert r.status_code in (200, 201), r.text
    body: dict[str, Any] = r.json()
    return body


def test_kgdb_gene_is_imported_curated_scored_and_exported(
    client: TestClient, w: W
) -> None:
    url = "/api/v1/schemas/methodologies/import"
    items = _ok(client.post(url, json=BUNDLE, headers=_h(w.admin)))["items"]
    ids = {i["name"]: i["id"] for i in items}

    # The susceptibility pair's precuration makes its own entity (#539)
    risk = _ok(
        client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": w.scope,
                "precuration_schema_id": ids["KGDB Susceptibility Precuration"],
                "evidence_data": {**ENTITY, "relationship_type": "susceptibility"},
            },
            headers=_h(w.alice),
        )
    )
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("SELECT entity_key FROM precurations WHERE id = %s", (risk["id"],))
        assert cur.fetchone() == ("MONDO:0009633|AR|SUSCEPTIBILITY",)

    pre = _ok(
        client.post(
            "/api/v1/precurations/",
            json={
                "gene_id": str(w.gene),
                "scope_id": w.scope,
                "precuration_schema_id": ids["KGDB Mendelian Precuration"],
                "evidence_data": ENTITY,
            },
            headers=_h(w.alice),
        )
    )
    _ok(
        client.post(
            f"/api/v1/precurations/{pre['id']}/submit",
            json={"lock_version": pre["lock_version"], "reviewer_id": str(w.bob)},
            headers=_h(w.alice),
        )
    )
    cid = _ok(
        client.post(f"/api/v1/precurations/{pre['id']}/approve", headers=_h(w.bob))
    )["curation_id"]

    curation = f"/api/v1/curations/{cid}"
    lock = _ok(client.get(curation, headers=_h(w.alice)))["lock_version"]
    evidence = {
        **CLDN16,
        "diagnostics": DIAGNOSTICS,
        "diagnostics_notes": NOTES,
        "evidence_summary": "CLDN16",
    }
    saved = _ok(
        client.patch(
            f"{curation}/draft",
            json={"evidence_data": evidence, "lock_version": lock},
            headers=_h(w.alice),
        )
    )
    read = _ok(client.get(curation, headers=_h(w.alice)))
    assert (read["computed_verdict"], read["computed_scores"]["total_score"]) == (
        "definitive",
        16,
    )
    _ok(
        client.post(
            f"{curation}/submit",
            json={"lock_version": saved["lock_version"], "reviewer_id": str(w.bob)},
            headers=_h(w.alice),
        )
    )
    (review,) = _ok(
        client.get("/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob))
    )
    _ok(
        client.post(
            f"/api/v1/workflow/reviews/{review['review_id']}/submit",
            json={"decision": "approve", "comments": "Pilot gene"},
            headers=_h(w.bob),
        )
    )

    page = _ok(
        client.get(
            "/api/v1/export/curations",
            params={"scope_name": SCOPE, "limit": 500},
            headers=_h(w.carol),
        )
    )
    [item] = [i for i in page["items"] if i["curation_id"] == cid]
    assert item["status"] == "active"
    assert (item["computed_verdict"], item["final_classification"]) == (
        "definitive",
        "definitive",
    )
    assert (item["genetic_score"], item["experimental_score"]) == (10, 6)
    assert item["entity_key"] == "MONDO:0009633|AR"
    assert item["methodology"]["schema_name"] == "KGDB Mendelian Curation"
    assert item["methodology"]["version"] == 1
    assert item["evidence"]["diagnostics"] == DIAGNOSTICS
    assert item["evidence"]["diagnostics_notes"] == NOTES
    assert len(item["evidence"]["genetic"]["probands"]) == 10
    assert item["evidence"]["replicated_over_time"] is True
