"""Opt-in cumulative timing samples for hot paths — default off (`PIPELA_UI_FRAME_TIMING` unset).

Writes `profiling/agent_profile/frame_timing.tsv` on interpreter exit via atexit.

# AGENT: no Qt dependency; keep guards O(1) when disabled.
"""

from __future__ import annotations

import atexit
import os
from collections import defaultdict
from pathlib import Path

_ENV_OK = frozenset({"1", "true", "yes"})
_enabled_cache: bool | None = None

# PipelaApplication.notify-only hot path uses append_notify_frame_timing_ns (constant label, no extra call depth).
_FT_LABEL_NOTIFY_TOTAL = "PipelaApplication.notify_total"


def _enabled_raw() -> str:
    return os.environ.get("PIPELA_UI_FRAME_TIMING", "").strip().lower()


def frame_timing_ui_enabled() -> bool:
    # Read env once — never changes at runtime here; avoids os.environ lookup per notify().
    global _enabled_cache
    if _enabled_cache is None:
        _enabled_cache = _enabled_raw() in _ENV_OK
    return bool(_enabled_cache)


_acc_ns: defaultdict[str, float] | None = None
_acc_counts: defaultdict[str, int] | None = None
_registered = False
# PipelaApplication.notify runs only on Qt main thread; accumulation has no concurrent writers.


def _flush_to_disk() -> None:
    global _acc_ns, _acc_counts
    if _acc_ns is None or _acc_counts is None:
        return
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "profiling" / "agent_profile"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "frame_timing.tsv"
        lines = ["label\tcalls\ttotal_ms\tavg_us"]
        items = sorted(_acc_ns.keys(), key=lambda k: (-_acc_ns[k], k))
        for k in items:
            n = float(_acc_counts[k])
            tot_ms = float(_acc_ns[k]) / 1e6
            avg_us = (_acc_ns[k] / n / 1000.0) if n > 0 else 0.0
            lines.append(f"{k}\t{int(_acc_counts[k])}\t{tot_ms:.6f}\t{avg_us:.3f}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _ensure_and_register() -> None:
    global _acc_ns, _acc_counts, _registered
    if _registered:
        return
    _registered = True
    _acc_ns = defaultdict(float)
    _acc_counts = defaultdict(int)
    atexit.register(_flush_to_disk)


def record_phase_ns(label: str, elapsed_ns: int) -> None:
    """Add one sample (nanoseconds) for label."""
    if not frame_timing_ui_enabled():
        return
    _accumulate_phase_ns(label, elapsed_ns)


def record_phase_ns_when_ui_timing_on(label: str, elapsed_ns: int) -> None:
    """Same as ``record_phase_ns`` but skips the enabled check — caller verified ``PIPELA_UI_FRAME_TIMING`` (hot path per-notify)."""
    _accumulate_phase_ns(label, elapsed_ns)


def _accumulate_phase_ns(label: str, elapsed_ns: int) -> None:
    _ensure_and_register()
    assert _acc_ns is not None and _acc_counts is not None
    _acc_ns[label] += float(elapsed_ns)
    _acc_counts[label] += 1


def append_notify_frame_timing_ns(elapsed_ns: int) -> None:
    """Notify timing only — inlined label; skips ``record_phase_ns`` wrappers (``PIPELA_UI_FRAME_TIMING`` on)."""
    _ensure_and_register()
    assert _acc_ns is not None and _acc_counts is not None
    k = _FT_LABEL_NOTIFY_TOTAL
    _acc_ns[k] += float(elapsed_ns)
    _acc_counts[k] += 1
