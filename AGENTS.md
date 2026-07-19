# Pipela — Agent handbook

`AUDIENCE`: LLM agents and maintainers.  
`PURPOSE`: **Single document** — governance, release, architecture, incidents, session dashboard.

---

## Changelog

### [Unreleased]

_Empty — ship next changes here._

### [0.9.13] - 2026-07-20

- Added: Unified `AGENTS.md` handbook (merged former `HANDOFF.md`); GitHub release policy; F5 dev workflow (`.vscode/`, `tools/pipela_dev_prepare.ps1`, workspace `.venv`).
- Changed: Consolidated shipped PNGs under `assets/`; Qt/PyQt6 app and tooling updates across `pipela_qt/`, `pipela_core/`, `main.py`.

### [0.9.12] - 2026-04-30

- Baseline before unified `AGENTS.md` (see git history).

---

## 1. Ownership and language

- Codebase is **AI-maintained**; the owner directs work in **Korean chat only**.
- **User replies**: Korean.
- **Code, comments, agent docs, rules, changelog**: English (`# AGENT:` on new inline notes).
- **In-app UI strings**: Korean — do not bulk-change without product intent.
- **Registry keys, manifest JSON fields, serialized enums**: English.

---

## 2. Single source of truth

| Artifact | Role |
|----------|------|
| **`AGENTS.md`** (this file) | Governance, release, architecture, incidents, changelog — **only agent doc** |
| **`version.json`** | Release manifest (`version`, `download_url`, `release_url`) — published on `main` |
| **`pipela_core/version_info.py`** | Runtime version constants — **must match** `version.json` |
| **`.vscode/`** | IDE workflow (F5 run, workspace `.venv`) — tracked in git |
| **`UpdateLog/update_log.md`** (optional) | User-facing changelog (Korean) |
| **`WINDOW_Z_ORDER_AND_LAYOUT.md`** | Z-order / dock geometry detail (linked from §13, §15, §18) |
| **`docs/UI_STUTTER_REPRO_SCENARIOS.md`** | UI stutter repro S0–S5 (§17) |

**Do not** put version bump or release procedure only in chat or changelog bullets.

---

## 3. Version policy

### 3.1 Files to keep in sync

On every **shipped** version bump, update **all** of:

| File | Fields |
|------|--------|
| `version.json` | `version`, `download_url`, `release_url` |
| `pipela_core/version_info.py` | `PIPELA_APP_VERSION`, `PIPELA_STRIP_DISPLAY_VERSION` |

Never hardcode the app version string elsewhere.

### 3.2 Segment policy

| Bump | When |
|------|------|
| **Patch** | Default — completed user task that ships to users or tags a release |
| **Minor** | New subsystem, major milestone |
| **Major** | Breaking settings format, 1.0 |

### 3.3 Docs-only tasks

Governance/docs/`.vscode` edits: append **`[Unreleased]`** in §Changelog; **no version bump** until the next user-visible release unless the owner asks.

---

## 4. GitHub and release

### 4.1 Repository

- **Remote**: `https://github.com/Baegovda/PipEL.A`
- **Default branch**: `main`
- **Release assets**: `Pipela.exe` (PyInstaller output from `build.bat` → `dist\Pipela.exe`)

### 4.2 Manifest (in-app update check)

Apps fetch manifest from:

`https://raw.githubusercontent.com/Baegovda/PipEL.A/refs/heads/main/version.json`

Override for testing: env **`PIPELA_UPDATE_MANIFEST_URL`**.

`version.json` shape:

```json
{
  "version": "0.9.12",
  "download_url": "https://github.com/Baegovda/PipEL.A/releases/download/v0.9.12/Pipela.exe",
  "release_url": "https://github.com/Baegovda/PipEL.A/releases/tag/v0.9.12"
}
```

- **`download_url`** — EXE direct link (GitHub Release asset URL pattern).
- **`release_url`** — release notes / tag page (browser).
- Optional same-version EXE swap: **`PIPELA_REINSTALL_EXE_URL`** (env).

Auto-install works only for **frozen** `Pipela.exe` (PyInstaller), not `python main.py`.

### 4.3 Release procedure (when shipping a new version)

1. **Bump version** — §3.1 files.
2. **Build EXE** — `build.bat` (or CI artifact matching `Pipela.spec`).
3. **Commit** — only when the owner requests (§6).
4. **Push** `main` — includes updated `version.json`.
5. **GitHub Release** — tag `vX.Y.Z`, upload `dist\Pipela.exe`.
6. **Verify URLs** — `download_url` and `release_url` match the new tag.
7. **Changelog** — move `[Unreleased]` → dated section; update `UpdateLog/update_log.md` if used.

```powershell
gh release create v0.9.13 dist\Pipela.exe --repo Baegovda/PipEL.A --title "v0.9.13" --notes "..."
```

### 4.4 Anti-patterns

- Changelog without version bump when shipping to users.
- Version bump without updating `version.json` URLs.
- Release EXE from a different commit than tagged `version.json` on `main`.
- Release URLs only in chat — they must live in `version.json`.

---

## 5. Build policy

| Who | Dev run | Ship EXE |
|-----|---------|----------|
| Human | **F5** → `Pipela: Build and Run` (`main.py`) | `build.bat` or **Ctrl+Shift+B** |
| AI | — | `build.bat` at task close **only if** Python/bundle inputs changed |

- **Workspace venv**: `Pipela/.venv/` — isolated per Cursor window; `tools/pipela_dev_prepare.ps1`.
- **Native HUD DLL** (only when `native/cursor_hud_dcomp/*` changes): `native\cursor_hud_dcomp\build_dcomp.bat`.
- **Docs/rules only** → skip `build.bat`.

---

## 6. Task close checklist

### While implementing

- Append bullets under **`[Unreleased]`** in §Changelog.
- English, specific (file/behavior).

### Before closing a **shipping** task

When the owner requests commit/push/release:

1. Version bump (§3) if shipping to users.
2. `build.bat` if compile/bundle inputs changed.
3. Move `[Unreleased]` → dated section.
4. Update **§9 Session dashboard** if technical context or risks changed.
5. New `pipela_core` module → one row in **§16** only.
6. New `pipela_qt` surface or public `m.*` API → **§11** and/or **§12**.
7. New env vars / CLI flags / dock behavior → **§15** and/or **§17** (+ bump doc header `UPDATED` if cross-cutting).
8. **Git**: `add` → `commit` → `push origin main` — **only when the owner requests**.
9. **GitHub Release** (§4.3) — **mandatory on every version bump users install**.

### Git commits

Commits and pushes are **owner-requested** unless the same task explicitly says otherwise.

---

## 7. IDE (Cursor / VS Code)

| Action | How |
|--------|-----|
| Run | **F5** → `Pipela: Build and Run` |
| Build EXE | **Ctrl+Shift+B** → `Pipela: Build EXE (PyInstaller)` |
| Python | `${workspaceFolder}\.venv\Scripts\python.exe` (workspace only) |

CMake Tools disabled in `.vscode/settings.json` so other projects in other windows are unaffected.

---

## 8. Agent policy (Cursor)

**Response style:** 요약·결론만 간결하고 명료하게. (Short, clear; no filler unless the user wants depth.)

**Operator UX (mandatory):** The owner prefers **minimal ceremony** — no reliance on opening a separate terminal, copy-pasting commands, or multi-step tooling for everyday workflows unless unavoidable. Prefer: **launch `main.py` from the IDE (or one shortcut)**; wire optional behaviors through **`main.py` flags / env vars** documented here or in-repo one-liners, not “run this ps1 then that.” Agents should implement flows so **one rerun of the app finishes the job** when adding diagnostics, profiling, or debug switches (e.g. `--profile-agent` → `profiling/agent_profile/`). Scripts under `tools/` stay for agents/CI/advanced cases, not as the primary owner path.

**UI popups (Qt):** Prefer `pipela_qt.card_popup_shell.CardFramelessDialog` (+ `center_card_popup`) for modal/image/detail. Avoid `QMessageBox` in new or touched code unless a native OS sheet is required.

**Adaptive / fluid UI (default policy for new or touched Qt):** Prefer **density-aware sizing** — `pipela_qt/ui_adaptive` (`scale_px`, `spt`, letter/padding helpers), `pipela_qt/theme` typography tokens, stretch/`QSizePolicy`/scroll for overflow — over **raw pixel literals** in layout and QSS. Reuse **`TypographyStyleBundle` + `apply_scaled_typography()`** on panels that expose it; align with global UI font PT via **`pipela_qt/qt_typography_refresh`**. Where Qt meets Win32 rects (docking, strips), follow **§18** / `dpi.py` / `qt_side_dock.py` — never mix logical Qt width with physical coords. Card dialog body text: **`pipela_qt.card_popup_shell.dialog_body_html`** for consistent wrapping (CJK-safe).

**After rules load:** (1) Read this file (`AGENTS.md`) end-to-end. (2) Optional: `docs/UI_STUTTER_REPRO_SCENARIOS.md` for stutter repro. (3) `pipela_qt/roadmap.py` → `roadmap.summary()`.

**Comments & docs (audience: agents, not end users):** See **§20** — repo comments & handoff text use **concise English** and `# AGENT:` on new inline notes for fast grep; `main.py` / `pipela_qt` still have older Hangul in comments in places — **translate only when you edit that region** (no bulk rewrite). UI **strings** in Hangul: do not change without product intent.

**Paste stub (minimal):**

```
Read repo root AGENTS.md in full. `pipela_mod` = `_pipela_mod_for_qt()` (§10). Update §9 session dashboard when done.
```

---

## 9. Session dashboard (copy / update each task)

| key | value |
|-----|--------|
| `LAST_TASK` | **Session rollup (2026-04-29–30):** (1) **Kill dock / resolution** — `qt_side_dock.compute_side_dock_layout` + `clamp_dock_logical_geometry`; `kill_counter_window` dedupe/retry + `PIPELA_DEBUG_KILL_DOCK`; `control_main._apply_computed_side_dock` clamp. (2) **Main tabs** — `_apply_main_tabs_cluster_label_style` implemented; `_post_typography_layout_and_fit` calls it. (3) **Startup splash** — `PipelaSplashProgress` custom widget: bottom eased gauge + milestones in `shell.run_qt_application`; optional `assets/splash.png` via `paths.PIPELA_SPLASH_IMAGE_PATH`; fallback 520×292 synthesized panel; **`PIPELA_NO_SPLASH`** disables. (4) **Cursor / Flame HUD** — no user toggle; removed `pipela_cursor_hud_enabled` from `interface_settings`, `main`, `config_registry_tables`; deleted `pipela_cursor_hud_startup_wanted` / `apply_pipela_cursor_hud_enabled` from `cursor_hud.py`; `shell` always creates `QtCursorHud`. (5) **Bugfix** — `shell._splash_raise` nested def restored after refactor. (6) **HANDOFF §10** — `pipela_mod` row + §8/§23 paste stubs: `_pipela_mod_for_qt()` / `sys.modules` / `_PipelaExecGlobalsProxy` fallback (matches `main.py`). (7) **main.py split (Phase 1~2)** — profile/diagnostics argv helpers extracted to `pipela_core/profile_bootstrap.py`; key mapping helper `_pynput_key_to_vk` extracted to `pipela_core/input_keymap.py`; `main.py` now wires those modules directly. (8) **main.py Phase 3 bridge** — `pipela_core/app_state.py` + `_state_get/_state_set` bridge added; state domain map + worker RW map documented in code; worker/input paths started migration (`kill_counter_loop`, `reload_loop`, `ammo_restock_loop`, `check_left_hold`, `on_key`). (9) **Phase 3 cleanup pass** — migrated status helpers now read through `_state_get`; removed redundant `global` declarations in migrated loops/helpers to reduce dual-source drift risk while bridge remains. (10) **Phase 3 continuation** — input route (`left_click_loop`, `on_click`, `_delayed_arm_left_off_pending`, `_pause_left_click_and_right_hold_for_flame_trigger`) now uses `_state_get/_state_set`; `running` lifecycle writes in `main_qt`/shutdown also routed via bridge. (11) **Phase 3 continuation-2** — `right_hold_loop` and `flame_trigger_loop` now read `running`/`select_mode`/`target_hwnd`/`flame_trigger_active` through bridge paths; no-window FT teardown writes `flame_trigger_active` via `_state_set`. (12) **Phase 3 continuation-3** — bridged flame runtime fields (`flame_trigger_*`) into `InputState`; `flame_trigger_loop` and reload/call-merc FT restore paths now write/read those fields through `_state_get/_state_set` to reduce direct global drift. (13) **Phase 3 continuation-4** — removed redundant `global` declarations from fully bridged loops (`left_click_loop`, `right_hold_loop`, `flame_trigger_loop`) for readability and lower maintenance noise. (14) **Phase 3 continuation-5** — introduced `_state_getk(key)` for keyed fallback and rewired migrated input/FT paths to reduce direct symbol fallback usage (`_state_get(..., some_global)`), easing later bridge removal. (15) **Phase 3 continuation-6** — rewired `kill_counter_loop`/`reload_loop`/`ammo_restock_loop` hot-path reads to `_state_getk`, including score/counter/arm-timer accesses and loop guards; reduced remaining `_state_get(..., global)` fallbacks to only unmigrated loops. (16) **Phase 3 continuation-7** — removed the final `_state_get(...)` callsites in flame/reload runtime branches (`flame_trigger_session_reload_count`, `flame_trigger_last_reload_trigger_time`, `flame_trigger_prev_press_timestamp`), leaving `_state_get` as bridge-internal only and unifying runtime reads on `_state_getk`. (17) **Phase 3 continuation-8** — added `_state_inc_int(key, delta=1)` and rewired migrated counter increments (`reload_success_count`, `ammo_restock_loop_count`, `flame_trigger_session_reload_count`, `flame_trigger_press_count`, `left_click_id`) to a single typed increment path, reducing duplicated read-modify-write code. (18) **Phase 3 continuation-9** — added `_state_gets(key)` (strict AppState getter) and rewired `kill_counter`/`reload`/`ammo_restock` migrated read paths to strict state reads, limiting globals-fallback reads (`_state_getk`) to still-unmigrated loops/routes. (19) **Phase 3 continuation-10** — rewired remaining input/FT and ride runtime reads (`left_click_loop`, `right_hold_loop`, `flame_trigger_loop`, `_delayed_arm_left_off_pending`, `_pause_left_click_and_right_hold_for_flame_trigger`, `on_click`, `check_left_hold`, `on_key`, `ride_loop`) from `_state_getk` to `_state_gets`; runtime callsites of `_state_getk` are now removed. (20) **Phase 3 continuation-11** — removed `_state_getk` helper and switched `_state_inc_int` to strict `_state_gets` reads, finalizing keyed fallback helper retirement while keeping `_state_get` bridge available for compatibility. (21) **Phase 3 continuation-12** — removed `_state_get` bridge helper itself (full bridge removal) after strict-read migration; verified no `_state_get*` compatibility reader usages remain, with runtime reads consolidated on `_state_gets` and writes on `_state_set`. (22) **Phase 3 continuation-13 (hotfix)** — after full bridge removal, fixed remaining direct global writes on AppState-owned keys that could desync strict reads: `refresh_target_hwnd_if_needed` now writes via `_state_set("target_hwnd", ...)`; kill-counter session helpers now read/write via `_state_gets/_state_set`; call-merc FT disable path now writes `flame_trigger_active` via `_state_set`; region/template overlay force-close paths now clear `select_mode` via `_state_set`. (23) **Kill panel goal-line typography** — added `KC_PT_GOAL_LINE = 11.0` (half of `KC_PT_PRIMARY`) to `pipela_qt/panels/kill_counter_panel.py` token block; `_reapply_goal_plain_labels_typography` now uses it for `_grem`/`_geta`/`_gcrm`/`_gcel` (다음·킬작 졸업 "남은 킬/남은 시간" 4 라벨), independent of lap-cumulative card primary sizing. |
| `OPEN_RISKS` | Resolution-change **full process exit** still unproven in logs — use `PIPELA_DEBUG_KILL_DOCK=1` if repro. |
| `TODO` | — |
| `LAST_UPDATE` | 2026-05-07 |

---

## 10. Architecture (non-negotiable)

| fact | detail |
|------|--------|
| `ENTRY` | `main_qt()` → `pipela_qt.shell.run_qt_application` |
| `pipela_mod` | `_pipela_mod_for_qt()` in `main.py`: walks `sys.modules` in order `(__name__, "__main__", "main")` where the first entry is this file's `__name__` (e.g. `__main__` when launched as `main.py`, or `main` when imported); returns the first hit that defines `pipela_overlay_tick_ms`, `target_hwnd`, and `refresh_target_hwnd_if_needed`; else `_PipelaExecGlobalsProxy(main_qt.__globals__)`. Qt and workers call `m.*` on that object. |
| `UI` | **PyQt6 only** in `pipela_qt/`. No Tk / no `pipela_legacy_tk`. |
| `pure logic` | `pipela_core/` (no Qt imports) |
| `WORKERS` | `main.py` background threads — `grep` `def .*_loop\(` |

**Worker names (search in `main.py`):**  
`left_click_loop`, `right_hold_loop`, `flame_trigger_loop`, `ride_loop`, `hp_refill_loop`, `reload_loop`, `ammo_restock_loop`, `call_merc_loop`, `kill_counter_loop`, `start_game_launcher_loop`, …

---

## 11. Directory map

| path | role |
|------|------|
| `main.py` | globals, registry, workers, pynput, `pipela_mod` API for Qt |
| `pipela_qt/` | all product UI, overlays, shell, panels |
| `pipela_core/` | Win32, registry, vision, templates, paths |
| `Pipela.spec` | PyInstaller |
| `profiling/agent_profile/` | **Single handoff folder** for agents (Cursor @); see `README.txt` inside after any profile run |
| `tools/profile_pipela.ps1` | cProfile → `pipela_cprofile_*.stats` + copy/summary into `agent_profile/` |
| `tools/profile_pipela_pyspy.ps1` | py-spy → `agent_profile/pyspy.speedscope.json` (needs `pip install py-spy`) |
| `tools/profile_pipela_scalene.ps1` | Scalene → `agent_profile/scalene.json` (needs `pip install scalene`) |
| `tools/dump_cprofile_summary.py` | pstats text from any `.stats` → default `agent_profile/summary.txt` |
| `pipela_qt/frame_timing.py` | **`PIPELA_UI_FRAME_TIMING=1`** → `agent_profile/frame_timing.tsv` |
| `tools/compare_agent_profile.py` | unified diff two `summary.txt` or two `agent_profile/` dirs |
| `tools/profile_kernprof_pipela.ps1` | kernprof line_profiler → `line_profiler_notify.lprof` |
| `requirements-profiling-extra.txt` | optional pip: py-spy, scalene, line_profiler (provides `kernprof`) |
| `tools/profile_pipela_bundle.ps1` | **one paste** → cProfile+tracemalloc+frame_timing+(py-spy if installed); `profiling/agent_profile/` |
| `pipela_core/profile_bootstrap.py` | `main.py` profiling/bootstrap helpers (`--profile-*`, `PIPELA_*`, py-spy/scalene child, cProfile/tracemalloc handoff) |
| `pipela_core/input_keymap.py` | pynput key → VK mapping helper (`pynput_key_to_vk`) used by keyboard listener |
| `pipela_core/app_state.py` | phase-3 state container (`AppState` + `InputState`/`WorkerRuntimeState`/`KillCounterState`) for global→state migration |
| `pipela_core/kill_counter_tier_data.py` | 킬 카운터 등급·몬스터킬 구간 내장 표 |
| `pipela_qt/splash_screen.py` | Startup splash + loading gauge; `paths.PIPELA_SPLASH_IMAGE_PATH` (`assets/splash.png` optional) |
| `pipela_qt/kill_counter_viewport_typography.py` | KC floater typography bands (`hero_prog_pts`, `lap_sheet_*_pts`, …) + `kc_fit_qpushbutton_text_width_qss` (viewport-aware button fit) |

**Grep (navigation):** workers `def .*_loop\(` in `main.py`; registry `config_registry_*`, `config_parse`; Qt→main `pipela_mod.` / `m.` in `pipela_qt/`.

---

## 12. Qt — files to open first

| area | module |
|------|--------|
| App / `QApplication` | `pipela_qt/shell.py` — splash + tray + Qt boot order |
| Startup splash + gauge | `pipela_qt/splash_screen.py` (`PipelaSplashProgress`, `create_startup_splash`, `finish_startup_splash`) |
| Control window | `pipela_qt/control_main.py` |
| Terminal log (줄 UI·페이드) | `pipela_qt/terminal_log_list_widget.py` — 데이터/HTML/`rebuild` 는 `control_main` |
| Dock phase | `pipela_qt/dock_ui_phase.py` |
| Game overlay | `pipela_qt/overlay.py` |
| Title strip | `pipela_qt/game_title_bar_overlay.py` |
| Cursor / flame HUD | `pipela_qt/cursor_hud.py` — **always** instantiated from `shell.py` (no registry/UI off switch) |
| Debug pulse | `pipela_qt/debug_pulse_overlay.py` |
| DPI / dock math | `pipela_qt/dpi.py` |
| Side dock geometry (L/R snap) | `pipela_qt/qt_side_dock.py` |
| Kill counter floater (dock to game) | `pipela_qt/kill_counter_window.py` — shares `clamp_dock_logical_geometry`, see §15 `KILL_DOCK_RESOLUTION_TRANSITION`; panel viewport typography `pipela_qt/kill_counter_viewport_typography.py` |
| Docked chrome Z (game < overlay < panel) | `pipela_qt/qt_dock_z_stack.py` |
| Dock anchor HWND rules | `pipela_qt/qt_dock_anchor.py` |
| Adaptive sizing / UI pt refresh | `pipela_qt/ui_adaptive.py`, `pipela_qt/qt_typography_refresh.py` (with `pipela_qt/theme.py`) |
| Theme / QSS | `pipela_qt/theme.py`, `pipela_qt/app_shell.py` |
| Feature checklist | `pipela_qt/roadmap.py` → `roadmap.summary()` |

### Terminal log list (`ResizableTerminalLogList`)

- **역할:** 예전 `QTextEdit` 대신 줄당 `_LogLineRow` + `QScrollArea`. HTML·아이콘·색은 `pipela_qt/terminal_log_html.py`. 큐(`_terminal_log_fading` / `memory` / `archive`)와 `rebuild_terminal_log_display_for_time_mode()` 는 `control_main` — `entries` + `row_height_factors` 로 `apply_log_rows` 호출 후 `flush_terminal_log_layout()`.
- **페이드 3초:** `_TERMINAL_LOG_FADE_OUT_SEC`, `_TERMINAL_FADE_TICK_MS`, `_TERMINAL_FADE_EASING` (`OutCubic`). 불투명도와 줄 높이 비율 모두 `_terminal_fade_eased_progress` 기준. `row_height_factors`: fading 줄 `1 - progress`, memory 줄 `1.0`.
- **`apply_log_rows`:** 키 동일 → `set_html` + 높이 팩터 + `_prune_stale_prefix_rows`. 앞에서만 `n_drop` 제거(≤24) → 맨 앞이 이미 `not visible` 또는 `maxH≤0` 이면 **즉시 `removeWidget`/`deleteLater`** 후 필요 시 `allow_animate=False` 재진입; 꼬리는 HTML·factor 동기화 + `_continue_front_strip_chain` (맨 앞 `maximumHeight` 애니). 그 외 `_full_reset_rows`.
- **`set_html` / `_nh_cache`:** 페이드 중(부분 접힘 또는 이미 `maxH≤0`)에는 캐시를 지우지 않음 — 색만 바뀌는 틱마다 `sizeHint` 흔들림 방지. `fk≈0` → `maxH=0`, `setVisible(False)`, 레이아웃에서 막히지 않게 스트립 시 곧바로 위젯 제거.
- **스크롤 복원(아카이브 되돌리기):** `valueChanged` 는 코드 `setValue` 에도 나가므로 **연결하지 않음**. `sliderMoved` + `actionTriggered` + 앱 `eventFilter` 의 터미널 영역 **Wheel** 만 `_schedule_terminal_scroll_restore_from_user`.
- **튜닝:** 페이드/틱/이징은 `control_main` 상단 상수; 맨 앞 접기 애니는 `terminal_log_list_widget` 의 duration·`QEasingCurve`.

---

## 13. Dock UI phase (runtime, not registry)

`IMPL`: `pipela_qt/dock_ui_phase.py`.

| value | const | meaning |
|-------|-------|---------|
| `client` | `UI_DOCK_PHASE_CLIENT` | Game target HWND valid, not minimized — anchor = game |
| `launcher` | `UI_DOCK_PHASE_LAUNCHER` | Launcher (smart updater) only |
| `standby` | `UI_DOCK_PHASE_STANDBY` | Neither — idle (legacy `"none"` → `standby`) |

`API`: `get_ui_dock_phase(pipela_mod)` — order **client → launcher → standby**.  
`RUNTIME`: `pipela_mod.pipela_ui_dock_phase` (not registry).

**Strip geometry** (`game_title_bar_overlay._compute_strip_geometry`): **launcher** — strip width from launcher **outer** client `cr` only (avoid left overhang). **client** — `right = cr[2]` unless kill panel visible → `max(..., kr)`. **Left edge:** control Win32 rect only if `chrome_outer_rect_plausible_for_left_dock` (outer-right ≈ client-left); else `compute_side_dock_layout(..., side="left")` like the control window.

**Start Game template1:** `is_start_game_launcher_template1_effective_on` — ON when registry flag **or** `launcher` phase.

**Launcher chrome:** `control_main._sync_launcher_phase_docked_chrome` — hide control+killer on launcher when policy says so. `pipela_qt/dock_chrome_restore.py` — skip restore in launcher phase.

*Shared dock / Z / strip incident notes:* §15 `DOCK_GEOMETRY_AND_Z_SHARED`, `TITLE_STRIP_RIGHT_EDGE`.

---

## 14. Vision / capture — critical patch (`CURSOR_FLICKER_MSS_CAPTUREBLT`, closed 2026-04-26)

| key | value |
|-----|--------|
| `SYMPTOM` | System cursor rapid blink / perceived jump near (0,0); foreground app only; minimized OK. Repro: **Ride + HP Refill + Ammo Restock + Call Merc** ON (multi-thread `mss.grab`); Flame Trigger could be off. |
| `ROOT` | `mss.windows.MSS._grab_impl` uses `BitBlt(..., SRCCOPY \| CAPTUREBLT)`. `CAPTUREBLT` forces layered capture; DWM **tears/restores hardware cursor** per grab → high grab rate → visible flicker. |
| `FIX` | `pipela_core/vision_lazy.py` → `_patch_mss_windows_disable_captureblt` replaces `_grab_impl` with **`SRCCOPY` only**, inside `ensure_cv2_numpy_mss()` before first `mss.mss()`. |
| `SAFE` | Template ROIs are inside game **client**; omitting layered Pipela overlays from bitmap is desired for matching anyway. |
| `CAPTURE_API` | `pipela_core/vision_capture.py` — `capture_region`, full-client BGR cache (`_CLIENT_BGR_CACHE_TTL_SEC`). |

**Regression:** Never re-add CAPTUREBLT without cursor re-test; re-patch if upstream mss changes `_grab_impl`.

---

## 15. Incident log (closed)

### CURSOR_HUD_DCOMP_NATIVE (2026-05)

**Goal:** eliminate perceived lag/jitter from moving Qt overlay windows for LC/RH/RIDE cursor HUD by switching to a **DirectComposition** native overlay (D3D11+DXGI+D2D+WIC), driven by **Win32 low-level hooks**.

**Python entry points:**
- `pipela_qt/cursor_hud.py`: `QtCursorHud` (hook-driven) calls `pipela_qt/dcomp_hud.py` (`DCompHud`) to drive the native HUD.
- `pipela_qt/dcomp_hud.py`: `DCompHud` ctypes wrapper + DLL path resolution.
- `pipela_qt/shell.py`: always constructs `QtCursorHud` (HUD always-on policy).

**Current policy (important):**
- Cursor icon HUD is **DComp-only** (Qt icon HUD removed). If DComp init fails, icon HUD is **silently off** (no Qt fallback).
- DComp is **default ON**. Set `PIPELA_CURSOR_HUD_DCOMP=0/false/off` to disable explicitly.

**Env vars:**
- `PIPELA_CURSOR_HUD_DCOMP`: default ON; explicit OFF disables DComp HUD.
- `PIPELA_CURSOR_HUD_DCOMP_DLL`: optional override absolute path to `cursor_hud_dcomp.dll`.

**DLL auto-discovery (no env needed):**
- `pipela_qt/dcomp_hud.py` resolves candidates in order:
  - `native/cursor_hud_dcomp/build/cursor_hud_dcomp.dll` (local dev default)
  - `native/cursor_hud_dcomp/build/Release/cursor_hud_dcomp.dll`
  - `native/cursor_hud_dcomp/build/Debug/cursor_hud_dcomp.dll`

**Native implementation:**
- `native/cursor_hud_dcomp/cursor_hud_dcomp.cpp`
  - Creates a click-through top-level host window sized to the **game window rect** (anchor HWND).
  - Uses DirectComposition visual offset to place the icon canvas at cursor position.
  - PNG icons are **embedded into the DLL** via `.rc` + decoded via WIC to D2D bitmaps.
  - Render path uses **aspect-preserving fit**, pixel-snap + nearest-neighbor for tiny sizes.
  - Stability hardening:
    - Handles `EndDraw()` failure / `D2DERR_RECREATE_TARGET` by resetting swapchain/target and recreating.
    - Handles `Present()` failure similarly.
    - Validates anchor HWND (`IsWindow`) and hides host if anchor becomes invalid.
    - `hud_shutdown()` hides + destroys window and resets WIC/bitmaps to avoid DLL lock issues.
- `native/cursor_hud_dcomp/CMakeLists.txt`
  - Generates `cursor_hud_dcomp.rc` from `cursor_hud_dcomp.rc.in` with **REALPATH** absolute PNG paths.
  - Links `windowscodecs` for WIC.
- `native/cursor_hud_dcomp/cursor_hud_dcomp.rc.in`
  - Embedded PNG resources:
    - `assets/arrow.png` (MOVE)
    - `assets/gunfire.png` (FIRE)
    - `assets/chopper.png` (RIDE)

**Build (owner path):**
- `cmd /c native\\cursor_hud_dcomp\\build_dcomp.bat` (outputs `native/cursor_hud_dcomp/build/cursor_hud_dcomp.dll`)

**Exported C ABI (ctypes):**
- `int hud_init(unsigned long long anchor_hwnd)`
- `void hud_set_visible(int visible)`
- `void hud_set_icons(int move_on, int fire_on, int ride_on)`
- `void hud_set_position(int x_phys, int y_phys)`
- `void hud_shutdown()`

**Runtime tuning (current):**
- In `cursor_hud_dcomp.cpp::Render()`:
  - `dx_lr`, `dy_ride` (spacing)
  - `nudge_lr_x/y`, `nudge_ride_x/y` (per-icon offsets)
  - `pngSide` (max side for fit)

### TITLE_STRIP_RIGHT_EDGE

Kill panel off: strip right edge = game client `cr[2]` (not outer frame) so strip does not extend past client. Kill on: extend to `kr`. Code: `pipela_qt/game_title_bar_overlay.py` `_compute_strip_geometry`.

### DOCK_GEOMETRY_AND_Z_SHARED (2026-04-26)

- **`pipela_qt/qt_side_dock.py`:** `compute_side_dock_layout` (left = `dock_outer_rect_touch_client_left`, right = `…_right`); `chrome_outer_rect_plausible_for_left_dock` for strip/control consistency.
- **`pipela_qt/qt_dock_z_stack.py`:** `sync_docked_chrome_z_order`, `clear_docked_chrome_z_stack_state` — same stack as former title-strip `_apply_z_stack_relative` (game < overlay < chrome).
- **Consumers:** `control_main._dock_to_anchor` / `_apply_computed_side_dock`, `kill_counter_window.dock_to_right_of_target_game`, `game_title_bar_overlay._sync_z` + strip left fallback.

### CLIENT_PHASE_DOCK_BURST (2026-04-26)

When UI phase transitions **to** `client` (`pipela_qt/control_main.py` `_refresh`), `_start_client_phase_dock_burst` arms a **1s** `QTimer` for **10** ticks; each calls `_force_client_dock_resync` (no visibility/dedupe guards) + `_emit_client_dock_stdout`. Leaving `client` calls `_stop_client_phase_dock_burst`. Replaces earlier experimental 5s always-on timer.

### KILL_DOCK_RESOLUTION_TRANSITION (2026-04-29)

**Symptom:** Changing **in-game resolution** — kill counter floater fails to re-dock; possible **process exit** (not fully traced in logs).

**Impl (read these together with §18):**

| area | file / symbol | change |
|------|-----------------|--------|
| Layout | `pipela_qt/qt_side_dock.py` | `compute_side_dock_layout`: avoid **1–7px** `fh_phys` / bad rects during anchor transitions — floor heights, post-touch clamps; **`clamp_dock_logical_geometry(x,y,w,h)`** — cap size, bound to primary **available** geometry. |
| Kill window | `pipela_qt/kill_counter_window.py` | Uses **`clamp_dock_logical_geometry`** before Qt geometry + Win32 outer rect; invalidates layout **dedupe** when anchor **client rect** tuple changes; **`layout is None`** path clears dedupe and **retries** (timer, bounded); optional **`PIPELA_DEBUG_KILL_DOCK`** (`1`/`true`/…) → stderr **`[KillDock][debug]`** (+ traceback on errors in guarded paths). |
| Control | `pipela_qt/control_main.py` | **`_apply_computed_side_dock`**: apply **`clamp_dock_logical_geometry`** to logical `w_log`/`h_log` (and position) before **`setFixedWidth`** / move. |
| Main tabs | `pipela_qt/control_main.py` | **`_apply_main_tabs_cluster_label_style`**: `QTabBar.setStyle(None)` so `_PairedControlTabBar` custom **clustered** icon+label paint is not overridden by stylesheet proxy; called from **`__init__`** (after tabs built) and **`_sync_terminal_settings_tab_chrome`**; **`_post_typography_layout_and_fit`** calls it instead of duplicating `setStyle(None)`. |

**Debug:** `set PIPELA_DEBUG_KILL_DOCK=1` (Windows) then run `main.py`; grep console for `[KillDock][debug]`.

### STARTUP_SPLASH_AND_GAUGE (2026-04-30)

| item | detail |
|------|--------|
| `IMPL` | `pipela_qt/splash_screen.py` — **`PipelaSplashProgress`**: frameless top-level; background = `assets/splash.png` if present else **520×292** synthesized pixmap (app icon + version text). Bottom **eased progress bar** (`set_loading_target` monotonic 0…1; display lerps per 60fps tick). |
| `BOOT` | `pipela_qt/shell.py` — after `create_startup_splash(app)`, milestones call `set_loading_target` (e.g. 0.32 / 0.53 / 0.66 / 0.93); **`_splash_raise()`** keeps splash above overlay/strip during sync init; `finish_startup_splash` sets target **1.0**, drains `processEvents` until `load_anim_quiescent()`, then closes. |
| `ENV` | **`PIPELA_NO_SPLASH`** = `1`/`true`/… → no splash. |
| `PATH` | **`pipela_core/paths.py`**: `PIPELA_SPLASH_IMAGE_PATH` → `assets/splash.png` (PyInstaller already bundles `assets/`). |

### HUD_ALWAYS_ON (2026-04-30)

| item | detail |
|------|--------|
| `REMOVED` | Registry bool **`pipela_cursor_hud_enabled`** (load/save tuples in `config_registry_tables.py`); global `pipela_cursor_hud_enabled` in `main.py`; Interface settings **커서·플레임 HUD** toggle block (`interface_settings.py`). |
| `REMOVED API` | `pipela_cursor_hud_startup_wanted`, `apply_pipela_cursor_hud_enabled` from `cursor_hud.py`. **`PIPELA_CURSOR_HUD`** env no longer read for launch. |
| `RUNTIME` | `shell.run_qt_application` **always** constructs `QtCursorHud` + `QtFlameStartBanner` (same `QTimer.singleShot(0, hud.show)` pattern). |

---

## 16. `pipela_core` module index (51 files)

New `.py` → add **one row** in this table (single source; do not fork lists elsewhere).

| module | role |
|--------|------|
| `vision_lazy` | lazy cv2/np/mss; **patches `mss.windows.MSS._grab_impl`** (SRCCOPY only) |
| `vision_capture` | `capture_region`, client BGR cache |
| `template_matching` | OpenCV `matchTemplate` helpers |
| `template_roi` | ROI → screen coords |
| `template_capture_catalog` | capture-kind registry |
| `template_capture_region` | region capture helpers |
| `template_apply` | template apply pipeline |
| `template_debug_match` | settings “test match” one-shot |
| `template_match_config` | thresholds |
| `win32_game_windows` | HWND enum, titles, client rect |
| `win32_window_ops` | `SetWindowPos`, dock snap, z-order |
| `win32_client_capture` | client DC capture |
| `win32_input_constants` | VK constants |
| `config_parse` | parse registry values |
| `config_registry_load` / `save` / `query` | registry IO |
| `config_registry_extended` | extended keys |
| `config_registry_kill_counter` | KC keys |
| `config_registry_tables` | table schemas |
| `registry_config_snapshot` | hot snapshot for workers |
| `registry_snapshot_read` | read helpers |
| `registry_constants` | key names |
| `paths` | frozen-aware paths; **`PIPELA_SPLASH_IMAGE_PATH`** = `assets/splash.png` (optional splash image) |
| `image_registry` | load template images |
| `reload_sequence` | reload state machine pieces |
| `reload_nobullet_bullet` | nobullet/bullet helpers |
| `reload_idle_secondary` | idle score refresh |
| `ammo_restock_catalog` | ammo UI map |
| `ammo_restock_templates` | ammo template names |
| `call_merc_catalog` | merc UI map |
| `call_merc_match` | merc match helpers |
| `call_merc_templates` | merc template names |
| `flame_trigger_automation` | FT automation bits |
| `kill_counter_layout` | KC panel row keys |
| `kill_counter_tier_data` | Built-in rank/monster-kill thresholds (`KILL_COUNTER_RANK_*`), tier rows for UI |
| `kill_counter_tier_colors` | Honorific→foreground hex (`KILL_COUNTER_TIER_HONORIFIC_FG_HEX`), `kill_counter_honorific_key` |
| `region_dispatch` | ROI type dispatch |
| `scale_geometry` | `get_scale_ratio`, regions |
| `primary_monitor` | monitor dict |
| `display_timing` | `display_tick_ms` |
| `telemetry_metrics` | capture timing metrics |
| `profile_bootstrap` | extracted profiling/bootstrap helpers from `main.py` (`--profile-*`, tracemalloc, cProfile handoff, child profiler spawn) |
| `input_keymap` | extracted key conversion helper (`pynput_key_to_vk`) from `main.py` keyboard listener path |
| `app_state` | phase-3 state container + key index (`AppState`, `InputState`, `WorkerRuntimeState`, `KillCounterState`) |
| `console_log_constants` / `prefix` | terminal prefixes |
| `ui_fonts` | font stacks |
| `version_info` | `PIPELA_*_VERSION` |
| `ai_debug_session_log` | `PIPELA_AI_DEBUG` session files |
| `__init__` | package exports |

---

## 17. Profiling & troubleshooting

**One-shot for agents:** link **`profiling/agent_profile/`** only (or zip it). `README.txt` there lists expected filenames; cProfile also leaves timestamped `pipela_cprofile_*.stats` beside that folder.

| axis | tool | output / notes |
|------|------|----------------|
| CPU (deterministic hotspots) | cProfile | `.\tools\profile_pipela.ps1` → `agent_profile/summary.txt` + `agent_profile/cprofile.stats` (+ `profiling/pipela_cprofile_*.stats`) |
| Sampling / stutter-ish stacks | py-spy | `.\tools\profile_pipela_pyspy.ps1` → `agent_profile/pyspy.speedscope.json`. `-Svg` → second run → `agent_profile/pyspy.svg`. `pip install py-spy` |
| CPU + memory | Scalene | `.\tools\profile_pipela_scalene.ps1` → `agent_profile/scalene.json`. `-Html` → second run → `agent_profile/scalene.html`. `pip install scalene` |
| CPU (same as `python main.py`) | cProfile flag | **`python main.py --profile-agent`** or **`PIPELA_PROFILE_AGENT=1`** — on exit fills `profiling/agent_profile/` (no ps1 required) |
| CPU (direct) | | `python -m cProfile -o profiling\run.stats main.py` then `python tools\dump_cprofile_summary.py profiling\run.stats` → `profiling\agent_profile\summary.txt` by default |
| AI session log | `PIPELA_AI_DEBUG` | `%LOCALAPPDATA%\Pipela\ai_debug\session_*.log` — `pipela_core/ai_debug_session_log.py` (`PIPELA_AI_DEBUG=0` disables) |
| Kill dock (Qt/Win32 dock path) | **`PIPELA_DEBUG_KILL_DOCK`** | `1`/`true`/… — **`[KillDock][debug]`** on stderr (`pipela_qt/kill_counter_window.py`); pair with §15 `KILL_DOCK_RESOLUTION_TRANSITION`. |
| Splash off | **`PIPELA_NO_SPLASH`** | `1`/`true`/… — skip startup splash (`pipela_qt/splash_screen.py`). |
| UI stutter | scenarios | `docs/UI_STUTTER_REPRO_SCENARIOS.md` (S0–S5) |

**Diagnostics ladder (impl) — default off; no UI/layout/behavior change unless flag/env set:**

| Step | What | How (repo) |
|------|------|------------|
| cProfile | hotspots | `--profile-agent`, `PIPELA_PROFILE_AGENT=1`, `tools/profile_pipela.ps1` |
| py-spy | sampling | `--profile-pyspy`, or `tools/profile_pipela_pyspy.ps1` → `pyspy.speedscope.json` |
| Scalene | CPU+mem | `--profile-scalene`, or `profile_pipela_scalene.ps1` → `scalene.json` |
| tracemalloc | allocation top | **`PIPELA_TRACEMALLOC=1`** or **`--profile-tracemalloc`** → `tracemalloc_top.txt` |
| line_profiler | line hotspots | **`@builtins.profile`** on `PipelaApplication.notify` (identity stub in `main.py` when not kernprof); **`pip install kernprof line_profiler`** → **`tools/profile_kernprof_pipela.ps1`** → `line_profiler_notify.lprof`; text: `python -m line_profiler main.py profiling\agent_profile\line_profiler_notify.lprof` |
| Frame timing | notify wall | **`PIPELA_UI_FRAME_TIMING=1`** → `pipela_qt/frame_timing.py` → **`frame_timing.tsv`** on exit |
| Before/after diff | two runs | **`python tools/compare_agent_profile.py <before> <after>`** (path = `summary.txt` or `agent_profile/` dir) |
| Native stacks | WPR/WPA | **`tools/wpr_native_profile_hint.txt`** (no Pipela code) |
| Qt attach | GammaRay / Qt Creator | External install only |

Optional pip packages: **`requirements-profiling-extra.txt`**.

**Owner one-liner bundle** (then play once, quit, @ `profiling/agent_profile/`):

`Set-Location "<repo>"; .\tools\profile_pipela_bundle.ps1` — default uses **Scalene** when `pip install scalene` (single run: `scalene.json` + cProfile + TM + frame timing). `-PreferPySpy` swaps to py-spy speedscope; `-CProfileOnly` skips both.

**Agent rule:** New `--profile-*` / `PIPELA_*` diagnostics: one row here + `tools/profiling_agent_profile_README.txt`; keep shipped paths free of always-on probes.

**Impl note (2026-04-30):** `main.py` delegates profiling/bootstrap flows to **`pipela_core/profile_bootstrap.py`**. Keep CLI/env semantics identical there (`--profile-agent`, `--profile-pyspy`, `--profile-scalene`, `--profile-tracemalloc`, `PIPELA_PROFILE_AGENT`, `PIPELA_TRACEMALLOC`).

**Impl note (2026-04-30, Phase 3):** state migration is **bridged**: `_state_get/_state_set` in `main.py` mirrors selected globals into `pipela_core.app_state.AppState`. During transition, globals remain compatibility source for untouched paths.

**Deeper diagnostics (1–4 from agent guidance) — zero default UI/behavior impact:** Product UI and runtime paths **stay unchanged** unless an explicit flag/env or external tool session is used.

**Removed (2026-04):** `PIPELA_UI_PERF` / `ui_perf_probe`; KC hover JSONL (`PIPELA_KC_HOVER_PROFILE`). Use cProfile + scenarios instead.

**Removed (2026-04-30):** **`PIPELA_CURSOR_HUD`** (launch-time HUD disable via env); **`pipela_cursor_hud_enabled`** registry + settings toggle — HUD is always on (see §15 `HUD_ALWAYS_ON`).

---

## 18. DPI / docking (125% symptom)

**Symptom:** docked control width shrinks until invisible. **Cause:** mixing Qt logical width with Win32 physical coords. **Fix:** store `_dock_w` from `dock_panel_size()` where applicable; `win32_dpi_scale_for_hwnd`; `dock_outer_rect_touch_client_left` / `right` via **`pipela_qt/qt_side_dock.compute_side_dock_layout`**; `control_main._dock_to_anchor` / `_apply_computed_side_dock`; `kill_counter_window.dock_to_right_of_target_game`. **Grep** those symbols in `win32_window_ops` / `control_main`.

**Resolution transitions:** transient bad anchor rects can yield unusable layout — see **§15 `KILL_DOCK_RESOLUTION_TRANSITION`** and **`clamp_dock_logical_geometry`** in `qt_side_dock.py`.

---

## 19. Typography

- **Fonts:** `pipela_core/ui_fonts.py`, `pipela_qt.theme`; app default `qt_fonts.app_default_qfont`, `main_window.configure_app`. New panels should subscribe to pt refresh per **§8** Adaptive UI (`qt_typography_refresh`, `TypographyStyleBundle`).

---

## 20. Comments & locale policy

- Repo docs + comments target **agents**: dense English, `# AGENT:` prefix for new inline comments.
- `main.py`: many `#` comments migrated; **docstrings** / some branches still have Hangul — translate when you edit that symbol.
- `pipela_qt`: Hangul in **UI strings** — do not bulk-change without product intent; translate **comments** when touching files.

---


---

## 22. Other docs

| file | role |
|------|------|
| `AGENTS.md` | **Single agent doc** (this file). |
| `UpdateLog/update_log.md` | User-facing changelog (Korean). |
| `docs/UI_STUTTER_REPRO_SCENARIOS.md` | Stutter repro S0–S5 (see §17). Do not duplicate here. |

See also `pipela_qt/roadmap.py` → `roadmap.summary()`.

---

## 23. Paste stub (new chat) — see also §8

```
Read repo root AGENTS.md in full. `pipela_mod` = `_pipela_mod_for_qt()` (§10). Qt-only UI in pipela_qt/. MSS grab patch in pipela_core/vision_lazy.py. Update §9 session dashboard when done.
```
