#!/usr/bin/env python3
"""Compare Python registry load vs C++ load_registry_strings (golden harness)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _python_registry_strings() -> dict[str, str]:
    import winreg

    from pipela_core.registry_constants import REGISTRY_PATH

    out: dict[str, str] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            i = 0
            while True:
                try:
                    name, value, typ = winreg.EnumValue(key, i)
                except OSError:
                    break
                i += 1
                if typ != winreg.REG_SZ:
                    continue
                out[str(name)] = str(value)
    except OSError:
        pass
    return out


def _cpp_registry_strings() -> dict[str, str] | None:
    try:
        import pipela_native  # type: ignore[import-not-found]
    except Exception as exc:
        print(f"pipela_native unavailable: {exc}")
        return None
    try:
        return dict(pipela_native.load_registry_strings())
    except Exception as exc:
        print(f"load_registry_strings failed: {exc}")
        return None


def main() -> int:
    schema_path = ROOT / "registry" / "schema.json"
    if not schema_path.is_file():
        print("Run tools/codegen/export_registry_schema.py first")
        return 2
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    py_map = _python_registry_strings()
    cpp_map = _cpp_registry_strings()
    print(f"schema entries: {schema.get('entry_count', 0)}")
    print(f"python REG_SZ keys: {len(py_map)}")
    if cpp_map is None:
        print("SKIP C++ diff (pipela_native not built)")
        return 0
    print(f"cpp REG_SZ keys: {len(cpp_map)}")
    only_py = sorted(set(py_map) - set(cpp_map))
    only_cpp = sorted(set(cpp_map) - set(py_map))
    diff_val = [k for k in py_map if k in cpp_map and py_map[k] != cpp_map[k]]
    if only_py:
        print("only python:", only_py[:20], "..." if len(only_py) > 20 else "")
    if only_cpp:
        print("only cpp:", only_cpp[:20], "..." if len(only_cpp) > 20 else "")
    if diff_val:
        print("value mismatch:", diff_val[:20])
    if not only_py and not only_cpp and not diff_val:
        print("OK: python/cpp registry string maps match")
    print("Hint: run tools/parity/golden_registry_snapshot_diff.py for snapshot key/value parity")
    return 0 if not diff_val else 1


if __name__ == "__main__":
    raise SystemExit(main())
