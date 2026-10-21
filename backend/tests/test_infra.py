"""Exercise the Makefile migration command at its Docker/psql boundary."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class MigrationCommandTests(unittest.TestCase):
    def run_migrate(
        self, *args: str
    ) -> tuple[subprocess.CompletedProcess[str], str, str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / "docker"
            docker.write_text(
                '#!/bin/bash\ncat >> "$CAPTURE_SQL"\n'
                'printf "%s\\n" "$@" >> "$CAPTURE_ARGS"\n'
            )
            docker.chmod(0o755)
            sql = root / "sql"
            argv = root / "args"
            result = subprocess.run(  # noqa: S603 - arguments are test cases
                ["/usr/bin/make", "db-migrate", *args],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PATH": f"{root}:{os.environ['PATH']}",
                    "CAPTURE_SQL": str(sql),
                    "CAPTURE_ARGS": str(argv),
                },
                check=False,
                capture_output=True,
                text=True,
            )
            return (
                result,
                sql.read_text() if sql.exists() else "",
                argv.read_text() if argv.exists() else "",
            )

    def test_no_file_applies_pending_migrations_atomically(self) -> None:
        result, sql, argv = self.run_migrate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--single-transaction", argv)
        self.assertIn("ON_ERROR_STOP=1", argv)
        self.assertIn("pg_advisory_xact_lock", sql)
        self.assertIn("SELECT NOT EXISTS", sql)
        self.assertIn("027_fix_reactivation_and_log_retention.sql", sql)
        self.assertIn("INSERT INTO schema_migrations", sql)
        # Historical files contain transaction wrappers; these must not commit
        # outside the runner's transaction before their ledger row is written.
        self.assertNotIn("\nCOMMIT;\n", sql)
        self.assertNotIn("\nBEGIN;\n", sql)

    def test_explicit_file_is_tracked(self) -> None:
        result, sql, argv = self.run_migrate(
            "FILE=database/sql/027_fix_reactivation_and_log_retention.sql"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--single-transaction", argv)
        self.assertIn("SELECT NOT EXISTS", sql)
        self.assertIn("027_fix_reactivation_and_log_retention.sql", sql)
        self.assertNotIn("CREATE TABLE scopes", sql)

    def test_invalid_file_fails_before_docker(self) -> None:
        result, sql, argv = self.run_migrate("FILE=missing.sql")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sql, "")
        self.assertEqual(argv, "")


class InfrastructureServicesTests(unittest.TestCase):
    def test_infrastructure_starts_only_postgres(self) -> None:
        result = subprocess.run(
            [
                "/usr/bin/docker",
                "compose",
                "--env-file",
                ".env.dev",
                "config",
                "--services",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.splitlines(), ["postgres"])
        result = subprocess.run(
            ["/usr/bin/make", "-n", "services-up"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.split()[-4:], ["up", "-d", "--wait", "postgres"])


if __name__ == "__main__":
    unittest.main()
