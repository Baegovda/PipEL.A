#!/usr/bin/env python3
"""Generate docs/cpp_migration/parity_matrix.md from repo layout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_MAP = {
    "config_parse.py": "cpp/src/core/registry/parse.cpp",
    "registry_constants.py": "cpp/src/core/registry/constants.hpp",
    "config_registry_load.py": "cpp/src/core/registry/store.cpp",
    "config_registry_save.py": "cpp/src/core/registry/store.cpp",
    "config_registry_tables.py": "registry/schema.json",
    "app_state.py": "cpp/src/core/state/app_state.cpp",
    "template_matching.py": "cpp/src/core/vision/template_match.cpp",
    "vision_capture.py": "cpp/src/core/vision/capture.cpp",
    "win32_game_windows.py": "cpp/src/core/win32/game_windows.cpp",
    "win32_window_ops.py": "cpp/src/core/win32/window_ops.cpp",
    "kill_counter_tier_data.py": "cpp/src/core/kill_counter/tier_data.cpp",
    "version_info.py": "cpp/src/core/version.cpp",
    "paths.py": "cpp/src/core/paths.cpp",
}

UI_MAP = {
    "shell.py": "cpp/src/ui/shell/application.cpp",
    "control_main.py": "cpp/src/ui/control/main_window.cpp",
    "theme.py": "cpp/src/ui/theme/theme.cpp",
    "game_title_bar_overlay.py": "cpp/src/ui/strip/title_bar_strip.cpp",
    "kill_counter_window.py": "cpp/src/ui/kill_counter/floater_window.cpp",
    "dev_ui_mode.py": "cpp/src/ui/dev_ui_mode.cpp",
}


def _table(title: str, mapping: dict[str, str], glob_dir: str) -> list[str]:
    lines = [f"### {title}", "", "| Python | C++ target | Status |", "| --- | --- | --- |"]
    py_dir = ROOT / glob_dir
    for py_path in sorted(py_dir.glob("*.py")):
        if py_path.name.startswith("_"):
            continue
        rel = f"{glob_dir}/{py_path.name}".replace("\\", "/")
        cpp = mapping.get(py_path.name, "cpp/ (planned)")
        status = "mapped" if py_path.name in mapping else "planned"
        lines.append(f"| `{rel}` | `{cpp}` | {status} |")
    lines.append("")
    return lines


def main() -> int:
    out = ROOT / "docs" / "cpp_migration" / "parity_matrix.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    body: list[str] = [
        "# Pipela C++ parity matrix",
        "",
        "Auto-generated mapping Python modules to C++ targets. Regenerate:",
        "",
        "```powershell",
        "python tools/export_parity_matrix.py",
        "```",
        "",
    ]
    body.extend(_table("pipela_core", CORE_MAP, "pipela_core"))
    body.extend(_table("pipela_qt (selected)", UI_MAP, "pipela_qt"))
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
