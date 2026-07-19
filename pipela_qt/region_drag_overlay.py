"""게임/런처 클라이언트 위 드래그 영역 선택 — Qt 전용."""

from __future__ import annotations

import ctypes
import sys
from typing import Optional

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from pipela_core.template_capture_region import (
    drag_rect_exceeds_min_size,
    normalized_roi_xywh_from_drag_rect,
)
from pipela_qt import theme as T
from pipela_qt.capture_freeze_frame import build_capture_freeze_assets
from pipela_qt.dpi import win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay_chrome import (
    OVERLAY_FULL_WINDOW_OPACITY,
    overlay_full_dim_color,
    paint_selection_drag_rect,
)

_active_overlay: Optional["QtClientRegionSelectOverlay"] = None


def _win32_set_topmost_no_activate(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    try:
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            int(hwnd),
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except Exception:
        pass


def close_qt_region_select_overlay() -> None:
    """활성 Qt 영역 선택 오버레이를 닫고 select_mode·active_type 정리."""
    global _active_overlay
    o = _active_overlay
    if o is None:
        return
    _active_overlay = None


def _set_select_mode(pipela_mod, enabled: bool) -> None:
    if hasattr(pipela_mod, "_state_set"):
        pipela_mod._state_set("select_mode", bool(enabled))
    else:
        pipela_mod.select_mode = bool(enabled)
    try:
        o._cleanup_state()
    except Exception:
        pass
    try:
        o.hide()
        o.deleteLater()
    except Exception:
        pass


def qt_region_select_start(pipela_mod, region_type: str, label: str) -> bool:
    """
    Qt 앱이 뜬 상태에서 영역 선택을 연다(또는 같은 종류면 토글로 닫는다).
    `main.start_region_select` 에서 호출 — QApplication 없으면 False.
    """
    global _active_overlay
    if QApplication.instance() is None:
        return False

    if _active_overlay is not None and getattr(_active_overlay, "_region_type", None) == region_type:
        print(f"[{label}] 선택 취소", flush=True)
        close_qt_region_select_overlay()
        return True

    if _active_overlay is not None:
        close_qt_region_select_overlay()

    if region_type == "start_game_launcher":
        uh = pipela_mod.refresh_smart_updater_hwnd_if_needed()
        if not uh:
            print(f"[{label}] 스마트업데이터 창 없음", flush=True)
            return True
        rect = pipela_mod.get_window_rect(uh)
        hwnd = uh
    else:
        th = pipela_mod.refresh_target_hwnd_if_needed()
        if not th:
            print(f"[{label}] window?", flush=True)
            return True
        rect = pipela_mod.get_window_rect(th)
        hwnd = th

    if not rect:
        print(f"[{label}] window?", flush=True)
        return True
    wx, wy, wx2, wy2 = rect
    win_w, win_h = wx2 - wx, wy2 - wy
    if win_w < 2 or win_h < 2:
        print(f"[{label}] 창 크기 실패", flush=True)
        return True

    _active_overlay = QtClientRegionSelectOverlay(
        pipela_mod, region_type, int(hwnd), int(wx), int(wy), int(win_w), int(win_h), label,
    )
    _set_select_mode(pipela_mod, True)
    pipela_mod._region_select_active_type = region_type
    print(f"[{label}] drag → region", flush=True)
    _active_overlay.show()
    QTimer.singleShot(0, _active_overlay._defer_raise_topmost)
    return True


class QtClientRegionSelectOverlay(QWidget):
    def __init__(
        self,
        pipela_mod,
        region_type: str,
        hwnd: int,
        wx: int,
        wy: int,
        win_w: int,
        win_h: int,
        label: str,
    ) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._region_type = region_type
        self._hwnd = hwnd
        wxl, wyl, wwl, whl = win32_physical_screen_rect_to_qt_overlay_geometry(
            pipela_mod, hwnd, wx, wy, win_w, win_h,
        )
        self._win_w = wwl
        self._win_h = whl
        self._label = label

        self._dragging = False
        self._origin = QPoint(0, 0)
        self._corner = QPoint(0, 0)
        self._sel_rect: Optional[QRect] = None

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowOpacity(OVERLAY_FULL_WINDOW_OPACITY)
        self.setGeometry(wxl, wyl, wwl, whl)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        _, self._freeze_px = build_capture_freeze_assets(int(hwnd))
        if self._freeze_px is not None:
            self.setWindowOpacity(1.0)

    def _defer_raise_topmost(self) -> None:
        if sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    _win32_set_topmost_no_activate(wid)
            except Exception:
                pass
        try:
            self.raise_()
            self.activateWindow()
            self.setFocus(Qt.FocusReason.PopupFocusReason)
        except Exception:
            pass

    def _cleanup_state(self) -> None:
        _set_select_mode(self._pl, False)
        try:
            self._pl._region_select_active_type = None
        except Exception:
            pass

    def closeEvent(self, e):
        global _active_overlay
        if _active_overlay is self:
            _active_overlay = None
        self._cleanup_state()
        super().closeEvent(e)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Escape:
            print(f"[{self._label}] 선택 취소 (Esc)", flush=True)
            global _active_overlay
            if _active_overlay is self:
                _active_overlay = None
            self._cleanup_state()
            self.hide()
            self.deleteLater()
            return
        super().keyPressEvent(e)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        if getattr(self, "_freeze_px", None) is not None:
            p.drawPixmap(self.rect(), self._freeze_px)
            dim = QColor(T.PANEL_BG)
            dim.setAlpha(85)
            p.fillRect(self.rect(), dim)
        else:
            p.fillRect(self.rect(), overlay_full_dim_color())
        if self._sel_rect is not None and self._sel_rect.width() >= 2 and self._sel_rect.height() >= 2:
            paint_selection_drag_rect(p, self._sel_rect, pipela_mod=self._pl)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._dragging = True
        self._origin = QPoint(int(e.position().x()), int(e.position().y()))
        self._corner = self._origin
        self._sel_rect = QRect(self._origin, self._origin).normalized()
        self.update()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if not self._dragging:
            return
        x = max(0, min(int(e.position().x()), max(1, self._win_w - 1)))
        y = max(0, min(int(e.position().y()), max(1, self._win_h - 1)))
        self._corner = QPoint(x, y)
        self._sel_rect = QRect(self._origin, self._corner).normalized()
        self.update()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if not self._dragging:
            return
        self._dragging = False
        x = max(0, min(int(e.position().x()), max(1, self._win_w - 1)))
        y = max(0, min(int(e.position().y()), max(1, self._win_h - 1)))
        x0 = min(self._origin.x(), x)
        y0 = min(self._origin.y(), y)
        w = abs(x - self._origin.x())
        h = abs(y - self._origin.y())

        global _active_overlay
        if _active_overlay is self:
            _active_overlay = None

        if drag_rect_exceeds_min_size(float(w), float(h)):
            region_data = normalized_roi_xywh_from_drag_rect(
                float(x0), float(y0), float(w), float(h),
                float(self._win_w), float(self._win_h),
            )
            self._pl._region_roi_global_set(self._region_type, region_data)
            self._pl.schedule_save_config()
            print(f"[{self._label}] region OK", flush=True)
        else:
            print(f"[{self._label}] region small", flush=True)

        self._cleanup_state()
        self.hide()
        self.deleteLater()
