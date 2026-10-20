#!/usr/bin/env python3
"""Fail when a tracked source file exceeds MAX_LINES (AGENTS.md: keep files small).

Files that were already larger are listed in file-size-allowlist.txt with their
current size: they may shrink but never grow. Run with --update after shrinking
a file to lower (or drop) its allowance.
"""

import subprocess
import sys
from pathlib import Path

MAX_LINES = 650
ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "scripts" / "file-size-allowlist.txt"
SUFFIXES = {".py", ".js", ".ts", ".vue", ".mjs", ".cjs"}
# Generated code is exempt; SQL migrations are immutable history.
EXEMPT = {"frontend/src/types/api.generated.ts"}


def tracked_sizes() -> dict[str, int]:
    files = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    sizes = {}
    for f in files:
        path = ROOT / f
        if f and path.suffix in SUFFIXES and f not in EXEMPT and path.is_file():
            sizes[f] = len(path.read_text(encoding="utf-8").splitlines())
    return sizes


def load_allowlist() -> dict[str, int]:
    if not ALLOWLIST.exists():
        return {}
    entries = {}
    for line in ALLOWLIST.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            size, path = line.split(maxsplit=1)
            entries[path] = int(size)
    return entries


def violations(sizes: dict[str, int], allow: dict[str, int]) -> list[str]:
    out = []
    for f, n in sorted(sizes.items()):
        limit = max(MAX_LINES, allow.get(f, 0))
        if n > limit:
            hint = f"allowlisted at {allow[f]}, may only shrink" if f in allow else f"max {MAX_LINES}"
            out.append(f"{f}: {n} lines ({hint}) - split it")
    return out


def write_allowlist(sizes: dict[str, int], allow: dict[str, int]) -> None:
    # Only shrink: keep files still over the limit, at min(current, previous allowance).
    kept = {f: min(n, allow.get(f, n)) for f, n in sizes.items() if n > MAX_LINES}
    lines = [f"# Files over {MAX_LINES} lines: allowance may only go down (scripts/check_file_size.py)"]
    lines += [f"{n} {f}" for f, n in sorted(kept.items())]
    ALLOWLIST.write_text("\n".join(lines) + "\n")


def main() -> int:
    sizes, allow = tracked_sizes(), load_allowlist()
    if "--update" in sys.argv:
        write_allowlist(sizes, allow)
        return 0
    errors = violations(sizes, allow)
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    assert violations({"a.py": 651}, {}) and not violations({"a.py": 700}, {"a.py": 700})
    assert violations({"a.py": 701}, {"a.py": 700}) and not violations({"a.py": 650}, {})
    sys.exit(main())
