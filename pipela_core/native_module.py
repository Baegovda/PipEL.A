"""AGENT: shared pipela_native import (repo root / frozen exe directory)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_NATIVE: Any | None = None
_NATIVE_TRIED = False
_LAST_IMPORT_ERROR: str | None = None


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    try:
        roots.append(Path(__file__).resolve().parents[1])
    except IndexError:
        pass
    roots.append(Path.cwd())
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def last_native_import_error() -> str | None:
    return _LAST_IMPORT_ERROR


def import_native_module(*, force: bool = False) -> Any | None:
    """Return pipela_native module or None (cached after first attempt unless force=True)."""
    global _NATIVE, _NATIVE_TRIED, _LAST_IMPORT_ERROR
    if _NATIVE_TRIED and not force:
        return _NATIVE
    _NATIVE_TRIED = True
    _LAST_IMPORT_ERROR = None

    for root in _candidate_roots():
        if not (root / "pipela_native.pyd").is_file():
            continue
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)
        break

    try:
        import pipela_native as native  # type: ignore[import-not-found]

        _NATIVE = native
        return native
    except Exception as exc:
        _NATIVE = None
        _LAST_IMPORT_ERROR = str(exc)
        return None


def native_module_available() -> bool:
    return import_native_module() is not None
