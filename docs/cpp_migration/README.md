# Pipela C++ migration

Incremental Python → Qt 6 C++ transition (`cpp/` tree). Master plan: Cursor plan *Pipela C++ Migration* (do not edit plan file in-repo).

## Layout

| Path | Role |
|------|------|
| `cpp/CMakeLists.txt` | Root CMake (core, pybind, Qt app, tests, native HUD) |
| `cpp/vcpkg.json` | qtbase (widgets), opencv4, pybind11 |
| `cpp/src/core/` | `libpipela_core` — registry, state, vision, win32 dock, workers |
| `cpp/bindings/pybind/` | `pipela_native` module (transitional) |
| `cpp/src/ui/` | Qt6 `Pipela.exe` scaffold |
| `cpp/src/native/` | Wraps `native/cursor_hud_dcomp/` |
| `cpp/tests/golden/` | Catch2 unit/golden tests |
| `registry/schema.json` | Exported registry key schema |
| `docs/cpp_migration/parity_matrix.md` | Python ↔ C++ module map |

## Dev build (Windows)

```powershell
cd cpp
cmake --preset dev -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"
cmake --build --preset dev
ctest --preset dev
```

Or from repo root:

```powershell
.\build_cpp.bat
```

## Python bridge (Phase 1+)

Set `PIPELA_NATIVE_CORE=1` and ensure `pipela_native.pyd` is on `PYTHONPATH` (CMake pybind output dir). Python falls back to pure logic when the module is absent.

## Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Foundation | Done | CMake, schema, parity matrix, golden tests |
| 1 Core | Scaffold | Registry parse/store, AppState, vision hook, pybind |
| 2 Workers | Scaffold | `WorkerRuntime` 10 idle loops; full logic TBD |
| 3 Native | Done | HUD via CMake `add_subdirectory` |
| 4 UI | Scaffold | Qt6 shell + theme tokens |
| 5 Ship | Scaffold | `build_cpp.bat`, package script; Python retained until cutover |

## Regenerate artifacts

```powershell
python tools/export_registry_schema.py
python tools/export_parity_matrix.py
python tools/golden_registry_diff.py
```
