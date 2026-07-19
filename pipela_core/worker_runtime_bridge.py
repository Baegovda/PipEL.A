"""AGENT: optional C++ worker runtime (PIPELA_NATIVE_WORKERS=1)."""

from __future__ import annotations

import atexit
import os
from dataclasses import fields
from typing import Any, Mapping

from pipela_core.app_state import InputState, KillCounterState, WorkerRuntimeState

_RUNTIME: Any | None = None
_STATE: Any | None = None
_NATIVE_WORKERS_ACTIVE = False


def native_workers_enabled() -> bool:
    v = os.environ.get("PIPELA_NATIVE_WORKERS", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def native_workers_active() -> bool:
    return _NATIVE_WORKERS_ACTIVE


def get_native_app_state() -> Any | None:
    return _STATE


def _install_snapshot_provider(native: Any) -> None:
    from pipela_core.registry_config_snapshot import get_registry_config_snapshot

    def _provider() -> dict[str, Any]:
        snap = get_registry_config_snapshot()
        out: dict[str, Any] = {}
        for key, value in snap.items():
            if value is None:
                continue
            out[str(key)] = value
        return out

    native.set_snapshot_provider(_provider)


def _install_template_bgr_loader(native: Any) -> None:
    import numpy as np
    from pipela_core.image_registry import load_image_from_registry

    def _loader(registry_key: str):
        img = load_image_from_registry(registry_key)
        if img is None:
            return None
        arr = np.ascontiguousarray(img)
        h, w = arr.shape[:2]
        return (bytes(arr), int(w), int(h))

    native.set_template_bgr_loader(_loader)


def _seed_native_state_from_globals(module_globals: Mapping[str, Any] | None) -> None:
    if _STATE is None or module_globals is None:
        return
    for group in (InputState, WorkerRuntimeState, KillCounterState):
        for field in fields(group):
            key = field.name
            if key not in module_globals or not _STATE.has(key):
                continue
            _STATE.set(key, module_globals[key])


def start_native_workers(module_globals: Mapping[str, Any] | None = None) -> bool:
    global _RUNTIME, _STATE, _NATIVE_WORKERS_ACTIVE
    if not native_workers_enabled():
        return False
    try:
        from pipela_core.native_bridge import load_native

        native = load_native()
        if native is None:
            return False
        _STATE = native.AppState()
        _STATE.seed_from_defaults()
        _seed_native_state_from_globals(module_globals)
        _install_snapshot_provider(native)
        _install_template_bgr_loader(native)
        _RUNTIME = native.WorkerRuntime(_STATE)
        _RUNTIME.start_all()
        _NATIVE_WORKERS_ACTIVE = True
        atexit.register(stop_native_workers)
        return True
    except Exception:
        return False


def stop_native_workers() -> None:
    global _RUNTIME, _STATE, _NATIVE_WORKERS_ACTIVE
    if _RUNTIME is not None:
        try:
            _RUNTIME.stop_all()
        except Exception:
            pass
    _RUNTIME = None
    _STATE = None
    _NATIVE_WORKERS_ACTIVE = False
