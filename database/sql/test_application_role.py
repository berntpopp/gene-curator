"""Migration 031 (#156); run via `make test-postgres` (OWNER_DATABASE_URL = throwaway owner DB)."""

import os
import shutil
import subprocess
from pathlib import Path

import psycopg2
import pytest

MIGRATION = Path(__file__).resolve().parent / "031_application_role.sql"
pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("password", [None, ""])
def test_031_refuses_to_run_without_app_password(password: str | None) -> None:
    env = {k: v for k, v in os.environ.items() if k != "APP_DB_PASSWORD"}
    if password is not None:
        env["APP_DB_PASSWORD"] = password
    psql = shutil.which("psql")
    assert psql is not None
    result = subprocess.run(  # noqa: S603 - fixed arguments
        [
            psql,
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "--single-transaction",
            "-f",
            str(MIGRATION),
            os.environ["OWNER_DATABASE_URL"],
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "APP_DB_PASSWORD must be set" in result.stderr


def test_views_do_not_bypass_rls() -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'v' "
            "AND NOT coalesce('security_invoker=true' = ANY(c.reloptions), false)"
        )
        assert cur.fetchall() == []


def test_every_forced_rls_table_has_a_select_policy() -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT relname FROM pg_class c WHERE relrowsecurity AND NOT EXISTS ("
            "SELECT 1 FROM pg_policies p WHERE p.tablename = c.relname "
            "AND p.cmd IN ('SELECT', 'ALL'))"
        )
        assert cur.fetchall() == []
