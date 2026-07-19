"""AGENT: C++ AppState proxy for main.py when PIPELA_NATIVE_STATE=1."""

from __future__ import annotations

import os
from typing import Any

from pipela_core.native_bridge import load_native

_STATE: Any | None = None
_MISSING = object()


def native_state_enabled() -> bool:
    v = os.environ.get("PIPELA_NATIVE_STATE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def native_state_reads_enabled() -> bool:
    if native_state_enabled():
        return True
    try:
        from pipela_core.worker_runtime_bridge import native_workers_active

        return native_workers_active()
    except Exception:
        return False


def get_shared_native_state() -> Any | None:
    try:
        from pipela_core.worker_runtime_bridge import get_native_app_state

        shared = get_native_app_state()
        if shared is not None:
            return shared
    except Exception:
        pass
    return _state()


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
    st = get_shared_native_state()
    if st is None or not st.has(key):
        return default
    value = st.get(key)
    if value is None:
        return default
    return value


def state_set(key: str, value: Any) -> bool:
    st = get_shared_native_state()
    if st is None or not st.has(key):
        return False
    return bool(st.set(key, value))


def state_inc_int(key: str, delta: int = 1) -> int | None:
    st = get_shared_native_state()
    if st is None or not st.has(key):
        return None
    return int(st.increment_int(key, int(delta)))
