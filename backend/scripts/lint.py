#!/usr/bin/env python3
"""
Comprehensive linting script for Gene Curator backend.

This script runs all linting tools in the correct order and provides
a unified interface for code quality checks.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print(f"✅ {description} passed")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stdout.strip():
                print(f"   stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"   stderr: {result.stderr.strip()}")
            return False

    except FileNotFoundError:
        print(f"❌ {description} failed - command not found: {' '.join(cmd)}")
        return False


def main() -> int:
    """Run all linting checks."""
    print("🚀 Starting Gene Curator Backend Linting Suite")
    print("=" * 60)

    checks = [
        (["uv", "tree"], "uv dependency tree check"),
        (["uv", "run", "ruff", "check", "app/"], "Ruff linting"),
        (["uv", "run", "ruff", "format", "--check", "app/"], "Ruff formatting check"),
        (["uv", "run", "mypy", "app/"], "MyPy type checking"),
        (["uv", "run", "bandit", "-c", ".bandit", "-r", "app/"], "Bandit security check"),
    ]

    failed_checks = []

    for cmd, description in checks:
        if not run_command(cmd, description):
            failed_checks.append(description)

    print("\n" + "=" * 60)

    if failed_checks:
        print(f"❌ {len(failed_checks)} check(s) failed:")
        for check in failed_checks:
            print(f"   - {check}")
        print("\n💡 Run individual tools to see detailed error messages:")
        print("   - uv tree")
        print("   - uv run ruff check app/ tests/")
        print("   - uv run ruff format --diff app/ tests/")
        print("   - uv run mypy app/")
        print("   - uv run bandit -c .bandit -r app/")
        return 1
    else:
        print("✅ All linting checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
