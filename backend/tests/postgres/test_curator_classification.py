"""Curator/final classification (#533) through the real API as app_user: the curator
proposes an override with a rationale, another reviewer approves, the catalogue and export
publish the final class next to the computed one; no override publishes the computed."""

import json
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

pytestmark = pytest.mark.postgres


@dataclass
class W:
    scope: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator, author
    bob: UUID = field(default_factory=uuid4)  # reviewer
    gene: UUID = field(default_factory=uuid4)
    cur: UUID = field(default_factory=uuid4)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    members = ((x.alice, "curator"), (x.bob, "reviewer"))
    ids = [str(u) for u, _ in members]
    with _owner() as conn, conn.cursor() as cur:
        for uid, _ in members:
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, 'u', 'user')",
                (str(uid), f"{uid.hex[:8]}-{tag}@cc.org", get_password_hash("pw")),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'CC', false, %s)",
            (str(x.scope), f"cc-{x.scope}", str(x.alice)),
        )
        for uid, role in members:
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, %s, %s, now())",
                (str(x.scope), str(uid), role, str(x.alice)),
            )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (str(x.gene), f"HGNC:{x.gene.int % 10**9}", f"CC{tag}", x.gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
            "workflow_stage, is_draft, evidence_data, created_by) SELECT %s, %s, %s, id, "
            "'draft', 'curation', true, %s, %s FROM workflow_pairs WHERE is_active LIMIT 1",
            (
                str(x.cur),
                str(x.gene),
                str(x.scope),
                json.dumps(
                    {
                        "summary": "ok",
                        "entity_definition": {
                            "mondo_id": "MONDO:0000001",
                            "disease_name": "Test disease",
                            "mode_of_inheritance": "Autosomal dominant",
                        },
                    }
                ),
                str(x.alice),
            ),
        )
    yield x
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


@pytest.mark.parametrize("override", ["Strong", None])
def test_final_classification_is_proposed_approved_and_published(
    client: TestClient, w: W, override: str | None
) -> None:
    url = f"/api/v1/curations/{w.cur}"
    lock = client.get(url, headers=_h(w.alice)).json()["lock_version"]
    r = client.put(
        url,
        json={"curator_classification": override, "lock_version": lock},
        headers=_h(w.alice),
    )
    assert r.status_code == 200, r.text
    lock = r.json()["lock_version"]
    submit = {"lock_version": lock, "reviewer_id": str(w.bob)}
    if override:
        refused = client.post(f"{url}/submit", json=submit, headers=_h(w.alice))
        assert refused.status_code == 422, refused.text
        assert "curator_classification_rationale" in refused.text
        r = client.patch(
            f"{url}/draft",
            json={
                "evidence_data": {},
                "merge": True,  # an empty merge patch keeps the evidence
                "curator_classification_rationale": "Replicated over time",
                "lock_version": lock,
            },
            headers=_h(w.alice),
        )
        assert r.status_code == 200, r.text
        submit["lock_version"] = r.json()["lock_version"]
    r = client.post(f"{url}/submit", json=submit, headers=_h(w.alice))
    assert r.status_code == 200, r.text

    read = client.get(f"{url}/review", headers=_h(w.bob)).json()["curation"]
    computed = read["computed_verdict"]
    final = override.lower() if override else computed  # stored as its key
    assert final  # the empty evidence still classifies
    assert read["final_classification"] == final
    assert read["curator_classification_rationale"] == (
        "Replicated over time" if override else None
    )
    (review,) = client.get(
        "/api/v1/workflow/reviews/my-assignments", headers=_h(w.bob)
    ).json()
    r = client.post(
        f"/api/v1/workflow/reviews/{review['review_id']}/submit",
        json={"decision": "approve", "comments": "Agree with the final class"},
        headers=_h(w.bob),
    )
    assert r.status_code == 200, r.text

    cat = client.get(
        "/api/v1/gene-catalogue/",
        params={"scope_id": str(w.scope)},
        headers=_h(w.bob),
    ).json()
    [summary] = cat["entries"][0]["scope_curations"]
    assert (summary["classification"], summary["computed_verdict"]) == (
        final,
        computed,
    )
    items = client.get(
        "/api/v1/export/curations",
        params={"scope_name": f"cc-{w.scope}"},
        headers=_h(w.bob),
    ).json()["items"]
    [item] = [i for i in items if i["curation_id"] == str(w.cur)]
    assert (item["final_classification"], item["computed_verdict"]) == (final, computed)
    assert item["status"] == "active"
    assert (
        item["curator_classification_rationale"]
        == read["curator_classification_rationale"]
    )

    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT changes->>'curator_classification' FROM audit_log "
            "WHERE entity_id = %s AND operation = 'UPDATE' ORDER BY timestamp DESC "
            "LIMIT 1",
            (str(w.cur),),
        )
        row = cur.fetchone()
    assert row is not None and row[0] == (final if override else None)  # audited
