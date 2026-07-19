# Pipela C++ migration

Incremental Python → Qt 6 C++ transition (`cpp/` tree).

## Docs (read in order)

1. **[`STATUS.md`](STATUS.md)** — **live worker/core progress** (update when porting)
2. [`README.md`](README.md) — build & runtime
3. [`parity_matrix.md`](parity_matrix.md) — module file map (auto-generated)
4. [`COMPLETE.md`](COMPLETE.md) — cutover gates

## Phase status (summary)

| Phase | Status |
|-------|--------|
| 0–1 | Done |
| 2 Workers | **In progress** — see [`STATUS.md`](STATUS.md) |
| 3 Native | Done |
| 4 UI | Scaffold |
| 5 Ship | Prep |

## Dev build

```powershell
.\scripts\build_native_core.bat      # pipela_native.pyd → repo root (PIPELA_ENABLE_OPENCV=ON)
.\scripts\build_cpp_release.bat      # Pipela.exe (Qt6)
```

## F5 (Python UI + C++ workers)

After `build_native_core.bat`, **no env vars** — `pipela_native.pyd` auto-starts C++ workers.

```powershell
$env:PIPELA_NATIVE_WORKERS = "0"   # force Python loops (debug)
```

## Parity harness

```powershell
python tools\export_registry_snapshot_keys.py
python tools\golden_registry_snapshot_diff.py
python tools\export_parity_matrix.py
```
