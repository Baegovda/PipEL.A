# Pipela tools

Agent/CI utilities. **Owner daily path:** F5 → `scripts/build-and-run.ps1` (not these).

## Layout

| Folder | Scripts | When |
|--------|---------|------|
| **(root)** | `cpp_ui_smoke.ps1` | C++ UI smoke after `cpp/` edits |
| **codegen/** | `export_*.py` | Regenerate C++ tier data, registry schema, parity matrix, theme tokens |
| **parity/** | `golden_*.py`, `run_worker_parity_preflight.py`, `verify_native_workers.py`, … | Pre-ship / CI parity gates |
| **profiling/** | `profile_pipela*.ps1`, `dump_cprofile_summary.py`, … | Agent diagnostics only |
| **dev/** | `pipela_dev_prepare.ps1`, `resolve_python_dev_paths.py` | Legacy Python venv (Phase 6 delete) |

## Common commands

```powershell
# C++ smoke (from repo root)
.\tools\cpp_ui_smoke.ps1

# Parity preflight (hybrid era — slim after Phase 6)
python tools\parity\run_worker_parity_preflight.py

# Regenerate kill-counter tier C++
python tools\codegen\export_kill_counter_tier_cpp.py

# Regenerate parity matrix doc
python tools\codegen\export_parity_matrix.py
```

See `docs/STRUCTURE.md` for repo-wide simplification plan.
