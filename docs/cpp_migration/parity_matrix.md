# Pipela C++ parity matrix

> **Worker/runtime progress:** see [`STATUS.md`](STATUS.md) (manual, authoritative for loops).

Auto-generated mapping Python modules to C++ targets. Regenerate:

```powershell
python tools/export_parity_matrix.py
```

### pipela_core

| Python | C++ target | Status |
| --- | --- | --- |
| `pipela_core/ai_debug_session_log.py` | `cpp/ (planned)` | planned |
| `pipela_core/ammo_restock_catalog.py` | `cpp/ (planned)` | planned |
| `pipela_core/ammo_restock_templates.py` | `cpp/ (planned)` | planned |
| `pipela_core/app_state.py` | `cpp/src/core/state/app_state.cpp` | mapped |
| `pipela_core/call_merc_catalog.py` | `cpp/ (planned)` | planned |
| `pipela_core/call_merc_match.py` | `cpp/ (planned)` | planned |
| `pipela_core/call_merc_templates.py` | `cpp/ (planned)` | planned |
| `pipela_core/client_idle_teardown.py` | `cpp/ (planned)` | planned |
| `pipela_core/config_parse.py` | `cpp/src/core/registry/parse.cpp` | mapped |
| `pipela_core/config_registry_extended.py` | `cpp/ (planned)` | planned |
| `pipela_core/config_registry_kill_counter.py` | `cpp/ (planned)` | planned |
| `pipela_core/config_registry_load.py` | `cpp/src/core/registry/store.cpp` | mapped |
| `pipela_core/config_registry_query.py` | `cpp/ (planned)` | planned |
| `pipela_core/config_registry_save.py` | `cpp/src/core/registry/store.cpp` | mapped |
| `pipela_core/config_registry_tables.py` | `registry/schema.json` | mapped |
| `pipela_core/console_log_constants.py` | `cpp/ (planned)` | planned |
| `pipela_core/console_log_prefix.py` | `cpp/ (planned)` | planned |
| `pipela_core/display_timing.py` | `cpp/ (planned)` | planned |
| `pipela_core/flame_trigger_automation.py` | `cpp/ (planned)` | planned |
| `pipela_core/image_registry.py` | `cpp/ (planned)` | planned |
| `pipela_core/input_keymap.py` | `cpp/ (planned)` | planned |
| `pipela_core/kill_counter_layout.py` | `cpp/ (planned)` | planned |
| `pipela_core/kill_counter_tier_colors.py` | `cpp/ (planned)` | planned |
| `pipela_core/kill_counter_tier_data.py` | `cpp/src/core/kill_counter/tier_data.cpp` | mapped |
| `pipela_core/native_bridge.py` | `cpp/ (planned)` | planned |
| `pipela_core/native_module.py` | `cpp/ (planned)` | planned |
| `pipela_core/paths.py` | `cpp/src/core/paths.cpp` | mapped |
| `pipela_core/primary_monitor.py` | `cpp/ (planned)` | planned |
| `pipela_core/profile_bootstrap.py` | `cpp/ (planned)` | planned |
| `pipela_core/region_dispatch.py` | `cpp/ (planned)` | planned |
| `pipela_core/registry_config_snapshot.py` | `cpp/ (planned)` | planned |
| `pipela_core/registry_constants.py` | `cpp/src/core/registry/constants.hpp` | mapped |
| `pipela_core/registry_snapshot_read.py` | `cpp/ (planned)` | planned |
| `pipela_core/reload_idle_secondary.py` | `cpp/ (planned)` | planned |
| `pipela_core/reload_nobullet_bullet.py` | `cpp/ (planned)` | planned |
| `pipela_core/reload_sequence.py` | `cpp/ (planned)` | planned |
| `pipela_core/scale_geometry.py` | `cpp/ (planned)` | planned |
| `pipela_core/state_native_proxy.py` | `cpp/ (planned)` | planned |
| `pipela_core/telemetry_metrics.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_apply.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_capture_catalog.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_capture_region.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_debug_match.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_match_config.py` | `cpp/ (planned)` | planned |
| `pipela_core/template_matching.py` | `cpp/src/core/vision/template_match.cpp` | mapped |
| `pipela_core/template_roi.py` | `cpp/ (planned)` | planned |
| `pipela_core/ui_fonts.py` | `cpp/ (planned)` | planned |
| `pipela_core/version_info.py` | `cpp/src/core/version.cpp` | mapped |
| `pipela_core/vision_capture.py` | `cpp/src/core/vision/capture.cpp` | mapped |
| `pipela_core/vision_lazy.py` | `cpp/ (planned)` | planned |
| `pipela_core/win32_client_capture.py` | `cpp/ (planned)` | planned |
| `pipela_core/win32_game_windows.py` | `cpp/src/core/win32/game_windows.cpp` | mapped |
| `pipela_core/win32_input_constants.py` | `cpp/ (planned)` | planned |
| `pipela_core/win32_window_ops.py` | `cpp/src/core/win32/window_ops.cpp` | mapped |
| `pipela_core/worker_runtime_bridge.py` | `cpp/ (planned)` | planned |

### pipela_qt (selected)

| Python | C++ target | Status |
| --- | --- | --- |
| `pipela_qt/app.py` | `cpp/ (planned)` | planned |
| `pipela_qt/app_shell.py` | `cpp/ (planned)` | planned |
| `pipela_qt/capture_freeze_frame.py` | `cpp/ (planned)` | planned |
| `pipela_qt/card_popup_shell.py` | `cpp/ (planned)` | planned |
| `pipela_qt/client_transition_debug.py` | `cpp/ (planned)` | planned |
| `pipela_qt/control_main.py` | `cpp/src/ui/control/main_window.cpp` | mapped |
| `pipela_qt/control_tab_chrome.py` | `cpp/ (planned)` | planned |
| `pipela_qt/cursor_hud.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dcomp_hud.py` | `cpp/ (planned)` | planned |
| `pipela_qt/debug_pulse_overlay.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dev_ui_mode.py` | `cpp/src/ui/dev_ui_mode.cpp` | mapped |
| `pipela_qt/dialog_dismiss_on_outside.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dock_chrome_restore.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dock_panel_pair_resize.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dock_ui_phase.py` | `cpp/ (planned)` | planned |
| `pipela_qt/dpi.py` | `cpp/ (planned)` | planned |
| `pipela_qt/flame_trigger_glass_button.py` | `cpp/ (planned)` | planned |
| `pipela_qt/frame_timing.py` | `cpp/ (planned)` | planned |
| `pipela_qt/game_title_bar_overlay.py` | `cpp/src/ui/strip/title_bar_strip.cpp` | mapped |
| `pipela_qt/kill_counter_viewport_metrics.py` | `cpp/ (planned)` | planned |
| `pipela_qt/kill_counter_viewport_typography.py` | `cpp/ (planned)` | planned |
| `pipela_qt/kill_counter_window.py` | `cpp/src/ui/kill_counter/floater_window.cpp` | mapped |
| `pipela_qt/main_window.py` | `cpp/ (planned)` | planned |
| `pipela_qt/outlined_text_pushbutton.py` | `cpp/ (planned)` | planned |
| `pipela_qt/overlay.py` | `cpp/ (planned)` | planned |
| `pipela_qt/overlay_chrome.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_capture.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_dock_anchor.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_dock_z_stack.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_fonts.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_icons.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_side_dock.py` | `cpp/ (planned)` | planned |
| `pipela_qt/qt_typography_refresh.py` | `cpp/ (planned)` | planned |
| `pipela_qt/region_drag_overlay.py` | `cpp/ (planned)` | planned |
| `pipela_qt/region_preview_overlay.py` | `cpp/ (planned)` | planned |
| `pipela_qt/resizable_text_widgets.py` | `cpp/ (planned)` | planned |
| `pipela_qt/resolution_chrome.py` | `cpp/ (planned)` | planned |
| `pipela_qt/roadmap.py` | `cpp/ (planned)` | planned |
| `pipela_qt/scroll_utils.py` | `cpp/ (planned)` | planned |
| `pipela_qt/scrub_spinboxes.py` | `cpp/ (planned)` | planned |
| `pipela_qt/settings_binary_toggle.py` | `cpp/ (planned)` | planned |
| `pipela_qt/settings_sequence_autoscroll.py` | `cpp/ (planned)` | planned |
| `pipela_qt/shell.py` | `cpp/src/ui/shell/application.cpp` | mapped |
| `pipela_qt/splash_screen.py` | `cpp/ (planned)` | planned |
| `pipela_qt/taskbar_hide.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_capture_confirm.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_drag_overlay.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_path_connector_arrow.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_section_probe_frame.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_toolbar_fit.py` | `cpp/ (planned)` | planned |
| `pipela_qt/template_toolbar_shimmer_button.py` | `cpp/ (planned)` | planned |
| `pipela_qt/terminal_log_html.py` | `cpp/ (planned)` | planned |
| `pipela_qt/terminal_log_list_widget.py` | `cpp/ (planned)` | planned |
| `pipela_qt/text_width_fit.py` | `cpp/ (planned)` | planned |
| `pipela_qt/theme.py` | `cpp/src/ui/theme/theme.cpp` | mapped |
| `pipela_qt/typography_refresh_support.py` | `cpp/ (planned)` | planned |
| `pipela_qt/ui_adaptive.py` | `cpp/ (planned)` | planned |
| `pipela_qt/ui_typography.py` | `cpp/ (planned)` | planned |
| `pipela_qt/update_helpers.py` | `cpp/ (planned)` | planned |
| `pipela_qt/win32_mouse_hook.py` | `cpp/ (planned)` | planned |
