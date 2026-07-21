# AGENTS.md — Pipela Master Document

**Current version:** `0.10.18` (`version.json`, `pipela_core/version_info.py`, `cpp/src/core/version.cpp`)

Sole development document for agents and maintainers. Exception: `README.md` (user landing). Append changelog to §11 `[Unreleased]` **while implementing**; **task close** = version triple bump + dated changelog + incremental build (§10) — not “ship day only”.

Governance compliance: [`docs/GOVERNANCE_CHECKLIST.md`](docs/GOVERNANCE_CHECKLIST.md). Bootstrap prompt for other repos: [`scripts/bootstrap-agent-governance-prompt.md`](scripts/bootstrap-agent-governance-prompt.md).

**Always-applied rules (must match this doc):** `.cursor/rules/changelog-versioning.mdc`, `build-policy.mdc`, `ai-governance.mdc`.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Stack and Dependencies](#2-stack-and-dependencies)
3. [Build and Run](#3-build-and-run)
4. [Repository Map](#4-repository-map)
5. [Architecture and Key Subsystems](#5-architecture-and-key-subsystems)
6. [UX Flows](#6-ux-flows)
7. [Data / JSON Format](#7-data--json-format)
8. [Critical Implementation Patterns](#8-critical-implementation-patterns)
9. [Development Governance](#9-development-governance)
10. [Versioning Policy](#10-versioning-policy)
11. [Changelog and Version History](#11-changelog-and-version-history)
12. [Risk and Legal Notices](#12-risk-and-legal-notices)
13. [Cursor Rules Summary](#13-cursor-rules-summary)

---

## 1. Project Overview

**Pipela** is a Windows game-assist automation tool (template matching, workers, docked Qt UI beside game/launcher HWND). **100% AI-maintained**; owner directs in **Korean chat only**.

| Fact | Detail |
|------|--------|
| **Ship target** | `Pipela.exe` (Qt6 C++) + native DLLs — **no** permanent Python/PyInstaller product |
| **Remote** | `https://github.com/Baegovda/PipEL.A` branch `main` |
| **Owner in-game QA** | [`docs/cpp_migration/오너_가이드.md`](docs/cpp_migration/오너_가이드.md) |
| **Migration status** | C++ ~97% — see [`docs/cpp_migration/PROGRESS.md`](docs/cpp_migration/PROGRESS.md) |

**Risk:** Automation interacts with live game input and screen capture — test on Windows with owner checklist after overlay/input changes.

---

## 2. Stack and Dependencies

| Layer | Technology |
|-------|------------|
| Product UI | Qt6 (`cpp/src/app/`), C++17, Ninja, MSVC 2022 |
| Core logic | `cpp/src/core/` (no Qt) |
| Native | `pipela_input_hooks.dll`, `cursor_hud_dcomp.dll` (DComp HUD) |
| Vision | OpenCV, vcpkg (`cpp/vcpkg.json`), MSS capture patch in legacy `pipela_core/vision_lazy.py` |
| Legacy (temporary) | `main.py`, `pipela_qt/`, `pipela_native.pyd` — parity/cutover only |
| Build tree | **Single:** `cpp/build/release` |
| Package | `scripts/package_cpp_release.bat` → `dist/Pipela-cpp-<ver>-win64.zip` |

---

## 3. Build and Run

### 3.1 IDE / Cursor build workflow (mandatory)

| Action | Command |
|--------|---------|
| Human build | **Ctrl+Shift+B**, `빌드.bat`, or `.\scripts\build-release.ps1` |
| AI task close | `.\scripts\build-release.ps1` **only** when `cpp/**`, headers, or `cpp/CMakeLists.txt` changed |
| F5 / Run | Default test task → `scripts/build-and-run.ps1` (`Start-Process`, no debugger) |
| First configure | `build-release.ps1` runs `cmake --preset release` **only** when `cpp/build/release/CMakeCache.txt` missing |
| Recovery | `.\scripts\recover-ide-build.ps1` then **Developer: Reload Window** |
| One-time setup | `.\scripts\ensure-dev-isolation.ps1` |

Tracked `.vscode/`: `tasks.json`, `settings.json` (`pipela.f5BuildAndRun: true`), `launch.json` (empty `configurations`), `keybindings.json` (F5 → test task).

### 3.2 No full rebuild / vcpkg lock prevention (mandatory)

| Failure | Cause |
|---------|--------|
| 10–30 min build | `cmake --preset` re-runs vcpkg while another configure holds `vcpkg-running.lock` |
| Exit -1 / task already running | Parallel CMake Tools + terminal cmake |

| Who | Build | First configure | Recovery |
|-----|-------|-----------------|----------|
| Human | Ctrl+Shift+B / `build-release.ps1` | Automatic when `CMakeCache.txt` missing | `recover-ide-build.ps1` |
| AI | `build-release.ps1` **only** | Never `cmake --preset` if `cpp/build/release/` exists | Same |

**AI hard bans** when `cpp/build/release/CMakeCache.txt` exists: `cmake --preset`, raw `cmake --build`, parallel configure, second build tree, re-enabling CMake Tools for F5.

**Timings:** no-change ~3s; one `.cpp` ~5–15s. If >2 min with no new vcpkg dep: stop → recover → Reload Window.

### 3.3 During implementation vs task close

| Phase | Rule |
|-------|------|
| **During** | Edit sources; append §11 `[Unreleased]` bullets. **No** version bump mid-task unless owner asks. **No** `build-release.ps1` unless owner says build or you are closing the task. |
| **Task close** (every completed user-facing task) | **(1)** Patch-bump version triple (§7). **(2)** Move `[Unreleased]` → dated §11 section; empty `[Unreleased]`. **(3)** `UpdateLog/update_log.md` if user-visible. **(4)** `build-release.ps1` if `cpp/**` / version sources changed. **(5)** Update **Current version** line at top of this file + §9 session dashboard. |
| **Git push + GitHub Release** | Only when owner requests backup/ship (§9.3) — **not** optional when you bumped version **and** owner asked to release. |

**Incremental build:** F5 / `build-and-run.ps1` / `build-release.ps1` all use `cpp/build/release/` cache — changed `.cpp` only (~3–15s). Never `cmake --preset` when `CMakeCache.txt` exists (§3.2).

### 3.4 Legacy / auxiliary scripts

| Script | When |
|--------|------|
| `scripts/build_native_core.bat` | `cpp/bindings/**` — once per task |
| `scripts/run_golden_cpp_tests.bat` | Core logic changed |
| `build.bat` / `scripts/build_release.bat` | PyInstaller ship (legacy bundle) |
| `native/cursor_hud_dcomp/build_dcomp.bat` | Native HUD C++ changed (shim → `cpp/src/native/hud_dcomp/`) |

### 3.5 Constants (incremental build)

| Token | Pipela value |
|-------|----------------|
| `CMAKE_TARGET` | `Pipela` |
| `CMAKE_PRESET` | `release` |
| `BUILD_DIR` | `cpp/build/release` |
| `EXE` | `cpp/build/release/src/app/Pipela.exe` |
| `SOURCE_DIR_CACHE_KEY` | `CMAKE_HOME_DIRECTORY` → `…/Pipela/cpp` |
| `USES_VCPKG` | `true` |

### 3.6 GitHub backup and release

| Step | Action |
|------|--------|
| Backup | `git add` → `commit` → `push origin main` (when owner requests or version-bump ship) |
| Release | `.\scripts\create-github-release.ps1` — packages zip + `gh release create` |

| Owner phrase (Korean) | AI action |
|-------------------------|-----------|
| 백업해줘 | commit + push `main` |
| 릴리즈 해줘 | `create-github-release.ps1` |
| 백업하고 릴리즈까지 | push + `create-github-release.ps1` |

Update `version.json` `download_url` / `release_url` to match tag before release.

### 3.7 User-facing update log

[`UpdateLog/update_log.md`](UpdateLog/update_log.md) — Korean, patch-decade blocks, UI terms only (no file names).

---

## 4. Repository Map

| Path | Role |
|------|------|
| `cpp/src/app/` | Qt6 UI, overlays, shell, panels |
| `cpp/src/core/` | Workers, registry, vision, Win32 (no Qt) |
| `cpp/src/native/` | Input hooks, DComp wrapper |
| `cpp/CMakePresets.json` | Preset `release` → `build/release` |
| `scripts/build-release.ps1` | **Sole daily C++ build entry** |
| `scripts/build-common.ps1` | Shared incremental helpers |
| `cpp/src/native/hud_dcomp/` | DComp HUD DLL source (canonical) |
| `native/cursor_hud_dcomp/` | Shim `build_dcomp.bat` only — see `docs/STRUCTURE.md` |
| `main.py`, `pipela_qt/` | Legacy Python UI (cutover) |
| `pipela_core/` | Legacy pure Python + shared paths |
| `assets/` | Icons, templates, splash |
| `docs/cpp_migration/` | Migration roadmap, owner in-game QA |
| `docs/STRUCTURE.md` | Repo simplification plan |
| `docs/GOVERNANCE_CHECKLIST.md` | PIPBONG-style compliance audit |
| `.cursor/rules/` | Always-on agent policies |

---

## 5. Architecture and Key Subsystems

| Area | Entry / module |
|------|----------------|
| **C++ product entry** | `cpp/src/app/main.cpp` → `Application` |
| **Legacy entry** | `main.py` → `main_qt()` → `pipela_qt.shell` |
| **Workers** | `cpp/src/core/workers/*` (+ legacy `main.py` loops) |
| **Dock / phase** | `dock_ui_phase`, `side_dock_layout`, `dock_chrome_controller` |
| **Title strip** | `title_strip_window`, `title_strip_geometry` |
| **Kill counter** | `kill_counter_window`, `kill_counter_panel`, OCR worker |
| **Template capture** | `template_overlay_controller`, `DragOverlayBase`, `capture_freeze_frame` |
| **Cursor HUD** | `cursor_hud_controller` + DComp DLL (always on) |
| **Registry** | `cpp/src/core/registry/store.cpp` — WCHAR UTF-8 |
| **State** | `AppState` in `cpp/src/core/state/` |

**Product direction:** Shipped Pipela is **C++ only**. Do not extend Python for new features. See [`docs/cpp_migration/PHASE6_PYTHON_DELETE.md`](docs/cpp_migration/PHASE6_PYTHON_DELETE.md).

---

## 6. UX Flows

| Flow | Notes |
|------|-------|
| **F5 dev run** | Build + `Pipela.exe` with `PIPELA_DEV_UI=1` |
| **Dock phases** | `client` / `launcher` / `standby` — `get_ui_dock_phase` |
| **Launcher debug** | Title-strip checkbox `pipela_launcher_debug_chrome` — dock control+KC beside launcher |
| **Settings** | Hub → panel factory; card dialogs via `card_popup_shell` |
| **Terminal log** | 3-queue fade, HTML rows — `terminal_log_widget` |
| **In-game QA** | Owner checklist 10 features — [`오너_가이드.md`](docs/cpp_migration/오너_가이드.md) |

---

## 7. Data / JSON Format

| Artifact | Role |
|----------|------|
| `version.json` | In-app update manifest on `main` |
| `cpp/src/core/registry/schema.json` | Registry key schema |
| KC stats JSON | `stats_store` — buckets, reload marks |
| Registry keys | English; UI strings Korean |

**Version sync (mandatory on bump):** `version.json`, `pipela_core/version_info.py` (`PIPELA_APP_VERSION`, `PIPELA_STRIP_DISPLAY_VERSION`), `cpp/src/core/version.cpp`.

---

## 8. Critical Implementation Patterns

### 8.1 MSS capture — no CAPTUREBLT

`pipela_core/vision_lazy.py` patches `mss` to **SRCCOPY only** — prevents cursor flicker. Never re-add CAPTUREBLT without re-test.

### 8.2 DPI / docking

Never mix Qt logical width with Win32 physical coords. Use `compute_side_dock_layout`, `clamp_dock_logical_geometry`. See `WINDOW_Z_ORDER_AND_LAYOUT.md`.

### 8.3 Kill dock resolution transition

Resolution change may transiently break anchor rects — `PIPELA_DEBUG_KILL_DOCK=1` for stderr `[KillDock][debug]`.

### 8.4 DComp cursor HUD

Default ON. `PIPELA_CURSOR_HUD_DCOMP=0` disables. DLL: `native/cursor_hud_dcomp/build_dcomp.bat`.

### 8.5 Qt changeEvent + QSS

No `setStyleSheet` from `changeEvent(StyleChange)`. See `.cursor/rules/qt-changeevent-stylesheet.mdc`.

### 8.6 Region overlay teardown

Overlay → capture sync → host restore → modal. See `.cursor/rules/screen-capture-overlay.mdc`.

### 8.7 Physical keyboard

Do not release user-held modifiers at workflow end. See `.cursor/rules/physical-keyboard-preservation.mdc`.

### 8.8 Profiling (optional)

`PIPELA_PROFILE_AGENT=1`, `profiling/agent_profile/` — `tools/profiling/profile_pipela_bundle.ps1`.

---

## 9. Development Governance

### 9.1 Language

| Audience | Language |
|----------|----------|
| Owner chat | Korean |
| Code, comments, agent docs, changelog | English (`# AGENT:` on new inline notes) |
| In-app UI | Korean — no bulk change without product intent |

### 9.2 Coding discipline

- Minimal diff; no drive-by refactors.
- Match surrounding style; reuse helpers.
- Tests only when requested or high-value.
- Run UX checklist after overlay/capture/modal changes.

### 9.2.1 Proactive defect remediation (mandatory)

When an agent **finds a clear bug** during the current task (logs, code review, repro, parity gap) — **fix it in the same session without asking the owner per issue**. Do **not** end with “want me to fix X?” lists.

| Do | Do not |
|----|--------|
| Fix root cause; keep diff scoped to the defect + shared helper if needed | Wait for approval on each obvious follow-up fix |
| Note fixes in Korean task close (“로그에서 RH 합성 클릭 오인식 → … 수정함”) | Ask “고칠까요?” for bugs you already diagnosed |
| Ask owner only when fix is **ambiguous product choice** or **large scope** (new subsystem, breaking UX) | Treat optional polish as mandatory without signal |

Diagnostics (`feature_trace.log`, `PIPELA_*`, terminal) exist so agents **act**, then **report**.

### 9.2.2 Version bump at task close (mandatory — no exceptions for user-visible work)

**Before the final reply** on any completed user-facing task, agents **must** patch-bump the version triple (§10) and move `[Unreleased]` → dated §11. **Do not** end the session with `Current version` stale or a non-empty `[Unreleased]` pile.

| Trigger | Action |
|---------|--------|
| C++ / UI / worker / input behavior changed | **Patch bump** same task, same session |
| Docs/governance only | `[Unreleased]` bullet only — no bump |
| Owner says “버전 올려” / ship | Bump + build + commit/push/release **when owner asks** |

**Failure mode (owner anti-pattern):** shipping multiple tasks while `version.json` still says `0.10.2`. If you closed a user-visible task without bumping → **bump immediately** on next message before any other work.

### 9.3 Git

- Commit/push when owner requests **or** version-bump ship per §10.
- No force-push `main`; no git config changes.

### 9.4 Session dashboard

| Key | Value |
|-----|--------|
| `LAST_TASK` | **v0.10.18** — Auto-update: manifest poll, zip download/extract, in-place replace+restart; settings toggle + interval; main-window update button. |
| `OPEN_RISKS` | Owner in-game A/B pending (`오너_가이드.md`). |
| `TODO` | — |
| `LAST_UPDATE` | 2026-07-21 |

### 9.5 User preference profile (cumulative — agents only)

**Status:** Added 2026-07-21. Not user-facing release notes unless preference changes in-app UI.

**Purpose:** Cumulative record of the human director’s **work style**, **collaboration habits**, **UI/aesthetic taste**, and **technical leanings** so every agent session starts aligned without chat history.

#### Work style (append dated bullets)

- **2026-07-21 — Proactive fix:** Clear bugs found during work (logs, trace, code) → agent fixes immediately; reports in close summary. No per-bug “fix this?” prompts. See §9.2.1.

#### Recording policy (mandatory)

| Rule | Detail |
| ---- | ------ |
| **Where** | **This section only** in `AGENTS.md` — **no** separate preference/style files |
| **When** | Same task when user states or clearly implies preference, habit, aesthetic, or anti-preference |
| **How** | **Append** dated bullet under best subsection — **never delete** prior bullets |
| **Task start** | Skim §9.5 before UI, docs, agent workflow, architecture |
| **Task close** | New preference signal in chat but not in §9.5 → append before close |
| **Cursor rules** | Always-applied **pointer only** in `ai-governance.mdc` / `immediate-handover.mdc`; **full text stays in §9.5** |

#### Work and collaboration style

- **2026-07-21:** Directs work in **Korean**; expects **100% AI-maintained** codebase (implement, document, changelog via agent).
- **2026-07-21:** Prefers agent **end-to-end execution** — not “copy step 3 yourself” checklists.
- **2026-07-21:** Wants **PIPBONG-style governance** portable to other repos — single copy-paste bootstrap prompt (`scripts/bootstrap-agent-governance-prompt.md`).
- **2026-07-21:** Daily operator path: **F5** / `빌드.bat` / `build-release.ps1` — minimal terminal ceremony.

#### UI, visual, and aesthetic

- **2026-07-21:** Wants polish **in C++ Qt** without unnecessary stack migration — improve in place (`cpp/src/app/`).
- **2026-07-21:** Favors **compact, scannable** dense UI — short labels, chips, less redundant wording in tables.
- **2026-07-21:** Prefers **subtle** feedback (soft borders, restrained motion) over loud/neon unless feature demands attention.
- **2026-07-21:** Launcher debug chrome: control + KC beside launcher, but **natural panel height (~740px)** — not squashed to short launcher client height.

#### Technical and architecture preferences

- **2026-07-21:** **Incremental builds only** — `.\scripts\build-release.ps1` at task close; no full configure when `cpp/build/release/CMakeCache.txt` exists (see §3).
- **2026-07-21:** **Version bump every completed user-facing task** — patch + triple sync (`version.json`, `version_info.py`, `version.cpp`) at task close; git push/release only when owner asks (§10). Agents must not defer bump to “release day only”.
- **2026-07-21:** **Single master handover doc** (`AGENTS.md`) — procedures in same task, not “document later”.
- **2026-07-21:** **Minimal diffs**; reuse existing abstractions; no drive-by refactors.
- **2026-07-21:** **Ship target** C++ `Pipela.exe` only; Python `main.py` / PyQt6 = legacy parity, not new features.

#### Anti-preferences (explicit don’ts)

- **2026-07-21:** Do **not** create separate preference memo files (`USER_STYLE.md`, `PREFERENCES.md`, etc.) outside `AGENTS.md`.
- **2026-07-21:** Do **not** tell user to manually copy policy fragments the agent could write to the repo.
- **2026-07-21:** Do **not** re-enable CMake Tools / raw `cmake --preset` for daily F5 or agent builds.
- **2026-07-21:** Do **not** finish user-visible tasks without **patch version bump** — owner expects version to rise every ship (`§9.2.2`, `changelog-versioning.mdc`).

---

## 10. Versioning Policy

| Bump | When |
|------|------|
| **Patch** | **Every completed user-facing task** (default) — see `changelog-versioning.mdc` |
| **Minor** | New subsystem / milestone |
| **Major** | Breaking settings format, 1.0 |

**Docs-only / governance-only** (no user-visible behavior): `[Unreleased]` bullet only — **no** version bump until next user-visible close.

**Task close checklist (mandatory for user-visible work):**

1. Bump **all** version sources (§7): `version.json`, `pipela_core/version_info.py`, `cpp/src/core/version.cpp` (default **patch**).
2. Move `[Unreleased]` → `## [x.y.z] - YYYY-MM-DD` in §11; leave `[Unreleased]` empty.
3. `UpdateLog/update_log.md` Korean bullets when users care.
4. `build-release.ps1` if `cpp/**` or version files changed (incremental — §3.2).
5. Update **Current version** at top of `AGENTS.md` + §9 `LAST_TASK` / `LAST_UPDATE`.
6. **Commit + push + `create-github-release.ps1`** — when owner requests ship/backup; mandatory when shipping a bumped version to users (§9.3).

**Do not:** leave `[Unreleased]` piling up across many tasks while `Current version` stays stale. **Do not:** tell owner “version only on release day” — bump at **task close**; release is separate step 6.

---

## 11. Changelog and Version History

### [Unreleased]

_Empty — ship next changes here._

### [0.10.18] - 2026-07-21

#### Added
- Auto-update system — periodic manifest check (default 10 min), zip download via WinHTTP, PowerShell extract, xcopy in-place replace + relaunch (`update/installer.cpp`, `update/update_controller.cpp`).
- Settings → 업데이트: 자동 업데이트 ON/OFF, 확인 주기(5–60분), 버전 확인 / 지금 업데이트.
- Main control window bottom: **업데이트** button left of **종료**.

### [0.10.17] - 2026-07-21

#### Fixed
- Flame Trigger — mouse center snap + `ClipCursor` lock failed because C++ `mouseMove` used broken `SendInput` absolute coords; now uses `SetCursorPos` like Python (`input_synth.cpp`). Clip applied immediately on FT session start (`flame_trigger_worker.cpp`).

### [0.10.16] - 2026-07-21

#### Changed
- Kill counter panel — modern layout: hero card (session kills + 1h/6h/24h/KPH chips), left-accent section headers, stacked tier/choin goal blocks, prominent lap timer + primary/ghost buttons, compact footer (`kill_counter_panel.cpp`, `theme_engine.cpp`).
- Kill counter window chrome + ROI toolbar — theme-aligned QSS (`kill_counter_window.cpp`, `kill_counter_region_toolbar.cpp`).

### [0.10.15] - 2026-07-21

#### Fixed
- Title strip min/max/close buttons — global `QPushButton` QSS no longer applied app-wide; scoped to control shell (`#pipelaControlRoot`); strip caption button QSS reinforced (`theme_engine.cpp`, `app_shell_styles.cpp`, `title_strip_styles.cpp`).

### [0.10.14] - 2026-07-21

#### Fixed
- Kill counter dock — height pinned to anchor client inner (no overflow below client); Qt geometry uses layout logical coords instead of corner DPI re-rounding; apply-path dedupe + 2px client-rect hysteresis (`dock_chrome_apply.cpp`, `side_dock_layout.cpp`, `dock_chrome_controller.cpp`).
- Kill counter panel — debounced resize layout + typography refresh only on meaningful viewport scale change (`kill_counter_panel.cpp`).

### [0.10.13] - 2026-07-21

#### Added
- C++ `theme_engine` — unified design tokens from `pipela_theme.json`, global interaction QSS, palette (`theme_engine.cpp`, `theme_tokens.cpp`).

#### Changed
- Full UI renewal — control shell, segmented pill tabs, action grid glass, settings hub/chrome, title strip, terminal log (left-aligned console), card popups, kill counter panel (`app_shell_styles`, `control_tab_chrome`, `paired_control_tab_bar`, `action_grid_widget`, `settings_chrome`, `title_strip_styles`, `terminal_log_*`, `card_popup_shell`, `kill_counter_panel`).

### [0.10.12] - 2026-07-21

#### Changed
- Settings hub category UI — replaced broken 2-col breadcrumb grid with single-column category list (`기능` / `기타` sections), simple `← 제목 →` header (`settings_hub.cpp`, `app_shell_styles.cpp`).

### [0.10.11] - 2026-07-21

#### Changed
- Global UI center alignment — `settings_chrome` centered page/field/checkbox helpers; settings panels, action grid, terminal log, KC section titles, settings hub breadcrumb, quit button (`settings_chrome.cpp`, `control_main_window.cpp`, settings panels).

### [0.10.10] - 2026-07-21

#### Changed
- Terminal log — rewritten as conventional read-only `QPlainTextEdit` console (monospace append, colored tags, auto-scroll); removed per-row QLabel fade/height animation and archive/fading queues (`terminal_log_widget.cpp`, `terminal_log_html.cpp`, `control_main_window.cpp`).

### [0.10.9] - 2026-07-21

#### Changed
- Settings numeric fields — drag-scrub rework: `grabMouse` during scrub, defer text selection until click-without-drag, Shift/Ctrl sensitivity; `DragSpinBox` on registry prefix + template threshold; font pt 2-notch wheel + pre-step highlight (`drag_spin_box.cpp`, `registry_prefix_panel.cpp`, `template_probe_section.cpp`, `dedicated_panels.cpp`).

### [0.10.8] - 2026-07-21

#### Fixed
- Title strip briefly under game title bar on client/Pipela focus switch — `EVENT_SYSTEM_FOREGROUND` monitor + `reassertZOrder(true)` on activation; Z restack bypasses 12ms throttle when forced; strip `SW_SHOWNA` lift (`foreground_monitor.cpp`, `title_strip_window.cpp`, `application.cpp`, `dock_z_stack.cpp`).

### [0.10.7] - 2026-07-21

#### Changed
- Cursor icon HUD — hook-thread immediate `setPosition` (coalesced Qt sync for icons/visibility); native `hud_set_position` moves DComp visual only (no full redraw per move); `Present(0)` (`cursor_hud_controller.cpp`, `hooks_bridge.cpp`, `cursor_hud_dcomp.cpp`).

### [0.10.6] - 2026-07-21

#### Fixed
- LeftClick activation micro-stutter and unreliable OFF toggle — process LMB on hook thread (not Qt queue); `MOUSE_CLICK_IGNORE` 48ms→4ms; classify synth via `LLMHF_INJECTED` only; removed `suppress_off_until_release` (`left_click_controller.cpp`, `hooks_bridge.cpp`, `input_synth.cpp`).

### [0.10.5] - 2026-07-21

#### Fixed
- Kill counter floater taller than game client — dock height policy `ClientInnerOnly`, shared `applySideDockLayoutToWidget` / `applySideDockLayoutWithHeightCap` (`side_dock_layout.cpp`, `dock_chrome_apply.cpp`, `kill_counter_window.cpp`, `dock_chrome_controller.cpp`, `overlay_placeholders.cpp`). Golden test: `kill_counter_height_never_exceeds_client_inner`.

### [0.10.4] - 2026-07-21

#### Fixed
- Call Merc action button — `CallMercCooldownButton` never received `setText`; `mercActionCaption()` + `refreshActionCaptions` now set label (cycle count when >0).

### [0.10.3] - 2026-07-21

#### Added
- Feature trace **deep profiling** — default depth `deep`; `+mono_ms` thread tags; `AppState::set` auto-log; per-worker `WorkerLoopTracer` (skip throttle + events); vision match scores; synth input detail; runtime snapshots (`feature_trace_log.cpp`, `worker_loop_trace.cpp`, all workers). Env: `PIPELA_FEATURE_TRACE=0` off, `PIPELA_FEATURE_TRACE_DEPTH=normal|verbose|deep`.
- `AGENTS.md` §9.2.1 Proactive defect remediation — agents fix clear bugs same session without per-issue owner approval; report in close summary (`ai-governance.mdc` pointer).
- `AGENTS.md` §9.5 User preference profile (cumulative): append-only director work/UI/technical preferences in master doc only; agents skim at task start (`ai-governance.mdc`, `immediate-handover.mdc`).
- Interface settings — **게임 창 화면 중앙 정렬** toggle (`game_window_center_on_detect_enabled`); 400ms timer + `centerOuterWindowOnMonitorWorkArea`; **off** → title strip drag moves game/launcher HWND; strip left edge uses dock layout so it spans control panel (`application.cpp`, `title_strip_window.cpp`, `window_ops.cpp`).

#### Changed
- Control panel footer — removed duplicate phase/resolution/dock status (title strip only); bottom row is **종료** only (`control_main_window.cpp`).
- Terminal log readability — wider time column, chip/body `·` separator, looser row spacing and 11pt body (`terminal_log_html.cpp`, `terminal_log_widget.cpp`).
- All `QPushButton` labels — global `text-align: center` (`app_shell_styles.cpp`); action grid glass buttons, settings breadcrumb/nav, template toolbar, kill-counter panels/toolbars, capture confirm (`action_grid_widget.cpp`, `control_tab_chrome.cpp`, …).
- Terminal log max line cap — registry `console_log_max_lines` (default 500, 100–5000); settings **콘솔** panel spin; trim oldest archive/fading/memory rows (`console_log_retention.hpp`, `control_main_window.cpp`, `dedicated_panels.cpp`; Python registry parity).
- Terminal log — modern compact layout: semantic color chips per feature, highlighted ON/OFF, friendly Korean messages, slimmer time prefix, refined scroll chrome (`terminal_log_html.cpp`, `terminal_log_widget.cpp`, `hooks_bridge.cpp`, `control_main_window.cpp`).
- Control main window — **종료** button moved from top-right to bottom of the panel (`control_main_window.cpp`).
- PIPBONG governance audit — `docs/GOVERNANCE_CHECKLIST.md`, `scripts/bootstrap-agent-governance-prompt.md`, `README.md` C++ ship landing, `AGENTS.md` TOC + dead link fix.
- Repo structure Phase A — `docs/STRUCTURE.md`; `tools/` reorganized (`codegen/`, `parity/`, `profiling/`, `dev/`); removed duplicate migration docs + native HUD source; `cpp/src/app/CMakeLists.txt` uses `GLOB` for `.cpp` sources.
- Template capture storage — **file-only** PNG under `%LOCALAPPDATA%\\Pipela\\templates\\`; no base64 `*_image_data` registry writes on capture (`apply.cpp`, `worker_context`, workers, `template_probe_test`).
- Template thumb load — OpenCV path loader + unified `path_resolve` (fixes Qt `QPixmap` PNG load failure / "로드 실패" with valid files).

#### Fixed
- RightHold / Flame Trigger — synthetic right/middle mouse (`LLMHF_INJECTED` + `synthIgnoreRight`) no longer toggle features during LeftClick auto-click (`hooks_bridge.cpp` `isSyntheticMouseEvent`).
- LeftClick immediate OFF — new `LeftClickController` (`left_click_controller.cpp`); classify `LLMHF_INJECTED` hook flags + 48ms synth guard; `suppress_off_until_release` after hold-to-arm; feature trace log (`feature_trace_log.cpp` → `%LOCALAPPDATA%/Pipela/feature_trace.log`).
- LeftClick / RightHold — synthetic mouse events no longer toggle features off immediately: atomic `synthIgnoreLeft`/`synthIgnoreRight` in `input_synth.cpp`, hook parity with Python `ignore_left`/`ignore_right` + delayed LC off-arm (`hooks_bridge.cpp`).
- Kill counter dock height flicker — match game client inner height (Python `compute_side_dock_layout` parity); drop C++-only `dockPanelTopPhys` offset; keep Qt/Win32 outer height in sync after clamp (`side_dock_layout.cpp`, `kill_counter_window.cpp`, `dock_chrome_controller.cpp`).
- Start Game action button — stay visible after launcher→client phase; latch `start_game_launcher_active` on transition (`action_grid_widget.cpp`).
- Start Game launcher template capture — fix flaky capture entry (`refreshSmartUpdaterHwndCached(0)` throttle returned HWND 0); cache launcher HWND in `application.cpp`; confirm dialog topmost + centered on launcher; dual registry path key + thumb reload (`game_windows.cpp`, `template_capture_*`, `apply.cpp`, `template_probe_section.cpp`).
- Launcher title-strip vertical mask — extend strip upward (~12px+ DPI-scaled) so launcher native title bar does not bleed through Pipela top bar (`title_strip_geometry.cpp`).
- Launcher debug dock — control + KC use natural **740px** panel height instead of squashing to launcher client height (`dock_chrome_controller`, `overlay_placeholders`).
- Template/ROI drag capture — `grabMouse` + clamped coords, top-level overlay window, DPI-correct `cropBgrFromDragRect`, fixed `getClientRectScreen` corner mapping; confirm dialog raised with focus (`drag_overlay_base.cpp`, `capture.cpp`, `game_windows.cpp`, `template_capture_overlay.cpp`).
- **Capture subsystem rewrite** — `overlays/capture/` (`CaptureOverlayService`, `CaptureOverlayView`, `capture_session`, `capture_confirm_card`, `region_preview_view`); single drag instance, modern chrome (dim hole, bracket handles, size badge, hint bar), `CardFramelessDialog` confirm; removed legacy `drag_overlay_base`, `template_capture_overlay`, `region_select_overlay`, `template_capture_confirm`, `capture_freeze_frame`, `region_preview_overlay`.
- Start Game worker terminal logs — `WorkerContext::loopLog` → UI queue; step logs `① Launcher` / `② Intro skip` / `③ Accept` with spacing (`start_game_launcher_worker.cpp`, `application.cpp`, `terminal_log_html.cpp`).

### [0.10.2] - 2026-07-21

#### Added
- Full AI governance transplant: 14 `.cursor/rules/*.mdc` (`ai-governance`, `changelog-versioning`, `immediate-handover`, build/F5/dual-cursor, UX/Qt/input/overlay domain rules).
- `scripts/create-github-release.ps1`, `fix-cursor-f5.ps1`, `ensure-dev-isolation.ps1`.
- `AGENTS.md` restructured as single master document (§1–§13).

#### Changed
- Replaced legacy `pipela-governance.mdc` and prior build-only rules with PIPBONG policy set.
- F5 daily path: empty `launch.json`, `pipela.f5BuildAndRun`, test task → `build-and-run.ps1`.

### [0.10.1] - 2026-07-20

- Added: PIPBONG incremental build (`build-common.ps1`, `build-release.ps1`, `build-and-run.ps1`, `recover-ide-build.ps1`, `빌드.bat`).
- Added: Launcher title-strip **디버그** checkbox (`pipela_launcher_debug_chrome`).

### [0.10.0] - 2026-07-20

- C++ migration batches through AS — KC chart, drag spin boxes, splash PNG, connector arrows, tray polish; perfect **97%**. See git history for full bullets.

### [0.9.13] - 2026-07-20

- Unified `AGENTS.md`; F5 dev workflow; assets consolidation.

### [0.9.12] - 2026-04-30

- Baseline before unified handbook.

---

## 12. Risk and Legal Notices

Pipela automates game input and screen reading. Owner is responsible for compliance with game ToS and local law. No warranty. Diagnostic builds may log to `%LOCALAPPDATA%\Pipela\` when env flags set.

---

## 13. Cursor Rules Summary

| Rule file | Purpose |
|-----------|---------|
| `ai-governance.mdc` | Ownership, language, task-close; **read/append §9.5** user preference profile |
| `changelog-versioning.mdc` | `[Unreleased]` + version bump steps |
| `immediate-handover.mdc` | Same-task `AGENTS.md` ops updates |
| `no-full-rebuild.mdc` | No preset when cache exists |
| `build-policy.mdc` | Close-out incremental build |
| `ide-build-workflow.mdc` | Ctrl+Shift+B / tasks, CMake Tools off |
| `f5-build-and-run.mdc` | F5 → test task, `Started Pipela.exe` |
| `dual-cursor-isolation.mdc` | Parallel Cursor windows, vcpkg lock wait |
| `ux-regression-checklist.mdc` | Overlay/capture/modal manual checks |
| `qt-changeevent-stylesheet.mdc` | No QSS from `changeEvent` |
| `physical-keyboard-preservation.mdc` | User modifier preservation |
| `screen-capture-overlay.mdc` | Region pick teardown order |
| `drag-adjust-numeric-input.mdc` | `DragSpinBox` default |
| `program-settings-dialog.mdc` | QGroupBox + tooltips |

**Paste stub (new chat):**

```
Read AGENTS.md (skim §9.5). C++ build: .\scripts\build-release.ps1 only. F5: build-and-run. Update §9 session dashboard when done.
```
