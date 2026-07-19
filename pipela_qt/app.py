"""앱 진입 — `python run_qt.py` 또는 `python main.py`(기본 Qt)."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    import main as m

    if argv is not None:
        sys.argv = [sys.argv[0]] + list(argv)
    m.pipela_cli_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
