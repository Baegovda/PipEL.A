"""게임 창에 맞추는 최상위 오버레이 — 좌표·크기 동기화."""

from __future__ import annotations

import ctypes
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget

from pipela_qt.dpi import win32_physical_screen_rect_to_qt_overlay_geometry

_HIDDEN = (-10000, -10000, 1, 1)


def _win32_apply_black_colorkey(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x80000
    ex = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
    LWA_COLORKEY = 0x1
    user32.SetLayeredWindowAttributes(hwnd, 0x000000, 0, LWA_COLORKEY)


class QtGameOverlay(QWidget):
    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._colorkey_done = False
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background-color: #000000;")
        self.setGeometry(*_HIDDEN)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        ms = max(8, int(pipela_mod.pipela_overlay_tick_ms()))
        self._timer.start(ms)
        self._last_ov_sig_qt: tuple[int, int, int, int] | None = None
        self._last_ov_sig_phys: tuple[int, int, int, int] | None = None
        # `_tick` 의 HIDDEN 폴백 경로가 매 틱 SetWindowPos 를 쏘면 WS_EX_LAYERED 창 갱신이
        # DWM 큐를 흔들어 일부 환경에서 시스템 커서가 좌상단·원위치 사이로 점멸하는 듯 보일 수 있어
        # 동일 HIDDEN 좌표는 한 번만 적용한다.
        self._hidden_applied = False

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._colorkey_done and sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    _win32_apply_black_colorkey(wid)
                    self._colorkey_done = True
            except Exception:
                pass

    def _tick(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            self.close()
            return
        target_hwnd = m.refresh_target_hwnd_if_needed()
        launcher_hwnd = m.refresh_smart_updater_hwnd_if_needed()
        anchor = None
        if target_hwnd and not m.is_window_minimized(target_hwnd):
            anchor = target_hwnd
        elif launcher_hwnd and not m.is_window_minimized(launcher_hwnd):
            anchor = launcher_hwnd
        if anchor and not getattr(m, "select_mode", False):
            rect = m.get_window_rect(anchor)
            if rect:
                wx, wy, wx2, wy2 = rect
                w, h = wx2 - wx, wy2 - wy
                if w >= 8 and h >= 8:
                    x_phys, y_phys = int(wx - 3), int(wy - 3)
                    cw_phys, ch_phys = int(w + 6), int(h + 6)
                    xl, yl, cwl, chl = win32_physical_screen_rect_to_qt_overlay_geometry(
                        m, int(anchor), x_phys, y_phys, cw_phys, ch_phys,
                    )
                    sig_qt = (int(xl), int(yl), int(cwl), int(chl))
                    sig_ph = (int(x_phys), int(y_phys), int(cw_phys), int(ch_phys))
                    if (
                        sig_qt == self._last_ov_sig_qt
                        and sig_ph == self._last_ov_sig_phys
                    ):
                        return
                    self._last_ov_sig_qt = sig_qt
                    self._last_ov_sig_phys = sig_ph
                    self._hidden_applied = False
                    self.setGeometry(xl, yl, cwl, chl)
                    if sys.platform == "win32":
                        try:
                            m.win32_set_window_outer_rect(
                                int(self.winId()), x_phys, y_phys, cw_phys, ch_phys,
                            )
                        except Exception:
                            pass
                    # 타이틀 스트립 Z 는 `QtGameTitleBarStrip._tick` 에서 스로틀됨.
                    # 여기서 매 틱 `reassert_z_order` 하면 게임 타이틀과 번쩍임이 난다.
                    return
        if self._hidden_applied:
            return
        self._last_ov_sig_qt = None
        self._last_ov_sig_phys = None
        x, y, w, h = _HIDDEN
        self.setGeometry(x, y, w, h)
        if sys.platform == "win32":
            try:
                m.win32_set_window_outer_rect(int(self.winId()), x, y, w, h)
            except Exception:
                pass
        self._hidden_applied = True
