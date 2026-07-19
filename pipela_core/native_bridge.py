"""AGENT: optional C++ core via pybind11 (PIPELA_NATIVE_CORE=1)."""

from __future__ import annotations

import os
from typing import Any

_NATIVE: Any | None = None
_NATIVE_TRIED = False


def native_core_enabled() -> bool:
    v = os.environ.get("PIPELA_NATIVE_CORE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def load_native() -> Any | None:
    global _NATIVE, _NATIVE_TRIED
    if _NATIVE_TRIED:
        return _NATIVE
    _NATIVE_TRIED = True
    if not native_core_enabled():
        return None
    try:
        import pipela_native as native  # type: ignore[import-not-found]

        _NATIVE = native
        return _NATIVE
    except Exception:
        _NATIVE = None
        return None


def reg_parse_bool(val) -> bool | None:
    native = load_native()
    if native is None:
        return None
    try:
        return bool(native.parse_bool(str(val)))
    except Exception:
        return None


def clamp_match_threshold_01(v: float) -> float | None:
    native = load_native()
    if native is None:
        return None
    try:
        return float(native.clamp_match_threshold(float(v)))
    except Exception:
        return None


def match_template_ccoeff_normed_max(screen: Any, template: Any) -> tuple[float, Any] | None:
    """Return (max_val, (x,y)) or None when native unavailable / invalid."""
    native = load_native()
    if native is None or screen is None or template is None:
        return None
    try:
        if screen.shape[0] < template.shape[0] or screen.shape[1] < template.shape[1]:
            return 0.0, None
        sstride = int(screen.strides[0])
        tstride = int(template.strides[0])
        result = native.match_template_ccoeff_normed_max(
            screen.tobytes(),
            int(screen.shape[1]),
            int(screen.shape[0]),
            sstride,
            template.tobytes(),
            int(template.shape[1]),
            int(template.shape[0]),
            tstride,
        )
        if not result.valid:
            return 0.0, None
        return float(result.score), (int(result.top_left_x), int(result.top_left_y))
    except Exception:
        return None
