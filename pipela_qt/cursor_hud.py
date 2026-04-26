"""Qt 전용 커서 HUD(이동/사격/탑승 아이콘) + Flame 패널 + Flame 시작 배너.

`pipela_mod` 전역(플레임·배너 상수·큐)을 읽는다.
"""

from __future__ import annotations

import ctypes
import html
import os
import queue
import sys
import time

import win32con
import win32gui
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QFontMetrics, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pipela_core.display_timing import display_tick_ms
from pipela_core.win32_window_ops import win32_native_root_hwnd_from_child
from pipela_qt import theme as T
from pipela_qt.dpi import win32_dpi_scale_for_hwnd, win32_physical_screen_rect_to_qt_overlay_geometry
from pipela_qt.overlay import _win32_apply_black_colorkey
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.ui_adaptive import qss_pad_vh, scale_px

_HIDDEN = (-10000, -10000, 1, 1)

# HUD 틱 주기가 짧아 ``refresh_target_hwnd_if_needed`` 가 과호출되기 쉬움 — 짧은 TTL 로만 재사용
_CURSOR_HUD_TH_CACHE_S = max(
    0.0,
    float(os.environ.get("PIPELA_CURSOR_HUD_TH_CACHE_MS", "42") or 42) / 1000.0,
)
_cursor_hud_th_mono: float = 0.0
_cursor_hud_th: int | None = None


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


def _scaled_icon(path: str) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None
    pm = QPixmap(path)
    if pm.isNull():
        return None
    s = scale_px(40, lo=20, hi=64)
    return pm.scaled(
        s,
        s,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _flame_panel_metrics_qt(line1: str, line2: str, line3: str):
    f1 = app_default_qfont(11, QFont.Weight.Bold)
    f2 = app_default_qfont(10)
    f3 = app_default_qfont(9)
    fm1 = QFontMetrics(f1)
    fm2 = QFontMetrics(f2)
    fm3 = QFontMetrics(f3)
    w = max(
        fm1.horizontalAdvance(line1),
        fm2.horizontalAdvance(line2),
        fm3.horizontalAdvance(line3),
    )
    gap = scale_px(2)
    pad_x = scale_px(12)
    pad_y = scale_px(7)
    ls1 = fm1.height()
    ls2 = fm2.height()
    ls3 = fm3.height()
    inner_h = ls1 + gap + ls2 + gap + ls3
    pw = max(8, w + 2 * pad_x)
    ph = inner_h + 2 * pad_y
    return pw, ph, pad_x, pad_y, gap, (f1, f2, f3)


def _flame_lines_html(line1: str, line2: str, line3: str) -> str:
    e1, e2, e3 = map(html.escape, (line1, line2, line3))
    return (
        f'<div style="margin:0;">'
        f'<span style="font-weight:600;font-size: {T.spt(12)};">{e1}</span><br/>'
        f'<span style="font-size: {T.spt(11)};">{e2}</span><br/>'
        f'<span style="font-size: {T.spt(10)};color:#cccccc;">{e3}</span>'
        f"</div>"
    )


class QtCursorHud(QWidget):
    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._colorkey = False
        self._pix: dict[str, QPixmap] = {}
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # 최상단·컬러키 창이 히트 테스트를 가리면 커서가 (0,0) 근처로 튀는 듯 보일 수 있음
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background-color: #000000;")

        self._lbl_move = QLabel(self)
        self._lbl_fire = QLabel(self)
        self._lbl_ride = QLabel(self)
        _iz = scale_px(40, lo=20, hi=64)
        for lb in (self._lbl_move, self._lbl_fire, self._lbl_ride):
            lb.setFixedSize(_iz, _iz)
            lb.setScaledContents(True)
            lb.setStyleSheet("background: transparent;")

        self._flame = QLabel(self)
        self._flame.setTextFormat(Qt.TextFormat.RichText)
        self._flame.setWordWrap(False)
        self._flame.setStyleSheet(
            "background-color: rgba(12, 12, 12, 204); color: #f0f0f0; "
            f"border: 1px solid #555555; border-radius: {scale_px(2)}px; "
            f"padding: {qss_pad_vh(7, 12)}; font-family: {T.FONT_CSS_UI};",
        )
        self._flame.hide()

        # 타이머보다 **먼저** 좌표를 둬야 함 — 아니면 첫 _tick 이 기본(0,0) 근처에
        # 창을 올렸다가 _park 으로 옮기며 좌상단·마우스 깜빡임이 난다.
        self.setGeometry(*_HIDDEN)
        self._hud_last_good_cur: tuple[int, int] | None = None
        self._hud_last_outer_sig: tuple[int, int, int, int] | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        ms = max(8, int(display_tick_ms()))
        self._timer.start(ms)

        QTimer.singleShot(max(50, min(200, ms * 2)), self._load_icons)

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

    def _load_icons(self) -> None:
        m = self._pl
        ride_path = (
            m.CURSOR_RIDE_ICON_PATH
            if os.path.isfile(m.CURSOR_RIDE_ICON_PATH)
            else m.RIDE_ICON_PATH
        )
        for name, path in (("move", m.MOVE_ICON_PATH), ("fire", m.FIRE_ICON_PATH), ("ride", ride_path)):
            pm = _scaled_icon(path)
            if pm is not None:
                self._pix[name] = pm
        self._tick()

    def _tick(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            self._park_hidden()
            return
        if getattr(m, "select_mode", False):
            self._park_hidden()
            return

        th = _cursor_hud_target_hwnd(m)
        caps = ctypes.windll.user32.GetKeyState(m.VK_CAPITAL) & 1
        move_on = bool(m.left_click_active and "move" in self._pix)
        fire_on = bool(m.right_hold_active and "fire" in self._pix)
        ride_on = bool(caps and "ride" in self._pix)
        flame_on = bool(m.flame_trigger_active)
        has_any = move_on or fire_on or ride_on or flame_on
        if not has_any:
            self._park_hidden()
            return
        if not th:
            self._park_hidden()
            return

        fg = win32gui.GetForegroundWindow()
        fg_ok = _win32_foreground_belongs_to_target(fg, th)
        cursor_phys: tuple[int, int] | None = None
        if not fg_ok:
            cursor_phys = _try_get_cursor_pos_physical()
            if cursor_phys is not None and _physical_point_in_window_rect(
                cursor_phys,
                m.get_window_rect(th),
            ):
                fg_ok = True
        if not fg_ok:
            self._park_hidden()
            return

        icon_px = scale_px(40, lo=20, hi=64)
        icon_row_y = scale_px(80)
        icon_gap = scale_px(55)

        ft_line1 = ft_line2 = ft_line3 = ""
        pw = ph = 0
        if flame_on:
            st = m.flame_trigger_start_time
            elapsed = (time.time() - st) if st else 0.0
            rlo = min(float(m.merc_fire_random_min_ms), float(m.merc_fire_random_max_ms))
            rhi = max(float(m.merc_fire_random_min_ms), float(m.merc_fire_random_max_ms))
            iv_sec = float(m.flame_trigger_last_press_interval_sec)
            ft_line1 = f"Flame Trigger : {m._format_flame_trigger_runtime_hms(elapsed)}"
            ft_line2 = (
                f"Merc Fire : {m.flame_trigger_press_count} : "
                f"{m._format_flame_overlay_sec(iv_sec)}초"
            )
            ft_line3 = (
                f"{m._format_flame_overlay_sec(rlo / 1000.0)}~"
                f"{m._format_flame_overlay_sec(rhi / 1000.0)}초"
            )
            pw, ph, pad_x, pad_y, _gap, _fonts = _flame_panel_metrics_qt(
                ft_line1, ft_line2, ft_line3,
            )
            self._flame.setText(_flame_lines_html(ft_line1, ft_line2, ft_line3))
            # QLabel rich text: 패딩은 스타일시트와 중복되지 않게 내부만
            self._flame.setStyleSheet(
                "background-color: rgba(12, 12, 12, 204); color: #f0f0f0; "
                f"border: 1px solid #555555; border-radius: {scale_px(2)}px; "
                f"padding: {pad_y}px {pad_x}px; font-family: {T.FONT_CSS_UI};",
            )
            self._flame.setFixedSize(pw, ph)
            self._flame.show()
        else:
            self._flame.hide()

        if flame_on and pw > 0:
            _flame_y_pad = scale_px(12)
            base_y_layout = icon_row_y + icon_gap + _flame_y_pad
            _cw_min = scale_px(160)
            _cw_mid = scale_px(280)
            _pw_extra = scale_px(56)
            canvas_w = max(_cw_min, max(_cw_mid, int(pw + _pw_extra)))
            canvas_h = max(_cw_min, int(base_y_layout + ph // 2 + scale_px(8)))
        else:
            _cw_min = scale_px(160)
            canvas_w, canvas_h = _cw_min, _cw_min

        cx = canvas_w // 2
        base_y_flame = icon_row_y + icon_gap + scale_px(12)
        fx = fy = 0
        if flame_on and pw > 0:
            fx = int(cx - pw // 2 + int(m.CURSOR_FLAME_PANEL_OFFSET_X))
            fy = int(base_y_flame - ph // 2)

        # 커서 핫스팟 = 클라이언트 (ax, ay) — 고정 50px 오프셋은 아이콘 중심과 어긋나 우·하단으로 보였음
        if move_on or fire_on:
            ax, ay = cx, icon_row_y
        elif ride_on:
            ax, ay = cx, icon_row_y + icon_gap
        elif flame_on and pw > 0:
            ax, ay = fx + pw // 2, fy + ph // 2
        else:
            ax, ay = cx, icon_row_y

        raw_pos = cursor_phys if cursor_phys is not None else _try_get_cursor_pos_physical()
        if raw_pos is None:
            if self._hud_last_good_cur is not None:
                curx, cury = self._hud_last_good_cur
            else:
                self._park_hidden()
                return
        else:
            raw_x, raw_y = raw_pos
            # (0,0) 은 전체화면·독점·드라이버에서 연속으로 튀는 유령값이 잦음 — HUD를 여기에 맞추면
            # Win32가 커서 그리기·히트 테스트를 어지럽히는 환경이 있어 **절대** 신뢰하지 않음.
            if raw_x == 0 and raw_y == 0:
                if self._hud_last_good_cur is not None:
                    curx, cury = self._hud_last_good_cur
                else:
                    self._park_hidden()
                    return
            else:
                curx, cury = raw_x, raw_y
                self._hud_last_good_cur = (raw_x, raw_y)
        th_i = int(th) if th else 0
        sc = float(win32_dpi_scale_for_hwnd(m, th_i)) if th_i else 1.0
        if sc <= 0.0:
            sc = 1.0
        # GetCursorPos = 물리; ax, ay·canvas_* = Qt 논리(scale_px) — 오버레이/게임과 동일 변환(overlay.py)
        x_phys = int(round(curx - float(ax) * sc))
        y_phys = int(round(cury - float(ay) * sc))
        w_phys = max(1, int(round(float(canvas_w) * sc)))
        h_phys = max(1, int(round(float(canvas_h) * sc)))
        xl, yl, cwl, chl = win32_physical_screen_rect_to_qt_overlay_geometry(
            m, th_i, x_phys, y_phys, w_phys, h_phys,
        )
        self.setGeometry(xl, yl, cwl, chl)

        self._lbl_move.setVisible(move_on)
        self._lbl_fire.setVisible(fire_on)
        self._lbl_ride.setVisible(ride_on)
        if move_on:
            self._lbl_move.setPixmap(self._pix["move"])
            self._lbl_move.move(cx - icon_gap - icon_px // 2, icon_row_y - icon_px // 2)
        if fire_on:
            self._lbl_fire.setPixmap(self._pix["fire"])
            self._lbl_fire.move(cx + icon_gap - icon_px // 2, icon_row_y - icon_px // 2)
        if ride_on:
            self._lbl_ride.setPixmap(self._pix["ride"])
            self._lbl_ride.move(cx - icon_px // 2, icon_row_y + icon_gap - icon_px // 2)

        if flame_on and pw > 0:
            self._flame.move(fx, fy)

        outer_sig = (x_phys, y_phys, w_phys, h_phys)
        if outer_sig != self._hud_last_outer_sig:
            self._hud_last_outer_sig = outer_sig
            if sys.platform == "win32":
                try:
                    wid = int(self.winId())
                    _win32_topmost_no_activate(wid)
                    m.win32_set_window_outer_rect(wid, x_phys, y_phys, w_phys, h_phys)
                except Exception:
                    pass
            self.raise_()

    def _park_hidden(self) -> None:
        self._hud_last_good_cur = None
        self._flame.hide()
        x, y, w, h = _HIDDEN
        # 60Hz `_tick` 가 아무 매크로도 켜지지 않은 대기 상태에서 매 틱 _park_hidden() 으로 떨어지면,
        # WS_EX_LAYERED + 컬러키 창에 SetWindowPos 가 폭주해 일부 환경에서 시스템 커서가
        # 좌상단·원위치 사이로 점멸하는 듯이 보인다 — 이미 HIDDEN 이면 단락.
        outer_sig = (x, y, w, h)
        if self._hud_last_outer_sig == outer_sig:
            return
        self._hud_last_outer_sig = outer_sig
        self.setGeometry(x, y, w, h)
        if sys.platform == "win32":
            try:
                wid = int(self.winId())
                if wid:
                    self._pl.win32_set_window_outer_rect(wid, x, y, w, h)
            except Exception:
                pass


class QtFlameStartBanner(QWidget):
    """워커가 넣는 `_flame_start_banner_queue` 를 소비해 게임 창 위 배너 표시."""

    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self._until = 0.0
        self._blink_on = True
        self._next_blink_mono = 0.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._lbl = QLabel()
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._lbl)

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(max(16, int(pipela_mod.FLAME_START_BANNER_ANIM_MS)))
        self.setGeometry(*_HIDDEN)
        self.hide()

    def _arm(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            return
        th = m.refresh_target_hwnd_if_needed()
        if not th:
            return
        now = time.time()
        self._until = max(self._until, now + float(m.FLAME_START_BANNER_DURATION_SEC))
        self._blink_on = True
        self._next_blink_mono = time.monotonic() + max(
            0.05,
            float(m.FLAME_START_BANNER_BLINK_MS) / 1000.0,
        )

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

        if self._until <= 0.0 or time.time() >= self._until:
            self._silence()
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
        font = app_default_qfont(sz, QFont.Weight.Bold)
        self._lbl.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(m.FLAME_START_BANNER_TEXT)
        ls = fm.height()
        pad_x = max(12, m.ui_px(14))
        pad_y = max(8, m.ui_px(10))
        bw = tw + 2 * pad_x
        bh = ls + 2 * pad_y
        bx = wx + (cw - bw) // 2
        by = wy + int(ch * float(m.FLAME_START_BANNER_CLIENT_Y_FRACTION)) - bh // 2

        self._lbl.setText(m.FLAME_START_BANNER_TEXT)
        self._lbl.setStyleSheet(
            "background-color: #080808; color: #ffffff; "
            f"border: 1px solid #555555; border-radius: {scale_px(2)}px; "
            f"padding: {pad_y}px {pad_x}px;",
        )
        self.setFixedSize(bw, bh)
        self.move(int(bx), int(by))

        now_m = time.monotonic()
        blink_sec = max(0.05, float(m.FLAME_START_BANNER_BLINK_MS) / 1000.0)
        if self._next_blink_mono <= 0.0:
            self._next_blink_mono = now_m + blink_sec
        while now_m >= self._next_blink_mono:
            self._blink_on = not self._blink_on
            self._next_blink_mono += blink_sec
        self.setWindowOpacity(
            float(m.FLAME_START_BANNER_BLINK_ON_ALPHA)
            if self._blink_on
            else float(m.FLAME_START_BANNER_BLINK_OFF_ALPHA),
        )
        self.show()
        self.raise_()
        if sys.platform == "win32":
            try:
                _win32_topmost_no_activate(int(self.winId()))
            except Exception:
                pass

    def _silence(self) -> None:
        self._until = 0.0
        self.hide()
        self.setGeometry(*_HIDDEN)


def pipela_cursor_hud_startup_wanted(pipela_mod) -> bool:
    """환경 변수(이번 실행 한정) 후 레지/전역. ``PIPELA_CURSOR_HUD=0|1`` 등."""
    v = os.environ.get("PIPELA_CURSOR_HUD", "").strip().lower()
    if v in ("0", "false", "off", "no"):
        try:
            pipela_mod.pipela_cursor_hud_enabled = False
        except Exception:
            pass
        return False
    if v in ("1", "true", "on", "yes"):
        try:
            pipela_mod.pipela_cursor_hud_enabled = True
        except Exception:
            pass
        return True
    return bool(getattr(pipela_mod, "pipela_cursor_hud_enabled", True))


def apply_pipela_cursor_hud_enabled(pipela_mod) -> None:
    """``pipela_cursor_hud_enabled`` 에 맞춰 HUD 위젯을 만들거나 제거한다(재시작 불필요)."""
    want = bool(getattr(pipela_mod, "pipela_cursor_hud_enabled", True))
    hud = getattr(pipela_mod, "_qt_cursor_hud", None)
    if want:
        if hud is None:
            h = QtCursorHud(pipela_mod)
            pipela_mod._qt_cursor_hud = h
            QTimer.singleShot(0, h.show)
        return
    if hud is not None:
        try:
            hud.hide()
            hud.deleteLater()
        except Exception:
            pass
        pipela_mod._qt_cursor_hud = None
