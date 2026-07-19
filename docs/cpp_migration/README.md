# Pipela C++ migration

Incremental Python → Qt 6 C++ transition (`cpp/` tree).

## Phase status (local — not released until full cutover)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Foundation | Done | CMake, schema, parity matrix, golden tests |
| 1 Core | Done | AppState, tier data, registry JSON, win32 capture, native bridge |
| 2 Workers | **Scaffold+loops** | 10 worker threads, input synth, registry context; FSM/OCR TBD |
| 3 Native | Done | DComp C++ wrapper, `pipela_input_hooks` DLL |
| 4 UI | **Scaffold** | Qt6 shell, tray, theme JSON, control tabs |
| 5 Ship | **Prep** | `build_cpp_release.bat`, CPack; Python still default entry |

See `docs/cpp_migration/COMPLETE.md` for cutover gates.

## Dev build

```powershell
.\scripts\build_native_core.bat      # pipela_native.pyd
.\scripts\build_cpp_release.bat      # Pipela.exe (Qt6)
```

## Python + native workers

```powershell
$env:PIPELA_NATIVE_CORE = "1"
$env:PIPELA_NATIVE_WORKERS = "1"
# F5 main.py — C++ workers replace Python loops
```
