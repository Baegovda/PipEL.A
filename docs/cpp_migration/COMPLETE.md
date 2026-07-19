# Pipela C++ migration — completion checklist

Migration phases 0–5 infrastructure is in `cpp/`. **Python remains the default production entry** until parity sign-off.

## Run C++ app (dev)

```powershell
$env:VCPKG_ROOT = "C:\path\to\vcpkg"
.\scripts\build_cpp_release.bat
.\cpp\build\cpp-release\src\ui\Pipela.exe
```

## Run Python app with C++ workers/core

```powershell
.\scripts\build_native_core.bat
# F5 main.py — auto when pipela_native.pyd is present (no env vars)
# Opt-out: $env:PIPELA_NATIVE_WORKERS = "0"
```

## Phase status

| Phase | Status |
|-------|--------|
| 0 Foundation | Done |
| 1 Core | Done |
| 2 Workers | 10/10 C++ loops; OCR via pybind; field parity 🟡 |
| 3 Native | DComp C++ wrapper + input_hooks DLL |
| 4 UI | Qt6 shell + `PIPELA_QT_NATIVE=1`; control_main parity TBD |
| 5 Ship | CPack zip script; Python cutover when parity met |

## Cutover gate (before removing Python)

- [x] All 10 workers have C++ implementations (parity testing ongoing)
- [ ] Full Qt UI visual parity (S0–S5)
- [ ] Registry/settings round-trip
- [ ] DComp HUD + dock resolution transitions
- [ ] Single `Pipela.exe` zip replaces PyInstaller

**Do not release/push until owner approves cutover.**
