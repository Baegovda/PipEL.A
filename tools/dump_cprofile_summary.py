"""Write plaintext summaries from cProfile .stats via stdlib `pstats` (no deps).

Default output: profiling/agent_profile/summary.txt (single handoff folder).
"""
from __future__ import annotations

import argparse
import io
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def default_summary_out_path(stats_file: Path) -> Path:
    """If .stats already live in profiling/agent_profile/, write summary beside them (not agent_profile/agent_profile/)."""
    p = stats_file.resolve().parent
    if p.name == "agent_profile":
        return p / "summary.txt"
    return p / "agent_profile" / "summary.txt"


def default_dump_error_path(stats_file: Path) -> Path:
    p = stats_file.resolve().parent
    if p.name == "agent_profile":
        return p / "cprofile_dump_error.txt"
    return p / "agent_profile" / "cprofile_dump_error.txt"


def _write_summary(stats_path: Path, out_path: Path, top: int) -> None:
    import pstats

    chunks: list[str] = []
    chunks.append(f"cProfile text summary — UTC {datetime.now(timezone.utc).isoformat()}")
    chunks.append(f"stats_file: {stats_path.resolve().as_posix()}")
    chunks.append("")
    for label, sort_key in (
        ("cumulative", "cumulative"),
        ("tottime", "tottime"),
    ):
        s = pstats.Stats(str(stats_path))
        s.sort_stats(sort_key)
        buf = io.StringIO()
        s.stream = buf
        s.print_stats(top)
        chunks.append(f"=== sorted by {label} (top ~{top} entries) ===")
        chunks.append(buf.getvalue().rstrip())
        chunks.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(chunks).rstrip() + "\n"
    out_path.write_text(text, encoding="utf-8", errors="strict")


def main() -> int:
    p = argparse.ArgumentParser(description="Dump pstats text summary from cProfile .stats")
    p.add_argument("stats_file", type=Path, help="Path to pipela_cprofile_*.stats")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: agent_profile/summary.txt next to .stats, or profiling/agent_profile/summary.txt)",
    )
    p.add_argument("--top", type=int, default=60, help="Max rows per sort block (default 60)")
    args = p.parse_args()
    stats_file = args.stats_file
    if not stats_file.is_file():
        print(f"[dump_cprofile_summary] not a file: {stats_file}", file=sys.stderr)
        return 2
    out_path = args.out if args.out is not None else default_summary_out_path(stats_file)
    try:
        _write_summary(stats_file, out_path, max(10, args.top))
    except Exception:  # noqa: BLE001
        err_path = default_dump_error_path(stats_file)
        err_path.parent.mkdir(parents=True, exist_ok=True)
        err_path.write_text(traceback.format_exc(), encoding="utf-8", errors="replace")
        print(f"[dump_cprofile_summary] failed — {err_path}", file=sys.stderr)
        return 1
    print(f"wrote {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
