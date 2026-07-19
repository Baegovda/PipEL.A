"""앱 진입 — `python main.py` (Qt)."""

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
