#!/usr/bin/env python3
"""Generate docs/cpp_migration/parity_matrix.md from repo layout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_MAP = {
    "config_parse.py": "cpp/src/core/registry/parse.cpp",
    "config_registry_load.py": "cpp/src/core/registry/store.cpp",
    "config_registry_save.py": "cpp/src/core/registry/store.cpp",
    "config_registry_tables.py": "registry/schema.json",
    "registry_config_snapshot.py": "cpp/src/core/registry/snapshot.cpp",
    "app_state.py": "cpp/src/core/state/app_state.cpp",
    "input_keymap.py": "cpp/src/core/input/keymap.cpp",
    "template_matching.py": "cpp/src/core/vision/template_match.cpp",
    "vision_capture.py": "cpp/src/core/vision/capture.cpp",
    "scale_geometry.py": "cpp/src/core/vision/roi.cpp",
    "reload_sequence.py": "cpp/src/core/reload/sequence.cpp",
    "win32_game_windows.py": "cpp/src/core/win32/game_windows.cpp",
    "kill_counter_tier_data.py": "cpp/src/core/kill_counter/tier_data.cpp",
    "version_info.py": "cpp/src/core/version.cpp",
    "paths.py": "cpp/src/core/paths.cpp",
    "image_registry.py": "cpp/src/core/vision/registry_image_loader.cpp",
}

# AGENT: registry_constants absorbed into store/snapshot; win32_window_ops split across win32/*.cpp
CORE_ABSORBED = {
    "registry_constants.py": "registry/store.cpp + registry/snapshot.cpp",
    "win32_window_ops.py": "cpp/src/core/win32/{clip_cursor,game_windows,input_synth}.cpp",
    "win32_client_capture.py": "cpp/src/core/vision/capture.cpp",
}

UI_MAP = {
    "shell.py": "cpp/src/app/shell/application.cpp",
    "control_main.py": "cpp/src/app/control/control_main_window.cpp",
    "theme.py": "cpp/src/app/theme/theme_tokens.cpp",
    "ui_adaptive.py": "cpp/src/app/theme/ui_adaptive.cpp",
    "game_title_bar_overlay.py": "cpp/src/app/overlays/title_strip_window.cpp",
    "kill_counter_window.py": "cpp/src/app/overlays/kill_counter_window.cpp",
    "overlay.py": "cpp/src/app/overlays/game_overlay_window.cpp",
    "dock_ui_phase.py": "cpp/src/app/dock/dock_ui_phase.cpp",
    "qt_dock_z_stack.py": "cpp/src/app/dock/dock_z_stack.cpp",
    "qt_side_dock.py": "cpp/src/app/dock/side_dock_layout.cpp",
    "terminal_log_list_widget.py": "cpp/src/app/widgets/terminal_log_widget.cpp",
    "splash_screen.py": "cpp/src/app/shell/splash_screen.cpp",
    "cursor_hud.py": "cpp/src/native/platform/dcomp_wrapper.cpp",
    "dcomp_hud.py": "cpp/src/native/hud_dcomp/cursor_hud_dcomp.cpp",
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


def _absorbed_table() -> list[str]:
    lines = [
        "### pipela_core (absorbed / split)",
        "",
        "| Python | C++ target | Status |",
        "| --- | --- | --- |",
    ]
    for py_name, cpp in sorted(CORE_ABSORBED.items()):
        rel = f"pipela_core/{py_name}"
        lines.append(f"| `{rel}` | `{cpp}` | absorbed |")
    lines.append("")
    return lines


def main() -> int:
    out = ROOT / "docs" / "cpp_migration" / "parity_matrix.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    body: list[str] = [
        "# Pipela C++ parity matrix",
        "",
        "> **Worker/runtime progress:** see [`STATUS.md`](STATUS.md) (manual, authoritative for loops).",
        "",
        "Auto-generated mapping Python modules to C++ targets. Regenerate:",
        "",
        "```powershell",
        "python tools/codegen/export_parity_matrix.py",
        "```",
        "",
    ]
    body.extend(_table("pipela_core", CORE_MAP, "pipela_core"))
    body.extend(_absorbed_table())
    body.extend(_table("pipela_qt (selected)", UI_MAP, "pipela_qt"))
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
