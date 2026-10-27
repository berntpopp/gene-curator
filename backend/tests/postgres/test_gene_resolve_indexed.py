"""#379: the local gene lookup filters in SQL on indexed expressions instead of scanning genes.

Same matches as before (case-insensitive symbol, previous symbol, alias, HGNC ID), on Postgres
as app_user; the indexes from migration 052 back every branch of the filter.
"""

import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.services.gene_resolver import _local_genes

pytestmark = pytest.mark.postgres

INDEXES = {
    "idx_genes_upper_symbol",
    "idx_genes_upper_hgnc_id",
    "idx_genes_upper_previous_symbols",
    "idx_genes_upper_alias_symbols",
}


def _owner() -> psycopg2.extensions.connection:
    return psycopg2.connect(os.environ["OWNER_DATABASE_URL"])


@pytest.fixture
def genes() -> Generator[dict[str, str], None, None]:
    tag = uuid4().hex[:6].upper()
    rows = {
        "sym": (f"SYM{tag}", [], []),
        "prev": (f"NEW{tag}", [f"Old{tag}"], []),
        "alias": (f"ALI{tag}", [], [f"Nick{tag}"]),
        "other": (f"OTH{tag}", [f"x{tag}"], [f"y{tag}"]),
    }
    ids: dict[str, str] = {}
    with _owner() as conn, conn.cursor() as cur:
        for key, (symbol, prev, alias) in rows.items():
            gid = uuid4()
            ids[key] = f"HGNC:{gid.int % 10**9}"
            cur.execute(
                "INSERT INTO genes (id, hgnc_id, approved_symbol, previous_symbols, "
                "alias_symbols, record_hash) VALUES (%s, %s, %s, %s, %s, %s)",
                (str(gid), ids[key], symbol, prev, alias, gid.hex * 2),
            )
    yield {"tag": tag, **ids}
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM genes WHERE hgnc_id = ANY(%s)",
            (list(ids.values()),),
        )


def test_lookup_matches_like_before_and_filters_in_sql(
    db: Session, genes: dict[str, str]
) -> None:
    tag = genes["tag"]
    statements: list[str] = []
    bind = db.get_bind()

    def capture(*args: object) -> None:
        statements.append(str(args[2]))

    event.listen(bind, "before_cursor_execute", capture)
    try:
        found = _local_genes(
            db,
            {f"sym{tag}", f"OLD{tag}", f"nick{tag}", genes["other"].lower(), "NOPE"},
        )
    finally:
        event.remove(bind, "before_cursor_execute", capture)
    assert {g.hgnc_id for g in found} == {
        genes["sym"],
        genes["prev"],
        genes["alias"],
        genes["other"],
    }
    assert any("upper_text_array" in s for s in statements)


def test_every_lookup_branch_has_an_index(db: Session) -> None:
    names = set(
        db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'genes'")
        ).scalars()
    )
    assert names >= INDEXES
    db.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db.execute(
            text(
                "EXPLAIN SELECT id FROM genes WHERE upper(approved_symbol) IN ('A') "
                "OR upper(hgnc_id) IN ('HGNC:1') "
                "OR upper_text_array(previous_symbols) && ARRAY['A'] "
                "OR upper_text_array(alias_symbols) && ARRAY['A']"
            )
        ).scalars()
    )
    for name in INDEXES:
        assert name in plan, plan


def test_migration_is_idempotent_and_self_recording() -> None:
    sql = (
        Path(__file__).parents[3] / "database/sql/052_gene_symbol_indexes.sql"
    ).read_text()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(sql)
        cur.execute(
            "SELECT count(*) FROM schema_migrations "
            "WHERE filename = '052_gene_symbol_indexes.sql'"
        )
        assert cur.fetchone()[0] == 1
