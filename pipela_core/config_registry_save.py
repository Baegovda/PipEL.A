"""레지스트리 저장 — 필드명·(레지키, 전역명) 쌍 루프."""

from __future__ import annotations

import json
import winreg
from typing import Any, Mapping


def save_sz_same_key(key: Any, gsave: Mapping[str, Any], names: tuple[str, ...]) -> None:
    """레지스트리 값 이름과 globals 키가 동일한 REG_SZ 저장."""
    for name in names:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(gsave[name]))


def save_merc_fire_fields(key: Any, gsave: Mapping[str, Any]) -> None:
    """Merc Fire 전용 — bool·실수를 레지에서 안정적으로 읽을 수 있는 REG_SZ 문자열로 저장."""
    en = bool(gsave["merc_fire_enabled"])
    winreg.SetValueEx(key, "merc_fire_enabled", 0, winreg.REG_SZ, "true" if en else "false")
    winreg.SetValueEx(key, "merc_fire_key_code", 0, winreg.REG_SZ, str(int(gsave["merc_fire_key_code"])))
    winreg.SetValueEx(
        key,
        "merc_fire_random_min_ms",
        0,
        winreg.REG_SZ,
        str(float(gsave["merc_fire_random_min_ms"])),
    )
    winreg.SetValueEx(
        key,
        "merc_fire_random_max_ms",
        0,
        winreg.REG_SZ,
        str(float(gsave["merc_fire_random_max_ms"])),
    )
    iu = bool(gsave["merc_fire_interval_use_seconds"])
    winreg.SetValueEx(
        key,
        "merc_fire_interval_use_seconds",
        0,
        winreg.REG_SZ,
        "true" if iu else "false",
    )


def save_reg_global_pairs(
    key: Any,
    gsave: Mapping[str, Any],
    pairs: tuple[tuple[str, str], ...],
) -> None:
    for reg_key, attr in pairs:
        winreg.SetValueEx(key, reg_key, 0, winreg.REG_SZ, str(gsave[attr]))


def save_json_region_optional(key: Any, name: str, val) -> None:
    """JSON 직렬화 영역: 값 있으면 REG_SZ, 없으면 키 삭제."""
    if val:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, json.dumps(val))
    else:
        try:
            winreg.DeleteValue(key, name)
        except OSError:
            pass


def delete_registry_values_if_present(key: Any, names: tuple[str, ...]) -> None:
    for name in names:
        try:
            winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
        except Exception:
            pass
