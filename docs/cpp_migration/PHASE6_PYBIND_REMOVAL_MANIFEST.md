# Phase 6 — Python / pybind removal manifest (AH4)

`AUDIENCE`: owner + agents. **Draft delete list** — apply only after [`AB_READINESS.md`](AB_READINESS.md) / Batch AG pass and [`PHASE6_ARCHIVE_BRANCH.md`](PHASE6_ARCHIVE_BRANCH.md) archive branch exists.

## Delete from `main` (Phase 6)

### Python application tree

| Path | Notes |
|------|-------|
| `main.py` | Legacy entry, globals, Python worker threads |
| `pipela_qt/` | Entire PyQt6 UI package |
| `pipela_core/` | Entire Python logic package (except migrate any remaining constants into C++ first) |
| `pipela_native.pyd` | Root hybrid bridge artifact |
| `requirements.txt` | Python runtime deps (keep `requirements-profiling-extra.txt` only if still needed for agent tooling — prefer delete) |
| `pyrightconfig.json` | Python IDE config |

### PyInstaller / legacy ship

| Path | Notes |
|------|-------|
| `Pipela.spec` | PyInstaller spec |
| `build.bat` | Primary PyInstaller path — replace with C++ release docs |
| `scripts/package_release.bat` | PyInstaller zip — superseded by `package_cpp_release.bat` |

### C++ pybind bridge

| Path | Notes |
|------|-------|
| `cpp/bindings/pybind/` | Entire pybind module (`module.cpp`, `CMakeLists.txt`) |
| `scripts/build_native_core.bat` | pyd build — remove or repurpose as core-only static lib build |
| `tools/parity/verify_native_workers.py` | pyd smoke — replace with exe-only harness |
| `tools/parity/compare_native_python_workers.py` | A/B compare — archive on branch only |

### Docs / launch configs to **update** (not delete)

| Path | Action |
|------|--------|
| `.vscode/launch.json` | Remove Python worker / hybrid configs; keep C++ exe only |
| `AGENTS.md` §7, §10, §11, §16 | Remove legacy rows; C++-only entry |
| `docs/cpp_migration/README.md` | Remove hybrid banner caveats |
| `version.json` | Bump 1.0.0 per [`drafts/version_1_0_0.json`](drafts/version_1_0_0.json) |

## Keep on `main` after Phase 6

| Path | Role |
|------|------|
| `cpp/` | Product source |
| `registry/schema.json` | HKCU schema |
| `assets/` | Icons, splash, template PNGs |
| `scripts/build_cpp_release.bat` | Ship build |
| `scripts/package_cpp_release.bat` | CPack zip |
| `scripts/verify_cutover_gates.ps1` | C++ exe gates |
| `docs/cpp_migration/` | Migration history (mark complete) |
| `tools/parity/run_worker_parity_preflight.py` | May slim to exe-only checks |

## CMake / vcpkg follow-up

- Remove pybind target from `cpp/CMakeLists.txt` and `cpp/bindings/`.
- Ensure `cpp/vcpkg.json` has no Python dev dependencies.
- `PIPELA_NATIVE_WORKERS` / `PIPELA_NATIVE_CORE` env vars — remove from docs and code paths.

## Verification after delete

```powershell
.\scripts\build_cpp_release.bat
.\scripts\verify_cutover_gates.ps1
# No python.exe on PATH:
cpp\build\release\src\app\Pipela.exe
```

## Agent rule

**Do not delete** any path in this manifest without owner explicit Phase 6 ship request.
