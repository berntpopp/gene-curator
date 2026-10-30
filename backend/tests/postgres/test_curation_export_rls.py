"""Export v1 (#532) on the production role: anonymous and member reads under RLS."""

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
URL = "/api/v1/export/curations"


@dataclass
class W:
    member: UUID = field(default_factory=uuid4)
    pub: UUID = field(default_factory=uuid4)
    priv: UUID = field(default_factory=uuid4)
    pair: UUID = field(default_factory=uuid4)
    gene: UUID = field(default_factory=uuid4)
    ids: dict[str, UUID] = field(default_factory=dict)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.pub)[:8]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'xmem', 'user')",
            (str(x.member), f"xmem-{tag}@export.org", get_password_hash("pw")),
        )
        for sid, public in ((x.pub, True), (x.priv, False)):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(sid), f"ex-{sid}", f"EX {sid}", public, str(x.member)),
            )
            cur.execute(
                "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
                "accepted_at) VALUES (%s, %s, 'viewer', %s, now())",
                (str(sid), str(x.member), str(x.member)),
            )
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id) SELECT %s, %s, '1', precuration_schema_id, "
            "curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1",
            (str(x.pair), f"ex-{x.pair}"),
        )
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
            "VALUES (%s, %s, %s, %s)",
            (
                str(x.gene),
                f"HGNC:{x.gene.int % 10**9}",
                f"EXG{tag}",
                str(x.gene).replace("-", "") * 2,
            ),
        )
        for name, scope, status in (
            ("pub_old", x.pub, "archived"),
            ("pub_new", x.pub, "active"),
            ("priv", x.priv, "active"),
        ):
            cid = x.ids[name] = uuid4()
            cur.execute(
                "INSERT INTO curations (id, gene_id, scope_id, workflow_pair_id, status, "
                "workflow_stage, computed_verdict, evidence_data) VALUES (%s, %s, %s, %s, "
                "%s::curation_status, %s::workflow_stage, 'Strong', %s)",
                (
                    str(cid),
                    str(x.gene),
                    str(scope),
                    str(x.pair),
                    status,
                    status,
                    f'{{"note": "{name}", "rows": [{{"pmid": "31558469"}}]}}',  # distinct record_hash
                ),
            )
            cur.execute(
                "INSERT INTO active_curations (gene_id, scope_id, curation_id, "
                "archived_at) VALUES (%s, %s, %s, CASE WHEN %s THEN now() END)",
                (str(x.gene), str(scope), str(cid), status == "archived"),
            )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM scopes WHERE id IN (%s, %s)", (str(x.pub), str(x.priv))
        )
        cur.execute("DELETE FROM audit_log WHERE workflow_pair_id = %s", (str(x.pair),))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair),))
        cur.execute("DELETE FROM genes WHERE id = %s", (str(x.gene),))
        cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(x.member),))
        cur.execute("DELETE FROM users WHERE id = %s", (str(x.member),))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _mine(client: TestClient, w: W, user: UUID | None) -> dict[str, dict]:  # type: ignore[type-arg]
    headers = {}
    if user:
        headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user)})}"}
    r = client.get(URL, params={"limit": 500}, headers=headers)
    assert r.status_code == 200, r.text
    names = {str(v): k for k, v in w.ids.items()}
    return {
        names[i["curation_id"]]: i
        for i in r.json()["items"]
        if i["curation_id"] in names
    }


def test_anonymous_sees_active_curations_of_public_scopes_only(
    client: TestClient, w: W
) -> None:
    rows = _mine(client, w, None)
    assert set(rows) == {"pub_new"}
    assert rows["pub_new"]["pmids"] == ["31558469"]
    assert rows["pub_new"]["methodology"]["schema_name"]
    assert rows["pub_new"]["methodology"]["version"] is None  # RLS: signed-in only


def test_member_sees_archived_and_private_curations(client: TestClient, w: W) -> None:
    rows = _mine(client, w, w.member)
    assert set(rows) == {"pub_old", "pub_new", "priv"}
    assert rows["pub_old"]["archived_at"] is not None
    assert rows["pub_old"]["status"] == "archived"
    assert rows["pub_new"]["methodology"]["version"] >= 1


def test_deleted_active_curation_archives_its_pointer(client: TestClient, w: W) -> None:
    admin = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'xadm', 'admin')",
            (str(admin), f"xadm-{admin}@export.org", get_password_hash("pw")),
        )
    try:
        token = create_access_token({"sub": str(admin)})
        r = client.delete(
            f"/api/v1/curations/{w.ids['pub_new']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204, r.text
        assert _mine(client, w, None) == {}
        assert set(_mine(client, w, w.member)) == {"pub_old", "priv"}
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT archived_at IS NOT NULL, archived_by FROM active_curations "
                "WHERE curation_id = %s",
                (str(w.ids["pub_new"]),),
            )
            assert cur.fetchone() == (True, str(admin))
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(admin),))
            cur.execute(
                "UPDATE active_curations SET archived_by = NULL WHERE archived_by = %s",
                (str(admin),),
            )
            cur.execute(
                "UPDATE curations SET updated_by = NULL WHERE updated_by = %s",
                (str(admin),),
            )
            cur.execute("DELETE FROM users WHERE id = %s", (str(admin),))
