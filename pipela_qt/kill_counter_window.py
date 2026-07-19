"""킬 카운터 — 이터널시티 **클라이언트 오른**에 맞춘 floater (제어창은 클라이언트 왼)."""

from __future__ import annotations

import os
import sys
import traceback

import win32gui
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QResizeEvent, QShowEvent
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from pipela_core.win32_window_ops import win32_set_window_outer_rect
from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_qt.app_shell import kill_counter_floater_window_qss, shell_hub_inner_gutter_px
from pipela_qt.dpi import get_dock_panel_wh
from pipela_qt.qt_dock_anchor import resolve_game_only_anchor_hwnd
from pipela_qt.qt_dock_z_stack import sync_docked_chrome_z_order
from pipela_qt.qt_side_dock import (
    anchor_client_inner_height_logical_qt,
    clamp_dock_logical_geometry,
    compute_side_dock_layout,
    reset_dock_pair_width_to_monitor_fill,
)
from pipela_qt.panels.kill_counter_panel import KillCounterPanel
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.ui_adaptive import main_shell_margins_lr_tb, scale_px_h, scale_px_v
from pipela_qt.dock_panel_pair_resize import (
    clamp_dock_pair_panel_w,
    resolve_unified_saved_dock_panel_w,
)
from pipela_qt.dev_ui_mode import pipela_dev_ui_standby_chrome

# 해상도 변경 시 ``compute_side_dock_layout=None`` 연속 시 재시도 상한
_KC_DOCK_RETRY_MAX = 14


def _kc_dock_debug(msg: str, *, err: BaseException | None = None) -> None:
    """환경 변수 ``PIPELA_DEBUG_KILL_DOCK=1`` 또는 ``true`` 일 때만."""
    v = (os.environ.get("PIPELA_DEBUG_KILL_DOCK", "") or "").strip().lower()
    if v not in ("1", "true", "yes", "on", "y"):
        return
    line = f"[KillDock][debug] {msg}"
    if err is not None:
        line = f"{line}: {err!r}"
    print(line, flush=True)


class _KCHResizeEdge(QWidget):
    """프레임리스 킬 창 우측 가장자리에서 폭 리사이즈."""

    def __init__(self, kc: "PipelaQtKillCounterWindow") -> None:
        super().__init__(kc)
        self._kc = kc
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip("폭 조절 — 더블클릭: 작업영역 채움")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._drag = False
        self._g0 = 0
        self._w0 = 0

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = True
            self._g0 = int(event.globalPosition().x())
            self._w0 = int(self._kc._dock_w)
            self.grabMouse()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag:
            nk_target = int(self._w0) + (
                int(event.globalPosition().x()) - int(self._g0)
            )
            w = clamp_dock_pair_panel_w(int(round(float(nk_target))))
            m = self._kc._m
            main = getattr(m, "_qt_control_main", None)
            if main is not None:
                ch = w != self._kc._dock_w or w != int(main._dock_w)
                if ch:
                    self._kc._dock_w = w
                    main._dock_w = w
                    self._kc._last_dock_sig = None
                    main._last_dock_sig = None
                    main._last_standby_sig = None
                    QTimer.singleShot(0, self._kc.dock_to_right_of_target_game)
                    QTimer.singleShot(0, lambda: main._dock_to_anchor(force=True))
            else:
                if w != self._kc._dock_w:
                    self._kc._dock_w = w
                    self._kc._last_dock_sig = None
                    QTimer.singleShot(0, self._kc.dock_to_right_of_target_game)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            m = self._kc._m
            main = getattr(m, "_qt_control_main", None)
            if main is not None:
                reset_dock_pair_width_to_monitor_fill(pipela_mod=m, main=main)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            self._drag = False
            try:
                self.releaseMouse()
            except Exception:
                pass
            try:
                m = self._kc._m
                main_win = getattr(m, "_qt_control_main", None)
                w_saved = clamp_dock_pair_panel_w(int(self._kc._dock_w))
                self._kc._dock_w = w_saved
                if main_win is not None:
                    main_win._dock_w = w_saved
                m.kill_counter_panel_w = w_saved
                m.control_panel_w = w_saved
                ss = getattr(m, "schedule_save_config", None)
                if callable(ss):
                    ss()
            except Exception:
                pass
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PipelaQtKillCounterWindow(QMainWindow):
    """킬 통계 패널 — `target` 게임 `GetWindowRect` 오른쪽에 붙임(작업 영역으로 클램프)."""

    userDismissed = pyqtSignal()

    def __init__(self, pipela_mod, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._last_dock_sig: object | None = None
        self._last_z_anchor: int | None = None
        self.setWindowTitle(f"Kill Counter ({PIPELA_APP_DISPLAY_NAME})")
        _wi = qt_application_icon()
        if not _wi.isNull():
            self.setWindowIcon(_wi)
        self.setObjectName("pipelaKcFrameless")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        _dw_def, _dh = get_dock_panel_wh(pipela_mod)
        main_win = getattr(pipela_mod, "_qt_control_main", None)
        if main_win is not None:
            self._dock_w = clamp_dock_pair_panel_w(int(main_win._dock_w))
        else:
            self._dock_w = resolve_unified_saved_dock_panel_w(pipela_mod, _dw_def)
        # 초기 높이는 도킹 기본값. 실제 높이는 도킹 시점에 앵커 클라 높이로 즉시 동기화된다.
        self.resize(self._dock_w, int(_dh))
        self.setFixedWidth(self._dock_w)
        self._kc_dock_retry_left = 0
        self._last_anchor_cr_sig: tuple[int, int, int, int] | None = None

        self.setStyleSheet(kill_counter_floater_window_qss())

        root = QWidget()
        root.setObjectName("pipelaKcRoot")
        self.setCentralWidget(root)
        out = QVBoxLayout(root)
        self._root_out = out
        ml, mt, mr, mb = main_shell_margins_lr_tb()
        # 좌·우 대칭 여백 — 본문 카드·가장자리 간격
        out.setContentsMargins(ml, mt, mr, mb)
        out.setSpacing(shell_hub_inner_gutter_px())
        self._panel = KillCounterPanel(pipela_mod, parent=root)
        self._panel.setObjectName("pipelaKcPanel")
        out.addWidget(self._panel, 1)

        self._kc_resize_edge = _KCHResizeEdge(self)

    def _kc_resize_margin_px(self) -> int:
        return max(5, int(scale_px_v(7)))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        rz = getattr(self, "_kc_resize_edge", None)
        if rz is not None:
            mpx = self._kc_resize_margin_px()
            rz.setGeometry(self.width() - mpx, 0, mpx, max(1, self.height()))
            rz.raise_()

    def apply_scaled_typography(self) -> None:
        self.setStyleSheet(kill_counter_floater_window_qss())
        out = getattr(self, "_root_out", None)
        if out is not None:
            ml, mt, mr, mb = main_shell_margins_lr_tb()
            out.setContentsMargins(ml, mt, mr, mb)
            out.setSpacing(shell_hub_inner_gutter_px())
        self._panel.apply_scaled_typography()

    def _dismiss(self) -> None:
        self.hide()
        self.userDismissed.emit()

    def showEvent(self, e: QShowEvent) -> None:
        super().showEvent(e)
        rz = getattr(self, "_kc_resize_edge", None)
        if rz is not None:
            QTimer.singleShot(0, rz.raise_)
        QTimer.singleShot(0, self.dock_to_right_of_target_game)
        QTimer.singleShot(100, self.dock_to_right_of_target_game)

    def clear_dismiss_and_show(self) -> None:
        self.show()
        self.raise_()
        QTimer.singleShot(0, self.dock_to_right_of_target_game)

    def dock_to_standby_dev_pair(self) -> None:
        """DEV UI: park kill floater to the right of the control window (no game HWND)."""
        m = self._m
        main = getattr(m, "_qt_control_main", None)
        if main is None or not main.isVisible():
            return
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return
        scr = app.primaryScreen()
        if scr is None:
            return
        ag = scr.availableGeometry()
        w_log = clamp_dock_pair_panel_w(int(self._dock_w))
        try:
            mg = main.geometry()
            x_log = int(mg.x() + mg.width())
            y_log = int(mg.y())
            h_log = max(8, int(mg.height()))
        except Exception:
            h_preset = max(8, int(get_dock_panel_wh(m)[1]))
            h_log = min(h_preset, max(8, ag.height() - 16))
            x_log = int(ag.left() + max(0, (ag.width() - 2 * w_log) // 2 + w_log))
            y_log = int(ag.top() + max(0, (ag.height() - h_log) // 2))
        try:
            x_log, y_log, w_log, h_log = clamp_dock_logical_geometry(
                x_log, y_log, w_log, h_log,
            )
        except Exception:
            pass
        sig = ("dev_pair", x_log, y_log, w_log, h_log)
        if sig == self._last_dock_sig:
            return
        self._last_dock_sig = sig
        try:
            self.setFixedWidth(w_log)
            self.setFixedHeight(h_log)
        except Exception:
            pass
        self.setGeometry(x_log, y_log, w_log, h_log)

    def dock_to_right_of_target_game(self) -> None:
        """이터널시티 **클라이언트 오른**에 맞춤(킬창 왼쪽 = `cr[2]`). 실패 시 외곽 오른."""
        m = self._m
        if sys.platform != "win32" or not self.isVisible():
            return
        if not getattr(m, "running", True):
            return
        try:
            th = resolve_game_only_anchor_hwnd(m)
            if not th:
                if pipela_dev_ui_standby_chrome(m):
                    self.dock_to_standby_dev_pair()
                else:
                    _kc_dock_debug("no anchor hwnd")
                return
            th_i = int(th)
            if not win32gui.IsWindow(th_i):
                _kc_dock_debug(f"anchor not a window: {th_i}")
                return
            # 요구사항: 킬카창 높이 = 클라(앵커) 높이. (compute_side_dock_layout의 h_log 규칙과 동일)
            try:
                h0 = anchor_client_inner_height_logical_qt(m, th_i)
                if h0 is not None and h0 >= 8:
                    self.setFixedHeight(int(h0))
            except Exception:
                pass
            cr = None
            try:
                cr = m.get_window_rect(th_i)
            except Exception as e:
                _kc_dock_debug("get_window_rect failed", err=e)
            cr_sig = None
            if cr and len(cr) >= 4 and cr[2] > cr[0] and cr[3] > cr[1]:
                cr_sig = (int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3]))
            if cr_sig != self._last_anchor_cr_sig:
                self._last_anchor_cr_sig = cr_sig
                self._last_dock_sig = None
                _kc_dock_debug(
                    "anchor client rect changed → invalidate dedupe "
                    + (repr(cr_sig) if cr_sig else "None"),
                )

            self.update()
            lay = compute_side_dock_layout(
                m, th_i, dock_w_log=int(self._dock_w), side="right",
            )
            if lay is None:
                _kc_dock_debug(f"compute_side_dock_layout returned None th={th_i} cr={cr_sig!r}")
                self._last_dock_sig = None
                if self._kc_dock_retry_left < _KC_DOCK_RETRY_MAX:
                    self._kc_dock_retry_left += 1
                    QTimer.singleShot(
                        max(48, min(320, 40 + self._kc_dock_retry_left * 12)),
                        self.dock_to_right_of_target_game,
                    )
                return
            self._kc_dock_retry_left = 0

            if lay.dedupe_sig == self._last_dock_sig:
                return
            self._last_dock_sig = lay.dedupe_sig
            w_log = lay.w_log
            h_log = lay.h_log
            x_log = lay.x_log
            y_log = lay.y_log
            x_phys = lay.x_phys
            y_phys = lay.y_phys
            fw_phys = lay.fw_phys
            fh_phys = lay.fh_phys
            try:
                x_log, y_log, w_log, h_log = clamp_dock_logical_geometry(
                    x_log, y_log, w_log, h_log,
                )
            except Exception as e:
                _kc_dock_debug("clamp geometry failed", err=e)
                return
            try:
                self.setFixedWidth(w_log)
            except Exception as e:
                _kc_dock_debug("setFixedWidth failed", err=e)
                return
            try:
                self.setFixedHeight(h_log)
            except Exception as e:
                _kc_dock_debug("setFixedHeight failed", err=e)
            self.setGeometry(x_log, y_log, w_log, h_log)
            try:
                wid = int(self.winId())
                if not win32gui.IsWindow(wid):
                    _kc_dock_debug(f"kill float winId not valid: {wid}")
                    return
                if not win32gui.IsWindow(th_i):
                    _kc_dock_debug("anchor gone before SetWindowPos")
                    return
                win32_set_window_outer_rect(
                    wid, x_phys, y_phys, fw_phys, fh_phys,
                )
                ah = th_i
                lo = self._last_z_anchor
                sync_docked_chrome_z_order(
                    m,
                    wid,
                    ah,
                    set_owner=(lo != ah),
                    force_z_restack=True,
                )
                self._last_z_anchor = ah
            except Exception as e:
                _kc_dock_debug("win32 outer rect / z-order", err=e)
                if (os.environ.get("PIPELA_DEBUG_KILL_DOCK", "") or "").strip().lower() in (
                    "1", "true", "yes", "on", "y",
                ):
                    traceback.print_exc()
        except Exception as e:
            _kc_dock_debug("dock_to_right_of_target_game top-level", err=e)
            try:
                if (os.environ.get("PIPELA_DEBUG_KILL_DOCK", "") or "").strip().lower() in (
                    "1", "true", "yes", "on", "y",
                ):
                    traceback.print_exc()
            except Exception:
                pass
