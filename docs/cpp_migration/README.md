# Pipela C++ migration

> **오너:** 게임 검수는 **[`오너_가이드.md`](오너_가이드.md)** 한 파일만.

> **Agents:** Product = `Pipela.exe` only. Repo layout: [`../STRUCTURE.md`](../STRUCTURE.md).

## Docs (living)

| Who | Read |
|-----|------|
| **Owner** | [`오너_가이드.md`](오너_가이드.md) |
| Agents | [`PROGRESS.md`](PROGRESS.md), [`GAP_AUDIT.md`](GAP_AUDIT.md), [`FILE_MAP.md`](FILE_MAP.md) |
| Ship | [`PHASE6_PYTHON_DELETE.md`](PHASE6_PYTHON_DELETE.md) |

## Metrics

| | Current |
|---|---------|
| Implementation | **99%** |
| Perfect replacement | **97%** (owner in-game A/B pending) |

Details: [`PROGRESS.md`](PROGRESS.md).

## Dev build

```powershell
.\scripts\setup_vcpkg.ps1          # once
.\scripts\build-release.ps1        # or F5 task "Build Release"
.\scripts\build-and-run.ps1        # run Pipela.exe
```

After `cpp/src/app/**` edits: incremental build task or `build-release.ps1`.

## Parity / CI

```powershell
python tools\parity\run_worker_parity_preflight.py
python tools\codegen\export_parity_matrix.py
```

## Removed docs (2026-07-21)

Consolidated into `PROGRESS.md` + Phase 6 docs: `STATUS.md`, `COMPLETE.md`, `ROADMAP.md`, `POST_OT_88PCT_ROADMAP.md`, `WORKER_PARITY_CHECKLIST.md`, `PHASE5_CUTOVER.md`.

## Python legacy

`main.py`, `pipela_qt/`, `pipela_core/` remain for Phase 6 archive delete — **not** F5 default. See [`PHASE6_PYBIND_REMOVAL_MANIFEST.md`](PHASE6_PYBIND_REMOVAL_MANIFEST.md).
