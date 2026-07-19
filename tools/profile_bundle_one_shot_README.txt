Bundle one-shot (owner)
========================

PowerShell — repo root:

  Set-Location "c:\Users\Revaptor_FX\Pipela"
  .\tools\profile_pipela_bundle.ps1

Optional:  pip install scalene
  (bundle: pip install -r requirements-profiling-extra.txt)

One play → quit normally → hand off folder only:

  profiling\agent_profile\

Expected (with Scalene installed, default path):
  scalene.json           — CPU + memory (same run)
  summary.txt, cprofile.stats — cProfile
  tracemalloc_top.txt
  frame_timing.tsv

If Scalene missing, script uses py-spy (if installed) or plain cProfile+extras.

If Qt control window / tray never appear (Scalene + Qt can conflict on Windows):

  .\tools\profile_pipela_bundle.ps1 -PreferPySpy
  (same as -Gui)

Prefer speedscope only:  .\tools\profile_pipela_bundle.ps1 -PreferPySpy
Minimal:  .\tools\profile_pipela_bundle.ps1 -CProfileOnly

Native Windows: tools\wpr_native_profile_hint.txt
Line hotspots (separate): .\tools\profile_kernprof_pipela.ps1

Agent: read all artifact text/JSON here; optimize without changing Hangul UI strings unless asked.
