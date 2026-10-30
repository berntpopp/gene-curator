"""scripts/backup.sh at its Docker boundary: verified dump, retention, no partial files."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Fake docker: `pg_dump` writes DUMP_BODY (or fails), `pg_restore --list` fails on "corrupt".
FAKE_DOCKER = """#!/bin/bash
case "$*" in
  *pg_dump*) printf '%s' "$DUMP_BODY"; [ "$DUMP_BODY" != fail ] ;;
  *pg_restore*--list*) [ "$(cat)" != corrupt ] ;;
  *) exit 2 ;;
esac
"""


class BackupScriptTests(unittest.TestCase):
    def run_backup(
        self, backups: Path, body: str, keep: str = "3"
    ) -> subprocess.CompletedProcess[str]:
        bin_dir = backups.parent / "bin"
        bin_dir.mkdir(exist_ok=True)
        docker = bin_dir / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(0o755)
        return subprocess.run(  # noqa: S603 - fixed script path
            [str(ROOT / "scripts" / "backup.sh"), str(backups)],
            env={
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "DUMP_BODY": body,
                "BACKUP_KEEP": keep,
                "POSTGRES_USER": "u",
                "POSTGRES_DB": "d",
            },
            check=False,
            capture_output=True,
            text=True,
        )

    def test_verified_dump_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backups = Path(directory) / "backups"
            result = self.run_backup(backups, "PGDMP ok")
            self.assertEqual(result.returncode, 0, result.stderr)
            files = list(backups.iterdir())
            self.assertEqual(len(files), 1)
            self.assertRegex(files[0].name, r"^backup_\d{8}_\d{6}\.dump$")
            self.assertEqual(files[0].read_text(), "PGDMP ok")

    def test_failed_dump_leaves_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backups = Path(directory) / "backups"
            result = self.run_backup(backups, "fail")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(backups.iterdir()), [])

    def test_unreadable_dump_leaves_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backups = Path(directory) / "backups"
            result = self.run_backup(backups, "corrupt")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(backups.iterdir()), [])

    def test_retention_keeps_newest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backups = Path(directory) / "backups"
            backups.mkdir()
            for i in range(4):
                old = backups / f"backup_2020010{i + 1}_000000.dump"
                old.write_text("old")
                os.utime(old, (1_000_000 + i, 1_000_000 + i))
            unrelated = backups / "keep-me.txt"
            unrelated.write_text("x")
            result = self.run_backup(backups, "PGDMP new", keep="2")
            self.assertEqual(result.returncode, 0, result.stderr)
            names = sorted(p.name for p in backups.glob("backup_*.dump"))
            self.assertEqual(len(names), 2)
            self.assertIn("backup_20200104_000000.dump", names)
            self.assertTrue(unrelated.exists())

    def test_rejects_bad_retention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backups = Path(directory) / "backups"
            result = self.run_backup(backups, "PGDMP", keep="0")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(backups.exists())
