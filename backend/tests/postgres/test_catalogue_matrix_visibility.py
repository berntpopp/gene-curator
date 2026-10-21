"""Catalogue matrix on the production role: private scopes, pending invites and admins (#276)."""

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
URL = "/api/v1/gene-catalogue/matrix"


@dataclass
class W:
    member: UUID = field(default_factory=uuid4)
    pending: UUID = field(default_factory=uuid4)
    outsider: UUID = field(default_factory=uuid4)
    root: UUID = field(default_factory=uuid4)  # application admin, no membership
    pub: UUID = field(default_factory=uuid4)
    priv: UUID = field(default_factory=uuid4)
    pair: UUID = field(default_factory=uuid4)
    active_gene: UUID = field(default_factory=uuid4)
    draft_gene: UUID = field(default_factory=uuid4)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _curation(
    cur, w: W, gene: UUID, scope: UUID, status: str, stage: str, verdict
) -> None:  # type: ignore[no-untyped-def]
    cid = uuid4()
    cur.execute(
        "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
        "workflow_stage, computed_verdict) "
        "VALUES (%s, %s, %s, %s, %s::curation_status, %s::workflow_stage, %s)",
        (str(cid), str(gene), str(scope), str(w.pair), status, stage, verdict),
    )
    if status == "active":
        cur.execute(
            "INSERT INTO active_curations (gene_id, scope_id, curation_id) "
            "VALUES (%s, %s, %s)",
            (str(gene), str(scope), str(cid)),
        )


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.pub)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name, role in (
            (x.member, "mmem", "user"),
            (x.pending, "mpen", "user"),
            (x.outsider, "mout", "user"),
            (x.root, "mroot", "admin"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(uid),
                    f"{name}-{tag}@matrix.org",
                    get_password_hash("pw"),
                    name,
                    role,
                ),
            )
        for sid, public in ((x.pub, True), (x.priv, False)):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(sid), f"mx-{sid}", f"MX {sid}", public, str(x.member)),
            )
        for uid, accepted in ((x.member, True), (x.pending, False)):
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, 'viewer', %s, CASE WHEN %s THEN now() END)",
                (str(x.priv), str(uid), str(x.member), accepted),
            )
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version) VALUES (%s, %s, '1')",
            (str(x.pair), f"mx-{x.pair}"),
        )
        for gid, sym in ((x.active_gene, "MXA"), (x.draft_gene, "MXD")):
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (
                    str(gid),
                    f"HGNC:{gid.int % 10**9}",
                    f"{sym}{tag}",
                    str(gid).replace("-", "") * 2,
                ),
            )
        _curation(cur, x, x.active_gene, x.pub, "active", "active", "Strong")
        _curation(cur, x, x.active_gene, x.priv, "active", "active", "Refuted")
        _curation(cur, x, x.draft_gene, x.priv, "draft", "curation", None)
    yield x
    with _owner() as conn, conn.cursor() as cur:
        users = [str(u) for u in (x.member, x.pending, x.outsider, x.root)]
        cur.execute(
            "DELETE FROM scopes WHERE id IN (%s, %s)", (str(x.pub), str(x.priv))
        )
        cur.execute("DELETE FROM audit_log WHERE workflow_pair_id = %s", (str(x.pair),))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair),))
        cur.execute(
            "DELETE FROM genes WHERE id IN (%s, %s)",
            (str(x.active_gene), str(x.draft_gene)),
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _get(client: TestClient, w: W, user: UUID | None) -> dict:  # type: ignore[type-arg]
    headers = {}
    if user:
        token = create_access_token(data={"sub": str(user)})
        headers = {"Authorization": f"Bearer {token}"}
    params = [("scope_ids", str(w.pub)), ("scope_ids", str(w.priv)), ("limit", "100")]
    r = client.get(URL, params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def _mine(body: dict, w: W) -> dict:  # type: ignore[type-arg]
    ids = {str(w.active_gene), str(w.draft_gene)}
    return {r["gene_id"]: r for r in body["rows"] if r["gene_id"] in ids}


def test_member_sees_private_cells_and_own_in_progress(
    client: TestClient, w: W
) -> None:
    body = _get(client, w, w.member)
    assert {s["id"] for s in body["scopes"]} == {str(w.pub), str(w.priv)}
    rows = _mine(body, w)
    active = rows[str(w.active_gene)]
    assert len(active["cells"]) == 2
    assert active["agreement"] == "disagree"
    draft = rows[str(w.draft_gene)]
    assert draft["cells"][0]["in_progress"] is True
    assert draft["cells"][0]["stage"] == "curation"


@pytest.mark.parametrize("who", ["anonymous", "pending", "outsider", "root"])
def test_everyone_else_sees_public_scope_only(
    client: TestClient, w: W, who: str
) -> None:
    user = {
        "anonymous": None,
        "pending": w.pending,
        "outsider": w.outsider,
        "root": w.root,
    }[who]
    body = _get(client, w, user)
    assert [s["id"] for s in body["scopes"]] == [str(w.pub)]
    rows = _mine(body, w)
    assert set(rows) == {str(w.active_gene)}
    assert [c["scope_id"] for c in rows[str(w.active_gene)]["cells"]] == [str(w.pub)]
    assert rows[str(w.active_gene)]["agreement"] == "single"
