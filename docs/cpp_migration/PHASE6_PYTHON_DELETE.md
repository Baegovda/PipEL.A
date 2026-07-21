# Phase 6 — Python cutover checklist (owner executes)

`AUDIENCE`: owner. **Do not run until** [`PARITY_RESULTS.md`](PARITY_RESULTS.md) in-game A/B is complete.

## C++ readiness snapshot (agents — update each batch)

| Area | C++ status | Notes |
|------|--------------|-------|
| Entry / shell | Done | `cpp/src/app/main.cpp` → `Pipela.exe` |
| Workers (10 loops) | Done | `pipela_core/workers/*` |
| Qt UI | Done (~99%) | Batches V–AF; agent PARITY pass |
| Native HUD / hooks | Done | DComp + `pipela_input_hooks` |
| Build / package | Done | `scripts/build_cpp_release.bat`, `package_cpp_release.bat` |
| Phase 6 docs | Done | [`PHASE6_ARCHIVE_BRANCH.md`](PHASE6_ARCHIVE_BRANCH.md), [`PHASE6_PYBIND_REMOVAL_MANIFEST.md`](PHASE6_PYBIND_REMOVAL_MANIFEST.md) |
| In-game A/B | **Pending** | Owner gate — [`AB_READINESS.md`](AB_READINESS.md) |
| Python delete | **Blocked** | owner explicit ship request only |

## Preconditions

- [ ] All workers `pass` in `PARITY_RESULTS.md` (owner — [`AB_READINESS.md`](AB_READINESS.md))
- [x] UI S0–S3 agent pass ([`PARITY_RESULTS.md`](PARITY_RESULTS.md))
- [ ] `cpp/build/release/src/app/Pipela.exe` runs without Python on PATH (owner verify at ship)
- [ ] Owner approves **1.0.0** ship (draft: [`drafts/version_1_0_0.json`](drafts/version_1_0_0.json))

## Cutover steps

1. Tag `archive/python-0.10.x` on current `main` — see [`PHASE6_ARCHIVE_BRANCH.md`](PHASE6_ARCHIVE_BRANCH.md).
2. Delete per [`PHASE6_PYBIND_REMOVAL_MANIFEST.md`](PHASE6_PYBIND_REMOVAL_MANIFEST.md):
   - `main.py`, `pipela_qt/`, `pipela_core/`
   - `pipela_native.pyd`, `cpp/bindings/pybind/`
   - PyInstaller `build.bat` primary path
3. Update `AGENTS.md` §10 — remove `LEGACY_*` rows; entry = `cpp/src/app/main.cpp`.
4. Bump version **1.0.0** in `version.json` + `pipela_core/version_info.py` (or C++ `version.cpp` only after Python removed).
5. `scripts/build_cpp_release.bat` + `scripts/package_cpp_release.bat` + GitHub Release.

## Agent rule

Agents **must not** delete the Python tree without explicit owner ship request in chat.
