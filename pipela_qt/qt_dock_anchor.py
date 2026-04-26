"""게임/런처 HWND — 메인·킬·상단 스트립 도킹이 같은 규칙으로 앵커를 쓰도록 공통화.

**UI 페이즈**(런처·클라·대기(standby)·도킹 패널 폭): ``pipela_qt.dock_ui_phase``  
최소화 복원(제어·킬): ``pipela_qt.dock_chrome_restore``
"""

from __future__ import annotations


def resolve_dock_anchor_from_session(
    pipela_mod,
    target_hwnd,
    launcher_hwnd,
) -> int | None:
    """``refresh_*`` 없이 앵커 HWND — 스트립 틱 등에서 한 번만 갱신한 핸들에 사용."""
    if target_hwnd and not pipela_mod.is_window_minimized(int(target_hwnd)):
        return int(target_hwnd)
    if launcher_hwnd and not pipela_mod.is_window_minimized(int(launcher_hwnd)):
        return int(launcher_hwnd)
    return None


def resolve_dock_anchor_hwnd(pipela_mod) -> int | None:
    """
    이터널시티 우선(최소화 아님) → 없으면 스마트업데이터 런처.
    ``PipelaQtMainWindow._dock_to_anchor`` / ``QtGameTitleBarStrip._tick`` 과 동일 규칙.
    """
    th = pipela_mod.refresh_target_hwnd_if_needed()
    if th and not pipela_mod.is_window_minimized(th):
        return int(th)
    luh = pipela_mod.refresh_smart_updater_hwnd_if_needed()
    if luh and not pipela_mod.is_window_minimized(luh):
        return int(luh)
    return None


def resolve_game_only_anchor_hwnd(pipela_mod) -> int | None:
    """킬 카운터: 이터널시티만(게임 없으면 도킹 안 함)."""
    th = pipela_mod.refresh_target_hwnd_if_needed()
    if th and not pipela_mod.is_window_minimized(th):
        return int(th)
    return None
