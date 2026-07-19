"""AGENT: optional C++ core via pybind11 (auto when pipela_native.pyd present)."""

from __future__ import annotations

import os
from typing import Any

from pipela_core.native_module import import_native_module

_NATIVE: Any | None = None


def _env_flag(name: str) -> str:
    return os.environ.get(name, "").strip().lower()


def native_core_explicitly_disabled() -> bool:
    return _env_flag("PIPELA_NATIVE_CORE") in ("0", "false", "no", "off")


def native_core_enabled() -> bool:
    if native_core_explicitly_disabled():
        return False
    if _env_flag("PIPELA_NATIVE_CORE") in ("1", "true", "yes", "on"):
        return True
    return import_native_module() is not None


def load_native() -> Any | None:
    global _NATIVE
    if _NATIVE is not None:
        return _NATIVE
    if not native_core_enabled():
        return None
    _NATIVE = import_native_module()
    return _NATIVE


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
