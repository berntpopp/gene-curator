"""ClinGen adoption (#105) as the API runs (app_user, RLS): the curator adopts, the adopter's
own approval is refused (D1), another reviewer of the scope approves it to active."""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.services.clingen_adoption import ADOPTION_COMMENT

pytestmark = pytest.mark.postgres
CGGV = "CGGV:assertion_d38c5bda-7182-403f-a99b-4f8492afb24f-2023-01-11T170000.000Z"


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, adopts
    bob: UUID = field(default_factory=uuid4)  # reviewer
    gene: UUID = field(default_factory=uuid4)
    hgnc: str = ""
    pair: str = ""


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W(hgnc=f"HGNC:{uuid4().int % 10**9}")
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid in (x.alice, x.bob):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid.hex[:8]}-{tag}@adopt.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'AD', false, %s)",
            (str(x.scope), f"adopt-{x.scope}", str(x.alice)),
        )
        for uid, role in ((x.alice, "curator"), (x.bob, "reviewer")):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute("SELECT id FROM workflow_pairs WHERE is_active LIMIT 1")
        x.pair = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), x.hgnc, f"AD{tag}", x.gene.hex * 2),
        )
    yield x
    ids = [str(x.alice), str(x.bob)]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[]) OR scope_id = %s",
            (ids, str(x.scope)),
        )
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (ids,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_adopt_then_only_another_reviewer_approves(client: TestClient, w: W) -> None:
    row = {
        "gene_id": str(w.gene),
        "scope_id": str(w.scope),
        "workflow_pair_id": w.pair,
        "mondo_id": "MONDO:0009889",
        "mode_of_inheritance": "Autosomal recessive",
        "disease_name": "autosomal recessive polycystic kidney disease",
        "clingen": {
            "cggv_id": CGGV,
            "permalink": f"https://search.clinicalgenome.org/kb/gene-validity/{CGGV}",
            "classification": "Definitive",
            "moi": "AR",
            "mondo": "MONDO:0009889",
            "hgnc_id": w.hgnc,
            "expert_panel": "Kidney Cystic and Ciliopathy Disorders GCEP",
            "classified_date": "2023-01-11T17:00:00.000Z",
            "retrieved_at": "2026-10-31T09:10:08.948367Z",
            "record_sha256": "16d03aeb2ecd2b4c65bc16a233fe194d4d7c01e1f26b794fdd44a77d2848fb0b",
            "citation": "ClinGen Gene-Disease Validity: PKD1 — Definitive (AR)",
        },
    }
    url = "/api/v1/curations/clingen-adoptions"
    assert client.post(url, json={"rows": [row]}, headers=_h(w.bob)).status_code == 403
    r = client.post(url, json={"rows": [row]}, headers=_h(w.alice))
    assert r.status_code == 200, r.text
    cid = r.json()["items"][0]["curation_id"]
    again = client.post(url, json={"rows": [row]}, headers=_h(w.alice))
    assert again.json()["items"][0]["action"] == "unchanged"

    detail = client.get(f"/api/v1/curations/{cid}", headers=_h(w.bob)).json()
    assert (detail["status"], detail["final_classification"]) == ("in_review", None)
    assert (detail["computed_verdict"], detail["computed_scores"]) == (None, {})
    # #613: diagnostics still go in while it waits for review, by its curator only
    diagnostics = {"diagnostics": {"recommended_transcript": {"refseq": "NM_138694.4"}}}
    put = {"evidence_data": diagnostics, "merge": True}
    cur = f"/api/v1/curations/{cid}"
    lock = {"lock_version": detail["lock_version"]}
    assert client.put(cur, json=put | lock, headers=_h(w.bob)).status_code == 403
    asked = client.post(
        f"/api/v1/workflow/curation/{cid}/assign-reviewer",
        json={"reviewer_id": str(w.bob)},
        headers=_h(w.alice),
    )
    assert asked.status_code == 200, asked.text
    r = client.put(cur, json=put | lock, headers=_h(w.alice))
    assert r.status_code == 200, r.text
    # the edit starts a new review round: bob is asked again, as app_user under RLS
    with _owner() as conn, conn.cursor() as c:
        c.execute(
            "SELECT count(*) FROM reviews r JOIN curations c ON c.id = r.curation_id "
            "WHERE r.curation_id = %s AND r.reviewer_id = %s "
            "AND r.assigned_at >= c.submitted_at",
            (cid, str(w.bob)),
        )
        assert c.fetchone()[0] == 1
    # KGDB e2e: the new round is a submission, so the reviewer sees what changed
    diff = client.get(
        f"{cur}/diff", params={"baseline": "previous_submission"}, headers=_h(w.bob)
    )
    assert diff.status_code == 200, diff.text
    assert any(i["path"].startswith("diagnostics") for i in diff.json()["items"])
    lock = {"lock_version": r.json()["lock_version"]}
    moved = {"curator_classification": "limited"} | lock
    refused = client.put(cur, json=moved, headers=_h(w.alice))
    assert refused.status_code == 409 and "ClinGen" in refused.text, refused.text
    assert detail["clingen_adoption"]["cggv_id"] == CGGV
    comments = client.get(f"/api/v1/curations/{cid}/review-comments", headers=_h(w.bob))
    assert [c["body"] for c in comments.json()] == [ADOPTION_COMMENT]

    move = f"/api/v1/workflow/curation/{cid}/transition"
    body = {"target_stage": "active", "notes": "confirmed against ClinGen"}
    assert client.post(move, json=body, headers=_h(w.alice)).status_code == 403
    ok = client.post(move, json=body, headers=_h(w.bob))
    assert ok.status_code == 200, ok.text
    assert ok.json()["to_stage"] == "active"
    assert client.post(move, json=body, headers=_h(w.bob)).status_code == 409

    items = client.get(
        "/api/v1/export/curations", params={"scope_id": str(w.scope)}, headers=_h(w.bob)
    ).json()["items"]
    roles = [c["activityType"]["name"] for c in items[0]["adoption"]["contributions"]]
    assert roles == ["interpreter", "curator", "approver"]
    item = items[0]
    assert (item["final_classification"], item["computed_verdict"]) == (
        "definitive",
        None,
    )
    assert [item[k] for k in ("genetic_score", "total_score", "scores")] == [None] * 3
    assert item["evidence"]["diagnostics"] == diagnostics["diagnostics"]
