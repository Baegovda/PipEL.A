"""`get_registry_config_snapshot()` dict에서 안전하게 값 읽기 (Qt·워커 단일 소스 보조)."""

from __future__ import annotations

from typing import Any, Mapping

from pipela_core.config_parse import reg_parse_bool


def snapshot_float(snap: Mapping[str, Any], key: str, default: float) -> float:
    try:
        return float(snap[key])
    except (KeyError, TypeError, ValueError):
        return default


def snapshot_int(snap: Mapping[str, Any], key: str, default: int) -> int:
    try:
        return int(snap[key])
    except (KeyError, TypeError, ValueError):
        return default


def snapshot_bool(snap: Mapping[str, Any], key: str, default: bool = False) -> bool:
    if key not in snap:
        return default
    return reg_parse_bool(snap[key])


def coalesce_registry_snapshot(snap: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """호출부가 이미 스냅샷을 들고 있으면 그대로 쓰고, 없으면 최신 스냅샷을 가져온다.

    Qt 패널·틱에서 `snap=None` 선택 인자를 둘 때 중복 `get`을 한 곳으로 모은다.
    """
    if snap is not None:
        return snap
    from pipela_core.registry_config_snapshot import get_registry_config_snapshot

    return get_registry_config_snapshot()
