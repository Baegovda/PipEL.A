"""게임 창 위 템플릿 PNG 드래그 캡처 — Qt 전용."""

from __future__ import annotations

import ctypes
import sys
from typing import Any, Callable, Optional

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from pipela_core.template_capture_region import (
    capture_drag_rect_to_pil_rgb,
    crop_drag_rect_from_full_bgr_to_pil_rgb,
    drag_rect_exceeds_min_size,
)
from pipela_core.vision_lazy import ensure_cv2_numpy_mss
from pipela_qt import theme as T
from pipela_qt.capture_freeze_frame import build_capture_freeze_assets
from pipela_qt.dpi import win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay_chrome import (
    OVERLAY_FULL_WINDOW_OPACITY,
    overlay_full_dim_color,
    paint_selection_drag_rect,
)

_active_overlay: Optional["QtTemplateCaptureOverlay"] = None


def qt_template_capture_overlay_active() -> bool:
    return _active_overlay is not None


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


def close_qt_template_capture_overlay() -> None:
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


def qt_template_capture_start(
    pipela_mod: Any,
    kind: str,
    label: str,
    on_applied: Callable[..., Any] | None = None,
) -> bool:
    """
    Qt 앱이 뜬 상태에서 템플릿 캡처 드래그를 연다(같은 kind면 토글로 닫음).
    QApplication 없으면 False.
    """
    global _active_overlay
    if QApplication.instance() is None:
        return False

    if _active_overlay is not None and getattr(_active_overlay, "_kind", None) == kind:
        print(f"[{label}] 지정 취소", flush=True)
        close_qt_template_capture_overlay()
        return True

    if _active_overlay is not None:
        close_qt_template_capture_overlay()

    meta = pipela_mod._template_capture_kind_meta(kind)
    if meta is None:
        print("[캡처] 알 수 없는 종류", flush=True)
        return True

    if kind != "start_game_launcher" and not pipela_mod.target_hwnd:
        print(f"[{label}] 게임 창 없음", flush=True)
        return True

    if kind == "start_game_launcher":
        uh = pipela_mod.refresh_smart_updater_hwnd_if_needed()
        if not uh:
            _set_select_mode(pipela_mod, False)
            print(f"[{label}] 스마트업데이터 창 없음 — 창을 연 뒤 다시 시도", flush=True)
            return True
        rect = pipela_mod.get_window_rect(uh)
        hwnd = uh
    else:
        rect = pipela_mod.get_window_rect(pipela_mod.target_hwnd)
        hwnd = pipela_mod.target_hwnd

    if not rect:
        _set_select_mode(pipela_mod, False)
        print(f"[{label}] 창 좌표 실패", flush=True)
        return True
    wx, wy, wx2, wy2 = rect
    win_w, win_h = wx2 - wx, wy2 - wy
    if win_w < 2 or win_h < 2:
        _set_select_mode(pipela_mod, False)
        print(f"[{label}] 창 크기 실패", flush=True)
        return True

    _active_overlay = QtTemplateCaptureOverlay(
        pipela_mod,
        kind,
        label,
        int(hwnd),
        int(wx),
        int(wy),
        int(win_w),
        int(win_h),
        on_applied,
    )
    _set_select_mode(pipela_mod, True)
    pipela_mod._template_capture_active_kind = kind
    print(f"[{label}] 드래그로 캡처 영역 지정 (Esc 취소)", flush=True)
    _active_overlay.show()
    QTimer.singleShot(0, _active_overlay._defer_raise_topmost)
    return True


class QtTemplateCaptureOverlay(QWidget):
    def __init__(
        self,
        pipela_mod: Any,
        kind: str,
        label: str,
        hwnd: int,
        wx: int,
        wy: int,
        win_w: int,
        win_h: int,
        on_applied: Callable[..., Any] | None,
    ) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._kind = kind
        self._label = label
        self._hwnd = hwnd
        wxl, wyl, wwl, whl = win32_physical_screen_rect_to_qt_overlay_geometry(
            pipela_mod, hwnd, wx, wy, win_w, win_h,
        )
        self._win_w = wwl
        self._win_h = whl
        self._on_applied = on_applied

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

        self._freeze_bgr, self._freeze_px = build_capture_freeze_assets(int(hwnd))
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
            self._pl._template_capture_active_kind = None
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
            print(f"[{self._label}] 캡처 취소", flush=True)
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
        if self._freeze_px is not None:
            p.drawPixmap(self.rect(), self._freeze_px)
            dim = QColor(T.PANEL_BG)
            dim.setAlpha(85)
            p.fillRect(self.rect(), dim)
        else:
            p.fillRect(self.rect(), overlay_full_dim_color())
        if self._sel_rect is not None and self._sel_rect.width() >= 2 and self._sel_rect.height() >= 2:
            paint_selection_drag_rect(p, self._sel_rect, pipela_mod=self._pl)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.RightButton:
            print(f"[{self._label}] 캡처 취소 (우클릭)", flush=True)
            global _active_overlay
            if _active_overlay is self:
                _active_overlay = None
            self._cleanup_state()
            self.hide()
            self.deleteLater()
            return
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
        hwnd = self._hwnd
        win_w_f = float(self._win_w)
        win_h_f = float(self._win_h)
        label = self._label
        kind = self._kind
        on_applied = self._on_applied
        ech = self._pl

        global _active_overlay
        if _active_overlay is self:
            _active_overlay = None

        if not drag_rect_exceeds_min_size(float(w), float(h)):
            print(f"[{label}] 영역이 너무 작음", flush=True)
            self._cleanup_state()
            self.hide()
            self.deleteLater()
            return

        self._cleanup_state()
        self.hide()
        self.deleteLater()

        pil = None
        if self._freeze_bgr is not None:
            pil = crop_drag_rect_from_full_bgr_to_pil_rgb(
                self._freeze_bgr,
                hwnd,
                float(x0),
                float(y0),
                float(w),
                float(h),
                win_w_f,
                win_h_f,
            )
        if pil is None:
            _, _, mss_mod = ensure_cv2_numpy_mss()
            sct = mss_mod.mss()
            try:
                pil = capture_drag_rect_to_pil_rgb(
                    hwnd, sct, float(x0), float(y0), float(w), float(h), win_w_f, win_h_f,
                )
            finally:
                try:
                    sct.close()
                except Exception:
                    pass

        if pil is None:
            print(f"[{label}] 화면 캡처 실패", flush=True)
            return

        from pipela_qt.template_capture_confirm import show_template_capture_confirm_qt

        show_template_capture_confirm_qt(ech, kind, pil, on_applied=on_applied)
