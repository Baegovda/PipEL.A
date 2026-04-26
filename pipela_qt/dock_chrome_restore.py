"""도킹된 제어창·킬 패널 복원 — 상단 스트립과 동일한 앵커(게임/런처) 맥락에서 맞춤.

``QtGameTitleBarStrip`` 전용이었던 복원 로직과 ``PipelaQtMainWindow`` 의 게임 최소화
복원(아이콉 전환)을 한곳에 두어, «스트립만 뜨고 메인/킬이 안 뜨는» 현상을 막는다.
"""

from __future__ import annotations

import sys

import win32gui
from PyQt6.QtCore import QTimer

from pipela_core.win32_window_ops import win32_window_restore_normal
from pipela_qt.dock_ui_phase import UI_DOCK_PHASE_LAUNCHER, get_ui_dock_phase, get_ui_dock_phase_from_session
from pipela_qt.qt_dock_anchor import resolve_dock_anchor_hwnd


def _needs_pipela_chrome_docked_state(
    m,
    qt_main,
    *,
    target_hwnd=None,
) -> bool:
    """복원이 필요한지 — 기존 스트립의 unify·최소화 조건 + 숨김(× 아님)·킬만 사라짐."""
    unify = bool(getattr(m, "_pipela_chrome_minimized_with_game", False))
    if unify:
        return True
    if qt_main.isMinimized():
        return True
    if qt_main.isHidden() and not getattr(qt_main, "_control_chrome_user_dismissed", False):
        return True
    if not getattr(m, "kill_counter_enabled", False):
        return False
    th = target_hwnd if target_hwnd is not None else m.refresh_target_hwnd_if_needed()
    if not th or m.is_window_minimized(th):
        return False
    if getattr(qt_main, "_kc_float_user_hidden", False):
        return False
    kc = getattr(qt_main, "_kc_float", None)
    if kc is not None and not kc.isVisible():
        return True
    return False


def restore_pipela_docked_chrome_if_needed(
    m,
    *,
    game_just_restored: bool = False,
    anchor_hwnd: int | None = None,
    target_hwnd: int | None = None,
    launcher_hwnd: int | None = None,
    dock_phase: str | None = None,
) -> bool:
    """
    앵커가 있을 때 제어창·킬 도킹을 복원한다.

    - ``game_just_restored=True`` : 게임이 아이콉에서 **막** 복구된 틱(제어 쪽 풀)에서
      «×로 닫음»이 아닌 경우 한 번에 제어+킬을 맞춘다.
    - 그렇지 않으면 ``_needs_…`` 가 True 일 때만(스트립과 유사) 수행.
    - ``anchor_hwnd`` / ``target_hwnd`` : 스트립 틱 등에서 ``refresh_*`` 를 이미 한 번 호출한 경우
      넘겨 중복 Enum·갱신을 줄인다.
    """
    if anchor_hwnd is None:
        r = resolve_dock_anchor_hwnd(m)
        if r is None:
            return False
    try:
        _ph = (
            dock_phase
            if dock_phase is not None
            else (
                get_ui_dock_phase_from_session(m, target_hwnd, launcher_hwnd)
                if target_hwnd is not None or launcher_hwnd is not None
                else get_ui_dock_phase(m)
            )
        )
        if _ph == UI_DOCK_PHASE_LAUNCHER:
            return False
    except Exception:
        pass
    qt_main = getattr(m, "_qt_control_main", None)
    if qt_main is None:
        try:
            m._pipela_chrome_minimized_with_game = False
        except Exception:
            pass
        return False
    if getattr(qt_main, "_start_tray_only", False):
        return False
    if getattr(qt_main, "_control_chrome_user_dismissed", False):
        return False
    if not game_just_restored and not _needs_pipela_chrome_docked_state(
        m, qt_main, target_hwnd=target_hwnd,
    ):
        return False

    try:
        if sys.platform == "win32":
            try:
                mw = int(qt_main.winId())
                if win32gui.IsWindow(mw):
                    win32_window_restore_normal(mw)
            except Exception:
                pass
        if qt_main.isMinimized():
            qt_main.showNormal()
        qt_main.show()
        qt_main.raise_()
        QTimer.singleShot(0, lambda q=qt_main: q._dock_to_anchor(force=True))
        QTimer.singleShot(120, lambda q=qt_main: q._dock_to_anchor(force=True))
    except Exception:
        pass
    try:
        m._pipela_chrome_minimized_with_game = False
    except Exception:
        pass
    sp = getattr(m, "_qt_title_bar_strip", None)
    if sp is not None:
        try:
            sp.invalidate_chrome_layout()
        except Exception:
            pass
    # 킬: 최소화 시 `kc.hide()` 만 된 뒤 복원 경로를 안 탄 경우
    QTimer.singleShot(0, lambda q=qt_main: q._sync_kill_counter_window())
    QTimer.singleShot(50, lambda q=qt_main: q._sync_kill_counter_window())
    return True
