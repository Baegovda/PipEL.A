# Pipela repository structure — simplification plan

`AUDIENCE`: owner + agents. Living map of what to keep, merge, or delete.

## Current product (ship target)

| Path | Role | Files (approx.) |
|------|------|-----------------|
| `cpp/src/app/` | Qt 6 UI, shell, overlays, panels | ~166 |
| `cpp/src/core/` | Logic, workers, registry, vision | ~83 |
| `cpp/src/native/` | DComp HUD + input hooks DLLs | ~10 |
| `assets/` | Icons, splash, bundled PNGs | ~28 |
| `scripts/` | Build, package, verify (owner F5 path) | ~22 |
| `registry/` | HKCU schema JSON | 2 |
| `AGENTS.md` | Single agent handbook | 1 |

**Entry:** `cpp/src/app/main.cpp` → `Pipela.exe` (F5 / `scripts/build-and-run.ps1`).

## Legacy (Phase 6 delete — owner gate)

| Path | Role | Action |
|------|------|--------|
| `main.py` | Python monolith entry | Delete after in-game A/B pass |
| `pipela_qt/` | PyQt6 UI (82 modules) | Delete with Phase 6 |
| `pipela_core/` | Python core (57 modules) | Delete with Phase 6 |
| `cpp/bindings/pybind/` | Hybrid `pipela_native.pyd` | Delete with Phase 6 |
| `Pipela.spec`, `build.bat` | PyInstaller | Delete with Phase 6 |

**Rule:** Agents do **not** delete Python without owner explicit ship request (`docs/cpp_migration/PHASE6_PYTHON_DELETE.md`).

## Tooling layout (after 2026-07-21 reorg)

```
tools/
  README.md              # index
  cpp_ui_smoke.ps1       # frequent — stays at root
  codegen/               # export_* generators → C++ / docs
  parity/                # golden tests, worker preflight, A/B harness
  profiling/             # cProfile, py-spy, scalene (agent-only)
  dev/                   # venv prepare, python path helpers
```

## Native HUD (single source)

| Canonical | Shim |
|-----------|------|
| `cpp/src/native/hud_dcomp/` | `native/cursor_hud_dcomp/build_dcomp.bat` → calls canonical `build.bat` |

Do not edit duplicate `.cpp` under `native/cursor_hud_dcomp/` (removed).

## Docs (after 2026-07-21 reorg)

| Keep | Role |
|------|------|
| `docs/STRUCTURE.md` | This file |
| `docs/cpp_migration/README.md` | Migration index |
| `docs/cpp_migration/PROGRESS.md` | Metrics + last delta |
| `docs/cpp_migration/GAP_AUDIT.md` | Open gaps |
| `docs/cpp_migration/FILE_MAP.md` | Python → C++ map |
| `docs/cpp_migration/ARCHITECTURE.md` | C++ tree layout |
| `docs/cpp_migration/오너_가이드.md` | Owner in-game checklist |
| `docs/cpp_migration/parity_matrix.md` | Generated parity table |
| `docs/cpp_migration/PHASE6_*.md` | Ship / delete checklists |

Removed stubs/duplicates: `STATUS.md`, `COMPLETE.md`, `ROADMAP.md`, `POST_OT_88PCT_ROADMAP.md`, `WORKER_PARITY_CHECKLIST.md`, `PHASE5_CUTOVER.md` (content → `PROGRESS.md` + Phase 6 docs).

## C++ file-count reduction (future — optional)

| Idea | Risk | Benefit |
|------|------|---------|
| `file(GLOB …)` in `app/CMakeLists.txt` | Low | No manual `.cpp` list |
| Domain subfolders (`overlays/template/`) | Medium | Clearer navigation |
| Merge tiny `.hpp`/`.cpp` pairs | High | Fewer files; larger units |
| Pimpl for overlays | High | Hide Qt in `.cpp` only |

**Done 2026-07-21:** CMake GLOB for `cpp/src/app/*.cpp` (no per-file list).

## Artifact hygiene (gitignored)

- `cpp/build/`, `native/cursor_hud_dcomp/build/`, `build/`, `dist/`, `.venv/`
- `pipela_native*.pyd`, root `Qt6*.dll`, `opencv_*.dll`

## Execution phases

| Phase | Status | Scope |
|-------|--------|-------|
| **A** | Done 2026-07-21 | Docs trim, tools reorg, native dedupe, CMake GLOB, gitignore |
| **B** | Owner gate | Delete Python tree (Phase 6) |
| **C** | Optional | C++ overlay/widget domain subfolders |
| **D** | Optional | Collapse `pipela_core`-style flat `core/` headers into fewer modules |

## Net effect (Phase A)

- **Docs:** 18 → 12 migration files (−33%)
- **tools/:** flat 27 → 4 buckets + index
- **native/:** duplicate C++ source removed; shim-only folder
- **CMake:** ~80-line source list → GLOB block

After Phase B (Python delete): tracked product surface **~45% smaller** (144 Python files + pybind + PyInstaller scripts).
