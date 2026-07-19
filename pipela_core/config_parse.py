"""레지스트리·설정 값 파싱/클램프 (순수, winreg 미사용)."""

from __future__ import annotations


def reg_parse_bool(val) -> bool:
    """레지 REG_SZ·스냅샷 혼합(bool / int / '1' / 'true' 등) 대응."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    try:
        s = str(val).strip().lower()
    except (TypeError, ValueError):
        return False
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off", ""):
        return False
    return False


def clamp_match_threshold_01(v: float) -> float:
    """이미지 매칭 임계값 0.1 ~ 1.0 (Ammo restock, Call merc 등 공통)."""
    if v < 0.1:
        return 0.1
    if v > 1.0:
        return 1.0
    return v
