"""Qt 전용 커서 HUD(이동/사격/탑승 아이콘) + Flame 패널 + Flame 시작 배너.

`pipela_mod` 전역(플레임·배너 상수·큐)을 읽는다.
"""

from __future__ import annotations

import ctypes
import math
import os
import queue
import sys
import threading
import time

import win32con
import win32gui
from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QLabel, QWidget

from pipela_core.display_timing import ui_anim_tick_ms_for_pipela, ui_anim_tick_ms_for_qwidget
from pipela_core.paths import FLAME_TRIGGER_CURSOR_HUD_ICON_PATH
from pipela_core.win32_window_ops import win32_native_root_hwnd_from_child
from pipela_qt.dpi import win32_dpi_scale_for_hwnd, win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay import _win32_apply_black_colorkey
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.ui_adaptive import qss_pad_vh, scale_px_h, scale_px_v
from pipela_qt.dcomp_hud import DCompHud, dcomp_hud_enabled

_HIDDEN = (-10000, -10000, 1, 1)

_CURSOR_HUD_HOOK_EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

# HUD 틱 주기가 짧아 ``refresh_target_hwnd_if_needed`` 가 과호출되기 쉬움 — 짧은 TTL 로만 재사용
_CURSOR_HUD_TH_CACHE_S = max(
    0.0,
    float(os.environ.get("PIPELA_CURSOR_HUD_TH_CACHE_MS", "42") or 42) / 1000.0,
)
_cursor_hud_th_mono: float = 0.0
_cursor_hud_th: int | None = None

_CURSOR_HUD_FORCE_OUTER_RECT = str(
    os.environ.get("PIPELA_CURSOR_HUD_FORCE_OUTER_RECT", "0"),
).strip().lower() in ("1", "true", "yes", "on", "y")
_CURSOR_HUD_TOPMOST_REFRESH_SEC = max(
    0.05,
    float(os.environ.get("PIPELA_CURSOR_HUD_TOPMOST_REFRESH_MS", "220") or 220) / 1000.0,
)


def _cursor_hud_target_hwnd(m) -> int | None:
    global _cursor_hud_th_mono, _cursor_hud_th
    if _CURSOR_HUD_TH_CACHE_S <= 0.0:
        return m.refresh_target_hwnd_if_needed()
    now = time.monotonic()
    th = _cursor_hud_th
    if th is not None and (now - _cursor_hud_th_mono) < _CURSOR_HUD_TH_CACHE_S:
        try:
            if win32gui.IsWindow(int(th)):
                return th
        except Exception:
            pass
    th2 = m.refresh_target_hwnd_if_needed()
    try:
        _cursor_hud_th = int(th2) if th2 else None
    except Exception:
        _cursor_hud_th = None
    _cursor_hud_th_mono = time.monotonic()
    return th2


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _try_get_cursor_pos_physical() -> tuple[int, int] | None:
    """``GetCursorPos`` 실패 시 None — pywin32 튜플만 쓰면 실패·독점 모드에서 (0,0) 유령값이 들어올 수 있음."""
    if sys.platform != "win32":
        return None
    pt = _POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return None
    return int(pt.x), int(pt.y)


def _win32_foreground_belongs_to_target(fg_hwnd: int, target_hwnd: int) -> bool:
    """포그라운드 HWND가 이터널시티 타깃과 동일 세션인지(자식·루트·소유 팝업).

    일부 클라이언트는 포커스를 자식 HWND에 두어 ``GetForegroundWindow() == target`` 만으로는 실패한다.
    """
    if sys.platform != "win32" or not fg_hwnd or not target_hwnd:
        return False
    try:
        fg = int(fg_hwnd)
        th = int(target_hwnd)
        if fg == th:
            return True
        root = win32_native_root_hwnd_from_child(fg)
        if root == th:
            return True
        owner = win32gui.GetWindow(fg, win32con.GW_OWNER)
        if owner == th:
            return True
    except Exception:
        pass
    return False


def _physical_point_in_window_rect(
    xy: tuple[int, int],
    rect: tuple[int, int, int, int] | None,
) -> bool:
    if rect is None:
        return False
    x, y = int(xy[0]), int(xy[1])
    L, T, R, B = (int(rect[i]) for i in range(4))
    return L <= x <= R and T <= y <= B


def _win32_topmost_no_activate(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    user32 = ctypes.windll.user32
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )


def _cursor_hud_native_click_through(hwnd: int) -> None:
    """레이어드 커서 HUD HWND — Win32 ``WS_EX_TRANSPARENT`` 로 아래 게임까지 클릭 통과.

    Qt ``WA_TransparentForMouseEvents`` 만으로는 레이어드/컬러키 창에서 히트가 남는 경우가 있어 FT·아이콘 공통으로 사용.
    """

    if sys.platform != "win32" or not hwnd:
        return
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        user32 = ctypes.windll.user32
        hwnd = int(hwnd)
        if not user32.IsWindow(hwnd):
            return
        ex = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
        if (ex & WS_EX_TRANSPARENT) != 0:
            return
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_TRANSPARENT)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


def _scaled_icon(
    path: str,
    *,
    design_px: float = 40,
    lo: int = 20,
    hi: int = 64,
) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None
    pm = QPixmap(path)
    if pm.isNull():
        return None
    s = scale_px_v(design_px, lo=lo, hi=hi)
    return pm.scaled(
        s,
        s,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _flame_panel_metrics_three_lines(
    line1: str, line2: str, line3: str,
) -> tuple[int, int, int, int, int]:
    f1 = app_default_qfont(11, QFont.Weight.Bold)
    f2 = app_default_qfont(10)
    fm1 = QFontMetrics(f1)
    fm2 = QFontMetrics(f2)
    w = max(
        fm1.horizontalAdvance(line1),
        fm2.horizontalAdvance(line2),
        fm2.horizontalAdvance(line3),
    )
    gap = scale_px_v(4)
    pad_x = scale_px_h(12)
    pad_y = scale_px_v(10)
    inner_h = fm1.height() + gap + fm2.height() + gap + fm2.height()
    pw = max(8, w + 2 * pad_x)
    ph = max(8, inner_h + 2 * pad_y)
    return pw, ph, pad_x, pad_y, gap


def _draw_chromatic_aberration_text(
    p: QPainter,
    rc: QRect,
    align: int,
    text: str,
    *,
    phase: float,
    dx: int,
    dy: int,
    base_alpha: float,
) -> None:
    """Draw text with strong RGB-split / chromatic aberration feel."""
    if not text:
        return
    base_alpha = max(0.0, min(1.0, float(base_alpha)))
    dx = int(dx)
    dy = int(dy)
    ph = float(phase) % 1.0

    # 3 passes: left/right chroma + core
    passes: list[tuple[int, int, float, float, float]] = [
        (+dx, 0, (ph + 0.02) % 1.0, 0.95, base_alpha * 0.55),
        (0, 0, (ph + 0.12) % 1.0, 0.92, base_alpha * 0.85),
        (-dx, dy, (ph + 0.22) % 1.0, 0.95, base_alpha * 0.55),
    ]

    p.save()
    try:
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
    except Exception:
        pass
    for ox, oy, hue, sat, a in passes:
        if a <= 0.001:
            continue
        p.setPen(QColor.fromHsvF(float(hue), float(sat), 1.0, float(a)))
        p.drawText(rc.translated(int(ox), int(oy)), align, text)
    p.restore()


# Flame HUD · Flame 시작 배너 — 무지개 파스텔 (HSV, Qt 0–255)
FLAME_HUD_RAINBOW_SAT = 78
FLAME_HUD_RAINBOW_VAL = 255


def _flame_hud_rainbow_gradient(
    x_left: float,
    x_right: float,
    phase: float,
    *,
    phase_off: float = 0.0,
) -> QLinearGradient:
    g = QLinearGradient(x_left, 0.0, x_right, 0.0)
    for i, t in enumerate((0.0, 0.2, 0.4, 0.6, 0.8, 1.0)):
        c = QColor()
        c.setHsv(
            int((phase + phase_off + i * 55.0) % 360),
            FLAME_HUD_RAINBOW_SAT,
            FLAME_HUD_RAINBOW_VAL,
            255,
        )
        g.setColorAt(t, c)
    return g


class _FlameTriggerHudPanel(QWidget):
    """검은 반투명 박스 + 무지개 그라데이션(애니) 텍스트 3줄."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line1 = ""
        self._line2 = ""
        self._line3 = ""
        self._phase = 0.0
        self._pad_x = scale_px_h(12)
        self._pad_y = scale_px_v(10)
        self._gap = scale_px_v(4)
        self._radius = max(3, scale_px_v(5))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_hue)

    def set_lines(
        self, line1: str, line2: str, line3: str, pad_x: int, pad_y: int, gap: int,
    ) -> None:
        self._line1 = line1
        self._line2 = line2
        self._line3 = line3
        self._pad_x = int(pad_x)
        self._pad_y = int(pad_y)
        self._gap = int(gap)
        self.update()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._timer.isActive():
            self._timer.setInterval(ui_anim_tick_ms_for_qwidget(self))
            self._timer.start()

    def hideEvent(self, e) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def _advance_hue(self) -> None:
        self._phase = (self._phase + 3.2) % 360.0
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        pop = self.parentWidget()
        _m = getattr(pop, "_pl", None) if pop is not None else None
        bg_a = int(getattr(_m, "FLAME_TRIGGER_HUD_PANEL_BG_ALPHA", 125) or 125)
        bd_a = int(getattr(_m, "FLAME_TRIGGER_HUD_PANEL_BORDER_ALPHA", 95) or 95)
        bg_a = max(0, min(255, bg_a))
        bd_a = max(0, min(255, bd_a))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setBrush(QColor(0, 0, 0, bg_a))
        p.setPen(QPen(QColor(60, 60, 60, bd_a), 1))
        p.drawRoundedRect(r, self._radius, self._radius)

        f1 = app_default_qfont(11, QFont.Weight.Bold)
        f2 = app_default_qfont(10)
        fm1 = QFontMetrics(f1)
        fm2 = QFontMetrics(f2)
        w = self.width()
        x_left = float(self._pad_x)
        x_right = float(max(self._pad_x + 1, w - self._pad_x))

        def _line_grad(phase_off: float) -> QLinearGradient:
            return _flame_hud_rainbow_gradient(
                x_left, x_right, self._phase, phase_off=phase_off,
            )

        y_top1 = self._pad_y
        rc1 = QRect(int(x_left), y_top1, int(w - 2 * self._pad_x), fm1.height())
        p.setFont(f1)
        p.setPen(QPen(QBrush(_line_grad(0.0)), 0))
        # core rainbow + chromatic aberration overlay
        p.drawText(rc1, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), self._line1)
        _draw_chromatic_aberration_text(
            p,
            rc1,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            self._line1,
            phase=(self._phase / 360.0),
            dx=scale_px_h(4),
            dy=scale_px_v(1),
            base_alpha=0.55,
        )

        y_top2 = y_top1 + fm1.height() + self._gap
        rc2 = QRect(int(x_left), y_top2, int(w - 2 * self._pad_x), fm2.height())
        p.setFont(f2)
        p.setPen(QPen(QBrush(_line_grad(72.0)), 0))
        p.drawText(rc2, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), self._line2)
        _draw_chromatic_aberration_text(
            p,
            rc2,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            self._line2,
            phase=(self._phase / 360.0),
            dx=scale_px_h(3),
            dy=scale_px_v(1),
            base_alpha=0.5,
        )

        y_top3 = y_top2 + fm2.height() + self._gap
        rc3 = QRect(int(x_left), y_top3, int(w - 2 * self._pad_x), fm2.height())
        p.setPen(QPen(QBrush(_line_grad(144.0)), 0))
        p.drawText(rc3, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), self._line3)
        _draw_chromatic_aberration_text(
            p,
            rc3,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            self._line3,
            phase=(self._phase / 360.0),
            dx=scale_px_h(3),
            dy=scale_px_v(1),
            base_alpha=0.5,
        )


class _CursorHudPopup(QWidget):
    """커서 HUD 한 덩어리(아이콘 1개 또는 Flame 패널) — 최상위 창, 한 행에 묶지 않음."""

    def __init__(self, pipela_mod) -> None:
        super().__init__(None)
        self._pl = pipela_mod
        self._colorkey = False
        self._hud_last_outer_sig: tuple[int, int, int, int] | None = None
        self._hud_last_topmost_mono: float = 0.0
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

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._colorkey and sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    _win32_apply_black_colorkey(wid)
                    self._colorkey = True
            except Exception:
                pass
        try:
            _cursor_hud_native_click_through(int(self.winId()))
        except Exception:
            pass

    def _place(
        self,
        m,
        th_i: int,
        curx: int,
        cury: int,
        ax: float,
        ay: float,
        canvas_w: int,
        canvas_h: int,
    ) -> None:
        sc = float(win32_dpi_scale_for_hwnd(m, th_i)) if th_i else 1.0
        if sc <= 0.01:
            sc = 1.0
        x_phys = int(round(curx - float(ax) * sc))
        y_phys = int(round(cury - float(ay) * sc))
        w_phys = max(1, int(round(float(canvas_w) * sc)))
        h_phys = max(1, int(round(float(canvas_h) * sc)))
        outer_sig = (x_phys, y_phys, w_phys, h_phys)
        if outer_sig == self._hud_last_outer_sig:
            return
        self._hud_last_outer_sig = outer_sig
        # Inline physical->Qt overlay conversion (avoid duplicate DPI lookup)
        x_l = int(round(x_phys / sc))
        y_l = int(round(y_phys / sc))
        right_l = int(round((x_phys + w_phys) / sc))
        bottom_l = int(round((y_phys + h_phys) / sc))
        cwl = max(1, int(right_l - x_l))
        chl = max(1, int(bottom_l - y_l))
        xl, yl = int(x_l), int(y_l)
        self.setGeometry(xl, yl, cwl, chl)
        now_m = time.monotonic()
        need_refresh = (now_m - self._hud_last_topmost_mono) >= _CURSOR_HUD_TOPMOST_REFRESH_SEC
        if need_refresh:
            if sys.platform == "win32":
                try:
                    wid = int(self.winId())
                    _win32_topmost_no_activate(wid)
                    if _CURSOR_HUD_FORCE_OUTER_RECT:
                        m.win32_set_window_outer_rect(wid, x_phys, y_phys, w_phys, h_phys)
                except Exception:
                    pass
            self.raise_()
            self._hud_last_topmost_mono = now_m

        try:
            _cursor_hud_native_click_through(int(self.winId()))
        except Exception:
            pass

    def park_hidden(self) -> None:
        x, y, w, h = _HIDDEN
        outer_sig = (x, y, w, h)
        if self._hud_last_outer_sig == outer_sig:
            return
        self._hud_last_outer_sig = outer_sig
        self.hide()
        self.setGeometry(x, y, w, h)
        if sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    self._pl.win32_set_window_outer_rect(wid, x, y, w, h)
            except Exception:
                pass


class _CursorHudFlamePopup(_CursorHudPopup):
    """Flame Trigger 전용 — Win32 검정 컬러키 없음(반투명 박스).
    핫스팟: padlock 아이콘 **중심**이 화면 커서(클릭 지점)와 겹침, 텍스트 박스는 기존처럼 아이콘 아래."""

    # 방향지시등·비상등과 비슷한 느낌(약 1Hz 전후)
    _FT_ICON_BLINK_MS = 500

    def __init__(self, pipela_mod) -> None:
        super().__init__(pipela_mod)
        self._ft_hotspot_ax = 0.0
        self._ft_hotspot_ay = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self._panel = _FlameTriggerHudPanel(self)
        self._icon_lbl = QLabel(self)
        # 부모만 투명이면 자식이 클릭을 잡음 → FT가 커서 위를 가리면 게임 클릭/FT가 멈춤
        for w in (self._panel, self._icon_lbl):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon_lbl.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._icon_lbl.setScaledContents(False)
        self._ft_icon_pm: QPixmap | None = None
        self._ft_has_icon = False
        self._ft_icon_blink_on = True
        self._icon_blink = QTimer(self)
        self._icon_blink.timeout.connect(self._on_ft_icon_blink)

    def showEvent(self, e) -> None:
        QWidget.showEvent(self, e)

    def hideEvent(self, e) -> None:
        self._icon_blink.stop()
        super().hideEvent(e)

    def _ensure_flame_hud_icon(self) -> None:
        if self._ft_icon_pm is not None:
            return
        # move/fire/ride 는 40 기준 — FT padlock 만 1.5배
        self._ft_icon_pm = _scaled_icon(
            FLAME_TRIGGER_CURSOR_HUD_ICON_PATH, design_px=60, lo=30, hi=96,
        )
        if self._ft_icon_pm is not None and self._ft_icon_pm.isNull():
            self._ft_icon_pm = None

    def _on_ft_icon_blink(self) -> None:
        if not self._ft_has_icon:
            return
        self._ft_icon_blink_on = not self._ft_icon_blink_on
        self._icon_lbl.setVisible(self._ft_icon_blink_on)

    def set_flame_text(self, line1: str, line2: str, line3: str) -> tuple[int, int]:
        self._ensure_flame_hud_icon()
        pw, ph, pad_x, pad_y, gap = _flame_panel_metrics_three_lines(line1, line2, line3)
        self._panel.set_lines(line1, line2, line3, pad_x, pad_y, gap)
        self._panel.setFixedSize(pw, ph)
        icon_sz = scale_px_v(60, lo=30, hi=96)
        icon_gap = scale_px_h(6)
        if self._ft_icon_pm is not None and not self._ft_icon_pm.isNull():
            self._icon_lbl.setPixmap(self._ft_icon_pm)
            self._icon_lbl.setFixedSize(icon_sz, icon_sz)
            self._ft_has_icon = True
        else:
            self._icon_lbl.clear()
            self._ft_has_icon = False
            icon_sz = 0
            icon_gap = 0
        total_w = max(pw, icon_sz) if self._ft_has_icon else pw
        if self._ft_has_icon:
            ix = (total_w - icon_sz) // 2
            px = (total_w - pw) // 2
            py = icon_sz + icon_gap
            self._icon_lbl.setGeometry(ix, 0, icon_sz, icon_sz)
            self._icon_lbl.show()
            self._icon_lbl.setVisible(self._ft_icon_blink_on)
            self._panel.setGeometry(px, py, pw, ph)
        else:
            self._icon_lbl.hide()
            self._panel.setGeometry(0, 0, pw, ph)
        total_h = (icon_sz + icon_gap if self._ft_has_icon else 0) + ph
        if self._ft_has_icon:
            self._ft_hotspot_ax = float(ix) + 0.5 * float(icon_sz)
            self._ft_hotspot_ay = 0.5 * float(icon_sz)
        else:
            self._ft_hotspot_ax = 0.5 * float(pw)
            self._ft_hotspot_ay = 0.5 * float(ph)
        return (total_w, total_h)

    def place_bottom_right_of_cursor(
        self,
        m,
        th_i: int,
        curx: int,
        cury: int,
        total_w: int,
        total_h: int,
    ) -> None:
        # padlock **중심** = GetCursor(화면) 핫스팟. (전역 오프셋은 다른 아이콘 dx/dy 쪽 — 여기에 더하면 커서에서 뜸)
        nx = int(getattr(m, "CURSOR_FLAME_HUD_NUDGE_X", 0) or 0)
        ny = int(getattr(m, "CURSOR_FLAME_HUD_NUDGE_Y", 0) or 0)
        curx2 = int(curx) + nx
        cury2 = int(cury) + ny
        ax = float(self._ft_hotspot_ax)
        ay = float(self._ft_hotspot_ay)
        self.setFixedSize(total_w, total_h)
        self.show()
        self._place(m, th_i, curx2, cury2, ax, ay, total_w, total_h)
        if self._ft_has_icon:
            if not self._icon_blink.isActive():
                self._icon_blink.setInterval(
                    int(getattr(m, "CURSOR_FLAME_HUD_ICON_BLINK_MS", self._FT_ICON_BLINK_MS) or 500),
                )
                self._ft_icon_blink_on = True
                self._icon_lbl.setVisible(True)
                self._icon_blink.start()
        else:
            self._icon_blink.stop()


class QtCursorHud(QObject):
    """아이콘·Flame 을 각각 독립 최상위 창으로 띄워 한 캔버스에서 잘리지 않게 한다."""

    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._pop_flame = _CursorHudFlamePopup(pipela_mod)
        self._hud_last_good_cur: tuple[int, int] | None = None
        self._hook_allow = False
        self._hook_th_i = 0
        self._hook_fg_ok = False

        self._hook_lock = threading.Lock()
        self._hook_pending = False
        self._hook_latest_xy: tuple[int, int] | None = None
        self._mouse_hook = None
        self._key_hook = None
        self._dcomp = DCompHud()
        self._dcomp_enabled = False
        if sys.platform == "win32":
            try:
                from pipela_qt.win32_mouse_hook import (
                    Win32LowLevelKeyboardHook,
                    Win32LowLevelMouseHook,
                )

                self._mouse_hook = Win32LowLevelMouseHook(self._on_hook_move)
                self._key_hook = Win32LowLevelKeyboardHook(self._on_hook_key)
            except Exception:
                self._mouse_hook = None
                self._key_hook = None

        # DComp HUD is optional, behind env flag
        self._dcomp_enabled = bool(dcomp_hud_enabled())
        # Do NOT init with anchor=0; wait until we have target HWND (th_i) so anchor rect resolves.

        # 100% hook-driven for icon HUD updates: no polling timer.
        if self._mouse_hook is not None:
            try:
                self._mouse_hook.start()
            except Exception:
                pass
        if self._key_hook is not None:
            try:
                self._key_hook.start()
            except Exception:
                pass

    def show(self) -> None:
        """shell / 설정 토글 호환 — 팝업은 `_tick` 에서만 표시."""
        return

    def close(self) -> None:
        if self._mouse_hook is not None:
            try:
                self._mouse_hook.stop()
            except Exception:
                pass
        if self._key_hook is not None:
            try:
                self._key_hook.stop()
            except Exception:
                pass
        try:
            self._dcomp.shutdown()
        except Exception:
            pass
        for w in (self._pop_flame,):
            try:
                w.close()
                w.deleteLater()
            except Exception:
                pass

    def _on_hook_move(self, x_phys: int, y_phys: int) -> None:
        # Hook thread -> coalesce + post one Qt event
        with self._hook_lock:
            self._hook_latest_xy = (int(x_phys), int(y_phys))
            if self._hook_pending:
                return
            self._hook_pending = True
        try:
            QCoreApplication.postEvent(self, QEvent(_CURSOR_HUD_HOOK_EVENT_TYPE))
        except Exception:
            with self._hook_lock:
                self._hook_pending = False

    def _on_hook_key(self, vk: int, is_down: bool) -> None:
        # Key hook thread -> just schedule an update; we read actual states in UI thread
        _ = (vk, is_down)
        with self._hook_lock:
            if self._hook_pending:
                return
            self._hook_pending = True
        try:
            QCoreApplication.postEvent(self, QEvent(_CURSOR_HUD_HOOK_EVENT_TYPE))
        except Exception:
            with self._hook_lock:
                self._hook_pending = False

    def event(self, e: QEvent) -> bool:
        if e.type() == _CURSOR_HUD_HOOK_EVENT_TYPE:
            with self._hook_lock:
                self._hook_pending = False
                xy = self._hook_latest_xy
            try:
                self._update_from_hook_event(xy)
            except Exception:
                pass
            return True
        return super().event(e)

    def _update_from_hook_event(self, xy: tuple[int, int] | None) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            self._park_hidden()
            return
        if getattr(m, "select_mode", False):
            self._park_hidden()
            return

        th = _cursor_hud_target_hwnd(m)
        if not th:
            self._park_hidden()
            return
        th_i = int(th)

        fg = win32gui.GetForegroundWindow()
        fg_ok = _win32_foreground_belongs_to_target(fg, th)
        if not fg_ok and xy is not None:
            if _physical_point_in_window_rect(xy, m.get_window_rect(th)):
                fg_ok = True
        if not fg_ok:
            # keep hooks running but hide HUD outside game
            if self._dcomp_enabled and self._dcomp.ok:
                self._dcomp.set_visible(False)
            self._park_hidden()
            return

        caps = ctypes.windll.user32.GetKeyState(m.VK_CAPITAL) & 1
        move_on = bool(m.left_click_active)
        fire_on = bool(m.right_hold_active)
        ride_on = bool(caps)
        icons_on = bool(move_on or fire_on or ride_on)
        flame_on = bool(getattr(m, "flame_trigger_active", False))

        if xy is None:
            xy = _try_get_cursor_pos_physical()
        if xy is None:
            return
        x, y = int(xy[0]), int(xy[1])
        if x == 0 and y == 0:
            return
        self._hud_last_good_cur = (x, y)
        # Icons: DComp-only. If DComp init fails, keep icon HUD off (no Qt fallback).
        if self._dcomp_enabled and self._dcomp.ensure_init(th_i):
            self._dcomp.set_icons(move_on, fire_on, ride_on)
            if icons_on:
                self._dcomp.set_visible(True)
                self._dcomp.set_position(x, y)
            else:
                self._dcomp.set_visible(False)
        else:
            if self._dcomp.ok:
                self._dcomp.set_visible(False)

        # FT Flame HUD도 타이머 없이 훅 이벤트로 배치 갱신
        if flame_on:
            try:
                ft_line1 = "Flame Trigger 작동 중!"
                merc_on = "ON" if bool(getattr(m, "merc_fire_enabled", False)) else "OFF"
                iv_sec = float(getattr(m, "flame_trigger_last_press_interval_sec", 0.0) or 0.0)
                ft_line2 = (
                    f"Merc Fire {merc_on} : {int(getattr(m, 'flame_trigger_press_count', 0) or 0)} : {iv_sec:.1f}초"
                )
                r_cnt = int(getattr(m, "flame_trigger_session_reload_count", 0) or 0)
                fmt_hms = getattr(m, "_format_flame_trigger_runtime_hms", None)
                now = time.time()
                trig_t = float(getattr(m, "flame_trigger_last_reload_trigger_time", 0.0) or 0.0)
                elapsed = (now - trig_t) if trig_t > 0.0 else 0.0
                hms = fmt_hms(elapsed) if callable(fmt_hms) else str(int(max(0.0, elapsed)))
                ft_line3 = f"Reload : {r_cnt} ({hms})"
                tw, th2 = self._pop_flame.set_flame_text(ft_line1, ft_line2, ft_line3)
                self._pop_flame.place_bottom_right_of_cursor(m, th_i, x, y, tw, th2)
            except Exception:
                pass
        else:
            self._pop_flame.park_hidden()

    def _park_hidden(self) -> None:
        self._hud_last_good_cur = None
        if self._dcomp.ok:
            self._dcomp.set_visible(False)
        self._pop_flame.park_hidden()


class QtFlameStartBanner(QWidget):
    """워커가 넣는 `_flame_start_banner_queue` 를 소비해 **게임 클라이언트 중앙**에 배너 표시."""

    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._hold_end = 0.0
        self._in_outro = False
        self._outro_t0 = 0.0
        self._pulse_t0 = 0.0
        self._banner_pulse = 1.0
        self._banner_text = ""
        self._banner_font = app_default_qfont(11, QFont.Weight.Bold)
        self._pad_x = 14
        self._pad_y = 10
        self._radius = max(3, scale_px_v(5))
        self._banner_last_outer_sig: tuple[int, int, int, int] | None = None

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(16, int(pipela_mod.FLAME_START_BANNER_ANIM_MS)))
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(ui_anim_tick_ms_for_pipela(pipela_mod))
        self._anim_timer.timeout.connect(self._banner_pulse_frame)
        self.setGeometry(*_HIDDEN)
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if not self._banner_text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        u = max(0.0, min(1.0, float(getattr(self, "_banner_pulse", 1.0))))
        bg_hi, bg_lo = 238, 118
        bd_hi, bd_lo = 215, 72
        bg_a = int(bg_lo + (bg_hi - bg_lo) * u)
        bd_a = int(bd_lo + (bd_hi - bd_lo) * u)
        bg_a = max(0, min(255, bg_a))
        bd_a = max(0, min(255, bd_a))
        p.setBrush(QColor(0, 0, 0, bg_a))
        p.setPen(QPen(QColor(72, 72, 92, bd_a), max(1, int(round(1.0 + u)))))
        p.drawRoundedRect(r, self._radius, self._radius)
        spd = float(
            getattr(self._pl, "FLAME_START_BANNER_RAINBOW_DEG_PER_SEC", 92.0) or 92.0,
        )
        phase = (time.monotonic() * spd) % 360.0
        w = float(self.width())
        xl = 0.0
        xr = max(1.0, w)
        g = _flame_hud_rainbow_gradient(xl, xr, phase)
        p.setFont(self._banner_font)
        p.setPen(QPen(QBrush(g), 0))
        rc = self.rect().adjusted(self._pad_x, self._pad_y, -self._pad_x, -self._pad_y)
        # core rainbow + strong chromatic aberration overlay
        p.drawText(rc, int(Qt.AlignmentFlag.AlignCenter), self._banner_text)
        _draw_chromatic_aberration_text(
            p,
            rc,
            int(Qt.AlignmentFlag.AlignCenter),
            self._banner_text,
            phase=(phase / 360.0),
            dx=scale_px_h(4),
            dy=scale_px_v(2),
            base_alpha=0.62 * u,
        )

    def _arm(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            return
        th = m.refresh_target_hwnd_if_needed()
        if not th:
            return
        now = time.time()
        dur = float(m.FLAME_START_BANNER_DURATION_SEC)
        self._hold_end = max(self._hold_end, now + dur)
        self._in_outro = False
        self._outro_t0 = 0.0
        self._pulse_t0 = time.monotonic()

    def _outro_opacity(self, u: float) -> float:
        """u ∈ [0,1] — 전체 느슨한 페이드 + sin 깜빡임(몇 번)으로 자연스럽게 0 쪽."""
        m = self._pl
        n = max(1, int(getattr(m, "FLAME_START_BANNER_OUTRO_FLICKERS", 4) or 4))
        if u >= 1.0:
            return 0.0
        env = (1.0 - u) ** 0.62
        flick = 0.5 + 0.5 * math.sin(2.0 * math.pi * n * u)
        w = 0.1 + 0.9 * (flick * flick)
        # 마지막 구간: 추가로 흡수(끊김 감소)
        tail = 1.0 - 0.4 * (u * u * u)
        return max(0.0, min(1.0, env * w * tail))

    def _sync_outro_lifecycle(self, t: float) -> None:
        """홀드 끝 → 아웃트로 시작, 아웃트로 끝 → _silence()."""
        m = self._pl
        outro = max(0.04, float(getattr(m, "FLAME_START_BANNER_OUTRO_SEC", 0.9) or 0.9))
        if self._in_outro and t >= self._outro_t0 + outro:
            self._silence()
            return
        if self._hold_end > 0.0 and (not self._in_outro) and t >= self._hold_end:
            self._in_outro = True
            self._outro_t0 = t
        if self._in_outro and t < self._outro_t0 + outro:
            u = (t - self._outro_t0) / outro
            opw = self._outro_opacity(u)
            self._banner_pulse = max(0.02, opw)
            try:
                self.setWindowOpacity(max(0.0, min(1.0, opw)))
            except Exception:
                pass
            self.update()

    def _banner_pulse_frame(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            return
        if not self._banner_text:
            return
        t = time.time()
        self._sync_outro_lifecycle(t)
        if self._hold_end <= 0.0 and (not self._in_outro):
            return
        if self._in_outro:
            return
        if t >= self._hold_end:
            return
        period = max(0.15, float(getattr(m, "FLAME_START_BANNER_PULSE_PERIOD_SEC", 0.48)))
        lo = float(getattr(m, "FLAME_START_BANNER_BLINK_OFF_ALPHA", 0.04))
        hi = float(getattr(m, "FLAME_START_BANNER_BLINK_ON_ALPHA", 0.98))
        hi = max(lo + 0.02, min(1.0, hi))
        lo = max(0.0, min(lo, hi - 0.02))
        gamma = max(0.35, min(2.0, float(getattr(m, "FLAME_START_BANNER_PULSE_PEAK_GAMMA", 0.52))))
        tmono = time.monotonic() - float(self._pulse_t0)
        u = 0.5 + 0.5 * math.sin((2.0 * math.pi * tmono) / period)
        self._banner_pulse = max(0.0, min(1.0, u))
        op = lo + (hi - lo) * (self._banner_pulse ** gamma)
        self.setWindowOpacity(max(0.02, min(1.0, op)))
        self.update()

    def _tick(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            self._silence()
            return
        q = m._flame_start_banner_queue
        armed = False
        try:
            while True:
                q.get_nowait()
                armed = True
        except queue.Empty:
            pass
        if armed:
            self._arm()

        t = time.time()
        self._sync_outro_lifecycle(t)
        if not self._in_outro and (self._hold_end <= 0.0 or t >= self._hold_end):
            return

        th = m.refresh_target_hwnd_if_needed()
        if not th:
            self._silence()
            return
        rect = m.get_window_rect(th)
        if not rect:
            self._silence()
            return

        wx, wy, wx2, wy2 = rect
        cw, ch = wx2 - wx, wy2 - wy
        sz = max(5, int(round(float(m.FLAME_START_BANNER_FONT_PT))))
        self._banner_font = app_default_qfont(sz, QFont.Weight.Bold)
        self._banner_text = str(m.FLAME_START_BANNER_TEXT)
        fm = QFontMetrics(self._banner_font)
        tw = fm.horizontalAdvance(self._banner_text)
        ls = fm.height()
        self._pad_x = max(12, int(m.ui_px(14)))
        self._pad_y = max(8, int(m.ui_px(10)))
        bw = tw + 2 * self._pad_x
        bh = ls + 2 * self._pad_y
        th_i = int(th)
        sc = float(win32_dpi_scale_for_hwnd(m, th_i))
        if sc <= 0.0:
            sc = 1.0
        bw_phys = max(1, int(round(float(bw) * sc)))
        bh_phys = max(1, int(round(float(bh) * sc)))
        y_frac = float(getattr(m, "FLAME_START_BANNER_CLIENT_Y_FRACTION", 0.30) or 0.30)
        y_frac = max(0.0, min(1.0, y_frac))
        ccx = float(wx) + float(cw) / 2.0
        ccy = float(wy) + float(ch) * y_frac
        x_phys = int(round(ccx - float(bw_phys) / 2.0))
        y_phys = int(round(ccy - float(bh_phys) / 2.0))
        xl, yl, wel, hel = win32_physical_screen_rect_to_qt_overlay_geometry(
            m, th_i, x_phys, y_phys, bw_phys, bh_phys,
        )
        self.setGeometry(xl, yl, wel, hel)
        outer_sig = (x_phys, y_phys, bw_phys, bh_phys)
        if outer_sig != self._banner_last_outer_sig:
            self._banner_last_outer_sig = outer_sig
            if sys.platform == "win32":
                try:
                    wid = int(self.winId())
                    if wid:
                        _win32_topmost_no_activate(wid)
                        m.win32_set_window_outer_rect(wid, x_phys, y_phys, bw_phys, bh_phys)
                except Exception:
                    pass
        self._banner_pulse_frame()
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.show()
        self.raise_()

    def _silence(self) -> None:
        self._hold_end = 0.0
        self._in_outro = False
        self._outro_t0 = 0.0
        self._anim_timer.stop()
        try:
            self.setWindowOpacity(1.0)
        except Exception:
            pass
        self._banner_last_outer_sig = None
        self.hide()
        self.setGeometry(*_HIDDEN)
        if sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    x, y, w, h = _HIDDEN
                    self._pl.win32_set_window_outer_rect(wid, x, y, w, h)
            except Exception:
                pass
