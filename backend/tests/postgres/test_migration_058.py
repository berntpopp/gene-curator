"""058 / #478: the gene_summaries cache, its stale trigger and function are gone, and the
migration re-runs cleanly (idempotent)."""

import os
from pathlib import Path

import psycopg2
import pytest

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/058_drop_gene_summaries.sql"


def test_gene_summaries_cache_is_dropped_and_058_is_idempotent() -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(MIGRATION.read_text())  # second run on a fresh DB: no error
        cur.execute("SELECT to_regclass('public.gene_summaries')")
        assert cur.fetchone() == (None,)
        cur.execute(
            "SELECT count(*) FROM pg_proc WHERE proname = 'mark_gene_summary_stale'"
        )
        assert cur.fetchone() == (0,)
        cur.execute(
            "SELECT count(*) FROM pg_trigger "
            "WHERE tgname = 'trigger_curation_update_mark_stale'"
        )
        assert cur.fetchone() == (0,)
        cur.execute(
            "SELECT 1 FROM schema_migrations WHERE filename = '058_drop_gene_summaries.sql'"
        )
        assert cur.fetchone() == (1,)
