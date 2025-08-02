#!/usr/bin/env python3
"""
Auto-formatting script for Gene Curator backend.

This script applies automatic code formatting using ruff and other tools.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd, cwd=Path(__file__).parent.parent, text=True, check=False
        )

        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")
            return False

    except FileNotFoundError:
        print(f"❌ {description} failed - command not found: {' '.join(cmd)}")
        return False


def main() -> int:
    """Run all formatting tools."""
    print("🎨 Starting Gene Curator Backend Auto-Formatting")
    print("=" * 60)

    formatters = [
        (["uv", "run", "ruff", "check", "--fix", "app/"], "Ruff auto-fixes"),
        (["uv", "run", "ruff", "format", "app/"], "Ruff formatting"),
    ]

    failed_formatters = []

    for cmd, description in formatters:
        if not run_command(cmd, description):
            failed_formatters.append(description)

    print("\n" + "=" * 60)

    if failed_formatters:
        print(f"❌ {len(failed_formatters)} formatter(s) failed:")
        for formatter in failed_formatters:
            print(f"   - {formatter}")
        return 1
    else:
        print("✅ All formatting completed!")
        print("\n💡 Next steps:")
        print("   - Run 'python scripts/lint.py' to verify formatting")
        print("   - Review changes with 'git diff'")
        print("   - Commit formatted code")
        return 0


if __name__ == "__main__":
    sys.exit(main())
