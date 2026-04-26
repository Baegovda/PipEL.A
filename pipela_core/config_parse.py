"""레지스트리·설정 값 파싱/클램프 (순수, winreg 미사용)."""

from __future__ import annotations


def reg_parse_bool(val) -> bool:
    try:
        return str(val).strip().lower() == "true"
    except (TypeError, ValueError):
        return False


def clamp_match_threshold_01(v: float) -> float:
    """이미지 매칭 임계값 0.1 ~ 1.0 (Ammo restock, Call merc 등 공통)."""
    if v < 0.1:
        return 0.1
    if v > 1.0:
        return 1.0
    return v
