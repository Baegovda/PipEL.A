"""열려 있는 레지스트리 키에서 값 읽기 — 순수(전역 미사용)."""

from __future__ import annotations

import winreg
from typing import Any


def try_query_float(key: Any, reg_key: str) -> float | None:
    try:
        return float(winreg.QueryValueEx(key, reg_key)[0])
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None


def try_query_int(key: Any, reg_key: str) -> int | None:
    try:
        return int(winreg.QueryValueEx(key, reg_key)[0])
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
