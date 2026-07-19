"""게임 클라이언트 없음·대기(절전) 진입 시 일시 입력 세션 정리 — main·워커에서 콜백 주입."""

from __future__ import annotations

from typing import Any, Callable


def apply_no_game_client_session_teardown(
    *,
    state_get: Callable[[str], Any],
    state_set: Callable[[str, Any], None],
    get_right_hold_active: Callable[[], bool],
    set_right_hold_active: Callable[[bool], None],
    mouse_right_up: Callable[[], None],
    release_flame_hardware: Callable[[], None],
    clear_user_left_pending: Callable[[], None],
) -> list[str]:
    """
    기능 마스터 토글은 유지하고, 세션(active)만 해제.
    반환: 변경된 논리 키 이름(로그·디버그용).
    """
    changed: list[str] = []
    if bool(state_get("flame_trigger_active")):
        state_set("flame_trigger_active", False)
        release_flame_hardware()
        changed.append("flame_trigger_active")
    if bool(state_get("left_click_active")):
        state_set("left_click_active", False)
        clear_user_left_pending()
        changed.append("left_click_active")
    if get_right_hold_active():
        set_right_hold_active(False)
        mouse_right_up()
        changed.append("right_hold_active")
    return changed
