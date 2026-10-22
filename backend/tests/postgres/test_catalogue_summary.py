"""Catalogue diseases and summary scores on the production role (#431).

First curations carry no disease of their own: the catalogue filter and options resolve it
from the linked precuration like the detail page. 048's view reads the stored score keys.
"""

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2.extras import Json
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import database
from app.core.security import create_access_token, get_password_hash
from app.main import app

pytestmark = pytest.mark.postgres
URL = "/api/v1/gene-catalogue/"
MIGRATION = Path(__file__).parents[3] / "database/sql/048_catalogue_summary.sql"
SCORES = {
    "genetic_evidence_total": 8.5,
    "experimental_evidence_total": 2,
    "total_score": 10.5,
}


@dataclass
class W:
    member: UUID = field(default_factory=uuid4)
    outsider: UUID = field(default_factory=uuid4)
    pub: UUID = field(default_factory=uuid4)
    priv: UUID = field(default_factory=uuid4)
    pair: UUID = field(default_factory=uuid4)
    genes: dict[UUID, UUID] = field(default_factory=dict)  # scope -> gene
    curations: dict[UUID, UUID] = field(default_factory=dict)  # scope -> curation

    @property
    def shown(self) -> str:
        return f"Shown syndrome {str(self.pub)[:8]}"

    @property
    def hidden(self) -> str:
        return f"Hidden syndrome {str(self.pub)[:8]}"


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


def _first_curation(cur, w: W, scope: UUID, precuration_evidence: dict) -> None:  # type: ignore[no-untyped-def,type-arg]
    """Active curation with empty evidence, linked to a precuration holding the disease."""
    gene, pre, cid = uuid4(), uuid4(), uuid4()
    cur.execute(
        "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) "
        "VALUES (%s, %s, %s, %s)",
        (
            str(gene),
            f"HGNC:{gene.int % 10**9}",
            f"CS{str(gene)[:6]}",
            str(gene).replace("-", "") * 2,
        ),
    )
    cur.execute(
        "INSERT INTO precurations (id, gene_id, scope_id, precuration_schema_id, "
        "evidence_data) SELECT %s, %s, %s, precuration_schema_id, %s "
        "FROM workflow_pairs WHERE id = %s",
        (str(pre), str(gene), str(scope), Json(precuration_evidence), str(w.pair)),
    )
    cur.execute(
        "INSERT INTO curations (id, gene_id, scope_id, precuration_id, workflow_pair_id, "
        "status, workflow_stage, computed_verdict, computed_scores) "
        "VALUES (%s, %s, %s, %s, %s, 'active', 'active', 'Moderate', %s)",
        (str(cid), str(gene), str(scope), str(pre), str(w.pair), Json(SCORES)),
    )
    cur.execute(
        "INSERT INTO active_curations (gene_id, scope_id, curation_id) "
        "VALUES (%s, %s, %s)",
        (str(gene), str(scope), str(cid)),
    )
    w.genes[scope], w.curations[scope] = gene, cid


@pytest.fixture
def w() -> Generator[W, None, None]:
    x = W()
    tag = str(x.pub)[:8]
    with _owner() as conn, conn.cursor() as cur:
        for uid, name in ((x.member, "cmem"), (x.outsider, "cout")):
            cur.execute(
                "INSERT INTO users (id, email, hashed_password, name, role) "
                "VALUES (%s, %s, %s, %s, 'user')",
                (str(uid), f"{name}-{tag}@summary.org", get_password_hash("pw"), name),
            )
        for sid, public in ((x.pub, True), (x.priv, False)):
            cur.execute(
                "INSERT INTO scopes (id, name, display_name, is_public, created_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(sid), f"cs-{sid}", f"CS {sid}", public, str(x.member)),
            )
        cur.execute(
            "INSERT INTO scope_memberships (scope_id, user_id, role, invited_by, "
            "accepted_at) VALUES (%s, %s, 'viewer', %s, now())",
            (str(x.priv), str(x.member), str(x.member)),
        )
        cur.execute(
            "INSERT INTO workflow_pairs (id, name, version, precuration_schema_id, "
            "curation_schema_id) SELECT %s, %s, '1', precuration_schema_id, "
            "curation_schema_id FROM workflow_pairs WHERE is_active LIMIT 1",
            (str(x.pair), f"cs-{x.pair}"),
        )
        _first_curation(cur, x, x.pub, {"disease_name": x.shown})
        _first_curation(
            cur, x, x.priv, {"entity_definition": {"disease_name": x.hidden}}
        )
    yield x
    with _owner() as conn, conn.cursor() as cur:
        users = [str(x.member), str(x.outsider)]
        cur.execute(
            "DELETE FROM scopes WHERE id IN (%s, %s)", (str(x.pub), str(x.priv))
        )
        cur.execute("DELETE FROM audit_log WHERE workflow_pair_id = %s", (str(x.pair),))
        cur.execute("DELETE FROM workflow_pairs WHERE id = %s", (str(x.pair),))
        cur.execute(
            "DELETE FROM genes WHERE id = ANY(%s::uuid[])",
            ([str(g) for g in x.genes.values()],),
        )
        cur.execute("DELETE FROM audit_log WHERE user_id = ANY(%s::uuid[])", (users,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (users,))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def _get(client: TestClient, user: UUID | None, path: str, **params: str) -> object:
    headers = {}
    if user:
        headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user)})}"}
    r = client.get(URL + path, params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _found(client: TestClient, user: UUID | None, disease: str) -> list[list[str]]:
    body = _get(client, user, "", disease=disease.lower())
    assert isinstance(body, dict)
    assert body["total"] == len(body["entries"])
    return [entry["diseases"] for entry in body["entries"]]


@pytest.mark.parametrize("who", ["anonymous", "outsider", "member"])
def test_disease_filter_finds_first_curations_only_where_visible(
    client: TestClient, w: W, who: str
) -> None:
    user = {"anonymous": None, "outsider": w.outsider, "member": w.member}[who]
    visible = [w.shown, w.hidden] if who == "member" else [w.shown]

    assert _found(client, user, w.shown) == [[w.shown]]
    assert _found(client, user, w.hidden) == ([[w.hidden]] if who == "member" else [])
    options = _get(client, user, "filters/diseases", limit="200")
    assert isinstance(options, list)
    assert [name for name in options if name in (w.shown, w.hidden)] == sorted(visible)


def test_summary_view_returns_stored_scores_to_members_only(db: Session, w: W) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(MIGRATION.read_text())  # a re-run changes nothing
        cur.execute(
            "SELECT reloptions FROM pg_class WHERE relname = 'active_curations_summary'"
        )
        assert cur.fetchone() == (["security_invoker=true"],)
        cur.execute(
            "SELECT 1 FROM schema_migrations WHERE filename = '048_catalogue_summary.sql'"
        )
        assert cur.fetchone() == (1,)

    def scores(user: UUID) -> dict[str, tuple[Decimal, ...]]:
        db.execute(
            text("SELECT set_config('app.current_user_id', :u, true)"),
            {"u": str(user)},
        )
        rows = db.execute(
            text(
                "SELECT curation_id, genetic_score, experimental_score, total_score "
                "FROM active_curations_summary WHERE curation_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": [str(c) for c in w.curations.values()]},
        ).all()
        return {str(row[0]): tuple(row[1:]) for row in rows}

    stored = (Decimal("8.5"), Decimal("2"), Decimal("10.5"))
    pub, priv = (str(w.curations[s]) for s in (w.pub, w.priv))
    assert scores(w.member) == {pub: stored, priv: stored}
    assert scores(w.outsider) == {pub: stored}
