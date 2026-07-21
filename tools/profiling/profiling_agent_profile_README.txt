Pipela profiling — handoff folder
===================================

**Easiest — everything in one play (recommended):**

  .\tools\profile_pipela_bundle.ps1

(from repo root PowerShell). Optional: pip install py-spy  (pip install -r requirements-profiling-extra.txt)

---

Link ONLY this folder for the coding agent (Cursor @ mention: profiling/agent_profile), or zip it.

Files you may see (depends which tools you ran):
  summary.txt           — cProfile text (read this first for hotspots)
  cprofile.stats        — binary stats for python -m pstats
  pyspy.speedscope.json — py-spy (--profile-pyspy on main.py or profile_pipela_pyspy.ps1)
  pyspy.svg             — optional second py-spy pass (-Svg on ps1)
  scalene.json          — Scalene (--profile-scalene on main.py or profile_pipela_scalene.ps1)
  scalene.html          — scalene.ps1 -Html (second run)
  tracemalloc_top.txt   — PIPELA_TRACEMALLOC=1 or --profile-tracemalloc
  frame_timing.tsv      — PIPELA_UI_FRAME_TIMING=1 (notify timing)
  line_profiler_notify.lprof — tools/profile_kernprof_pipela.ps1 (kernprof; pip install kernprof line_profiler)
  cprofile_dump_error.txt / cprofile_handoff_fatal.txt / cprofile_dump_subproc_error.txt — only on failure

Single command (main.py, no extra ps1):
  python main.py --profile-agent
  python main.py --profile-pyspy              (needs: pip install py-spy)
  python main.py --profile-scalene          (needs: pip install scalene)
  set PIPELA_PROFILE_AGENT=1  &&  python main.py
  set PIPELA_TRACEMALLOC=1     &&  python main.py
  set PIPELA_UI_FRAME_TIMING=1 && python main.py

Optional dev deps: pip install -r requirements-profiling-extra.txt

Compare two runs (unified diff):
  python tools/compare_agent_profile.py <before_dir_or_summary.txt> <after_dir_or_summary.txt>

kernprof line hotspots (notify):
  pip install kernprof line_profiler
  .\tools\profile_kernprof_pipela.ps1
  python -m line_profiler main.py profiling\agent_profile\line_profiler_notify.lprof

Native Windows stacks (no app code):
  see tools/wpr_native_profile_hint.txt

Legacy ps1 (same folder):
  .\tools\profile_pipela.ps1
  .\tools\profile_pipela_pyspy.ps1
  .\tools\profile_pipela_scalene.ps1
