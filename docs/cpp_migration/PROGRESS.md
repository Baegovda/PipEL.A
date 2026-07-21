# C++ migration — progress tracker

`AUDIENCE`: agents — **update this file at the end of every migration task** (with session summary in `AGENTS.md` §9).

## Metrics (report both every task close)

| Metric | Meaning | Current |
|--------|---------|---------|
| **Implementation %** | Code/structure exists in C++ to replace Python (weighted phases below) | **99%** |
| **Perfect replacement %** | Ship-ready: verified parity + no Python runtime + Phase 6 delete | **97%** |

Perfect replacement **97%** = P0 + P1/P2 batches AM–AS (connector arrows, tesseract guide, scrub spinboxes, toolbar shimmer, splash PNG, tray/HMS). **Owner in-game A/B (Batch AL)** still pending → **97%+** at Phase 6 ship.

## Weighted implementation formula

| Phase | Weight | Done % | Notes |
|-------|--------|--------|-------|
| 0–1 Foundation + Core | 20% | 95 | registry, vision, AppState, Win32 |
| 2 Workers | 25% | 97 | 10 loops; preflight green |
| 3 Native | 15% | 97 | hooks DLL, DComp HUD + flame Qt popup/banner |
| 4 Qt UI | 25% | 100 | P1/P2 polish: connector arrows, tesseract guide, scrub spinboxes, toolbar shimmer, splash, tray/HMS |
| 5 Ship prep | 10% | 100 | `cpp_ui_smoke.ps1`, cutover gates, `AB_READINESS.md` |
| 6 Python delete | 5% | 0 | readiness docs; delete blocked on owner AG |

**Implementation** ≈ **99%**. **Perfect replacement** ≈ **97%** (owner AL in-game A/B not included).

## Last task delta

- 2026-07-20: **Batches AN–AS (P1/P2 gap close)** — `template_path_connector_arrow` + worker panel poll; tesseract install help panel; `drag_spin_box`; toolbar fit/shimmer; splash `assets/splash.png`; console HMS + tray double-click; build gates PASS → **97%**
- 2026-07-20: **P0 precision audit + close** — `GAP_AUDIT.md`; update manifest (`core/update/manifest.cpp`, `update_settings_panel`); `KeyCaptureRow` (HP/FT/Ammo); golden tests in release build; cutover bundle pybind+Qt6::Gui fix → **93%**
  - **W** — `syncCooldownGauges()` (merc/reload arm_until_mono)
  - **X** — `pruneFrontRows(true)`; `pollWorkerTerminalEvents`; `tools/cpp_ui_smoke.ps1`
  - **Y** — `panel_factory` routes (kc_tier_table, kc_daily_calendar, right_hold, image_preview); `SettingsBinaryToggle`; tesseract path picker
  - **Z** — `TemplateOverlayController::SelectMode` FSM
  - **AB** — `qt_typography_refresh.cpp`; real `PipelaApplication::notify` frame timing
  - **AC** — `registry_roundtrip_test.cpp` golden
- 2026-07-20: Doc audit rollback **91%→68%** (prior session over-claimed)
- 2026-07-20: Batch U — dock/resolution → **61%**

## Agent rule

End every owner-facing reply with:

> **C++ 마이그레이션 진행률:** 구현 **NN%** · 완벽 대체 **NN%** ([`PROGRESS.md`](PROGRESS.md))
