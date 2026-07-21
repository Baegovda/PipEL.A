"""AGENT: C++ worker runtime — auto ON when pipela_native.pyd is present."""

from __future__ import annotations

import atexit
import os
from dataclasses import fields
from typing import Any, Mapping

from pipela_core.app_state import InputState, KillCounterState, WorkerRuntimeState
from pipela_core.native_module import import_native_module, last_native_import_error

_RUNTIME: Any | None = None
_STATE: Any | None = None
_NATIVE_WORKERS_ACTIVE = False
_NATIVE_WORKERS_AUTO = False


def _env_flag(name: str) -> str:
    return os.environ.get(name, "").strip().lower()


def native_workers_explicitly_disabled() -> bool:
    return _env_flag("PIPELA_NATIVE_WORKERS") in ("0", "false", "no", "off")


def native_workers_explicitly_enabled() -> bool:
    return _env_flag("PIPELA_NATIVE_WORKERS") in ("1", "true", "yes", "on")


def native_workers_enabled() -> bool:
    """True when C++ workers should run (auto-detect pyd unless env overrides)."""
    if native_workers_explicitly_disabled():
        return False
    if native_workers_explicitly_enabled():
        return True
    return import_native_module() is not None


def native_workers_active() -> bool:
    return _NATIVE_WORKERS_ACTIVE


def native_workers_auto_mode() -> bool:
    return _NATIVE_WORKERS_AUTO


def get_native_app_state() -> Any | None:
    return _STATE


def sync_native_state_from_globals(module_globals: Mapping[str, Any] | None) -> None:
    _seed_native_state_from_globals(module_globals)


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


def _install_kill_counter_ocr(native: Any, module_globals: Mapping[str, Any] | None) -> None:
    if module_globals is None:
        return
    from pipela_core.kill_counter_native_ocr import process_bgr_for_native

    def _ocr(bgr_bytes: bytes, w: int, h: int):
        return process_bgr_for_native(module_globals, bgr_bytes, w, h)

    native.set_kill_counter_ocr_loader(_ocr)


def _install_refresh_target_hwnd(native: Any, module_globals: Mapping[str, Any] | None) -> None:
    """Prefer C++ refreshEternalcityHwndCached when Python callback unavailable."""
    if module_globals is None:
        return
    refresh = module_globals.get("refresh_target_hwnd_if_needed")
    if refresh is None:
        return

    def _cb() -> None:
        refresh()

    native.set_refresh_target_hwnd_callback(_cb)


# AGENT: Template images — C++ loadTemplatePath is tried first; pybind loader is registry blob fallback.


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
    global _RUNTIME, _STATE, _NATIVE_WORKERS_ACTIVE, _NATIVE_WORKERS_AUTO
    if not native_workers_enabled():
        return False

    _NATIVE_WORKERS_AUTO = not native_workers_explicitly_enabled() and not native_workers_explicitly_disabled()

    native = import_native_module()
    if native is None:
        return False

    try:
        _STATE = native.AppState()
        _STATE.seed_from_defaults()
        _seed_native_state_from_globals(module_globals)
        _install_snapshot_provider(native)
        _install_template_bgr_loader(native)
        _install_kill_counter_ocr(native, module_globals)
        _install_refresh_target_hwnd(native, module_globals)
        _RUNTIME = native.WorkerRuntime(_STATE)
        _RUNTIME.start_all()
        _NATIVE_WORKERS_ACTIVE = True
        atexit.register(stop_native_workers)
        return True
    except Exception as exc:
        _RUNTIME = None
        _STATE = None
        _NATIVE_WORKERS_ACTIVE = False
        print(f"[Pipela] C++ worker runtime failed to start: {exc}", flush=True)
        if last_native_import_error():
            print(f"[Pipela] pipela_native import: {last_native_import_error()}", flush=True)
        return False


def stop_native_workers() -> None:
    global _RUNTIME, _STATE, _NATIVE_WORKERS_ACTIVE, _NATIVE_WORKERS_AUTO
    try:
        atexit.unregister(stop_native_workers)
    except (AttributeError, ValueError):
        pass
    if _RUNTIME is not None:
        try:
            _RUNTIME.stop_all()
        except Exception:
            pass
    _RUNTIME = None
    _STATE = None
    _NATIVE_WORKERS_ACTIVE = False
    _NATIVE_WORKERS_AUTO = False
