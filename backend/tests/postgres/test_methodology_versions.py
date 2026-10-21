"""Methodology versions on real PostgreSQL (042, #265 slice 1).

Published versions are immutable for every role, rows are pinned at creation and never
re-pinned, a later publish leaves existing curations on their version, and the migration
backfills legacy data and can run twice.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app
from tests.postgres.conftest import set_test_user_context

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/042_methodology_versions.sql"
LATEST = (
    "SELECT id FROM methodology_versions WHERE schema_id = :s "
    "ORDER BY version DESC LIMIT 1"
)


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _fails(s: Session, sql: str, **params: object) -> None:
    with pytest.raises(DBAPIError, match=r"immutable|pinned"), s.begin_nested():
        s.execute(text(sql), params)


# ---------------------------------------------------------------------------
# (a) published versions are immutable, also for the owner and platform admins
# ---------------------------------------------------------------------------


def test_published_version_cannot_change_as_owner(owner_session: Session) -> None:
    vid = owner_session.scalar(text("SELECT id FROM methodology_versions LIMIT 1"))
    _fails(
        owner_session,
        "UPDATE methodology_versions SET snapshot = '{}' WHERE id = :v",
        v=vid,
    )
    _fails(owner_session, "DELETE FROM methodology_versions WHERE id = :v", v=vid)


def test_admin_publishes_but_cannot_change_or_delete(db: Session) -> None:
    admin = db.scalar(
        text("SELECT id FROM users WHERE role = 'admin' AND is_active LIMIT 1")
    )
    set_test_user_context(db, str(admin))
    schema = db.scalar(text("SELECT id FROM curation_schemas LIMIT 1"))
    vid = db.scalar(
        text(
            "INSERT INTO methodology_versions (schema_id, version, snapshot, created_by) "
            "VALUES (:s, 999, '{}', :u) RETURNING id"
        ),
        {"s": schema, "u": admin},
    )
    # no UPDATE/DELETE policy: app_user changes nothing, not even as platform admin
    for sql in (
        "UPDATE methodology_versions SET snapshot = '{\"a\": 1}' WHERE id = :v",
        "DELETE FROM methodology_versions WHERE id = :v",
    ):
        assert db.execute(text(sql), {"v": vid}).rowcount == 0  # type: ignore[attr-defined]
    assert (
        db.scalar(
            text("SELECT snapshot FROM methodology_versions WHERE id = :v"), {"v": vid}
        )
        == {}
    )


def test_row_without_a_published_version_is_refused(owner_session: Session) -> None:
    s = owner_session
    s.execute(
        text(
            "ALTER TABLE curation_schemas "
            "DISABLE TRIGGER trigger_publish_initial_methodology_version"
        )
    )
    schema = s.scalar(
        text(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "workflow_states, ui_configuration, schema_hash) VALUES ('nover', '1', "
            "'precuration', '{}', '{}', '{}', repeat('6', 64)) RETURNING id"
        )
    )
    gene, scope = s.execute(
        text("SELECT (SELECT id FROM genes LIMIT 1), (SELECT id FROM scopes LIMIT 1)")
    ).one()
    with pytest.raises(DBAPIError, match="no published methodology version"):
        s.execute(
            text(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id) "
                "VALUES (:g, :sc, :ps)"
            ),
            {"g": gene, "sc": scope, "ps": schema},
        )


def test_non_admin_reads_but_cannot_write(db: Session) -> None:
    user = db.scalar(text("SELECT id FROM users WHERE role <> 'admin' LIMIT 1"))
    set_test_user_context(db, str(user))
    assert db.scalar(text("SELECT count(*) FROM methodology_versions")) > 0
    schema = db.scalar(text("SELECT id FROM curation_schemas LIMIT 1"))
    with pytest.raises(DBAPIError, match="row-level security"), db.begin_nested():
        db.execute(
            text(
                "INSERT INTO methodology_versions (schema_id, version, snapshot) "
                "VALUES (:s, 998, '{}')"
            ),
            {"s": schema},
        )


# ---------------------------------------------------------------------------
# (b) the pin is set at creation and can never change
# ---------------------------------------------------------------------------


def test_rows_are_pinned_at_creation_and_never_repinned(
    owner_session: Session,
) -> None:
    s = owner_session
    pair, cur_schema, pre_schema, scope, user = s.execute(
        text(
            "SELECT wp.id, wp.curation_schema_id, wp.precuration_schema_id, "
            "(SELECT id FROM scopes LIMIT 1), (SELECT id FROM users LIMIT 1) "
            "FROM workflow_pairs wp WHERE wp.is_active LIMIT 1"
        )
    ).one()
    gene = s.scalar(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, record_hash) "
            "VALUES ('HGNC:999042', 'PIN042', repeat('4', 64)) RETURNING id"
        )
    )
    pre = s.scalar(
        text(
            "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, created_by) "
            "VALUES (:g, :sc, :ps, :u) RETURNING id"
        ),
        {"g": gene, "sc": scope, "ps": pre_schema, "u": user},
    )
    cur = s.scalar(
        text(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, evidence_data, "
            "created_by) VALUES (:g, :sc, :p, '{}', :u) RETURNING id"
        ),
        {"g": gene, "sc": scope, "p": pair, "u": user},
    )
    pinned = s.execute(
        text(
            "SELECT (SELECT methodology_version_id FROM precurations WHERE id = :pre), "
            "(SELECT methodology_version_id FROM curations WHERE id = :cur)"
        ),
        {"pre": pre, "cur": cur},
    ).one()
    assert pinned == (
        s.scalar(text(LATEST), {"s": pre_schema}),
        s.scalar(text(LATEST), {"s": cur_schema}),
    )

    newer = s.scalar(
        text(
            "INSERT INTO methodology_versions (schema_id, version, snapshot) "
            "SELECT :s, max(version) + 1, '{}' "
            "FROM methodology_versions WHERE schema_id = :s RETURNING id"
        ),
        {"s": cur_schema},
    )
    for table, row in (("curations", cur), ("precurations", pre)):
        _fails(
            s,
            f"UPDATE {table} SET methodology_version_id = :v WHERE id = :r",
            v=newer,
            r=row,
        )
    # other updates of a pinned row still work
    s.execute(
        text("UPDATE curations SET evidence_data = '{\"x\": 1}' WHERE id = :c"),
        {"c": cur},
    )


# ---------------------------------------------------------------------------
# (c) the real API flow as app_user
# ---------------------------------------------------------------------------


@dataclass
class W:
    admin: UUID = field(default_factory=uuid4)
    alice: UUID = field(default_factory=uuid4)  # curator
    scope: UUID = field(default_factory=uuid4)
    genes: tuple[UUID, UUID] = field(default_factory=lambda: (uuid4(), uuid4()))
    schema: str = ""  # curation schema created after the migration
    pair: str = ""
    v1: str = ""


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.scope)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name, role in (
            (x.admin, "admin", "admin"),
            (x.alice, "alice", "user"),
        ):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(uid), f"{name}-{tag}@mv.org", get_password_hash("pw"), name, role),
            )
        cur.execute(
            "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
            "VALUES (%s, %s, 'MV', false, %s)",
            (str(x.scope), f"mv-{x.scope}", str(x.alice)),
        )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'curator', %s, now())",
            (str(x.scope), str(x.alice), str(x.alice)),
        )
        cur.execute(
            "SELECT precuration_schema_id, curation_schema_id FROM workflow_pairs "
            "WHERE is_active LIMIT 1"
        )
        pre_schema, seeded = cur.fetchone()
        cur.execute(
            "INSERT INTO curation_schemas (name, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash, created_by) SELECT %s, version, schema_type, field_definitions, "
            "validation_rules, scoring_configuration, workflow_states, ui_configuration, "
            "schema_hash, %s FROM curation_schemas WHERE id = %s RETURNING id",
            (f"mv-{tag}", str(x.admin), seeded),
        )
        x.schema = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO workflow_pairs (name, version, precuration_schema_id, "
            "curation_schema_id) VALUES (%s, '1', %s, %s) RETURNING id",
            (f"mv-{tag}", pre_schema, x.schema),
        )
        x.pair = str(cur.fetchone()[0])
        cur.execute(
            "SELECT id, version FROM methodology_versions WHERE schema_id = %s",
            (x.schema,),
        )
        rows = cur.fetchall()
        assert [r[1] for r in rows] == [1]  # auto-published v1 on insert
        x.v1 = str(rows[0][0])
        for gene in x.genes:
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
                "VALUES (%s, %s, %s, %s)",
                (
                    str(gene),
                    f"HGNC:{gene.int % 10**9}",
                    f"MV{gene.hex[:6]}",
                    gene.hex * 2,
                ),
            )
            cur.execute(
                "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, "
                "status, workflow_stage, is_draft, created_by) VALUES "
                "(%s, %s, %s, 'approved', 'curation', false, %s)",
                (str(gene), str(x.scope), pre_schema, str(x.alice)),
            )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM scopes WHERE id = %s", (str(x.scope),))
        cur.execute(
            "DELETE FROM audit_log WHERE user_id IN (%s, %s) OR scope_id = %s "
            "OR workflow_pair_id = %s OR schema_id = %s",
            (str(x.admin), str(x.alice), str(x.scope), x.pair, x.schema),
        )
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (x.pair,))
        # an unpinned schema can still be deleted, its versions go with it
        cur.execute("DELETE FROM curation_schemas WHERE id = %s", (x.schema,))
        cur.execute(
            "DELETE FROM genes WHERE id IN (%s, %s)", tuple(str(g) for g in x.genes)
        )
        cur.execute(
            "DELETE FROM users WHERE id IN (%s, %s)", (str(x.admin), str(x.alice))
        )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _h(uid: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(uid)})}"}


def test_publish_leaves_old_curations_on_their_version(
    client: TestClient, w: W
) -> None:
    def create(gene: UUID) -> dict[str, object]:
        r = client.post(
            "/api/v1/curations/",
            json={
                "gene_id": str(gene),
                "scope_id": str(w.scope),
                "workflow_pair_id": w.pair,
                "evidence_data": {},
            },
            headers=_h(w.alice),
        )
        assert r.status_code == 201, r.text
        body: dict[str, object] = r.json()
        return body

    old = create(w.genes[0])
    assert old["methodology_version_id"] == w.v1

    r = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert r.status_code == 201, r.text
    v2 = r.json()
    assert v2["version"] == 2

    got = client.get(f"/api/v1/curations/{old['id']}", headers=_h(w.alice))
    assert got.status_code == 200, got.text
    assert got.json()["methodology_version_id"] == w.v1
    assert create(w.genes[1])["methodology_version_id"] == v2["id"]

    listed = client.get(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert [v["version"] for v in listed.json()] == [2, 1]
    assert (
        client.post(
            f"/api/v1/schemas/curation-schemas/{w.schema}/versions",
            headers=_h(w.alice),
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# (d) the migration backfills legacy rows and is idempotent
# ---------------------------------------------------------------------------


def _downgrade(s: Session) -> None:
    for table in ("curations", "precurations"):
        for trigger in ("pin_methodology_version", "methodology_version_pinned"):
            s.execute(text(f"DROP TRIGGER trigger_{trigger} ON {table}"))
        s.execute(text(f"ALTER TABLE {table} DROP COLUMN methodology_version_id"))
    s.execute(
        text(
            "DROP TRIGGER trigger_publish_initial_methodology_version ON curation_schemas"
        )
    )
    s.execute(text("DROP TABLE methodology_versions"))
    s.execute(
        text(
            "DELETE FROM schema_migrations WHERE filename = '042_methodology_versions.sql'"
        )
    )


def test_migration_backfills_legacy_rows_and_reruns_cleanly(
    owner_session: Session,
) -> None:
    s = owner_session
    _downgrade(s)
    pair, pre_schema, scope = s.execute(
        text(
            "SELECT id, precuration_schema_id, (SELECT id FROM scopes LIMIT 1) "
            "FROM workflow_pairs WHERE is_active LIMIT 1"
        )
    ).one()
    gene = s.scalar(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, record_hash) "
            "VALUES ('HGNC:998042', 'LEG042', repeat('5', 64)) RETURNING id"
        )
    )
    s.execute(
        text(
            "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id) "
            "VALUES (:g, :sc, :ps)"
        ),
        {"g": gene, "sc": scope, "ps": pre_schema},
    )
    s.execute(
        text(
            "INSERT INTO curations (gene_id, scope_id, workflow_pair_id, evidence_data) "
            "VALUES (:g, :sc, :p, '{}')"
        ),
        {"g": gene, "sc": scope, "p": pair},
    )

    def state() -> tuple[object, ...]:
        return tuple(
            s.execute(
                text(
                    "SELECT (SELECT count(*) FROM curation_schemas), "
                    "(SELECT count(*) FROM methodology_versions WHERE version = 1), "
                    "(SELECT count(*) FROM methodology_versions), "
                    "(SELECT count(*) FROM precurations p JOIN methodology_versions mv "
                    " ON mv.id = p.methodology_version_id "
                    " AND mv.schema_id = p.precuration_schema_id AND mv.version = 1), "
                    "(SELECT count(*) FROM precurations), "
                    "(SELECT count(*) FROM curations c "
                    " JOIN workflow_pairs wp ON wp.id = c.workflow_pair_id "
                    " JOIN methodology_versions mv ON mv.id = c.methodology_version_id "
                    " AND mv.schema_id = wp.curation_schema_id AND mv.version = 1), "
                    "(SELECT count(*) FROM curations), "
                    "(SELECT count(*) FROM schema_migrations "
                    " WHERE filename = '042_methodology_versions.sql')"
                )
            ).one()
        )

    untouched = (
        "SELECT (SELECT array_agg(lock_version ORDER BY id) FROM curations), "
        "(SELECT array_agg(lock_version ORDER BY id) FROM precurations), "
        "(SELECT count(*) FROM audit_log)"
    )
    before = s.execute(text(untouched)).one()
    s.execute(text(MIGRATION.read_text()))
    # the backfill fires no user triggers: no lock_version bump, no audit row
    assert s.execute(text(untouched)).one() == before
    first = state()
    schemas, v1s, versions, pre_pinned, pres, cur_pinned, curs, recorded = first
    assert schemas == v1s == versions  # one published v1 per schema
    assert (pre_pinned, cur_pinned, recorded) == (pres, curs, 1)  # every row pinned
    s.execute(text(MIGRATION.read_text()))
    assert state() == first
