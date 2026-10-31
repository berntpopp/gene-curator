"""Real PostgreSQL checks; run with OWNER_DATABASE_URL pointing at a throwaway owner DB.

cd backend && uv run pytest ../database/sql/test_migrations.py -m postgres
"""

import os
import subprocess
from pathlib import Path

import psycopg2
import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.postgres


def test_runner_applies_once_and_rolls_back_failed_file(tmp_path: Path) -> None:
    # Forward Docker's stdin to a real psql connection, without touching dev DB.
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nexec psql -X -v ON_ERROR_STOP=1 --single-transaction "$MIGRATION_TEST_URL"\n'
    )
    docker.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "MIGRATION_TEST_URL": os.environ["OWNER_DATABASE_URL"],
    }
    # initdb only records the baseline; files between 027 and 030 are recorded by the first run.
    subprocess.run(["/usr/bin/make", "db-migrate"], cwd=ROOT, env=env, check=True)
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT filename, applied_at FROM schema_migrations ORDER BY filename"
        )
        before = cursor.fetchall()
    assert before
    for _ in range(2):
        subprocess.run(["/usr/bin/make", "db-migrate"], cwd=ROOT, env=env, check=True)
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT filename, applied_at FROM schema_migrations ORDER BY filename"
        )
        assert cursor.fetchall() == before
        assert {row[0] for row in before} == {
            file.name for file in (ROOT / "database/sql").glob("[0-9]*.sql")
        }

    # Use a copied command surface, so the real migration directory stays immutable.
    (tmp_path / "database/sql").mkdir(parents=True)
    (tmp_path / "Makefile").write_text((ROOT / "Makefile").read_text())
    (tmp_path / ".env.dev").write_text((ROOT / ".env.dev").read_text())
    runner = tmp_path / "database/migrate.sh"
    runner.write_text((ROOT / "database/migrate.sh").read_text())
    runner.chmod(0o755)
    (tmp_path / "database/sql/030_schema_migrations.sql").write_text(
        (ROOT / "database/sql/030_schema_migrations.sql").read_text()
    )
    (tmp_path / "database/sql/999_test_failure.sql").write_text(
        "BEGIN;\nCREATE TABLE migration_rollback_probe(id int);\nCOMMIT;\nSELECT 1/0;\n"
    )
    result = subprocess.run(
        ["/usr/bin/make", "db-migrate", "FILE=database/sql/999_test_failure.sql"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT to_regclass('migration_rollback_probe')")
        assert cursor.fetchone() == (None,)
        cursor.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename='999_test_failure.sql'"
        )
        assert cursor.fetchone() == (0,)
