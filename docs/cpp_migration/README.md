# Pipela C++ migration

Incremental Python → Qt 6 C++ transition (`cpp/` tree).

## Phase status (local — not released until full cutover)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Foundation | Done | CMake, schema, parity matrix, golden tests |
| 1 Core | Done | AppState, tier data, registry JSON, win32 capture, native bridge |
| 2 Workers | **Deepening (local)** | ride/hp_refill/reload capture+match+input; auto native when `.pyd` built |
| 3 Native | Done | DComp C++ wrapper, `pipela_input_hooks` DLL |
| 4 UI | **Scaffold** | Qt6 shell, tray, theme JSON, control tabs |
| 5 Ship | **Prep** | CPack zip script; Python cutover when parity met |

See `docs/cpp_migration/COMPLETE.md` for cutover gates.

## Dev build

```powershell
.\scripts\build_native_core.bat      # pipela_native.pyd → repo root (PIPELA_ENABLE_OPENCV=ON)
.\scripts\build_cpp_release.bat      # Pipela.exe (Qt6)
```

## Python + native workers (F5)

**No env vars required** after `build_native_core.bat` — `pipela_native.pyd` beside `main.py` auto-starts C++ workers and skips Python loops.

```powershell
# Optional overrides
$env:PIPELA_NATIVE_WORKERS = "0"   # force Python loops (debug)
$env:PIPELA_NATIVE_WORKERS = "1"   # force native (error if pyd missing)
$env:PIPELA_NATIVE_STATE = "1"     # optional; auto-shared when native workers on
```

## Parity harness

```powershell
python tools\export_registry_snapshot_keys.py
python tools\golden_registry_snapshot_diff.py
```
