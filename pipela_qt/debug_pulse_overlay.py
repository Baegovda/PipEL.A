"""킬/템플릿 감지 디버그 큐(`pipela_mod` 전역)를 Qt에서 펄스 오버레이로 표시.

- `_template_debug_overlay_queue`: 템플릿 「감지」1회 박스·점수
- `_kill_counter_overlay_queue`: 킬카운터 OCR 라벨/숫자 영역 펄스
"""

from __future__ import annotations

import ctypes
import queue
import sys
import time
from typing import Any, Optional

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from pipela_core.display_timing import display_tick_ms
from pipela_qt.dpi import win32_dpi_scale_for_hwnd, win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay_chrome import (
    paint_debug_kill_counter_boxes,
    paint_debug_template_match,
)
from pipela_qt.qt_fonts import app_default_qfont


def _dpi_scale_for_hwnd(pipela_mod: Any, hwnd: int) -> float:
    if sys.platform != "win32" or not hwnd:
        return 1.0
    try:
        sc = float(win32_dpi_scale_for_hwnd(pipela_mod, int(hwnd)))
        return sc if sc > 0.01 else 1.0
    except Exception:
        return 1.0


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


def _client_ltrb_to_screen(
    pipela_mod: Any,
    hwnd: int | None,
    l: float,
    t: float,
    r: float,
    b: float,
) -> tuple[int, int, int, int] | None:
    if not hwnd:
        return None
    gr = pipela_mod.get_window_rect(hwnd)
    if not gr:
        return None
    ox, oy = int(gr[0]), int(gr[1])
    sl, st = ox + int(round(l)), oy + int(round(t))
    sr, sb = ox + int(round(r)), oy + int(round(b))
    if sr <= sl:
        sr = sl + 2
    if sb <= st:
        sb = st + 2
    return (sl, st, sr, sb)


def _hwnd_for_template_kind(pipela_mod: Any, kind: str | None) -> int | None:
    if kind == "start_game_launcher":
        return pipela_mod.refresh_smart_updater_hwnd_if_needed()
    pipela_mod.refresh_target_hwnd_if_needed()
    th = pipela_mod.target_hwnd
    return int(th) if th else None


class QtDebugPulseOverlay(QWidget):
    def __init__(self, pipela_mod: Any) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._mode: str | None = None
        self._t0: float | None = None
        self._kind: str | None = None
        self._caption: str | None = None
        self._box_main: Optional[tuple[int, int, int, int]] = None
        self._box_num: Optional[tuple[int, int, int, int]] = None
        self._hue_index = 0

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._poll_queues)
        self._poll.start(max(16, int(pipela_mod.pipela_kill_counter_overlay_poll_ms())))

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._anim_step)
        self.hide()

    def _defer_raise(self) -> None:
        if sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    _win32_set_topmost_no_activate(wid)
            except Exception:
                pass
        try:
            self.raise_()
        except Exception:
            pass

    def _poll_queues(self) -> None:
        if not getattr(self._pl, "running", True):
            return
        tmpl = None
        q1 = getattr(self._pl, "_template_debug_overlay_queue", None)
        if q1 is not None:
            try:
                while True:
                    tmpl = q1.get_nowait()
            except queue.Empty:
                pass
        kc = None
        q2 = getattr(self._pl, "_kill_counter_overlay_queue", None)
        if q2 is not None:
            try:
                while True:
                    kc = q2.get_nowait()
            except queue.Empty:
                pass
        if tmpl is not None:
            self._start_template(tmpl)
        elif kc is not None:
            self._start_kc(kc)

    def _start_template(self, item: object) -> None:
        if not isinstance(item, tuple) or len(item) < 3:
            return
        rect, cap, kind = item[0], item[1], item[2]
        if rect is None:
            return
        hwnd = _hwnd_for_template_kind(self._pl, kind if isinstance(kind, str) else None)
        if not hwnd:
            return
        hwnd = int(hwnd)
        sc = _dpi_scale_for_hwnd(self._pl, hwnd)
        scr = _client_ltrb_to_screen(self._pl, hwnd, *rect)
        if not scr:
            return
        sl, st, sr, sb = scr
        cap_extra_phys = 28 if cap else 0
        bw_phys = max(8, sr - sl)
        bh_phys = max(8, (sb - st) + cap_extra_phys)
        xl, yl, bwl, bhl = win32_physical_screen_rect_to_qt_overlay_geometry(
            self._pl, hwnd, sl, st, bw_phys, bh_phys,
        )
        self._mode = "template"
        self._kind = kind if isinstance(kind, str) else None
        self._caption = str(cap) if cap else None
        self._box_main = (
            0,
            0,
            max(1, int(round((sr - sl) / sc))),
            max(1, int(round((sb - st) / sc))),
        )
        self._box_num = None
        self.setGeometry(xl, yl, bwl, bhl)
        self._arm_anim()

    def _start_kc(self, item: object) -> None:
        if not isinstance(item, tuple):
            return
        label_r, num_r = item[0], item[1]
        self._pl.refresh_target_hwnd_if_needed()
        hwnd = self._pl.target_hwnd
        if not hwnd:
            return
        hwnd = int(hwnd)
        sc = _dpi_scale_for_hwnd(self._pl, hwnd)
        scr_boxes: list[tuple[int, int, int, int]] = []
        for r in (label_r, num_r):
            if r is None:
                continue
            l, t, r2, b = r
            scr = _client_ltrb_to_screen(self._pl, hwnd, l, t, r2, b)
            if scr:
                scr_boxes.append(scr)
        if not scr_boxes:
            return
        pad = 4
        sl = min(s[0] for s in scr_boxes) - pad
        st = min(s[1] for s in scr_boxes) - pad
        sr = max(s[2] for s in scr_boxes) + pad
        sb = max(s[3] for s in scr_boxes) + pad

        self._mode = "kc"
        self._kind = None
        self._caption = None
        self._box_main = None
        self._box_num = None
        if label_r:
            scr = _client_ltrb_to_screen(self._pl, hwnd, *label_r)
            if scr:
                self._box_main = (
                    int(round((scr[0] - sl) / sc)),
                    int(round((scr[1] - st) / sc)),
                    max(1, int(round((scr[2] - scr[0]) / sc))),
                    max(1, int(round((scr[3] - scr[1]) / sc))),
                )
        if num_r:
            scr = _client_ltrb_to_screen(self._pl, hwnd, *num_r)
            if scr:
                self._box_num = (
                    int(round((scr[0] - sl) / sc)),
                    int(round((scr[1] - st) / sc)),
                    max(1, int(round((scr[2] - scr[0]) / sc))),
                    max(1, int(round((scr[3] - scr[1]) / sc))),
                )
        bw_phys = max(8, sr - sl)
        bh_phys = max(8, sb - st)
        xl, yl, bwl, bhl = win32_physical_screen_rect_to_qt_overlay_geometry(
            self._pl, hwnd, sl, st, bw_phys, bh_phys,
        )
        self.setGeometry(xl, yl, bwl, bhl)
        self._arm_anim()

    def _arm_anim(self) -> None:
        self._t0 = time.monotonic()
        self._hue_index = 0
        self.show()
        QTimer.singleShot(0, self._defer_raise)
        self._anim.stop()
        self._anim.start(max(8, int(display_tick_ms())))

    def _anim_step(self) -> None:
        t0 = self._t0
        if t0 is None or self._mode is None:
            self._anim.stop()
            self.hide()
            return
        ph = int((time.monotonic() - float(t0)) / 0.25)
        if ph >= 12:
            self._anim.stop()
            self._mode = None
            self._t0 = None
            self.hide()
            return
        self._hue_index = ph % 6
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._mode == "template" and self._box_main:
            x, y, w, h = self._box_main
            kind = self._kind or "ride_target"
            t_sec = time.time()
            paint_debug_template_match(
                p,
                x,
                y,
                w,
                h,
                pipela_mod=self._pl,
                kind=kind,
                t_sec=t_sec,
            )
            cap = self._caption
            if cap:
                p.setFont(app_default_qfont(12, QFont.Weight.Bold))
                cap_r = QRect(0, y + h, self.width(), 24)
                p.setPen(QColor("#000000"))
                p.drawText(cap_r.translated(1, 1), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, cap)
                p.setPen(QColor("#ffffff"))
                p.drawText(cap_r, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, cap)
        elif self._mode == "kc":
            kc_fg = str(getattr(self._pl, "KILL_COUNTER_DETECTED_NUM_FG", "#52E6DA"))
            paint_debug_kill_counter_boxes(
                p,
                self._box_main,
                self._box_num,
                kc_edge_hex=kc_fg,
                phase=self._hue_index,
            )
