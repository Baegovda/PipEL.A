"""저장된 감지 ROI를 게임 창 위에 표시 — Qt 전용."""

from __future__ import annotations

import sys
import time
from typing import Any, Optional

import win32gui
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from pipela_core.display_timing import display_tick_ms
from pipela_core.win32_window_ops import (
    set_window_z_order_directly_above,
    win32_set_window_owner,
    win32_set_window_topmost,
)
from pipela_qt.dpi import win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay_chrome import paint_region_preview_box

_active_preview: Optional["QtRegionPreviewOverlay"] = None


def qt_region_preview_overlay_active() -> bool:
    return _active_preview is not None


def qt_region_preview_current_kind() -> str | None:
    if _active_preview is None:
        return None
    return getattr(_active_preview, "_region_type", None)


def close_qt_region_preview_overlay() -> None:
    global _active_preview
    o = _active_preview
    if o is None:
        return
    _active_preview = None
    try:
        o._timer.stop()
    except Exception:
        pass
    try:
        o.hide()
        o.deleteLater()
    except Exception:
        pass


def close_qt_region_preview_if_active(kind: str) -> bool:
    if _active_preview is None or getattr(_active_preview, "_region_type", None) != kind:
        return False
    close_qt_region_preview_overlay()
    return True


def qt_region_preview_toggle(pipela_mod: Any, region_type: str, label: str) -> bool:
    """
    QApplication 있을 때만 True 반환(처리됨). 별도 루트 윈도우 없음.
    """
    global _active_preview
    if QApplication.instance() is None:
        return False

    if region_type == "start_game_launcher":
        if not pipela_mod.refresh_smart_updater_hwnd_if_needed():
            print(f"[{label}] 스마트업데이터 창 없음", flush=True)
            return True
    elif not pipela_mod.target_hwnd:
        print(f"[{label}] window?", flush=True)
        return True

    if _active_preview is not None and getattr(_active_preview, "_region_type", None) == region_type:
        close_qt_region_preview_overlay()
        print(f"[{label}] preview OFF", flush=True)
        pipela_mod._region_preview_persist_set(None)
        return True

    closed_other = _active_preview is not None
    if closed_other:
        close_qt_region_preview_overlay()

    rp = pipela_mod._region_preview_client_rect_pixels(region_type)
    if region_type == "start_game_launcher":
        uh = pipela_mod.refresh_smart_updater_hwnd_if_needed()
        if not uh or not rp:
            print(f"[{label}] region load FAIL", flush=True)
            if closed_other:
                pipela_mod._region_preview_persist_set(None)
            return True
        rect = pipela_mod.get_window_rect(uh)
        if not rect:
            print(f"[{label}] region load FAIL", flush=True)
            if closed_other:
                pipela_mod._region_preview_persist_set(None)
            return True
        rx, ry, rw, rh = rp
        if rw < 2 or rh < 2:
            print(f"[{label}] region small", flush=True)
            if closed_other:
                pipela_mod._region_preview_persist_set(None)
            return True
        sx = int(rect[0] + rx)
        sy = int(rect[1] + ry)
        anchor_hwnd = int(uh)
    else:
        rect = pipela_mod.get_window_rect(pipela_mod.target_hwnd)
        if not rp or not rect:
            print(f"[{label}] region load FAIL", flush=True)
            if closed_other:
                pipela_mod._region_preview_persist_set(None)
            return True
        rx, ry, rw, rh = rp
        if rw < 2 or rh < 2:
            print(f"[{label}] region small", flush=True)
            if closed_other:
                pipela_mod._region_preview_persist_set(None)
            return True
        sx = int(rect[0] + rx)
        sy = int(rect[1] + ry)
        anchor_hwnd = int(pipela_mod.target_hwnd)

    rw_i = max(1, int(rw))
    rh_i = max(1, int(rh))
    qx, qy, qw, qh = win32_physical_screen_rect_to_qt_overlay_geometry(
        pipela_mod, anchor_hwnd, sx, sy, rw_i, rh_i,
    )
    _active_preview = QtRegionPreviewOverlay(pipela_mod, region_type, label)
    _active_preview.setGeometry(qx, qy, qw, qh)
    _active_preview.show()
    QTimer.singleShot(0, _active_preview._defer_apply_stack_above_anchor)

    saved_region = pipela_mod._region_roi_global_get(region_type)
    print(
        f"[{label}] preview ON" + (" (전체 클라이언트)" if not saved_region else ""),
        flush=True,
    )
    pipela_mod._region_preview_persist_set(region_type)
    return True


class QtRegionPreviewOverlay(QWidget):
    def __init__(self, pipela_mod: Any, region_type: str, label: str) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._region_type = region_type
        self._label = label
        self._t = time.time()

        # 전역 StaysOnTop + TOPMOST 는 다른 모니터·창 위까지 덮어 «게임창만» 보이게 맞지 않음 —
        # Win32 에서는 앵커·게임 오버레이·Z-order 로만 올린다.
        _flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        if sys.platform != "win32":
            _flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # 픽셀 알파(반투명)는 `overlay_chrome.paint_region_preview_box` — 창 투과와 혼동 방지
        self.setWindowOpacity(1.0)
        self._last_owner_anchor: int | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, e):
        super().showEvent(e)
        self._timer.start(display_tick_ms())

    def hideEvent(self, e):
        try:
            self._timer.stop()
        except Exception:
            pass
        super().hideEvent(e)

    def _current_anchor_hwnd(self) -> int | None:
        m = self._pl
        if self._region_type == "start_game_launcher":
            uh = m.refresh_smart_updater_hwnd_if_needed()
            return int(uh) if uh else None
        th = m.refresh_target_hwnd_if_needed()
        return int(th) if th else None

    def _apply_stack_above_anchor(self) -> None:
        """게임(또는 런처) + 검정 게임 오버레이 **바로 위**만 — 전체 화면 TOPMOST 사용 안 함."""
        if sys.platform != "win32":
            try:
                self.raise_()
            except Exception:
                pass
            return
        try:
            wid = int(self.winId())
            if not wid or not win32gui.IsWindow(wid):
                return
            anchor = self._current_anchor_hwnd()
            if not anchor or not win32gui.IsWindow(anchor):
                return
            win32_set_window_topmost(wid, False)
            if self._last_owner_anchor != anchor:
                win32_set_window_owner(wid, anchor)
                self._last_owner_anchor = anchor
            m = self._pl
            ov = getattr(m, "_qt_game_overlay", None)
            if ov is not None:
                try:
                    oid = int(ov.winId())
                    if win32gui.IsWindow(oid):
                        set_window_z_order_directly_above(oid, anchor)
                        set_window_z_order_directly_above(wid, oid)
                    else:
                        set_window_z_order_directly_above(wid, anchor)
                except Exception:
                    set_window_z_order_directly_above(wid, anchor)
            else:
                set_window_z_order_directly_above(wid, anchor)
        except Exception:
            pass
        try:
            self.raise_()
        except Exception:
            pass

    def _defer_apply_stack_above_anchor(self) -> None:
        self._apply_stack_above_anchor()

    def _tick(self) -> None:
        global _active_preview
        if _active_preview is not self:
            return
        rp = self._pl._region_preview_client_rect_pixels(self._region_type)
        if not rp:
            self._timer.stop()
            return
        rx, ry, rw, rh = rp
        rk = self._region_type
        if rk == "start_game_launcher":
            uh = self._pl.refresh_smart_updater_hwnd_if_needed()
            if not uh:
                self._timer.stop()
                return
            rect = self._pl.get_window_rect(uh)
            if not rect:
                self._timer.stop()
                return
            sx = int(rect[0] + rx)
            sy = int(rect[1] + ry)
        else:
            if not self._pl.target_hwnd:
                self._timer.stop()
                return
            rect = self._pl.get_window_rect(self._pl.target_hwnd)
            if not rect:
                self._timer.stop()
                return
            sx = int(rect[0] + rx)
            sy = int(rect[1] + ry)
        rw_i = max(1, int(rw))
        rh_i = max(1, int(rh))
        if rw_i < 2 or rh_i < 2:
            self._timer.stop()
            return
        anchor = int(uh) if rk == "start_game_launcher" else int(self._pl.target_hwnd)
        qx, qy, qw, qh = win32_physical_screen_rect_to_qt_overlay_geometry(
            self._pl, anchor, sx, sy, rw_i, rh_i,
        )
        self.setGeometry(qx, qy, qw, qh)
        self._t = time.time()
        self._apply_stack_above_anchor()
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        w = max(2, self.width())
        h = max(2, self.height())
        t = float(self._t)
        paint_region_preview_box(
            p,
            w,
            h,
            pipela_mod=self._pl,
            t_sec=t,
        )
