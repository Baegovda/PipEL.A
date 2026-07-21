# AGENT: Bootstrap prompt — PIPBONG-style governance for another repo

Copy everything below the line into a **new project's Cursor chat**.  
**Reference implementation (completed):** this repo (`Baegovda/PipEL.A`) — attach `@AGENTS.md`, `.cursor/rules/`, `scripts/`, `.vscode/` when transplanting.

---

# MISSION: Transplant PIPBONG-style AI governance to this project

You are restructuring this repository to match the **PIPBONG AI maintenance system** (reference: `Baegovda/PIPBONG` or completed `Baegovda/PipEL.A` / Pipela).

**Goal:** Not feature code — **file structure, policy, agent workflow, IDE settings, release procedure** in one pass.

---

## 0. Explore first (before code changes)

1. Read repo structure, build system, CI, existing docs.
2. Short audit: app name, version source, OS target, build commands, git remote/branch, UI vs code language, existing Cursor/VS Code config.
3. **Incremental transplant** — no large renames until governance is stable.

---

## 1. Core philosophy (mandatory)

| Principle | Content |
|-----------|---------|
| **Single master doc** | **`AGENTS.md` only** for dev/handover/changelog/build. Exception: root **`README.md`** = user landing. Merge/delete `HANDOVER.md`, duplicate `docs/dev.md`. |
| **100% AI-maintained** | Human directs in chat only. |
| **Language** | User chat: **Korean** (or project locale). Code/docs/rules/changelog: **English**. App UI: project locale. |
| **Immediate handover** | Infra/script/release/IDE changes → same-task `AGENTS.md` §3/§8/§9 — not changelog alone. |
| **Task close** | `[Unreleased]` → **version bump** → incremental build (if code) → push → GitHub Release (when shipping). |
| **Minimal diff** | No drive-by refactors during transplant. |

---

## 2. Target layout (adapt names to stack)

```
<repo-root>/
├── AGENTS.md
├── README.md
├── UpdateLog/update_log.md
├── scripts/
│   ├── build-common.ps1
│   ├── build-release.ps1      # AI sole build entry
│   ├── build-and-run.ps1      # F5: Start-Process exe
│   ├── recover-ide-build.ps1
│   ├── fix-<project>-cursor-f5.ps1
│   └── create-github-release.ps1
├── .vscode/                   # git tracked
│   ├── tasks.json
│   ├── launch.json            # configurations: []
│   └── settings.json          # cmake.enabled: false, <project>.f5BuildAndRun: true
└── .cursor/rules/
    ├── ai-governance.mdc
    ├── changelog-versioning.mdc
    ├── build-policy.mdc
    ├── ide-build-workflow.mdc
    ├── f5-build-and-run.mdc
    ├── no-full-rebuild.mdc
    └── immediate-handover.mdc
```

**C++/CMake:** also `CMakePresets.json`, `vcpkg.json`, `빌드.bat` → `build-release.ps1`.  
**npm/rust:** same *roles*, different commands — keep "one AI build script at task close".

---

## 3. AGENTS.md skeleton (required sections)

1. Project Overview  
2. Stack and Dependencies  
3. Build and Run (3.1 IDE, 3.2 no full rebuild, 3.6 GitHub, 3.7 UpdateLog)  
4. Repository Map  
5. Architecture  
6. UX Flows (if any)  
7. Data / JSON (if any)  
8. Critical patterns (§8.x + domain `.mdc`)  
9. Governance (9.5 User preference profile — cumulative, append-only)  
10. Versioning  
11. Changelog  
12. Risk/Legal (if any)  
13. Cursor Rules Summary  

---

## 4. IDE rules

- **Ctrl+Shift+B** → `scripts/build-release.ps1`
- **F5** → `workbench.action.tasks.test` → Build and Run → `Start-Process` (no CodeLLDB)
- **`launch.json`:** `"configurations": []`
- **CMake Tools:** all off if using scripted cmake
- **Recovery:** `recover-ide-build.ps1` + Reload Window

---

## 5. Execution phases

| Phase | Work |
|-------|------|
| **A** | `AGENTS.md` skeleton, `.cursor/rules/`, `UpdateLog/`, README trim |
| **B** | `scripts/`, `.vscode/`, `빌드.bat`, `fix-*-cursor-f5.ps1` |
| **C** | Fill §3/§8/§9/§10/§11/§13; delete duplicate docs |
| **D** | Verify incremental build + F5 + recover |
| **E** | Version bump, changelog, build, commit/push/release (if owner ships) |

---

## 6. Agent hard rules

| Do | Don't |
|----|-------|
| `build-release.ps1` at task close | `cmake --preset` when cache exists |
| `AGENTS.md` §11 during work | New `HANDOVER.md` |
| Same-task doc updates for infra | Procedures only in chat |
| Korean user replies | Korean in code comments |

---

## 7. Completion checklist (report all YES)

- [ ] `AGENTS.md` §1–§13 + Current version
- [ ] `.cursor/rules/` ≥7 alwaysApply
- [ ] `scripts/build-release.ps1`
- [ ] `.vscode/` tasks + empty launch + settings
- [ ] `UpdateLog/update_log.md`
- [ ] Duplicate dev docs removed
- [ ] Incremental build + F5 verified
- [ ] (If shipping) push + GitHub Release

---

## 8. Start now

1. Run Phase A from exploration audit.  
2. Substitute project name, exe path, remote URL.  
3. If Pipela files attached, use as reference — adapt paths, do not copy Win32/game-specific domain rules blindly.  
4. Report in Korean after each phase.  
5. Complete through Phase D; Phase E only when owner requests ship.

**User language:** Korean. **Code / AGENTS.md / rules:** English.

---

## Pipela fill-in example (for agents calibrating another repo)

| Token | Pipela value |
|-------|----------------|
| `f5BuildAndRun` key | `pipela.f5BuildAndRun` |
| `BUILD_DIR` | `cpp/build/release` |
| `EXE` | `cpp/build/release/src/app/Pipela.exe` |
| `CMAKE_PRESET` | `release` |
| Compliance doc | `docs/GOVERNANCE_CHECKLIST.md` |
