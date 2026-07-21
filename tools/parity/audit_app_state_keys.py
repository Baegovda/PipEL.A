"""AGENT: Diff Python AppState dataclass fields vs C++ app_state key table."""

from __future__ import annotations

import re
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def python_keys() -> set[str]:
    from pipela_core.app_state import InputState, KillCounterState, WorkerRuntimeState

    keys: set[str] = set()
    for grp in (InputState, WorkerRuntimeState, KillCounterState):
        for f in fields(grp):
            if f.name.startswith("_"):
                continue
            if f.name.endswith("_detect_region"):
                continue
            keys.add(f.name)
    return keys


def cpp_keys() -> set[str]:
    text = (ROOT / "cpp" / "src" / "core" / "state" / "app_state.cpp").read_text(encoding="utf-8")
    return set(re.findall(r'\{"([a-z_][a-z0-9_]*)"', text))


def main() -> int:
    py = python_keys()
    cxx = cpp_keys()
    missing_in_cpp = sorted(py - cxx)
    extra_in_cpp = sorted(cxx - py)
    print(f"Python AppState fields: {len(py)}")
    print(f"C++ key table entries: {len(cxx)}")
    if missing_in_cpp:
        print("\nMissing in C++ (add to app_state.hpp/cpp):")
        for k in missing_in_cpp:
            print(f"  - {k}")
    if extra_in_cpp:
        print("\nC++ only (not in Python dataclasses):")
        for k in extra_in_cpp:
            print(f"  - {k}")
    if not missing_in_cpp:
        print("\nOK: all Python AppState fields have C++ keys")
    return 1 if missing_in_cpp else 0


if __name__ == "__main__":
    sys.exit(main())
