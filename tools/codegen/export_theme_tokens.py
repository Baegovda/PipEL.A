#!/usr/bin/env python3
"""Export pipela_qt/theme.py color tokens to cpp/resources/theme/pipela_theme.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipela_qt import theme  # noqa: E402

OUT = ROOT / "cpp" / "resources" / "theme" / "pipela_theme.json"

TOKEN_NAMES = [
    "STRIP_BG",
    "STRIP_ACCENT",
    "STRIP_FG",
    "STRIP_FG_MUTED",
    "PANEL_BG",
    "CARD_BG",
    "ACCENT",
    "TERMINAL_BG",
    "TERMINAL_FG",
    "WINDOW_BG",
]


def main() -> int:
    payload = {name: getattr(theme, name) for name in TOKEN_NAMES if hasattr(theme, name)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(payload)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
