# Python → C++ canonical file map

`AUDIENCE`: agents porting UI/core. Use **C++ canonical name** in new code; legacy Python name is reference only until Phase 6 deletion.

## Entry

| Legacy (delete Phase 6) | Canonical C++ |
|-------------------------|-----------------|
| `main.py` `main_qt()` | `cpp/src/app/main.cpp` → `runQtApplication()` |
| `pipela_qt/shell.py` | `cpp/src/app/shell/application.cpp` |
| — | `cpp/src/app/shell/runtime_bootstrap.cpp` |

## Core (`pipela_core/` → `cpp/src/core/`)

| Python | C++ canonical |
|--------|----------------|
| `app_state.py` | `state/app_state.cpp` |
| `config_parse.py` | `registry/parse.cpp` |
| `config_registry_*.py` | `registry/store.cpp` + `registry/schema.json` |
| `registry_config_snapshot.py` | `registry/snapshot.cpp` |
| `image_registry.py` | `vision/registry_image_loader.cpp` |
| `vision_capture.py` | `vision/capture.cpp` |
| `scale_geometry.py` | `vision/roi.cpp` |
| `template_matching.py` | `vision/template_match.cpp` |
| `kill_counter_tier_data.py` | `kill_counter/tier_data.cpp` |
| `win32_game_windows.py` | `win32/game_windows.cpp` |
| `win32_window_ops.py` | `win32/clip_cursor.cpp` + `win32/input_synth.cpp` |
| `input_keymap.py` | `input/keymap.cpp` |
| `reload_sequence.py` | `reload/sequence.cpp` |
| `paths.py` | `paths.cpp` |
| `version_info.py` | `version.cpp` |
| `*_loop` in `main.py` | `workers/*_worker.cpp`, `workers/worker_loops.cpp` |

## App UI (`pipela_qt/` → `cpp/src/app/`)

| Python | C++ canonical | Notes |
|--------|---------------|-------|
| `control_main.py` | `control/control_main_window.cpp` | |
| `control_tab_chrome.py` | `control/control_main_window.cpp` | inline QSS |
| `terminal_log_list_widget.py` | `widgets/terminal_log_widget.cpp` | |
| `dock_ui_phase.py` | `dock/dock_ui_phase.cpp` | |
| `qt_dock_z_stack.py` | `dock/dock_z_stack.cpp` | |
| `qt_side_dock.py` | `dock/side_dock_layout.cpp` | moved from core |
| `game_title_bar_overlay.py` | `overlays/title_strip_window.cpp` | intentional rename |
| `overlay.py` | `overlays/game_overlay_window.cpp` | |
| `kill_counter_window.py` | `overlays/kill_counter_window.cpp` | was `kill_counter_floater_window` |
| `dock_chrome_restore.py` | `overlays/dock_chrome_controller.cpp` | |
| `splash_screen.py` | `shell/splash_screen.cpp` | |
| `theme.py` | `theme/theme_tokens.cpp` | |
| `ui_adaptive.py` | `theme/ui_adaptive.cpp` | |
| `cursor_hud.py` / `dcomp_hud.py` | `native/platform/dcomp_wrapper.cpp` + `native/hud_dcomp/` | |
| `win32_mouse_hook.py` | `input/hooks_bridge.cpp` + `native/input_hooks/` | |
| `panels/ride_settings.py` | `panels/settings/ride_panel.cpp` | |
| `panels/reload_settings.py` | `panels/settings/reload_panel.cpp` | |
| *(17 more panels)* | `panels/settings/<name>_panel.cpp` | see `settings_panel_defs` |

## Native DLLs

| Artifact | Path |
|----------|------|
| `pipela_input_hooks.dll` | `cpp/src/native/input_hooks/` |
| `cursor_hud_dcomp.dll` | `cpp/src/native/hud_dcomp/` |

## Do not port (Python-only, delete Phase 6)

`profile_bootstrap.py`, `worker_runtime_bridge.py`, `state_native_proxy.py`, `native_bridge.py`, PyInstaller `build.bat` path.
