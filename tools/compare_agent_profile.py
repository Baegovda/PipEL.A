"""Compare two cProfile text summaries (Unified diff). Each path may be ``summary.txt`` or a directory containing it.

Examples:

  python tools/compare_agent_profile.py path/before/summary.txt path/after/summary.txt

  python tools/compare_agent_profile.py profiling/_old/agent_profile profiling/agent_profile

# AGENT: ignores binary .stats; stderr on missing files.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path


def _resolve_summary(p: Path) -> Path:
    if p.is_file():
        return p
    if p.is_dir():
        c = p / "summary.txt"
        if c.is_file():
            return c
    raise FileNotFoundError(f"no summary.txt for {p}")


def main() -> int:
    p = argparse.ArgumentParser(description="Diff two profiling agent_profile summary.txt files")
    p.add_argument("before", type=Path, help="summary.txt or agent_profile/ folder (before)")
    p.add_argument("after", type=Path, help="summary.txt or agent_profile/ folder (after)")
    args = p.parse_args()
    try:
        ta = _resolve_summary(args.before)
        tb = _resolve_summary(args.after)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        la = ta.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        lb = tb.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as e:
        print(e, file=sys.stderr)
        return 2
    title_a = str(ta.resolve())
    title_b = str(tb.resolve())
    for line in difflib.unified_diff(la, lb, fromfile=title_a, tofile=title_b, n=8):
        sys.stdout.write(line)
    print("", flush=True)
    print("# compared:", title_a, flush=True)
    print("#       to:", title_b, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
