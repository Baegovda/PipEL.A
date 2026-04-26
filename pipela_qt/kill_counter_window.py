"""킬 카운터 — 이터널시티 **클라이언트 오른**에 맞춘 floater (제어창은 클라이언트 왼)."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from pipela_core.win32_window_ops import (
    dock_outer_rect_touch_client_right,
    win32_set_window_outer_rect,
)
from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_qt.app_shell import kill_counter_floater_window_qss
from pipela_qt.dpi import get_dock_panel_wh, win32_dpi_scale_for_hwnd
from pipela_qt.qt_dock_anchor import resolve_game_only_anchor_hwnd
from pipela_qt.panels.kill_counter_panel import KillCounterPanel
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.ui_adaptive import main_shell_margins_lr_tb, scale_px


class PipelaQtKillCounterWindow(QMainWindow):
    """킬 통계 패널 — `target` 게임 `GetWindowRect` 오른쪽에 붙임(작업 영역으로 클램프)."""

    userDismissed = pyqtSignal()

    def __init__(self, pipela_mod, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._last_dock_sig: object | None = None
        self.setWindowTitle(f"Kill Counter ({PIPELA_APP_DISPLAY_NAME})")
        _wi = qt_application_icon()
        if not _wi.isNull():
            self.setWindowIcon(_wi)
        self.setObjectName("pipelaKcFrameless")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        self._dock_w, _dh = get_dock_panel_wh(pipela_mod)
        self.resize(self._dock_w, _dh)
        self.setFixedWidth(self._dock_w)
        self.setMinimumHeight(1)

        self.setStyleSheet(kill_counter_floater_window_qss())

        root = QWidget()
        root.setObjectName("pipelaKcRoot")
        self.setCentralWidget(root)
        out = QVBoxLayout(root)
        self._root_out = out
        ml, mt, mr, mb = main_shell_margins_lr_tb()
        # 좌·우 대칭 여백 — 맨 위 현재 킬 숫자 오른쪽이 창 테두리에 붙지 않도록
        out.setContentsMargins(ml, mt, mr, mb)
        out.setSpacing(scale_px(0))
        self._panel = KillCounterPanel(pipela_mod, parent=root)
        out.addWidget(self._panel, 1)

    def apply_scaled_typography(self) -> None:
        self.setStyleSheet(kill_counter_floater_window_qss())
        out = getattr(self, "_root_out", None)
        if out is not None:
            ml, mt, mr, mb = main_shell_margins_lr_tb()
            out.setContentsMargins(ml, mt, mr, mb)
            out.setSpacing(scale_px(0))
        self._panel.apply_scaled_typography()

    def _dismiss(self) -> None:
        self.hide()
        self.userDismissed.emit()

    def showEvent(self, e: QShowEvent) -> None:
        super().showEvent(e)
        QTimer.singleShot(0, self.dock_to_right_of_target_game)
        QTimer.singleShot(100, self.dock_to_right_of_target_game)

    def clear_dismiss_and_show(self) -> None:
        self.show()
        self.raise_()
        QTimer.singleShot(0, self.dock_to_right_of_target_game)

    def dock_to_right_of_target_game(self) -> None:
        """이터널시티 **클라이언트 오른**에 맞춤(킬창 왼쪽 = `cr[2]`). 세로도 클라이언트. 실패 시 외곽 오른."""
        m = self._m
        if sys.platform != "win32" or not self.isVisible():
            return
        if not getattr(m, "running", True):
            return
        try:
            th = resolve_game_only_anchor_hwnd(m)
            if not th:
                return
            gr = m.get_window_outer_rect_screen(th)
            if not gr:
                return
            ol, ot, o_right, ob = (int(x) for x in gr)
            cr = m.get_window_rect(th)
            self.update()
            w_cfg, _h2 = get_dock_panel_wh(m)
            w_cfg = max(8, int(w_cfg))
            if w_cfg != int(self._dock_w):
                self._dock_w = w_cfg
                self._last_dock_sig = None
            scale = win32_dpi_scale_for_hwnd(m, int(th))
            dock_w_log = max(8, int(self._dock_w))
            fw_phys = max(8, int(round(dock_w_log * scale)))
            fh_phys = max(1, int(cr[3] - cr[1]) if cr and (cr[2] > cr[0]) else int(ob - ot))
            y_phys = int(cr[1]) if cr and (cr[2] > cr[0]) else int(ot)
            if fw_phys < 8 or fh_phys < 8:
                return
            snap_left_to_x = int(cr[2]) if cr and (cr[2] > cr[0]) else int(o_right)
            x_phys, y_phys, fw_phys, fh_phys = dock_outer_rect_touch_client_right(
                th,
                snap_left_to_x,
                y_phys,
                fw_phys,
                fh_phys,
            )
            sig = (snap_left_to_x, ol, ot, o_right, ob, x_phys, y_phys, fw_phys, fh_phys)
            if sig == self._last_dock_sig:
                return
            self._last_dock_sig = sig
            w_log = max(8, int(round(fw_phys / scale)))
            h_log = max(1, int(round(fh_phys / scale)))
            x_log = int(round(x_phys / scale))
            y_log = int(round(y_phys / scale))
            try:
                self.setFixedWidth(w_log)
            except Exception:
                pass
            self.setGeometry(x_log, y_log, w_log, h_log)
            try:
                win32_set_window_outer_rect(
                    int(self.winId()), x_phys, y_phys, fw_phys, fh_phys,
                )
            except Exception:
                pass
        except Exception:
            pass
