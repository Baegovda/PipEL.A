# AGENT: Python runtime cutover checklist (Phase 5)

When C++ `Pipela.exe` reaches feature parity:

1. Tag `archive/python-0.9.x` branch with final Python release.
2. Bump `version.json` + `pipela_core/version_info.py` to **1.0.0** (ship).
3. Replace PyInstaller `build.bat` primary path with `build_cpp.bat` + `scripts/package_cpp_release.bat`.
4. Update `AGENTS.md` entry point to `cpp/src/ui/app/main.cpp`.
5. Remove `pipela_qt/`, `main.py` workers (or move to `archive/`).

Until then, **Python remains the production entry** (`main.py` / F5).
