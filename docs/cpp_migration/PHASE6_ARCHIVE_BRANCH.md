# Phase 6 — archive branch procedure (AH2)

`AUDIENCE`: owner + agents. **Do not execute** until Batch AG (owner in-game A/B) is complete per [`PARITY_RESULTS.md`](PARITY_RESULTS.md).

## Purpose

Preserve the last Python+hybrid runtime on a named branch before deleting `main.py`, `pipela_qt/`, `pipela_core/`, and pybind from `main`.

## Preconditions

- [ ] All 10 workers `pass` in [`PARITY_RESULTS.md`](PARITY_RESULTS.md)
- [ ] UI S0–S3 agent/owner rows green
- [ ] `cpp/build/release/src/app/Pipela.exe` runs without Python on PATH
- [ ] Owner approves **1.0.0** ship

## Procedure

### 1. Freeze current `main`

```powershell
git checkout main
git pull origin main
git status   # clean or only intentional ship commits
```

### 2. Create archive branch from current HEAD

```powershell
git branch archive/python-0.10.x
git push origin archive/python-0.10.x
```

Use the actual last Python-shipped version tag if different (e.g. `archive/python-0.9.x`).

### 3. Tag the archive (optional but recommended)

```powershell
git tag archive/python-0.10.x-final
git push origin archive/python-0.10.x-final
```

### 4. Return to `main` for Phase 6 delete

```powershell
git checkout main
```

Apply deletes per [`PHASE6_PYBIND_REMOVAL_MANIFEST.md`](PHASE6_PYBIND_REMOVAL_MANIFEST.md) on `main` only.

## What stays on the archive branch

| Path | Role |
|------|------|
| `main.py` | Legacy entry + Python workers |
| `pipela_qt/` | PyQt6 UI |
| `pipela_core/` | Python logic |
| `cpp/bindings/pybind/` | `pipela_native.pyd` build |
| `Pipela.spec` / `build.bat` | PyInstaller ship path |
| `requirements.txt` | Python deps |

## What `main` becomes after Phase 6

- Entry: `cpp/src/app/main.cpp` → `Pipela.exe`
- Build: `scripts/build_cpp_release.bat` + `scripts/package_cpp_release.bat`
- Docs: `AGENTS.md` §10 — remove `LEGACY_*` rows (owner applies per [`PHASE6_PYTHON_DELETE.md`](PHASE6_PYTHON_DELETE.md))

## Agent rule

Agents **must not** create the archive branch or delete Python without explicit owner ship request in chat.
