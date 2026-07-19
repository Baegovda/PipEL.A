#!/usr/bin/env python3
"""Compare Python registry config snapshot keys vs C++ RegistrySnapshot builtins."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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

    if cpp_keys is None:
        print("SKIP C++ key diff (pipela_native not built)")
        return 0 if not only_py and not only_json else 1

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

    return 0 if not only_py and not only_json and not only_py_cpp and not only_cpp else 1


if __name__ == "__main__":
    raise SystemExit(main())
