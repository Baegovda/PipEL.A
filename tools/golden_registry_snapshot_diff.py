#!/usr/bin/env python3
"""Compare Python registry config snapshot keys vs C++ RegistrySnapshot builtins."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _python_snapshot_keys() -> tuple[str, ...]:
    from pipela_core.registry_config_snapshot import registry_config_snapshot_key_names

    return registry_config_snapshot_key_names()


def _json_snapshot_keys() -> list[str]:
    path = ROOT / "registry" / "snapshot_keys.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = data.get("keys", [])
    return [str(k) for k in keys]


def _cpp_snapshot_keys() -> list[str] | None:
    try:
        import pipela_native  # type: ignore[import-not-found]
    except Exception as exc:
        print(f"pipela_native unavailable: {exc}")
        return None
    try:
        snap = pipela_native.RegistrySnapshot()
        return list(snap.builtin_key_names())
    except Exception as exc:
        print(f"RegistrySnapshot.builtin_key_names failed: {exc}")
        return None


def _python_snapshot_values() -> dict[str, Any]:
    try:
        import main  # noqa: WPS433
        from pipela_core.registry_config_snapshot import sync_registry_snapshot_from_module

        sync_registry_snapshot_from_module(main)
        from pipela_core.registry_config_snapshot import get_registry_config_snapshot

        return dict(get_registry_config_snapshot())
    except Exception as exc:
        print(f"python snapshot values unavailable: {exc}")
        return {}


def _compare_typed_values(py_snap: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    try:
        import pipela_native  # type: ignore[import-not-found]
    except Exception:
        return []
    cpp_snap = pipela_native.RegistrySnapshot.from_dict(py_snap)
    mismatches: list[tuple[str, Any, Any]] = []
    for key, value in py_snap.items():
        if isinstance(value, bool):
            cpp_val = cpp_snap.snapshot_bool(key, not value)
            if cpp_val != value:
                mismatches.append((key, value, cpp_val))
        elif isinstance(value, int) and not isinstance(value, bool):
            cpp_val = cpp_snap.snapshot_int(key, value - 1)
            if cpp_val != value:
                mismatches.append((key, value, cpp_val))
        elif isinstance(value, float):
            cpp_val = cpp_snap.snapshot_float(key, value - 1.0)
            if abs(cpp_val - value) > 1e-9:
                mismatches.append((key, value, cpp_val))
    return mismatches


def main() -> int:
    py_keys = list(_python_snapshot_keys())
    json_keys = _json_snapshot_keys()
    cpp_keys = _cpp_snapshot_keys()

    print(f"python REGISTRY_CONFIG_SNAPSHOT_KEYS: {len(py_keys)}")
    print(f"registry/snapshot_keys.json: {len(json_keys)}")

    py_set = set(py_keys)
    json_set = set(json_keys)
    only_py = sorted(py_set - json_set)
    only_json = sorted(json_set - py_set)
    if only_py:
        print("only python:", only_py[:20], "..." if len(only_py) > 20 else "")
    if only_json:
        print("only json:", only_json[:20], "..." if len(only_json) > 20 else "")
    if not only_py and not only_json:
        print("OK: python/json snapshot key sets match")

    key_ok = not only_py and not only_json
    cpp_key_ok = True
    if cpp_keys is None:
        print("SKIP C++ key diff (pipela_native not built)")
    else:
        print(f"cpp builtin_key_names: {len(cpp_keys)}")
        cpp_set = set(cpp_keys)
        only_py_cpp = sorted(py_set - cpp_set)
        only_cpp = sorted(cpp_set - py_set)
        if only_py_cpp:
            print("only python vs cpp:", only_py_cpp[:20], "..." if len(only_py_cpp) > 20 else "")
        if only_cpp:
            print("only cpp:", only_cpp[:20], "..." if len(only_cpp) > 20 else "")
        if not only_py_cpp and not only_cpp:
            print("OK: python/cpp snapshot key sets match")
        cpp_key_ok = not only_py_cpp and not only_cpp

    py_snap = _python_snapshot_values()
    value_mismatches: list[tuple[str, Any, Any]] = []
    if py_snap and cpp_keys is not None:
        value_mismatches = _compare_typed_values(py_snap)
        if value_mismatches:
            print("typed value mismatches:", value_mismatches[:10], "..." if len(value_mismatches) > 10 else "")
        else:
            print(f"OK: typed snapshot parity ({len(py_snap)} keys scanned)")

    return 0 if key_ok and cpp_key_ok and not value_mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
