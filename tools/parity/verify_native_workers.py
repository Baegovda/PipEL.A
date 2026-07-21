"""AGENT: Verify pipela_native.pyd and C++ worker startup without full GUI session."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    pyd = ROOT / "pipela_native.pyd"
    print(f"pipela_native.pyd: {'OK' if pyd.is_file() else 'MISSING'}")
    if not pyd.is_file():
        print("Run: .\\scripts\\build_native_core.bat")
        return 2

    from pipela_core.native_module import import_native_module

    native = import_native_module(force=True)
    if native is None:
        print("pipela_native import failed")
        return 3

    state = native.AppState()
    state.seed_from_defaults()
    state.set("running", True)
    print(f"AppState running={state.get('running')}")

    os.environ.pop("PIPELA_NATIVE_WORKERS", None)
    from pipela_core.worker_runtime_bridge import native_workers_enabled, start_native_workers, stop_native_workers

    print(f"native_workers_enabled: {native_workers_enabled()}")
    print("F5: console should show C++ workers ON (auto) - Python macro loops skipped")
    if not start_native_workers({}):
        print("start_native_workers failed")
        return 4
    print("C++ WorkerRuntime started (smoke)")
    stop_native_workers()
    print("OK")
    # AGENT: Smoke harness exits without pybind WorkerRuntime teardown during interpreter shutdown.
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
