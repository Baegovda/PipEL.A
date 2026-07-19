"""AGENT: optional C++ worker runtime (PIPELA_NATIVE_WORKERS=1)."""

from __future__ import annotations

import atexit
import os
from typing import Any

_RUNTIME: Any | None = None
_STATE: Any | None = None


def native_workers_enabled() -> bool:
    v = os.environ.get("PIPELA_NATIVE_WORKERS", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def start_native_workers() -> bool:
    global _RUNTIME, _STATE
    if not native_workers_enabled():
        return False
    try:
        from pipela_core.native_bridge import load_native

        native = load_native()
        if native is None:
            return False
        _STATE = native.AppState()
        _STATE.seed_defaults()
        _RUNTIME = native.WorkerRuntime(_STATE)
        _RUNTIME.start_all()
        atexit.register(stop_native_workers)
        return True
    except Exception:
        return False


def stop_native_workers() -> None:
    global _RUNTIME, _STATE
    if _RUNTIME is not None:
        try:
            _RUNTIME.stop_all()
        except Exception:
            pass
    _RUNTIME = None
    _STATE = None
