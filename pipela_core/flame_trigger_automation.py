"""Reload / Call Merc 등 자동화 시퀀스에서 Flame Trigger(FT) 일시 해제·복귀 — I/O는 콜백."""

from __future__ import annotations

from typing import Callable


def automation_disable_flame_trigger_if_active(
    *,
    flame_trigger_active: bool,
    disable: Callable[[], None],
) -> None:
    """FT가 켜져 있을 때만 deactivate(전역 해제·우클릭 업 등 호출부에서 수행)."""
    if flame_trigger_active:
        disable()


def automation_reenable_flame_trigger_after_success(
    *,
    feature_enabled: bool,
    restore_flag: bool,
    enable: Callable[[], None],
) -> bool:
    """
    기능이 켜져 있고 복귀 조건이 참이면 enable() 호출.
    Reload: restore_flag=nobullet 시점에 FT가 켜져 있었는지(`_reload_had_ft`).
    Call Merc: restore_flag=call_merc_restore_ft_after_cycle.
    반환: 실제로 enable을 호출했으면 True.
    """
    if feature_enabled and restore_flag:
        enable()
        return True
    return False
