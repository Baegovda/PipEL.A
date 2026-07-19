"""도킹된 Pipela 크롬(제어·킬·상단 스트립) — 게임·오버레이 대비 동일 Z 스택."""

from __future__ import annotations

import sys

import win32gui

from pipela_core.win32_window_ops import (
    set_window_z_order_directly_above,
    win32_set_window_owner,
    win32_set_window_topmost,
)

_Z_STACK_LAST_KEY: dict[int, tuple[int, int, int]] = {}


def clear_docked_chrome_z_stack_state(wid: int) -> None:
    _Z_STACK_LAST_KEY.pop(int(wid), None)


def sync_docked_chrome_z_order(
    pipela_mod,
    wid: int,
    anchor: int,
    *,
    set_owner: bool,
    force_z_restack: bool = False,
) -> None:
    """게임 < 오버레이 < 크롬. ``set_owner`` 는 앵커가 바뀔 때만 True 권장(타이틀 스트립과 동일)."""
    if sys.platform != "win32":
        return
    w = int(wid)
    ah = int(anchor)
    if not w or not ah:
        return
    if not win32gui.IsWindow(w):
        return
    if set_owner:
        win32_set_window_owner(w, ah)
    win32_set_window_topmost(w, False)
    ov = getattr(pipela_mod, "_qt_game_overlay", None)
    if ov is not None:
        try:
            oid = int(ov.winId())
            if win32gui.IsWindow(oid):
                key = (ah, w, oid)
                if not force_z_restack and key == _Z_STACK_LAST_KEY.get(w):
                    return
                set_window_z_order_directly_above(oid, ah)
                set_window_z_order_directly_above(w, oid)
                _Z_STACK_LAST_KEY[w] = key
                return
        except Exception:
            pass
    key = (ah, w, 0)
    if not force_z_restack and key == _Z_STACK_LAST_KEY.get(w):
        return
    set_window_z_order_directly_above(w, ah)
    _Z_STACK_LAST_KEY[w] = key
