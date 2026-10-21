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


@pytest.mark.parametrize("role", ["test_user", "rls_probe_role"])
def test_only_app_user_may_drop_log_partitions(role: str) -> None:
    with psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn:
        try:
            with conn.cursor() as cur:
                if role == "rls_probe_role":
                    cur.execute("CREATE ROLE rls_probe_role NOLOGIN")
                cur.execute(f"SET ROLE {role}")
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    cur.execute("SELECT cleanup_old_logs(90)")
        finally:
            conn.rollback()


def test_log_cleanup_rejects_retention_below_one_day() -> None:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user")
                assert cur.fetchone() == ("app_user",)
                with pytest.raises(psycopg2.errors.RaiseException, match="at least 1"):
                    cur.execute("SELECT cleanup_old_logs(0)")
        finally:
            conn.rollback()


def test_legacy_test_user_cannot_log_in() -> None:
    owner = psycopg2.extensions.parse_dsn(os.environ["OWNER_DATABASE_URL"])
    with pytest.raises(psycopg2.OperationalError, match="not permitted to log in"):
        psycopg2.connect(**{**owner, "user": "test_user", "password": "test_password"})
