"""AGENT: C++ AppState proxy for main.py when PIPELA_NATIVE_STATE=1."""

from __future__ import annotations

import os
from typing import Any

from pipela_core.native_bridge import load_native

_STATE: Any | None = None


def native_state_enabled() -> bool:
    v = os.environ.get("PIPELA_NATIVE_STATE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _state() -> Any | None:
    global _STATE
    if _STATE is not None:
        return _STATE
    if not native_state_enabled():
        return None
    native = load_native()
    if native is None:
        return None
    _STATE = native.AppState()
    _STATE.seed_from_defaults()
    return _STATE


def state_get(key: str, default: Any = None) -> Any:
    st = _state()
    if st is None or not st.has(key):
        return default
    # pybind getters not fully wired — fallback to default for now.
    return default


def state_set(key: str, value: Any) -> bool:
    st = _state()
    if st is None or not st.has(key):
        return False
    return False
