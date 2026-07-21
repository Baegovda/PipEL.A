# Python → C++ gap audit (2026-07-20)

`AUDIENCE`: agents — precision comparison after AN–AS batch close.

## Build verification (this session)

| Check | Result |
|-------|--------|
| `scripts/build_cpp_release.bat` | **PASS** (Pipela.exe + `pipela_golden_tests`) |
| `ctest` | **PASS** |
| `tools/parity/run_worker_parity_preflight.py` | **PASS** (90 keys, AppState 57/57) |
| `tools/cpp_ui_smoke.ps1` | **PASS** |
| `scripts/build_cpp_cutover_bundle.bat` | **PASS** (pipela_native.pyd + Pipela.exe) |
| `scripts/package_cpp_release.bat` | **PASS** (`Pipela-cpp-0.10.0-win64.zip`) |
| Owner in-game A/B (`AB_READINESS.md`) | **PENDING** |

## Closed (P0 + AM–AS)

| Gap | Python | C++ |
|-----|--------|-----|
| Update manifest | `update_settings.py`, `main._pipela_fetch_update_manifest` | `core/update/manifest.cpp` + `update_settings_panel.cpp` |
| Key capture UI | HP / FT / Ammo `grabKeyboard` | `widgets/key_capture_row.cpp` |
| VK display names | `vk_to_display_name` | `core/input/keymap.cpp::vkToDisplayName` |
| Card confirm/message | `card_popup_shell` | `card_popup_shell.cpp` |
| Golden tests in release build | missing exe | `build_cpp_release.bat` builds `pipela_golden_tests` |
| Registry WCHAR UTF-8 | — | `registry/store.cpp` `wideToUtf8` + golden round-trip |
| Package zip version | — | `package_cpp_release.bat` UTF-8 `version.json` read |
| Template last-match thumb | `template_last_match_thumb.py` | `last_match_cache` + `template_last_match_thumb` + `TemplateProbeSection` |
| Image preview panel | `image_preview.py` | `panel_factory` registry key picker + `bgr_image_qt` |
| KC panel visual | goal tier colors, roll pulse | `kill_counter_panel.cpp` tier bars + `flashRecentValue` |
| KC bar chart polish | reload mark shimmer | `kill_counter_bar_chart_widget.cpp` reload pulse on glass bars |
| Settings autoscroll | `settings_sequence_autoscroll.py` | `settings_sequence_autoscroll.cpp` + worker `seqScrollSet` |
| Template connector arrows | `template_path_connector_arrow.py` | `template_path_connector_arrow.cpp` + `worker_template_panel` poll |
| Tesseract install guide | `tesseract_settings.py` | `kill_counter_install_help.hpp` + `createTesseractPanel` callout/copy |
| Scrub spinboxes | `scrub_spinboxes.py` | `drag_spin_box.cpp` (interface, console HMS, workers) |
| Template toolbar fit/shimmer | `template_toolbar_fit.py`, shimmer button | `template_toolbar.cpp` fit + test shimmer |
| Splash branding | `assets/splash.png` | `splash_screen.cpp` + `paths::splashImagePath` + CMake copy |
| Tray / console HMS | `shell.py` tray, `console_settings.py` H/M/S | `application.cpp` tray; `console_log_retention.hpp` + HMS UI |

## Remaining gaps (priority)

### P3 / defer

- `debug_pulse_overlay.py` (diagnostics only)
- `thumbnail_preview_dialog.py` full parity (C++ uses card popup subset)

## Metrics after AN–AS close

| Metric | Value |
|--------|-------|
| **Implementation %** | **99%** |
| **Perfect replacement %** | **97%** |
| **Phase 6 ship ceiling** | **97%+** after owner AL in-game A/B |

## Next batch

| Batch | Scope | Gate |
|-------|-------|------|
| **AL** | Owner 10-worker in-game A/B | [`AB_READINESS.md`](AB_READINESS.md) → [`PARITY_RESULTS.md`](PARITY_RESULTS.md) |
