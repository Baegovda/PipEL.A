# PIPBONG-style governance — Pipela compliance checklist

`AUDIENCE`: agents verifying transplant completeness. Reference model: Baegovda/PIPBONG.

**Last audit:** 2026-07-21 — **all items YES** (Pipela is the reference implementation for C++/Qt).

| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Single master doc `AGENTS.md` (§1–§13) | YES | `AGENTS.md` |
| 2 | User landing `README.md` only (no duplicate dev docs) | YES | `README.md` |
| 3 | `.cursor/rules/` ≥7 alwaysApply policies | YES | 14 files |
| 4 | `scripts/build-release.ps1` — AI sole build entry | YES | `scripts/` |
| 5 | `scripts/build-and-run.ps1` — F5 path | YES | `scripts/` |
| 6 | `scripts/recover-ide-build.ps1` | YES | `scripts/` |
| 7 | `scripts/fix-cursor-f5.ps1` | YES | `scripts/` |
| 8 | `scripts/create-github-release.ps1` | YES | `scripts/` |
| 9 | `빌드.bat` → `build-release.ps1` | YES | repo root |
| 10 | `.vscode/tasks.json` (build + test default) | YES | `.vscode/` |
| 11 | `.vscode/launch.json` empty `configurations` | YES | `.vscode/` |
| 12 | CMake Tools disabled in settings | YES | `pipela.f5BuildAndRun` |
| 13 | `UpdateLog/update_log.md` (Korean) | YES | `UpdateLog/` |
| 14 | §9.5 User preference profile | YES | `AGENTS.md` |
| 15 | §11 `[Unreleased]` changelog discipline | YES | `AGENTS.md` |
| 16 | Bootstrap prompt for other repos | YES | `scripts/bootstrap-agent-governance-prompt.md` |
| 17 | Repo structure plan | YES | `docs/STRUCTURE.md` |

## Pipela-specific (not generic PIPBONG)

| Item | Status | Notes |
|------|--------|-------|
| C++ exe `cpp/build/release/src/app/Pipela.exe` | YES | Not CMake root `build/Release/` |
| Version triple sync | YES | `version.json`, `version.cpp`, legacy `version_info.py` |
| Python legacy tree | PENDING Phase 6 | Owner in-game A/B gate |
| `package_cpp_release.bat` | YES | Called from `create-github-release.ps1` |

## Re-verify after changes

```powershell
.\scripts\build-release.ps1          # ~3s no-change
.\scripts\build-and-run.ps1          # prints Started Pipela.exe
.\scripts\recover-ide-build.ps1      # dry-run OK
```

F5 must open **no** CodeLLDB tab — only terminal `Started Pipela.exe`.
