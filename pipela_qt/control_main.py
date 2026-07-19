"""Qt 제어창 — 토글·해상도·터미널·설정 스택."""

from __future__ import annotations

import html
import math
import os
import sys
import threading
import time
from collections import deque
from collections.abc import Callable

from PyQt6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QRect,
    QSize,
    QEasingCurve,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetricsF,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QPaintEvent,
    QPainter,
    QPalette,
    QResizeEvent,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyleOptionTab,
    QStylePainter,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pipela_core.console_log_constants import (
    CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    CONSOLE_LOG_TIME_MODE_RELATIVE,
    console_log_retention_total_sec,
)
from pipela_core.console_log_prefix import (
    format_console_log_prefix,
    format_terminal_log_stored_prefix,
)
from pipela_core.display_timing import display_tick_ms_for_window, ui_anim_tick_ms_for_qwidget
from pipela_core.paths import (
    CURSOR_RIDE_ICON_PATH,
    FIRE_ICON_PATH,
    MOVE_ICON_PATH,
    UI_ICON_AMMO_PATH,
    UI_ICON_FLAME_PATH,
    UI_ICON_HP_REFILL_PATH,
    UI_ICON_KILL_COUNTER_PATH,
    UI_ICON_MERC_PATH,
    UI_ICON_RELOAD_PATH,
    UI_ICON_SETTINGS_PATH,
    UI_ICON_TERMINAL_PATH,
)
from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_core.win32_window_ops import (
    win32_set_window_outer_rect,
    win32_window_minimize,
)
from pipela_qt import control_tab_chrome as ctc
from pipela_qt import theme as T
from pipela_qt.app_shell import (
    control_frameless_window_qss,
    intro_skip_settings_popup_qss,
    settings_hub_entry_button_qss,
    shell_hub_inner_gutter_px,
)
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.ui_adaptive import (
    action_button_qss_padding,
    action_icon_label_gap,
    control_action_label_pt_factor,
    control_icon_side_px,
    letter_spacing_qss,
    main_shell_margins_lr_tb,
    qss_pad_all,
    qss_pad_vh,
    scale_px_h,
    scale_px_v,
    scaled_design_pt,
    set_typography_layout_height_px,
    set_typography_layout_width_px,
    spt,
)
from pipela_qt.dock_ui_phase import (
    UI_DOCK_PHASE_CLIENT,
    UI_DOCK_PHASE_LAUNCHER,
    UI_DOCK_PHASE_STANDBY,
    get_ui_dock_phase_from_session,
    get_ui_dock_phase,
    is_start_game_launcher_template1_effective_on,
)
from pipela_qt.client_transition_debug import log as ctd_log
from pipela_qt.client_transition_debug import log_exc as ctd_log_exc
from pipela_qt.client_transition_debug import span as ctd_span
from pipela_qt.dev_ui_mode import pipela_dev_ui_enabled, pipela_dev_ui_standby_chrome
from pipela_qt.dpi import get_dock_panel_wh
from pipela_qt.flame_trigger_glass_button import FlameTriggerGlassButton
from pipela_qt.main_window import (
    HUB_ENTRIES,
    HUB_FOOTER_ENTRIES,
    HUB_MAIN_ENTRIES,
)

_HUB_TITLE_BY_PID: dict[str, str] = dict(HUB_ENTRIES)
from pipela_qt.qt_dock_anchor import resolve_dock_anchor_hwnd
from pipela_qt.qt_dock_z_stack import sync_docked_chrome_z_order
from pipela_qt.qt_side_dock import (
    SideDockLayout,
    clamp_dock_logical_geometry,
    compute_side_dock_layout,
    reset_dock_pair_width_to_monitor_fill,
)
from pipela_qt.scroll_utils import relayout_scroll_areas_under, tie_scroll_content_min_width
from pipela_qt.panels.ammo_restock_settings import AmmoRestockSettingsPanel
from pipela_qt.panels.call_merc_settings import CallMercSettingsPanel
from pipela_qt.panels.console_settings import ConsoleSettingsPanel
from pipela_qt.panels.interface_settings import InterfaceSettingsPanel
from pipela_qt.panels.flame_trigger_settings import FlameTriggerSettingsPanel
from pipela_qt.panels.hp_refill_settings import HpRefillSettingsPanel
from pipela_qt.panels.left_click_settings import LeftClickSettingsPanel
from pipela_qt.panels.reload_settings import ReloadSettingsPanel
from pipela_qt.panels.ride_settings import RideSettingsPanel
from pipela_qt.panels.start_game_settings import StartGameSettingsPanel
from pipela_qt.panels.tesseract_settings import TesseractSettingsPanel
from pipela_qt.panels.update_settings import UpdateSettingsPanel
from pipela_qt.panels.settings_chrome import (
    settings_footnote_style,
    settings_label_align_center_h,
)
from pipela_qt.dock_panel_pair_resize import (
    clamp_dock_pair_panel_w,
    resolve_unified_saved_dock_panel_w,
)
from pipela_qt.kill_counter_window import PipelaQtKillCounterWindow
from pipela_qt.terminal_log_list_widget import ResizableTerminalLogList
from pipela_qt.terminal_log_html import format_terminal_log_line_html

# 앱 전역 eventFilter 핫패스 — int 비교(프로파일: enum 数百万 호출)로 통과
_EV_MOUSE_BUTTON_PRESS = int(QEvent.Type.MouseButtonPress)
_EV_WHEEL = int(QEvent.Type.Wheel)


def _action_icon_qicon(path: str | None) -> QIcon:
    if not path:
        return QIcon()
    try:
        if os.path.isfile(path):
            return QIcon(path)
    except Exception:
        pass
    return QIcon()


def _norm_outer_rect(rs):
    if rs is None:
        return None
    try:
        return tuple(int(x) for x in rs)
    except Exception:
        return None


class _StreamBridge(QObject):
    text = pyqtSignal(str)
    """(wall_time, line_monotonic, raw_line_without_prefix) — 줄이 찍힌 시각(monotonic) 기준 상대 표시용."""
    record_terminal_line = pyqtSignal(float, float, str)

    def __init__(self, orig, pipela_mod) -> None:
        super().__init__()
        self._orig = orig
        self._m = pipela_mod
        self._buf = ""
        self._lock = threading.Lock()

    def _decorate_line_body(self, body: str, line_mono: float) -> str:
        if not body or not body.strip():
            return body
        try:
            p = format_console_log_prefix(self._m, line_mono=line_mono)
        except Exception:
            return body
        return p + body

    def _decorate_line_body_html(
        self,
        body: str,
        line_mono: float,
        wall_t: float | None = None,
    ) -> str:
        try:
            tp = format_console_log_prefix(self._m, line_mono=line_mono)
        except Exception:
            return html.escape(body, quote=False)
        raw = body.strip("\r\n")
        mode = getattr(
            self._m,
            "console_log_time_display_mode",
            CONSOLE_LOG_TIME_MODE_ABSOLUTE,
        )
        try:
            if mode == CONSOLE_LOG_TIME_MODE_RELATIVE:
                age = max(0.0, time.monotonic() - float(line_mono))
            elif wall_t is not None:
                age = max(0.0, time.time() - float(wall_t))
            else:
                age = 0.0
        except Exception:
            age = 0.0
        ipx = max(12, min(22, scale_px_v(14)))
        if not raw.strip():
            return format_terminal_log_line_html(tp, "", icon_px=ipx, time_age_sec=age)
        return format_terminal_log_line_html(tp, raw, icon_px=ipx, time_age_sec=age)

    def write(self, s) -> int:
        if not s:
            return 0
        if not isinstance(s, str):
            s = str(s)
        n = len(s)
        out_chunks: list[str] = []
        html_chunks: list[str] = []
        with self._lock:
            self._buf += s
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                _wt = time.time()
                _lm = time.monotonic()
                _raw = line.rstrip("\r\n")
                self.record_terminal_line.emit(_wt, _lm, _raw)
                dec = self._decorate_line_body(line, _lm)
                out_chunks.append(dec + "\n")
                html_chunks.append(self._decorate_line_body_html(line, _lm, _wt) + "<br/>")
        if out_chunks:
            combined = "".join(out_chunks)
            try:
                self._orig.write(combined)
            except Exception:
                pass
            self.text.emit("".join(html_chunks))
        return n

    def flush(self) -> None:
        with self._lock:
            pending = self._buf
            self._buf = ""
        if pending:
            _wt = time.time()
            _lm = time.monotonic()
            self.record_terminal_line.emit(_wt, _lm, pending.rstrip("\r\n"))
            out = self._decorate_line_body(pending, _lm)
            try:
                self._orig.write(out)
            except Exception:
                pass
            self.text.emit(self._decorate_line_body_html(pending, _lm, _wt))
        try:
            self._orig.flush()
        except Exception:
            pass


def _format_reload_hud_elapsed_hms(elapsed: float) -> str:
    """FT 커서 HUD `Reload : n (경과)` — `main._format_flame_trigger_runtime_hms` 와 동일 규격."""
    t = int(max(0.0, float(elapsed)))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# 제어 버튼 우클릭 → 해당 설정 패널로 이동 (RightHold는 전용 설정 없음)
_BTN_CONTEXT_PANEL: dict[str, str | None] = {
    "left": "lc",
    "right": None,
    "reload": "rl",
    "flame": "ft",
    "ammo": "ammo",
    "merc": "merc",
    "ride": "ride",
    "hp": "hp",
    "kc": None,
    "sg": "sg",
}


class CallMercCooldownButton(QPushButton):
    """Call Merc / Reload — 쿨타임 하단 게이지(아래→위 소진) + 쿨 종료 시 짧은 플래시."""

    _FLASH_DUR_SEC = 0.55

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cd_fill = 0.0
        # 리프레시 틱이 쿨다운 말미를 건너뛸 수 있어, fill 이 0.04 미만인 채로 0 이 되면
        # prev>임계값 조건으로는 플래시가 안 뜸 → 게이지가 한 번이라도 올라온 뒤 0 이면 종료로 본다.
        self._cd_gauge_armed = False
        self._flash_start_mono = 0.0
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._tick_cooldown_flash)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._flash_timer.setInterval(ui_anim_tick_ms_for_qwidget(self))

    def _stop_cooldown_done_flash(self) -> None:
        self._flash_start_mono = 0.0
        self._flash_timer.stop()

    def _start_cooldown_done_flash(self) -> None:
        self._flash_start_mono = time.monotonic()
        if not self._flash_timer.isActive():
            self._flash_timer.start()

    def _tick_cooldown_flash(self) -> None:
        if self._flash_start_mono <= 0.0:
            self._flash_timer.stop()
            return
        if time.monotonic() - self._flash_start_mono >= self._FLASH_DUR_SEC:
            self._stop_cooldown_done_flash()
        self.update()

    def set_cooldown_fill(self, v: float) -> None:
        v = max(0.0, min(1.0, float(v)))
        prev = self._cd_fill
        if abs(v - prev) < 0.002:
            if not (self._cd_gauge_armed and v <= 0.01):
                return
        if v > 0.02:
            self._stop_cooldown_done_flash()
        if v > 0.001:
            self._cd_gauge_armed = True
        self._cd_fill = v
        if self._cd_gauge_armed and v <= 0.01:
            self._start_cooldown_done_flash()
            self._cd_gauge_armed = False
        self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        super().paintEvent(e)
        h = int(self.height())
        w = int(self.width())
        if h <= 0 or w <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._cd_fill > 0.001:
            fill_h = max(1, int(round(float(h) * self._cd_fill)))
            y0 = h - fill_h
            c = QColor(T.ACCENT)
            c.setAlpha(108)
            p.fillRect(0, y0, w, fill_h, c)
        if self._flash_start_mono > 0.0:
            elapsed = time.monotonic() - self._flash_start_mono
            if elapsed >= self._FLASH_DUR_SEC:
                self._stop_cooldown_done_flash()
            else:
                u = elapsed / self._FLASH_DUR_SEC
                wfade = (1.0 - u) ** 2.05
                r = self.rect()
                c2 = QColor(T.ACCENT)
                c2.setAlpha(int(55 + 185 * wfade))
                p.fillRect(r, c2)
                p.fillRect(r, QColor(255, 255, 255, int(40 + 145 * wfade)))


class _IntroSkipPopupDialog(QDialog):
    """OS 타이틀 없음 — Esc 로 닫기."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from pipela_qt.dialog_dismiss_on_outside import register_dialog_dismiss_on_outside_click

        register_dialog_dismiss_on_outside_click(self)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)


class _IntroSkipPopupDragHeader(QFrame):
    """프레임리스 Intro Skip 팝업 상단 바 — 드래그 이동·닫기."""

    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self.setObjectName("pipelaIntroSkipPopupHead")
        self._dlg = dialog
        self._drag_anchor: QPoint | None = None
        hl = QHBoxLayout(self)
        hl.setContentsMargins(scale_px_h(10), scale_px_v(6), scale_px_h(6), scale_px_v(6))
        hl.setSpacing(scale_px_h(8))
        ttl = QLabel("Intro Skip 설정")
        ttl.setObjectName("pipelaIntroSkipPopupTitle")
        hl.addWidget(ttl, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch(1)
        btn = QPushButton()
        btn.setObjectName("pipelaIntroSkipPopupClose")
        btn.setFlat(True)
        st = dialog.style()
        btn.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        iz = max(10, min(22, scale_px_v(14)))
        btn.setIconSize(QSize(iz, iz))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("닫기")
        btn.clicked.connect(dialog.close)
        hl.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_anchor = e.globalPosition().toPoint() - self._dlg.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_anchor is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self._dlg.move(e.globalPosition().toPoint() - self._drag_anchor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_anchor = None
        super().mouseReleaseEvent(e)


def _main_tab_resolve_gear_pixmap(bar: QTabBar, gear_side: int, en: bool) -> tuple[QPixmap, int]:
    """터미널 탭 우측 톱니 — 설정 아이콘 또는 폴백."""
    gs = max(10, min(28, int(gear_side)))
    ic = _action_icon_qicon(UI_ICON_SETTINGS_PATH)
    if ic.isNull():
        ic = bar.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
    mode = QIcon.Mode.Normal if en else QIcon.Mode.Disabled
    pm = ic.pixmap(QSize(gs, gs), mode, QIcon.State.Off)
    if pm.isNull():
        return pm, gs
    try:
        pm.setDevicePixelRatio(1.0)
    except Exception:
        pass
    return pm, gs


def _gear_hit_rect_and_paint_main_tab_cluster(
    bar: QTabBar,
    tab: QStyleOptionTab,
    painter: QPainter | None,
    *,
    terminal_gear: bool,
) -> QRect | None:
    """패딩 안에서 아이콘(+선택) + 텍스트 + 터미널 우측 톱니 측정; ``painter`` 있으면 그린다."""
    gear_rect_bar: QRect | None = None
    rect = QRect(tab.rect)
    icon_sz = tab.iconSize
    if icon_sz.width() <= 0 or icon_sz.height() <= 0:
        _s = max(
            16,
            int(bar.style().pixelMetric(QStyle.PixelMetric.PM_SmallIconSize, tab, bar)),
        )
        icon_sz = QSize(_s, _s)
    en = bool(tab.state & QStyle.StateFlag.State_Enabled)
    icon_mode = QIcon.Mode.Normal if en else QIcon.Mode.Disabled
    icon_state = QIcon.State.On if (tab.state & QStyle.StateFlag.State_Selected) else QIcon.State.Off
    _ph = int(ctc.main_tabs_tab_pad_h_px())
    _pv = int(ctc.main_tabs_tab_pad_v_px())
    if _ph > 0 or _pv > 0:
        rect = rect.adjusted(_ph, _pv, -_ph, -_pv)
    if rect.width() <= 0 or rect.height() <= 0:
        return None

    pm_icon = tab.icon.pixmap(icon_sz, icon_mode, icon_state)
    icon_valid = bool(not pm_icon.isNull() and pm_icon.width() > 1 and pm_icon.height() > 1)
    if not terminal_gear and not icon_valid:
        return None

    _gap = int(ctc.main_tabs_icon_label_gap_px())
    _gap_gear = max(int(ctc.main_tabs_icon_label_gap_px()), scale_px_h(6))
    text = tab.text
    try:
        _font = QFont(tab.font)
        if _font.pointSizeF() == 0 and _font.pixelSize() == 0:
            _font = bar.font()
    except Exception:
        _font = bar.font()
    icon_w = max(1, int(icon_sz.width()))
    icon_h = max(1, int(icon_sz.height()))
    tw = 0
    fm = None
    if text:
        if painter:
            painter.setFont(_font)
            fm = painter.fontMetrics()
        else:
            tb = QFontMetricsF(_font)
            fm = tb
            # QFontMetricsF has horizontalAdvance
        tw = int(fm.horizontalAdvance(text))
        tw = max(tw, int(fm.boundingRect(text).width()))
    igw, igh = 0, 0
    gear_pm = QPixmap()
    if terminal_gear:
        iz = max(icon_w, icon_h, int(bar.iconSize().width()), int(bar.iconSize().height()))
        if iz <= 0:
            iz = max(14, int(ctc.main_tabs_bar_icon_size_px()))
        gear_pm, _gs = _main_tab_resolve_gear_pixmap(bar, max(12, iz - 2), en)
        if not gear_pm.isNull():
            igw = int(gear_pm.width())
            igh = int(gear_pm.height())

    cluster = 0
    if icon_valid:
        cluster += icon_w + _gap
    cluster += tw
    if terminal_gear and igw > 0:
        cluster += _gap_gear + igw
    elif terminal_gear and gear_pm.isNull():
        igw = 0
        igh = 0

    _left = int(rect.left())
    _w = int(rect.width())
    x0 = _left + max(0, (_w - cluster) // 2)
    y_c = int(rect.center().y())

    if painter:
        painter.save()
    try:
        if painter and icon_valid:
            painter.drawPixmap(
                int(x0),
                y_c - icon_h // 2,
                int(icon_w),
                int(icon_h),
                pm_icon,
            )
        text_left = float(x0)
        if icon_valid:
            text_left = float(x0 + icon_w + _gap)
        tr = QRect(
            int(round(text_left)),
            int(rect.top()),
            max(1, tw),
            int(rect.height()),
        )
        tf = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if painter and tw > 0:
            bar.style().drawItemText(
                painter,
                tr,
                tf,
                tab.palette,
                en,
                text,
                QPalette.ColorRole.WindowText,
            )

        after_text_edge = float(x0)
        if icon_valid:
            after_text_edge = float(x0 + icon_w + _gap)
        after_text_edge += float(tw)
        if terminal_gear and igw > 0 and igh > 0:
            gx_draw = int(round(after_text_edge + float(_gap_gear)))
            gh_i = max(1, int(igh))
            gw_i = max(1, int(igw))
            gy = y_c - gh_i // 2
            gear_rect_bar = QRect(gx_draw, gy, gw_i, gh_i)
            if painter:
                painter.drawPixmap(gx_draw, gy, gw_i, gh_i, gear_pm)

    finally:
        if painter:
            painter.restore()
    return gear_rect_bar


def _terminal_tab_gear_rect(bar: QTabBar) -> QRect | None:
    """인덱스 0 탭 우측 톱니 hit rect (탭바 좌표)."""
    try:
        if bar.count() <= 0:
            return None
        opt = QStyleOptionTab()
        bar.initStyleOption(opt, 0)
        return _gear_hit_rect_and_paint_main_tab_cluster(
            bar, opt, None, terminal_gear=True,
        )
    except Exception:
        return None


def _paint_main_tab_clustered_tab_label(
    bar: QTabBar,
    tab: QStyleOptionTab,
    p: QPainter,
    *,
    terminal_gear: bool = False,
) -> None:
    """Shape 다음 레이어 — 아이콘+글자(+터미널일 때 우측 톱니) 가운데 배치."""
    _gear_hit_rect_and_paint_main_tab_cluster(
        bar, tab, p, terminal_gear=terminal_gear,
    )

class _PairedControlTabBar(QTabBar):
    """터미널·설정 두 탭 — 가로 폭에 맞춘 **균등(50/50)** 세그먼트 + 고정 간격."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._terminal_gear_click: Callable[[], None] | None = None
        self._terminal_gear_hover: bool = False
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setExpanding(True)
        _db = getattr(self, "setDrawBase", None)
        if callable(_db):
            try:
                _db(False)
            except Exception:
                pass

    def _target_bar_width(self) -> int:
        p = self.parentWidget()
        if isinstance(p, QTabWidget):
            return max(int(p.width()), int(self.width()))
        return int(self.width())

    def tabSizeHint(self, index: int) -> QSize:
        sh = super().tabSizeHint(index)
        n = self.count()
        if n <= 0:
            return sh
        w_bar = self._target_bar_width()
        if w_bar <= 0:
            return sh
        gap = int(ctc.main_tabs_inter_tab_gap_px())
        r = int(ctc.main_tabs_rail_hpad_px())
        rail_hpad = r * 2
        inner = max(0, w_bar - gap * (n - 1) - rail_hpad)
        idx = int(index)
        if n == 2:
            w_half = inner // 2
            w = w_half if idx == 0 else (inner - w_half)
        else:
            base = inner // n
            rem = inner % n
            w = base + (1 if idx < rem else 0)
        h = max(int(sh.height()), int(ctc.main_tabs_min_height_px()) + 2)
        return QSize(max(1, w), h)

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        n = self.count()
        if n <= 0:
            return sh
        w_bar = self._target_bar_width()
        if w_bar <= 0:
            return sh
        _th = int(ctc.main_tabs_min_height_px()) + int(scale_px_v(6))
        h = max(int(sh.height()), _th)
        return QSize(w_bar, h)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.updateGeometry()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.updateGeometry()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self.updateGeometry()

    def _paint_one_main_tab(self, painter: QStylePainter, opt: QStyleOptionTab, i: int) -> None:
        self.initStyleOption(opt, i)
        painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, opt)
        term_gear = i == 0
        if opt.icon.isNull():
            if term_gear:
                _gear_hit_rect_and_paint_main_tab_cluster(
                    self, opt, painter, terminal_gear=True,
                )
            else:
                painter.drawControl(QStyle.ControlElement.CE_TabBarTabLabel, opt)
        else:
            _paint_main_tab_clustered_tab_label(self, opt, painter, terminal_gear=term_gear)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._terminal_gear_click is not None:
            if self.tabAt(event.pos()) == 0:
                gr = _terminal_tab_gear_rect(self)
                if gr is not None and gr.contains(event.pos()):
                    try:
                        self._terminal_gear_click()
                    except Exception:
                        pass
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        over = False
        if (
            self._terminal_gear_click is not None
            and self.tabAt(event.pos()) == 0
        ):
            gr = _terminal_tab_gear_rect(self)
            over = bool(gr is not None and gr.contains(event.pos()))
        if over != self._terminal_gear_hover:
            self._terminal_gear_hover = over
            try:
                if over:
                    self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    self.setToolTip("터미널 설정")
                else:
                    self.unsetCursor()
                    self.setToolTip("")
            except Exception:
                pass
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self._terminal_gear_hover:
            self._terminal_gear_hover = False
            try:
                self.unsetCursor()
                self.setToolTip("")
            except Exception:
                pass
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        # Qt 와 동일: 선택되지 않은 탭 먼저, 선택 탭을 맨 위에 그림 (`qtabbar.cpp`).
        painter = QStylePainter(self)
        opt = QStyleOptionTab()
        selected = int(self.currentIndex())
        for i in range(self.count()):
            if i == selected:
                continue
            self._paint_one_main_tab(painter, opt, i)
        if selected >= 0:
            self._paint_one_main_tab(painter, opt, selected)


# 터미널 보존 초과 줄 — 페이드아웃 후 제거(터미널 탭이 앞에 있을 때만 애니메이션)
# 짧게 잡아 «줄 높이 접힘·리스트에서 빠짐»보다 텍스트 페이드가 덜 늘어지게 함(구 3.0s 는 체감상 과함).
_TERMINAL_LOG_FADE_OUT_SEC = 1.35
_TERMINAL_FADE_TICK_MS = 33
_TERMINAL_FADE_EASING = QEasingCurve(QEasingCurve.Type.OutCubic)
# 보존·숨김 후 페이드까지 끝난 줄은 모델에서 지우지 않고 아카이브에 둠 — 위로 스크롤하면 다시 읽음
_TERMINAL_LOG_MAX_STORED_LINES = 5000


def _terminal_fade_eased_progress(elapsed_sec: float) -> float:
    """0→1 페이드 진행(시간 정규화 + 이징). 불투명도·줄 높이에 동일 적용."""
    u = min(1.0, max(0.0, float(elapsed_sec) / _TERMINAL_LOG_FADE_OUT_SEC))
    return float(_TERMINAL_FADE_EASING.valueForProgress(u))


def _terminal_fade_line_opacity(elapsed_sec: float) -> float:
    t = _terminal_fade_eased_progress(elapsed_sec)
    return max(0.0, 1.0 - t)


class _ControlLeftResizeEdge(QWidget):
    """프레임리스 제어창 **외곽(왼쪽)** 가장자리에서 폭 조절(게임 쪽 오른쪽 끝은 고정 — 왼쪽으로 드래그 시 확장)."""

    def __init__(self, main: "PipelaQtMainWindow") -> None:
        super().__init__(main)
        self._main = main
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip("폭 조절 — 더블클릭: 작업영역 채움")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._drag = False
        self._g0 = 0
        self._main_sm = 8

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = True
            self._g0 = int(event.globalPosition().x())
            self._main_sm = max(8, int(self._main._dock_w))
            self.grabMouse()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag:
            gx = int(event.globalPosition().x())
            nw_target = self._main_sm + (self._g0 - gx)
            w = clamp_dock_pair_panel_w(int(round(float(nw_target))))
            kc = getattr(self._main, "_kc_float", None)
            ch = w != self._main._dock_w or (
                kc is not None and int(kc._dock_w) != w
            )
            if ch:
                self._main._dock_w = w
                self._main._last_dock_sig = None
                self._main._last_standby_sig = None
                if kc is not None:
                    kc._dock_w = w
                    kc._last_dock_sig = None
                    QTimer.singleShot(0, kc.dock_to_right_of_target_game)
                else:
                    setattr(self._main, "_paired_kill_width_pending", w)
                QTimer.singleShot(0, lambda: self._main._dock_to_anchor(force=True))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            reset_dock_pair_width_to_monitor_fill(
                pipela_mod=self._main._m,
                main=self._main,
            )
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
                m = self._main._m
                w_saved = int(self._main._dock_w)
                kc = getattr(self._main, "_kc_float", None)
                setattr(self._main, "_paired_kill_width_pending", None)
                if kc is not None:
                    w_saved = max(w_saved, int(kc._dock_w))
                    w_saved = int(clamp_dock_pair_panel_w(w_saved))
                    self._main._dock_w = w_saved
                    kc._dock_w = w_saved
                m.control_panel_w = w_saved
                m.kill_counter_panel_w = w_saved
                ss = getattr(m, "schedule_save_config", None)
                if callable(ss):
                    ss()
            except Exception:
                pass
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PipelaQtMainWindow(QMainWindow):
    def __init__(self, pipela_mod, *, start_tray_only: bool = False) -> None:
        super().__init__()
        self._m = pipela_mod
        pipela_mod.pipela_qt_control_win_hwnd = None
        self._start_tray_only = start_tray_only
        # 프레임리스 X — hide() 시 True; show() / 트레이 «제어창 표시» 시 False (자동으로 메인+킬 같이 쓰지 않게)
        self._control_chrome_user_dismissed = False
        self._launcher_intro_skip_dialog: QDialog | None = None
        self._kc_float: PipelaQtKillCounterWindow | None = None
        self._kc_float_user_hidden = False
        self._last_btn_style_state: object | None = None
        self._last_dock_sig: object | None = None
        self._last_standby_sig: object | None = None
        self._dock_track_anchor: int | None = None
        self._dock_track_game_iconic: bool | None = None
        self._dock_track_outer: tuple[int, int, int, int] | None = None
        self._dock_track_client: tuple[int, int, int, int] | None = None
        self._dock_rect_miss_count: int = 0
        self._last_z_anchor: int | None = None
        self._typography_flush_scheduled = False
        self._last_typography_layout_w: int | None = None
        self._last_docked_w_log: int | None = None
        self._tabs: QTabWidget | None = None
        self._tab_area: QWidget | None = None
        self._actions_tabs_sep: QWidget | None = None
        self._feature_top_dock: QWidget | None = None
        self._main_splitter: QSplitter | None = None
        self._settings_wrap: QWidget | None = None
        self._terminal_log_memory: deque[tuple[float, float, str]] = deque()
        self._terminal_log_fading: deque[tuple[float, float, str, float]] = deque()
        self._terminal_log_archive: deque[tuple[float, float, str]] = deque()
        self._terminal_log_scroll_from_code = False
        self._terminal_scroll_restore_pending = False
        self._terminal_scroll_grace_mono: float | None = None
        self.setWindowTitle(PIPELA_APP_DISPLAY_NAME)
        _wi = qt_application_icon()
        if not _wi.isNull():
            self.setWindowIcon(_wi)
        self.setObjectName("pipelaFramelessMain")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        self._dock_w, _dh = get_dock_panel_wh(pipela_mod)
        self._dock_w = resolve_unified_saved_dock_panel_w(pipela_mod, self._dock_w)
        self._last_typography_layout_w = int(self._dock_w)
        self._last_typography_layout_h: int | None = int(max(8, int(_dh)))
        self.resize(self._dock_w, _dh)
        self.setFixedWidth(self._dock_w)
        set_typography_layout_width_px(self._dock_w)
        set_typography_layout_height_px(int(max(8, int(_dh))))
        self.setMenuBar(None)
        self.setStyleSheet(control_frameless_window_qss())

        root = QWidget()
        root.setObjectName("pipelaRoot")
        self.setCentralWidget(root)
        out = QVBoxLayout(root)
        out.setContentsMargins(0, 0, 0, 0)
        out.setSpacing(0)

        cw = QWidget()
        cw.setObjectName("pipelaBody")
        out.addWidget(cw, 1)
        main_l = QVBoxLayout(cw)
        _ml, _mt, _mr, _mb = main_shell_margins_lr_tb()
        main_l.setContentsMargins(_ml, _mt, _mr, _mb)
        main_l.setSpacing(shell_hub_inner_gutter_px())

        btn_grid = QGridLayout()
        self._btn_grid = btn_grid
        btn_grid.setHorizontalSpacing(scale_px_h(8))
        btn_grid.setVerticalSpacing(scale_px_v(8))
        btn_grid.setContentsMargins(0, 0, 0, 0)
        btn_grid.setColumnStretch(0, 1)
        btn_grid.setColumnStretch(1, 1)
        self._btns: dict[str, QPushButton] = {}
        self._action_btn_label_base: dict[str, str | None] = {}
        _isz = QSize(
            control_icon_side_px(pipela_mod),
            control_icon_side_px(pipela_mod),
        )
        # 행: (0) LeftClick·RightHold (1) Flame Trigger 한 줄 (2) Reload 한 줄
        # (3) Ride·HP Refill (4) Ammo·Merc (5) Kill Counter 한 줄 — Intro Skip 은 설정 탭
        specs = [
            ("left", "LeftClick", self._toggle_left, MOVE_ICON_PATH),
            ("right", "RightHold", self._toggle_right, FIRE_ICON_PATH),
            ("flame", "Flame Trigger", self._toggle_flame, UI_ICON_FLAME_PATH),
            ("reload", "Reload", self._toggle_reload, UI_ICON_RELOAD_PATH),
            ("ride", "Ride", self._toggle_ride, CURSOR_RIDE_ICON_PATH),
            ("hp", "HP Refill", self._toggle_hp, UI_ICON_HP_REFILL_PATH),
            ("ammo", "Ammo Restock", self._toggle_ammo, UI_ICON_AMMO_PATH),
            ("merc", "Call Merc", self._toggle_merc, UI_ICON_MERC_PATH),
            ("kc", "Kill Counter", self._toggle_kc, UI_ICON_KILL_COUNTER_PATH),
        ]
        placements: list[tuple[int, int, int, int]] = [
            (0, 0, 1, 1),
            (0, 1, 1, 1),
            (1, 0, 1, 2),
            (2, 0, 1, 2),
            (3, 0, 1, 1),
            (3, 1, 1, 1),
            (4, 0, 1, 1),
            (4, 1, 1, 1),
            (5, 0, 1, 2),
        ]
        _gap = action_icon_label_gap()
        for (key, label, fn, icon_path), (r, c, rs, cs) in zip(specs, placements):
            b = (
                CallMercCooldownButton()
                if key in ("merc", "reload")
                else FlameTriggerGlassButton()
                if key == "flame"
                else QPushButton()
            )
            b.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            self._action_btn_label_base[key] = None if key in ("flame", "reload") else label
            _ic = _action_icon_qicon(icon_path)
            if not _ic.isNull():
                b.setIcon(_ic)
                b.setIconSize(_isz)
                b.setText(_gap + label)
            else:
                b.setText(label)
            b.clicked.connect(fn)
            pid = _BTN_CONTEXT_PANEL.get(key)
            if pid:
                b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                b.customContextMenuRequested.connect(
                    lambda _p, panel_id=pid: self._open_settings_panel(
                        panel_id, "", toggle_same_panel_to_terminal=True,
                    ),
                )
            self._btns[key] = b
            btn_grid.addWidget(b, r, c, rs, cs)
        self._action_btn_panel = QWidget()
        self._action_btn_panel.setObjectName("pipelaActionBtnPanel")
        self._action_btn_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        _ag_l = QVBoxLayout(self._action_btn_panel)
        _ag_pad_v = scale_px_v(8)
        _ag_pad_h = scale_px_h(8)
        _ag_l.setContentsMargins(_ag_pad_h, _ag_pad_v, _ag_pad_h, _ag_pad_v)
        _ag_l.setSpacing(0)
        _ag_l.addLayout(btn_grid)

        sep_wrap = QWidget()
        sep_wrap.setObjectName("pipelaActionsTabsSep")
        sep_l = QVBoxLayout(sep_wrap)
        _sep_vm = scale_px_v(12)
        sep_l.setContentsMargins(0, _sep_vm, 0, _sep_vm)
        sep_l.setSpacing(0)
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setFixedHeight(max(1, scale_px_v(1)))
        sep_line.setStyleSheet(
            f"background: {T.DIVIDER}; color: {T.DIVIDER}; border: none; "
            f"min-height: 1px; max-height: 1px;",
        )
        sep_l.addWidget(sep_line)
        self._actions_tabs_sep = sep_wrap

        feature_dock = QWidget()
        feature_dock.setObjectName("pipelaFeatureDock")
        fd_l = QVBoxLayout(feature_dock)
        fd_l.setContentsMargins(0, 0, 0, 0)
        fd_l.setSpacing(shell_hub_inner_gutter_px())
        fd_l.addWidget(self._action_btn_panel, 0)
        fd_l.addWidget(sep_wrap, 0)
        self._feature_top_dock = feature_dock

        tabs = QTabWidget()
        tabs.setObjectName("pipelaMainTabs")
        tabs.setDocumentMode(True)
        tabs.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tabs.setTabBar(_PairedControlTabBar(tabs))
        _main_tabs_bar = tabs.tabBar()
        _main_tabs_bar.setUsesScrollButtons(False)
        if isinstance(_main_tabs_bar, _PairedControlTabBar):
            _main_tabs_bar._terminal_gear_click = lambda: self._open_settings_panel(
                "console",
                _HUB_TITLE_BY_PID.get("console", "터미널"),
            )
        self._tabs = tabs
        log = ResizableTerminalLogList()
        log.setObjectName("pipelaTerminalLog")
        log.setReadOnly(True)
        log.setAcceptRichText(True)
        self._log = log
        self._terminal_scroll_restore_timer = QTimer(self)
        self._terminal_scroll_restore_timer.setSingleShot(True)
        self._terminal_scroll_restore_timer.setInterval(60)
        self._terminal_scroll_restore_timer.timeout.connect(self._flush_terminal_scroll_restore)
        tsb = log.verticalScrollBar()
        # valueChanged 는 코드에서 setValue(맨 아래) 할 때도 나가 «사용자 스크롤» 복원이 도는 버그가 있음.
        tsb.sliderMoved.connect(self._schedule_terminal_scroll_restore_from_user)
        tsb.actionTriggered.connect(self._schedule_terminal_scroll_restore_from_user)

        # ``ai_debug_session_log.install_stdio_tee`` 가 켜져 있으면 ``sys.stdout`` 이 Tee — 그걸 감싼다.
        bridge = _StreamBridge(sys.stdout, pipela_mod)
        bridge.text.connect(self._append_terminal_log_html)
        bridge.record_terminal_line.connect(self._on_terminal_log_line_recorded)
        sys.stdout = bridge
        self._stdout_bridge = bridge

        settings_wrap = QWidget()
        sw_l = QVBoxLayout(settings_wrap)
        sw_l.setSpacing(shell_hub_inner_gutter_px())

        self._settings_breadcrumb_wrap = QWidget()
        _bread_l = QHBoxLayout(self._settings_breadcrumb_wrap)
        _bread_l.setContentsMargins(0, 0, 0, 0)
        _bread_l.setSpacing(scale_px_h(6))
        self._settings_breadcrumb_layout = _bread_l
        sw_l.addWidget(self._settings_breadcrumb_wrap)

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        hub_pg = QWidget()
        hvl = QVBoxLayout(hub_pg)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        _hub_gap = scale_px_v(8)
        hub_outer = QVBoxLayout(inner)
        hub_outer.setContentsMargins(0, 0, 0, 0)
        hub_outer.setSpacing(_hub_gap)
        self._settings_hub_outer = hub_outer

        grid_wrap = QWidget()
        iv = QGridLayout(grid_wrap)
        self._settings_hub_iv = iv
        iv.setHorizontalSpacing(_hub_gap)
        iv.setVerticalSpacing(_hub_gap)
        iv.setColumnStretch(0, 1)
        iv.setColumnStretch(1, 1)
        self._panel_placeholders: dict[str, int] = {}
        self._settings_hub_style_buttons: list[QPushButton] = []
        st_hub = settings_hub_entry_button_qss()
        for i, (pid, title) in enumerate(HUB_MAIN_ENTRIES):
            hb = QPushButton(title)
            hb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hb.setCursor(Qt.CursorShape.PointingHandCursor)
            hb.clicked.connect(
                lambda _checked=False, p=pid, t=title: self._open_settings_panel(p, t),
            )
            hb.setStyleSheet(st_hub)
            self._settings_hub_style_buttons.append(hb)
            iv.addWidget(hb, i // 2, i % 2)
        hub_outer.addWidget(grid_wrap, 0)
        hub_outer.addStretch(1)

        _hub_footer = QWidget()
        _hub_fl = QHBoxLayout(_hub_footer)
        _hub_fl.setContentsMargins(0, 0, 0, 0)
        _hub_fl.setSpacing(_hub_gap)
        for pid, title in HUB_FOOTER_ENTRIES:
            _fb = QPushButton(title)
            _fb.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            _fb.setCursor(Qt.CursorShape.PointingHandCursor)
            _fb.clicked.connect(
                lambda _checked=False, p=pid, t=title: self._open_settings_panel(
                    p, t
                ),
            )
            _fb.setStyleSheet(st_hub)
            self._settings_hub_style_buttons.append(_fb)
            _hub_fl.addWidget(_fb, 1)
        hub_outer.addWidget(_hub_footer, 0)
        sc.setWidget(inner)
        tie_scroll_content_min_width(sc)
        hvl.addWidget(sc, 1)
        self._stack.addWidget(hub_pg)
        for pid, title in HUB_ENTRIES:
            if pid == "console":
                ph = ConsoleSettingsPanel(pipela_mod)
            elif pid == "lc":
                ph = LeftClickSettingsPanel(pipela_mod)
            elif pid == "ft":
                ph = FlameTriggerSettingsPanel(pipela_mod)
            elif pid == "rl":
                ph = ReloadSettingsPanel(pipela_mod)
            elif pid == "hp":
                ph = HpRefillSettingsPanel(pipela_mod)
            elif pid == "ride":
                ph = RideSettingsPanel(pipela_mod)
            elif pid == "ammo":
                ph = AmmoRestockSettingsPanel(pipela_mod)
            elif pid == "merc":
                ph = CallMercSettingsPanel(pipela_mod)
            elif pid == "sg":
                ph = StartGameSettingsPanel(pipela_mod)
            elif pid == "iface":
                ph = InterfaceSettingsPanel(pipela_mod)
            elif pid == "update":
                ph = UpdateSettingsPanel(pipela_mod)
            elif pid == "tesseract":
                ph = TesseractSettingsPanel(pipela_mod)
            else:
                ph = QLabel(
                    f"«{title}»\n\n이 설정 패널을 준비 중입니다.\n패널 id: {pid}",
                )
                ph.setWordWrap(True)
                ph.setStyleSheet(
                    f"{settings_footnote_style()} padding: {qss_pad_all(16)};",
                )
                settings_label_align_center_h(ph)
            self._panel_placeholders[pid] = self._stack.count()
            self._stack.addWidget(ph)
        sw_l.addWidget(self._stack, 1)
        # 설정 허브(0) + 서브패널 — 마우스 뒤로/앞으로와 동일한 방문 스택
        self._settings_nav_hist: list[int] = [0]
        self._settings_nav_pos: int = 0
        self._update_settings_breadcrumb()

        _term_tab_ic = _action_icon_qicon(UI_ICON_TERMINAL_PATH)
        if _term_tab_ic.isNull():
            tabs.addTab(log, "터미널")
        else:
            tabs.addTab(log, _term_tab_ic, "터미널")
        _set_tab_ic = _action_icon_qicon(UI_ICON_SETTINGS_PATH)
        if _set_tab_ic.isNull():
            tabs.addTab(settings_wrap, "설정")
        else:
            tabs.addTab(settings_wrap, _set_tab_ic, "설정")
        tab_area = QWidget()
        tab_area.setObjectName("pipelaTabArea")
        tab_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tab_area.setAutoFillBackground(True)
        _tap = tab_area.palette()
        _tab_bg = QColor(T.SURFACE)
        _tap.setColor(QPalette.ColorRole.Window, _tab_bg)
        _tap.setColor(QPalette.ColorRole.Base, _tab_bg)
        tab_area.setPalette(_tap)
        tab_al = QVBoxLayout(tab_area)
        tab_al.setContentsMargins(0, 0, 0, 0)
        tab_al.setSpacing(0)
        tab_al.addWidget(tabs, 1)
        self._tab_area = tab_area
        tabs.setAutoFillBackground(True)
        _tbp = tabs.palette()
        _tbp.setColor(QPalette.ColorRole.Window, _tab_bg)
        _tbp.setColor(QPalette.ColorRole.Base, _tab_bg)
        tabs.setPalette(_tbp)
        _tb = tabs.tabBar()
        _tb.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        _tb.setAutoFillBackground(True)
        _tb.setPalette(_tbp)
        main_split = QSplitter(Qt.Orientation.Vertical)
        main_split.setObjectName("pipelaMainSplit")
        main_split.setChildrenCollapsible(False)
        main_split.setHandleWidth(max(1, scale_px_h(3)))
        main_split.addWidget(feature_dock)
        main_split.addWidget(tab_area)
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)
        self._main_splitter = main_split
        main_l.addWidget(main_split, 1)
        tabs.currentChanged.connect(self._on_main_tab_changed)
        self._apply_main_tabs_cluster_label_style()
        self._terminal_rel_timer = QTimer(self)
        self._terminal_rel_timer.setInterval(1000)
        self._terminal_rel_timer.timeout.connect(self._on_terminal_relative_tick)
        self._sync_terminal_relative_timer()  # always-on 1s: relative prefix + time-prefix age colors
        self._terminal_fade_timer = QTimer(self)
        self._terminal_fade_timer.setInterval(_TERMINAL_FADE_TICK_MS)
        self._terminal_fade_timer.timeout.connect(self._on_terminal_fade_tick)

        self._settings_wrap = settings_wrap
        self._stack.currentChanged.connect(self._on_settings_stack_current_changed)
        _app = QApplication.instance()
        if _app is not None:
            _app.installEventFilter(self)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._refresh)
        self._poll.start(self._control_poll_interval_ms())
        # 게임 창 화면 중앙 정렬은 Win32 SetWindowPos 경로가 길어질 수 있어 제어 폴링과 분리.
        self._game_center_timer = QTimer(self)
        self._game_center_timer.setInterval(400)
        self._game_center_timer.timeout.connect(self._tick_apply_game_window_screen_center)
        self._game_center_timer.start()
        self._client_dock_burst_timer = QTimer(self)
        self._client_dock_burst_timer.setInterval(1000)
        self._client_dock_burst_timer.timeout.connect(self._on_client_dock_burst_tick)
        self._client_dock_burst_ticks_remaining: int = 0
        # 게임 최소화로 CLIENT→LAUNCHER 된 뒤 복귀(LAUNCHER→CLIENT)는 burst 생략(진짜 런처→클라만 10초).
        self._suppress_next_client_dock_burst: bool = False
        self._paired_kill_width_pending: int | None = None
        self._typography_debounce = QTimer(self)
        self._typography_debounce.setSingleShot(True)
        self._typography_debounce.setInterval(95)
        self._typography_debounce.timeout.connect(self._flush_coalesced_typography)
        self._last_settings_breadcrumb_sig: object | None = None
        self._last_hub_entry_qss: str | None = None
        self._sync_action_button_icon_sizes()
        self._apply_shell_layout_metrics()
        self._sync_terminal_settings_tab_chrome()
        self._control_left_resize_edge = _ControlLeftResizeEdge(self)
        # 종료: 시스템 트레이 → «종료» (시스템 메뉴바 없음, 프레임리스)

        if start_tray_only:
            self.hide()
        else:
            self._control_chrome_user_dismissed = False
            self.show()
            self._sync_launcher_phase_docked_chrome()
            QTimer.singleShot(0, self._bring_qt_control_to_front)
        QTimer.singleShot(0, self._sync_feature_splitter_geometry)
        QTimer.singleShot(100, self._sync_feature_splitter_geometry)

    def _parse_action_button_pad_px(self) -> tuple[int, int]:
        """AGENT: QSS padding string → (vertical_px, horizontal_px)."""
        s = action_button_qss_padding()
        try:
            parts = s.replace("px", "").split()
            if len(parts) >= 2:
                return int(parts[0]), int(parts[1])
        except (TypeError, ValueError):
            pass
        return scale_px_v(8), scale_px_h(8)

    def _uniform_action_button_height_px(self) -> int:
        """AGENT: one height for all feature toggles — DemiBold+padding matches QSS so tab switch does not reflow."""
        m = self._m
        iz = int(control_icon_side_px(m))
        pt = float(scaled_design_pt(10.0 * control_action_label_pt_factor()))
        f = app_default_qfont(11)
        f.setWeight(QFont.Weight.DemiBold)
        f.setPointSizeF(max(7.5, min(22.0, pt)))
        fm = QFontMetricsF(f)
        text_h = int(math.ceil(float(fm.height())))
        pv, _ph = self._parse_action_button_pad_px()
        border = 2
        core = max(iz, text_h) + 2 * pv + border
        return max(scale_px_v(32), core)

    def _sync_feature_splitter_geometry(self) -> None:
        """AGENT: fixed feature block (buttons+sep) vs terminal/settings — splitter; uniform button heights."""
        if not getattr(self, "_btns", None):
            return
        td = getattr(self, "_feature_top_dock", None)
        sp = getattr(self, "_main_splitter", None)
        btn_h = self._uniform_action_button_height_px()
        try:
            for b in self._btns.values():
                b.setFixedHeight(btn_h)
        except Exception:
            pass
        grid_gap = scale_px_v(8)
        n_rows = 6
        grid_h = n_rows * btn_h + max(0, n_rows - 1) * grid_gap
        try:
            ap = getattr(self, "_action_btn_panel", None)
            if ap is not None:
                ap.setFixedHeight(grid_h)
        except Exception:
            pass
        sep_h = scale_px_v(10) + max(1, scale_px_v(1)) + scale_px_v(14)
        try:
            sw = getattr(self, "_actions_tabs_sep", None)
            if sw is not None:
                sl = sw.layout()
                if sl is not None:
                    sl.activate()
                sep_h = max(sep_h, int(sw.sizeHint().height()))
        except Exception:
            pass
        gutter = shell_hub_inner_gutter_px()
        total_top = grid_h + gutter + sep_h
        try:
            if td is not None:
                td.setFixedHeight(total_top)
        except Exception:
            pass
        try:
            if sp is not None:
                H = int(sp.height())
                if H <= 0:
                    try:
                        H = max(int(self.height()), total_top + scale_px_v(120))
                    except Exception:
                        H = total_top + scale_px_v(120)
                hw = int(sp.handleWidth())
                rest = max(scale_px_v(120), H - total_top - hw)
                sp.setSizes([total_top, rest])
        except Exception:
            pass

    def _sync_action_button_icon_sizes(self) -> None:
        try:
            iz = control_icon_side_px(self._m)
            sz = QSize(iz, iz)
            for b in self._btns.values():
                b.setIconSize(sz)
        except Exception:
            pass

    def _apply_shell_layout_metrics(self) -> None:
        try:
            root = self.centralWidget()
            if root is not None:
                body = root.findChild(QWidget, "pipelaBody")
                if body is not None:
                    bl = body.layout()
                    if isinstance(bl, QVBoxLayout):
                        ml, mt, mr, mb = main_shell_margins_lr_tb()
                        bl.setContentsMargins(ml, mt, mr, mb)
                        bl.setSpacing(shell_hub_inner_gutter_px())
            sw_sep = getattr(self, "_actions_tabs_sep", None)
            if sw_sep is not None:
                sls = sw_sep.layout()
                if isinstance(sls, QVBoxLayout):
                    sls.setContentsMargins(
                        0,
                        scale_px_v(10),
                        0,
                        scale_px_v(14),
                    )
            ta = getattr(self, "_tab_area", None)
            if ta is not None:
                tal = ta.layout()
                if isinstance(tal, QVBoxLayout):
                    tal.setContentsMargins(0, 0, 0, 0)
            bg = getattr(self, "_btn_grid", None)
            if bg is not None:
                bg.setHorizontalSpacing(scale_px_h(8))
                bg.setVerticalSpacing(scale_px_v(8))
            sw = getattr(self, "_settings_wrap", None)
            if sw is not None:
                sl = sw.layout()
                if isinstance(sl, QVBoxLayout):
                    sl.setSpacing(shell_hub_inner_gutter_px())
            _hg_h = scale_px_h(8)
            _hg_v = scale_px_v(8)
            iv = getattr(self, "_settings_hub_iv", None)
            if iv is not None and isinstance(iv, QGridLayout):
                iv.setHorizontalSpacing(_hg_h)
                iv.setVerticalSpacing(_hg_v)
            ho = getattr(self, "_settings_hub_outer", None)
            if ho is not None:
                ho.setSpacing(_hg_v)
        except Exception:
            pass

    def _sync_typography_width(self) -> None:
        try:
            w = int(max(8, int(getattr(self, "_dock_w", self.width()))))
        except Exception:
            try:
                w = int(self.width())
            except Exception:
                return
        try:
            h = int(max(8, int(self.height())))
        except Exception:
            h = None
        prev_w = self._last_typography_layout_w
        prev_h = getattr(self, "_last_typography_layout_h", None)
        if prev_w is not None and int(w) == int(prev_w):
            if h is None or (prev_h is not None and int(h) == int(prev_h)):
                return
        self._last_typography_layout_w = w
        if h is not None:
            self._last_typography_layout_h = h
        try:
            set_typography_layout_width_px(w)
        except Exception:
            return
        if h is not None:
            try:
                set_typography_layout_height_px(h)
            except Exception:
                pass
        self._last_btn_style_state = None
        self.apply_scaled_typography()
        try:
            kcw = getattr(self, "_kc_float", None)
            if kcw is not None and kcw.isVisible():

                def _kc_typo() -> None:
                    try:
                        fn = getattr(kcw, "apply_scaled_typography", None)
                        if callable(fn):
                            fn()
                    except Exception:
                        pass

                QTimer.singleShot(0, _kc_typo)
        except Exception:
            pass

    def apply_scaled_typography(self, *, immediate: bool = False) -> None:
        """폰트·도킹 폭 반영. 짧은 디바운스로 스트립·도킹 연쇄 시 같은 프레임 다중 호출을 한 번으로 합침."""
        if immediate:
            self._typography_debounce.stop()
            self._typography_flush_scheduled = False
            self._apply_scaled_typography_impl()
            return
        self._typography_flush_scheduled = True
        self._typography_debounce.start()

    def _flush_coalesced_typography(self) -> None:
        self._typography_flush_scheduled = False
        try:
            self._apply_scaled_typography_impl()
        except Exception:
            pass

    def _apply_scaled_typography_impl(self) -> None:
        st = self._stack
        tabs = self._tabs
        _on_settings = tabs is not None and int(tabs.currentIndex()) == 1
        _n_apply = 0
        if st is not None and _on_settings:
            _n_apply = 1 if st.currentWidget() is not None else 0
        _tag = f"stack={_n_apply}"
        _cq = control_frameless_window_qss()
        if _cq != getattr(self, "_last_control_root_qss", None):
            self._last_control_root_qss = _cq
            self.setStyleSheet(_cq)
        if _on_settings:
            if getattr(self, "_settings_breadcrumb_wrap", None) is not None:
                self._update_settings_breadcrumb()
            _hub_q = settings_hub_entry_button_qss()
            if _hub_q != getattr(self, "_last_hub_entry_qss", None):
                self._last_hub_entry_qss = _hub_q
                for hb in getattr(self, "_settings_hub_style_buttons", []) or []:
                    hb.setStyleSheet(_hub_q)
        # 터미널 탭일 때 스택은 가려짐 — 숨겨진 패널 십여 개를 매 틱 갱신하지 않음
        if st is not None and _on_settings:
            w = st.currentWidget()
            if w is not None:
                fn = getattr(w, "apply_scaled_typography", None)
                if callable(fn):
                    fn()
        self._apply_shell_layout_metrics()
        self._sync_action_button_icon_sizes()
        self._resync_action_button_captions()
        try:
            self._btns["flame"].setText(self._flame_action_caption())
        except Exception:
            pass
        try:
            self._btns["reload"].setText(self._reload_action_caption())
        except Exception:
            pass
        self._apply_action_toggle_styles(self._m)
        self._sync_terminal_settings_tab_chrome()
        self._sync_terminal_relative_timer()
        QTimer.singleShot(0, self._post_typography_layout_and_fit)

    def _apply_main_tabs_cluster_label_style(self) -> None:
        """메인 탭은 `_PairedControlTabBar.paintEvent`에서 아이콘+텍스트를 그림. QSS/프록시 잔여만 제거."""
        tabs = getattr(self, "_tabs", None)
        if tabs is None:
            return
        tb = tabs.tabBar()
        try:
            tb.setStyle(None)
        except Exception:
            pass
        try:
            tb.updateGeometry()
            tb.update()
        except Exception:
            pass

    def _post_typography_layout_and_fit(self) -> None:
        """레이아웃 확정 후 스플리터 정렬 등(폭 피팅 순회는 비활성)."""
        try:
            self._sync_feature_splitter_geometry()
        except Exception:
            pass
        self._apply_main_tabs_cluster_label_style()

    def _sync_terminal_settings_tab_chrome(self) -> None:
        """터미널 로그·탭바·설정 탭 — QSS와 동일 폭·루트 pt 스케일을 QFont 등으로 맞춤."""
        try:
            log = getattr(self, "_log", None)
            if log is not None:
                lf = app_default_qfont(11)
                lf.setPointSizeF(max(7.5, min(22.0, scaled_design_pt(9.25))))
                log.setFont(lf)
                if hasattr(log, "set_log_inner_margin_px"):
                    log.set_log_inner_margin_px(scale_px_v(4))
        except Exception:
            pass
        try:
            tabs = getattr(self, "_tabs", None)
            if tabs is not None:
                tb = tabs.tabBar()
                tf = app_default_qfont(11, QFont.Weight.Medium)
                tf.setPointSizeF(ctc.main_tabs_label_font_point_size())
                tb.setFont(tf)
                iz = ctc.main_tabs_bar_icon_size_px()
                tb.setIconSize(QSize(iz, iz))
                self._apply_main_tabs_cluster_label_style()
        except Exception:
            pass

    def _on_terminal_log_line_recorded(self, wall_t: float, line_mono: float, raw: str) -> None:
        self._terminal_log_memory.append((float(wall_t), float(line_mono), raw))

    def _flush_fading_to_archive(self) -> None:
        """페이드 큐에만 있던 줄을 잃지 않도록 아카이브로 옮김(탭 전환·비터미널 프룬 등)."""
        fd = self._terminal_log_fading
        arch = self._terminal_log_archive
        while fd:
            wt, lm, rw, _ = fd.popleft()
            arch.append((wt, lm, rw))

    def _cap_terminal_line_buffers(self) -> None:
        """아카이브+페이드+메모리 합산 상한 — 가장 오래된 줄(아카이브 앞)부터 제거."""
        arch = self._terminal_log_archive
        fd = self._terminal_log_fading
        mem = self._terminal_log_memory
        cap = int(_TERMINAL_LOG_MAX_STORED_LINES)
        while len(arch) + len(fd) + len(mem) > cap:
            if arch:
                arch.popleft()
            elif fd:
                fd.popleft()
            else:
                mem.popleft()

    def _terminal_tab_is_front(self) -> bool:
        t = self._tabs
        return t is None or int(t.currentIndex()) == 0

    def _drop_fully_faded_terminal_lines(self) -> None:
        fd = self._terminal_log_fading
        if not fd:
            return
        now = time.monotonic()
        arch = self._terminal_log_archive
        while fd and (now - fd[0][3]) >= _TERMINAL_LOG_FADE_OUT_SEC:
            wt, lm, rw, _ = fd.popleft()
            arch.append((wt, lm, rw))

    def _sync_terminal_fade_timer(self) -> None:
        tm = getattr(self, "_terminal_fade_timer", None)
        if tm is None:
            return
        if self._terminal_log_fading and self._terminal_tab_is_front():
            if not tm.isActive():
                tm.start(_TERMINAL_FADE_TICK_MS)
        else:
            tm.stop()

    def _on_terminal_fade_tick(self) -> None:
        if not self._terminal_tab_is_front():
            self._sync_terminal_fade_timer()
            return
        self.rebuild_terminal_log_display_for_time_mode()

    def _schedule_terminal_scroll_restore_from_user(self) -> None:
        if self._terminal_log_scroll_from_code:
            return
        if not self._terminal_tab_is_front():
            return
        # 휠/스크롤 직후부터 설정된 «로그 자동 숨김»(보존) 시간만큼은 mem→페이드 프룬을 쉼(생성 시각은 그대로).
        self._terminal_scroll_grace_mono = time.monotonic()
        if self._terminal_log_archive or self._terminal_log_fading:
            self._terminal_scroll_restore_pending = True
            self._terminal_scroll_restore_timer.start(60)

    def _flush_terminal_scroll_restore(self) -> None:
        if not self._terminal_scroll_restore_pending:
            return
        self._terminal_scroll_restore_pending = False
        self._apply_terminal_user_scroll_restore()
        self.rebuild_terminal_log_display_for_time_mode()

    def _apply_terminal_user_scroll_restore(self) -> None:
        """숨김(아카이브·페이드) 줄만 메모리로 되돌림 — wall_t·line_mono(생성 시각)는 그대로 유지."""
        arch = self._terminal_log_archive
        fd = self._terminal_log_fading
        mem = self._terminal_log_memory
        head: list[tuple[float, float, str]] = []
        while arch:
            w0, l0, rw = arch.popleft()
            head.append((w0, l0, rw))
        while fd:
            w0, l0, rw, _fs = fd.popleft()
            head.append((w0, l0, rw))
        new_mem = deque(head + list(mem))
        mem.clear()
        mem.extend(new_mem)
        self._sync_terminal_fade_timer()

    def _prune_terminal_log_memory_by_retention(self) -> int:
        """보존 분 초과 줄 — 터미널 탭이 보일 때는 페이드 큐로, 아니면 즉시 삭제."""
        m = self._m
        try:
            rm = int(getattr(m, "console_log_retention_minutes", 30))
        except Exception:
            rm = 30
        try:
            rs = int(getattr(m, "console_log_retention_seconds", 0))
        except Exception:
            rs = 0
        total_sec = float(console_log_retention_total_sec(rm, rs))
        cutoff = time.time() - total_sec
        mem = self._terminal_log_memory
        fade = self._terminal_log_fading
        n0 = len(mem)
        if not self._terminal_tab_is_front():
            self._flush_fading_to_archive()
            while mem and float(mem[0][0]) < cutoff:
                mem.popleft()
            self._sync_terminal_fade_timer()
            return n0 - len(mem)
        g = self._terminal_scroll_grace_mono
        if (
            g is not None
            and total_sec > 0.0
            and (time.monotonic() - float(g)) < total_sec
        ):
            self._sync_terminal_fade_timer()
            return 0
        while mem and float(mem[0][0]) < cutoff:
            wt, lm, rw = mem.popleft()
            fade.append((wt, lm, rw, time.monotonic()))
        self._sync_terminal_fade_timer()
        return n0 - len(mem)

    def apply_console_log_retention_now(self) -> None:
        """설정에서 보존 분 변경 직후 — 즉시 메모리·터미널 뷰 동기화."""
        self._terminal_scroll_grace_mono = None
        try:
            self.rebuild_terminal_log_display_for_time_mode()
        except Exception:
            pass

    def _sync_terminal_relative_timer(self) -> None:
        t = getattr(self, "_terminal_rel_timer", None)
        if t is None:
            return
        t.start()

    def sync_console_time_display_chrome(self) -> None:
        """`console_log_time_display_mode` 등 변경 후 — 상대 1s 타이머·뷰 갱신(레지/설정 패널에서 호출)."""
        self._sync_terminal_relative_timer()
        self.rebuild_terminal_log_display_for_time_mode()

    def _on_terminal_relative_tick(self) -> None:
        tabs = self._tabs
        if tabs is not None and int(tabs.currentIndex()) != 0:
            self._prune_terminal_log_memory_by_retention()
            return
        self.rebuild_terminal_log_display_for_time_mode()

    def rebuild_terminal_log_display_for_time_mode(self) -> None:
        """절대/상대 전환·1초 틱 — 보존 초과 줄은 페이드 후 제거, HTML 전부 다시 렌더."""
        self._prune_terminal_log_memory_by_retention()
        self._drop_fully_faded_terminal_lines()
        self._cap_terminal_line_buffers()
        try:
            log = self._log
            m = self._m
            sb = log.verticalScrollBar()
            at_bottom = sb.maximum() <= 0 or sb.value() >= sb.maximum() - 3
            saved_v = sb.value()
            ipx = max(12, min(22, scale_px_v(14)))
            now_m = time.monotonic()
            now_w = time.time()
            tmode = getattr(
                m,
                "console_log_time_display_mode",
                CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            )
            self._terminal_log_scroll_from_code = True
            entries: list[tuple[tuple[float, float], str]] = []
            for wall_t, line_mono, raw, fade_start in self._terminal_log_fading:
                tp = format_terminal_log_stored_prefix(
                    m, wall_time=wall_t, line_monotonic=line_mono,
                )
                try:
                    if tmode == CONSOLE_LOG_TIME_MODE_RELATIVE:
                        age = max(0.0, now_m - float(line_mono))
                    else:
                        age = max(0.0, now_w - float(wall_t))
                except Exception:
                    age = 0.0
                op = _terminal_fade_line_opacity(now_m - float(fade_start))
                html_ln = format_terminal_log_line_html(
                    tp,
                    raw,
                    icon_px=ipx,
                    time_age_sec=age,
                    line_opacity=op,
                )
                entries.append(((float(wall_t), float(line_mono)), html_ln))
            for wall_t, line_mono, raw in self._terminal_log_memory:
                tp = format_terminal_log_stored_prefix(
                    m, wall_time=wall_t, line_monotonic=line_mono,
                )
                try:
                    if tmode == CONSOLE_LOG_TIME_MODE_RELATIVE:
                        age = max(0.0, now_m - float(line_mono))
                    else:
                        age = max(0.0, now_w - float(wall_t))
                except Exception:
                    age = 0.0
                html_ln = format_terminal_log_line_html(
                    tp, raw, icon_px=ipx, time_age_sec=age,
                )
                entries.append(((float(wall_t), float(line_mono)), html_ln))
            row_height_factors: list[float] = []
            for _wt, _lm, _rw, fade_start in self._terminal_log_fading:
                t = _terminal_fade_eased_progress(now_m - float(fade_start))
                row_height_factors.append(max(0.0, 1.0 - t))
            row_height_factors.extend([1.0] * len(self._terminal_log_memory))
            log.apply_log_rows(entries, row_height_factors=row_height_factors)
            log.flush_terminal_log_layout()
            if at_bottom:
                sb.setValue(sb.maximum())
            else:
                new_max = sb.maximum()
                sb.setValue(min(saved_v, new_max))
        except Exception:
            pass
        finally:
            self._terminal_log_scroll_from_code = False
        self._sync_terminal_fade_timer()

    def _append_terminal_log_html(self, fragment: str) -> None:
        if not fragment:
            return
        try:
            self._terminal_log_scroll_from_code = True
            log = self._log
            mem = self._terminal_log_memory
            if mem:
                k = (float(mem[-1][0]), float(mem[-1][1]))
                log.append_terminal_html_row(k, fragment)
            if self._trim_terminal_log_blocks() > 0:
                self.rebuild_terminal_log_display_for_time_mode()
            elif self._prune_terminal_log_memory_by_retention() > 0:
                self.rebuild_terminal_log_display_for_time_mode()
        except Exception:
            pass
        finally:
            self._terminal_log_scroll_from_code = False

    def _trim_terminal_log_blocks(self) -> int:
        n = 0
        try:
            max_blocks = int(_TERMINAL_LOG_MAX_STORED_LINES)
            guard = 0
            arch = self._terminal_log_archive
            fd = self._terminal_log_fading
            mem = self._terminal_log_memory
            while len(arch) + len(fd) + len(mem) > max_blocks and guard < max_blocks + 50:
                guard += 1
                n += 1
                if arch:
                    arch.popleft()
                elif fd:
                    fd.popleft()
                elif mem:
                    mem.popleft()
                else:
                    break
        except Exception:
            pass
        return n

    def _bring_qt_control_to_front(self) -> None:
        if self._start_tray_only or self.isHidden():
            return
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def _resync_dock_w_for_ui_phase(self) -> None:
        """런처 ↔ 클라이언트 전환 후 — 레이아웃 프리셋으로 **사용자 저장 폭**을 덮지 않음(도킹·타이포만)."""
        with ctd_span("control._resync_dock_w.get_dock_panel_wh"):
            _, _ = get_dock_panel_wh(self._m)
        self._last_dock_sig = None
        self._last_standby_sig = None
        self._last_btn_style_state = None
        QTimer.singleShot(0, self.apply_scaled_typography)
        QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
        QTimer.singleShot(120, lambda: self._dock_to_anchor(force=True))

    def _start_client_phase_dock_burst(self) -> None:
        """클라이언트 페이즈 진입 후 약 10초간 1초마다 재스냅(총 10회, 첫 회는 1초 뒤)."""
        self._client_dock_burst_ticks_remaining = 10
        self._client_dock_burst_timer.start(1000)

    def _stop_client_phase_dock_burst(self) -> None:
        self._client_dock_burst_ticks_remaining = 0
        self._client_dock_burst_timer.stop()

    def _on_client_dock_burst_tick(self) -> None:
        if self._client_dock_burst_ticks_remaining <= 0:
            self._client_dock_burst_timer.stop()
            return
        try:
            ctd_log(
                f"client_dock_burst_tick remaining="
                f"{self._client_dock_burst_ticks_remaining}",
            )
        except Exception:
            pass
        self._client_dock_burst_ticks_remaining -= 1
        self._force_client_dock_resync()
        if self._client_dock_burst_ticks_remaining <= 0:
            self._client_dock_burst_timer.stop()

    def _force_client_dock_resync(self) -> None:
        """재스냅 전용 — 가드·시그 디듀프 없이 Win32 도킹."""
        m = self._m
        with ctd_span("control._force_client_dock_resync"):
            try:
                anchor = resolve_dock_anchor_hwnd(m)
                if not anchor:
                    ctd_log("_force_client_dock_resync no anchor")
                    return
                ah = int(anchor)
                lay = compute_side_dock_layout(
                    m, ah, dock_w_log=int(self._dock_w), side="left",
                )
                if lay is None:
                    ctd_log("_force_client_dock_resync compute_side_dock_layout→None")
                    return
                self._last_standby_sig = None
                self._last_dock_sig = lay.dedupe_sig
                self._apply_computed_side_dock(m, ah, lay)
            except Exception as e:
                ctd_log_exc("_force_client_dock_resync", e)

    def _schedule_client_resolution_dock_retries(self) -> None:
        """클라(앵커) 내부 해상도·클라이언트 영역 변경 직후 잠깐 반복 재도킹 — 전환 중깨짐·멈춤 완화."""
        if self._start_tray_only:
            return

        def _pulse() -> None:
            try:
                self._dock_to_anchor(force=True)
            except Exception:
                pass

        for ms in (0, 48, 96, 180, 320, 620, 1200):
            QTimer.singleShot(ms, _pulse)

    def _maybe_extend_client_phase_dock_burst(self) -> None:
        """해상도·클라 rect 변화 시에도 페이즈 전환과 같은 저주파 강제 동기 구간 부여."""
        if self._start_tray_only:
            return
        if getattr(self, "_ui_dock_phase_tracked", None) != UI_DOCK_PHASE_CLIENT:
            return
        try:
            self._client_dock_burst_ticks_remaining = max(
                int(self._client_dock_burst_ticks_remaining), 12
            )
            self._client_dock_burst_timer.start()
        except Exception:
            pass

    def _dock_to_standby_centered(self, *, force: bool = False) -> None:
        """게임·런처 앵커 없음(대기) — 제어창을 주 모니터 작업 영역 중앙에 둔다(도킹 좌표 잔상 방지)."""
        if self._start_tray_only:
            return
        m = self._m
        if self.isHidden() and not pipela_dev_ui_standby_chrome(m):
            return
        if not getattr(m, "running", True):
            return
        try:
            app = QApplication.instance()
            if app is None:
                return
            scr = app.primaryScreen()
            if scr is None:
                return
            ag = scr.availableGeometry()
            w_preset, h_log = get_dock_panel_wh(m)
            h_log = max(8, int(h_log))
            dock_cur = max(8, int(getattr(self, "_dock_w", w_preset)))
            try:
                cp = int(getattr(m, "control_panel_w", 0) or 0)
            except (TypeError, ValueError):
                cp = 0
            try:
                kcw = int(getattr(m, "kill_counter_panel_w", 0) or 0)
            except (TypeError, ValueError):
                kcw = 0
            if cp > 0:
                w_log = clamp_dock_pair_panel_w(cp)
            elif kcw > 0:
                w_log = clamp_dock_pair_panel_w(kcw)
            elif dock_cur > 16:
                w_log = clamp_dock_pair_panel_w(dock_cur)
            else:
                w_log = max(8, int(w_preset))
            w_log = min(w_log, max(8, ag.width() - 16))
            h_log = min(h_log, max(8, ag.height() - 16))
            x_log = int(ag.left() + max(0, (ag.width() - w_log) // 2))
            y_log = int(ag.top() + max(0, (ag.height() - h_log) // 2))
            sig = ("standby", x_log, y_log, w_log, h_log)
            if not force and sig == self._last_standby_sig:
                return
            self._last_standby_sig = sig
            self._last_dock_sig = None
            self._dock_w = w_log
            try:
                self.setFixedWidth(w_log)
            except Exception:
                pass
            self.setGeometry(x_log, y_log, w_log, h_log)
            if sys.platform == "win32":
                try:
                    scale = float(scr.devicePixelRatio()) or 1.0
                    if scale <= 0.01:
                        scale = 1.0
                    win32_set_window_outer_rect(
                        int(self.winId()),
                        int(round(x_log * scale)),
                        int(round(y_log * scale)),
                        int(round(w_log * scale)),
                        int(round(h_log * scale)),
                    )
                except Exception:
                    pass
            _prev_dw = self._last_docked_w_log
            try:
                set_typography_layout_width_px(int(self.width()))
            except Exception:
                pass
            try:
                set_typography_layout_height_px(int(h_log))
            except Exception:
                pass
            self._last_typography_layout_h = int(h_log)
            self._last_docked_w_log = w_log
            try:
                self._last_typography_layout_w = int(self.width())
            except Exception:
                self._last_typography_layout_w = w_log
            if _prev_dw is None or abs(int(w_log) - int(_prev_dw)) >= 2:
                self._last_btn_style_state = None
            QTimer.singleShot(0, self.apply_scaled_typography)
        except Exception:
            pass

    def _sync_launcher_phase_docked_chrome(self) -> None:
        """런처 UI 페이즈: 상단 스트립만 — 제어창·킬 floater 는 숨김. 그 외 페이즈는(×로 닫지 않은 경우) 복원."""
        if self._start_tray_only:
            return
        m = self._m
        if pipela_dev_ui_standby_chrome(m):
            if self._control_chrome_user_dismissed:
                return
            try:
                if self.isMinimized():
                    self.showNormal()
                if not self.isVisible():
                    self.show()
                self.raise_()
                self._sync_pipela_qt_control_win_hwnd()
            except Exception:
                pass
            self._dock_to_standby_centered(force=False)
            self._sync_kill_counter_window()
            return
        try:
            _th_sl = m.refresh_target_hwnd_if_needed()
            _luh_sl = m.refresh_smart_updater_hwnd_if_needed()
            _phase = get_ui_dock_phase_from_session(m, _th_sl, _luh_sl)
            if _phase == UI_DOCK_PHASE_LAUNCHER:
                try:
                    kc = self._kc_float
                    if kc is not None and kc.isVisible():
                        kc.hide()
                except Exception:
                    pass
                try:
                    if self.isVisible() or self.isMinimized():
                        self.hide()
                except Exception:
                    pass
                return
            if _phase == UI_DOCK_PHASE_STANDBY:
                try:
                    kc = self._kc_float
                    if kc is not None and kc.isVisible():
                        kc.hide()
                except Exception:
                    pass
                return
        except Exception:
            return
        if self._control_chrome_user_dismissed:
            return
        try:
            if (not self.isVisible()) or self.isMinimized():
                if self.isMinimized():
                    self.showNormal()
                self.show()
                self.raise_()
                self._sync_pipela_qt_control_win_hwnd()
                # 런처→클라 전환: 스트립 `_compute_strip_geometry`가 제어창 HWND·도킹에 의존 — 즉시 1회 도킹 후 한 틱 더.
                self._dock_to_anchor(force=True)
                QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
        except Exception:
            pass

    def _apply_computed_side_dock(self, m, anchor: int, lay: SideDockLayout) -> None:
        """계산된 좌표를 제어창에 반영(Qt + Win32 + Z + 타이포)."""
        self.update()
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
        except Exception:
            pass
        try:
            self.setFixedWidth(w_log)
        except Exception:
            pass
        self.setGeometry(x_log, y_log, w_log, h_log)
        if sys.platform == "win32":
            with ctd_span("control._apply_dock.win32_outer_and_z"):
                try:
                    wid = int(self.winId())
                    win32_set_window_outer_rect(
                        wid, x_phys, y_phys, fw_phys, fh_phys,
                    )
                    ah = int(anchor)
                    lo = self._last_z_anchor
                    sync_docked_chrome_z_order(
                        m,
                        wid,
                        ah,
                        set_owner=(lo != ah),
                        # Steady-state dock ticks: key (anchor, win, overlay) unchanged → skip
                        # redundant SetWindowPos. Force only when anchor identity changes (or
                        # first run: _last_z_anchor is None) so _Z_STACK_LAST_KEY dedupes.
                        force_z_restack=(lo != ah),
                    )
                    self._last_z_anchor = ah
                except Exception as e:
                    ctd_log_exc("_apply_computed_side_dock.win32", e)
        try:
            set_typography_layout_width_px(int(self.width()))
        except Exception:
            pass
        try:
            set_typography_layout_height_px(int(h_log))
        except Exception:
            pass
        try:
            self._last_typography_layout_h = int(h_log)
        except Exception:
            pass
        _prev_dw = self._last_docked_w_log
        self._last_docked_w_log = w_log
        try:
            self._last_typography_layout_w = int(self.width())
        except Exception:
            self._last_typography_layout_w = w_log
        if _prev_dw is None or abs(int(w_log) - int(_prev_dw)) >= 2:
            self._last_btn_style_state = None
        self._dock_rect_miss_count = 0
        QTimer.singleShot(0, self.apply_scaled_typography)

    def _dock_to_anchor(self, *, force: bool = False) -> None:
        """도킹: 메인창(제어) Win32 **외곽 오른쪽** = 앵커 **클라이언트 영역 왼쪽** ``cr[0]`` (화면 좌표).
        런처 등 ``cr`` 없을 때만 외곽 ``ol`` 폴백. 세로·높이는 클라."""
        if self._start_tray_only or self.isHidden():
            try:
                ctd_log("_dock_to_anchor skip start_tray_or_hidden")
            except Exception:
                pass
            return
        m = self._m
        if not getattr(m, "running", True):
            return
        with ctd_span("control._dock_to_anchor"):
            try:
                anchor = resolve_dock_anchor_hwnd(m)
                if not anchor:
                    ctd_log("_dock_to_anchor → standby (no anchor)")
                    self._dock_to_standby_centered(force=force)
                    return
                self._last_standby_sig = None
                with ctd_span("control._dock_to_anchor.compute_side_dock_layout"):
                    lay = compute_side_dock_layout(
                        m,
                        int(anchor),
                        dock_w_log=int(self._dock_w),
                        side="left",
                    )
                if lay is None:
                    self._dock_rect_miss_count = min(
                        int(getattr(self, "_dock_rect_miss_count", 0)) + 1,
                        10_000,
                    )
                    try:
                        ctd_log(
                            f"_dock_to_anchor lay=None miss_count="
                            f"{self._dock_rect_miss_count}",
                        )
                    except Exception:
                        pass
                    if self._dock_rect_miss_count <= 32:
                        QTimer.singleShot(48, lambda: self._dock_to_anchor(force=True))
                    return
                self._last_dock_sig = lay.dedupe_sig
                try:
                    ctd_log(
                        f"_dock_to_anchor apply anchor={anchor!r} "
                        f"log_geom=({lay.x_log},{lay.y_log},{lay.w_log},{lay.h_log}) "
                        f"phys=({lay.x_phys},{lay.y_phys},{lay.fw_phys},{lay.fh_phys})",
                    )
                except Exception:
                    pass
                self._apply_computed_side_dock(m, int(anchor), lay)
            except Exception as e:
                ctd_log_exc("_dock_to_anchor", e)

    def _quit_app(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        rz = getattr(self, "_control_left_resize_edge", None)
        if rz is not None:
            mpx = max(5, int(scale_px_h(7)))
            rz.setGeometry(0, 0, mpx, max(1, self.height()))
            rz.raise_()
        try:
            if e.oldSize().width() != self.width() or e.oldSize().height() != self.height():
                self._sync_typography_width()
        except Exception:
            pass
        try:
            if e.oldSize().height() != self.height():
                QTimer.singleShot(0, self._sync_feature_splitter_geometry)
        except Exception:
            pass

    def showEvent(self, e: QShowEvent) -> None:
        super().showEvent(e)
        rz = getattr(self, "_control_left_resize_edge", None)
        if rz is not None:
            QTimer.singleShot(0, rz.raise_)
        if not getattr(self, "_pipela_startup_typography_done", False):
            self._pipela_startup_typography_done = True

            def _startup_typography() -> None:
                try:
                    from pipela_qt.qt_typography_refresh import refresh_pipela_typography

                    m = getattr(self, "_m", None)
                    if m is not None:
                        refresh_pipela_typography(m)
                except Exception:
                    pass

            QTimer.singleShot(0, _startup_typography)
        self._sync_pipela_qt_control_win_hwnd()
        QTimer.singleShot(0, self._sync_feature_splitter_geometry)
        QTimer.singleShot(0, self._flush_settings_layout)
        QTimer.singleShot(80, self._flush_settings_layout)
        QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
        QTimer.singleShot(100, self._dock_to_anchor)
        QTimer.singleShot(500, lambda: self._dock_to_anchor(force=True))

    def changeEvent(self, e: QEvent) -> None:
        super().changeEvent(e)
        if e.type() != QEvent.Type.WindowStateChange:
            return
        try:
            strip = getattr(self._m, "_qt_title_bar_strip", None)
            if strip is not None:
                strip.invalidate_chrome_layout()
            if not self.isMinimized():
                self._last_dock_sig = None
                self._last_standby_sig = None
                QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
                QTimer.singleShot(150, lambda: self._dock_to_anchor(force=True))
        except Exception:
            pass

    def _on_settings_stack_current_changed(self, index: int) -> None:
        """설정 스택 전환 — 업데이트 패널이면 manifest 자동 확인(터미널 탭일 때는 생략)."""
        if self._tabs is None or int(self._tabs.currentIndex()) != 1:
            return
        self._try_auto_update_manifest_check(int(index))
        QTimer.singleShot(0, self.apply_scaled_typography)

    def _try_auto_update_manifest_check(self, stack_index: int | None = None) -> None:
        """설정 탭이 보이는 상태에서 스택이 업데이트 패널이면 `run_version_check`."""
        if self._tabs is None or self._stack is None:
            return
        if int(self._tabs.currentIndex()) != 1:
            return
        idx = int(self._stack.currentIndex()) if stack_index is None else int(stack_index)
        uidx = self._panel_placeholders.get("update")
        if uidx is None or idx != uidx:
            return
        w = self._stack.widget(idx)
        fn = getattr(w, "run_version_check", None)
        if callable(fn):
            fn()

    def _on_main_tab_changed(self, index: int) -> None:
        if index != 0:
            self._flush_fading_to_archive()
            self._sync_terminal_fade_timer()
        if index == 0:
            self._sync_terminal_relative_timer()
            self.rebuild_terminal_log_display_for_time_mode()
        if index == 1:
            QTimer.singleShot(0, self._flush_settings_layout)
            QTimer.singleShot(50, self._flush_settings_layout)
            # 터미널에서 설정으로 올 때 이미 스택이 «업데이트»면 스택 시그널이 안 올 수 있음
            QTimer.singleShot(0, self._try_auto_update_manifest_check)
            # 보이는 설정 패널만 이전에 터미널 전용 경로로 스킵됐을 수 있음 — 한 번 동기화
            QTimer.singleShot(0, self.apply_scaled_typography)
        QTimer.singleShot(0, self._sync_feature_splitter_geometry)

    def _settings_nav_record_open(self, idx: int) -> None:
        """허브에서 패널을 열 때 — 앞으로 스택은 버리고 새 분기만 남김."""
        if self._stack is None:
            return
        h = self._settings_nav_hist
        p = self._settings_nav_pos
        if p < len(h) - 1:
            del h[p + 1 :]
        if h and h[-1] == idx:
            self._settings_nav_pos = len(h) - 1
            self._stack.setCurrentIndex(idx)
            self._update_settings_breadcrumb()
            return
        h.append(idx)
        self._settings_nav_pos = len(h) - 1
        self._stack.setCurrentIndex(idx)
        self._update_settings_breadcrumb()

    def _settings_nav_back(self) -> bool:
        if self._tabs is None or self._stack is None:
            return False
        if self._tabs.currentIndex() != 1:
            return False
        p = self._settings_nav_pos
        if p <= 0:
            return False
        p -= 1
        self._settings_nav_pos = p
        self._stack.setCurrentIndex(self._settings_nav_hist[p])
        self._update_settings_breadcrumb()
        QTimer.singleShot(0, self._flush_settings_layout)
        return True

    def _settings_nav_forward(self) -> bool:
        if self._tabs is None or self._stack is None:
            return False
        if self._tabs.currentIndex() != 1:
            return False
        h = self._settings_nav_hist
        p = self._settings_nav_pos
        if p >= len(h) - 1:
            return False
        p += 1
        self._settings_nav_pos = p
        self._stack.setCurrentIndex(h[p])
        self._update_settings_breadcrumb()
        QTimer.singleShot(0, self._flush_settings_layout)
        return True

    def _on_breadcrumb_ensure_settings_tab(self) -> None:
        t = self._tabs
        if t is not None and int(t.currentIndex()) != 1:
            t.setCurrentIndex(1)

    def _on_breadcrumb_goto_hub(self) -> None:
        self._on_breadcrumb_ensure_settings_tab()
        if self._stack is None:
            return
        self._settings_nav_hist = [0]
        self._settings_nav_pos = 0
        self._stack.setCurrentIndex(0)
        self._update_settings_breadcrumb()
        QTimer.singleShot(0, self._flush_settings_layout)

    def _on_breadcrumb_goto_index(self, idx: int) -> None:
        self._on_breadcrumb_ensure_settings_tab()
        st = self._stack
        if st is None:
            return
        ii = int(idx)
        if ii < 0 or ii >= int(st.count()):
            return
        if int(st.currentIndex()) == ii:
            return
        if ii == 0:
            self._on_breadcrumb_goto_hub()
            return
        self._settings_nav_hist = [0, ii]
        self._settings_nav_pos = 1
        st.setCurrentIndex(ii)
        self._update_settings_breadcrumb()
        QTimer.singleShot(0, self._flush_settings_layout)

    def _update_settings_breadcrumb(self) -> None:
        """설정 스택 — 클릭 가능한 `설정` / `설정 > …` 경로."""
        w = getattr(self, "_settings_breadcrumb_wrap", None)
        lay = getattr(self, "_settings_breadcrumb_layout", None)
        st = getattr(self, "_stack", None)
        if w is None or lay is None or st is None:
            return
        idx = int(st.currentIndex())
        _bsig = (
            idx,
            tuple(getattr(self, "_settings_nav_hist", []) or ()),
            int(getattr(self, "_settings_nav_pos", 0)),
        )
        if _bsig == getattr(self, "_last_settings_breadcrumb_sig", None):
            return
        self._last_settings_breadcrumb_sig = _bsig
        while lay.count():
            it = lay.takeAt(0)
            ch = it.widget()
            if ch is not None:
                ch.setParent(None)
                ch.deleteLater()

        if idx <= 0:
            hub_cur = QLabel("설정")
            hub_cur.setObjectName("pipelaBreadcrumbCurrent")
            lay.addWidget(hub_cur, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            lay.addStretch(1)
            return

        b0 = QPushButton("설정")
        b0.setObjectName("pipelaBreadcrumbSeg")
        b0.setFlat(True)
        b0.setCursor(Qt.CursorShape.PointingHandCursor)
        b0.setToolTip("설정 허브로 이동")
        b0.clicked.connect(self._on_breadcrumb_goto_hub)
        lay.addWidget(b0, 0, Qt.AlignmentFlag.AlignLeft)

        for pid, i in self._panel_placeholders.items():
            if int(i) == idx:
                title = _HUB_TITLE_BY_PID.get(pid, pid)
                sep = QLabel("›")
                sep.setObjectName("pipelaBreadcrumbSep")
                lay.addWidget(sep, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                cur = QLabel(title)
                cur.setObjectName("pipelaBreadcrumbCurrent")
                cur.setWordWrap(False)
                lay.addWidget(cur, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                lay.addStretch(1)
                return
        lay.addStretch(1)

    def _widget_is_descendant_of(self, w: QWidget, ancestor: QWidget) -> bool:
        p: QWidget | None = w
        while p is not None:
            if p is ancestor:
                return True
            p = p.parentWidget()
        return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # QApplication 전역 필터 — 타입 정수만 두 번 비교 (~700k/s 이벤트; isinstance 제거)
        et = int(event.type())
        if et == _EV_WHEEL:
            log = getattr(self, "_log", None)
            if log is not None and isinstance(watched, QWidget):
                if watched is log or self._widget_is_descendant_of(watched, log):
                    self._schedule_terminal_scroll_restore_from_user()
            return False
        if et != _EV_MOUSE_BUTTON_PRESS:
            return False
        if self._settings_wrap is None or not isinstance(watched, QWidget):
            return False
        me = event
        if not self._widget_is_descendant_of(watched, self._settings_wrap):
            return False
        if me.button() in (
            Qt.MouseButton.BackButton,
            Qt.MouseButton.XButton1,
        ):
            if self._settings_nav_back():
                return True
        elif me.button() in (
            Qt.MouseButton.ForwardButton,
            Qt.MouseButton.XButton2,
        ):
            if self._settings_nav_forward():
                return True
        return False

    def _flush_settings_layout(self) -> None:
        if self._stack is None:
            return
        w = self._stack.currentWidget()
        if w is not None:
            relayout_scroll_areas_under(w)

    def _open_settings_panel(
        self,
        panel_id: str,
        _title: str,
        *,
        toggle_same_panel_to_terminal: bool = False,
    ) -> None:
        idx = self._panel_placeholders.get(panel_id)
        st = self._stack
        tabs = self._tabs
        # 기능 그리드 우클릭: 이미 해당 패널이면 터미널로 복귀 (허브 버튼 클릭에는 적용 안 함)
        if (
            toggle_same_panel_to_terminal
            and idx is not None
            and st is not None
            and tabs is not None
            and int(tabs.currentIndex()) == 1
            and int(st.currentIndex()) == int(idx)
        ):
            tabs.setCurrentIndex(0)
            return
        if tabs is not None and int(tabs.currentIndex()) != 1:
            tabs.setCurrentIndex(1)
        if idx is not None:
            self._settings_nav_record_open(idx)
            w = self._stack.currentWidget()

            def _nudge_layout() -> None:
                if w is None:
                    return
                relayout_scroll_areas_under(w)
                w.repaint()

            QTimer.singleShot(0, _nudge_layout)
            QTimer.singleShot(40, _nudge_layout)
            QTimer.singleShot(120, _nudge_layout)

    def _close_intro_skip_settings_popup_if_open(self) -> None:
        """클라 페이즈 전환 등 — 런처용 Intro Skip 팝업이 열려 있으면 닫는다."""
        d = getattr(self, "_launcher_intro_skip_dialog", None)
        if d is None:
            return
        try:
            if d.isVisible():
                d.close()
        except Exception:
            pass

    def open_settings_from_launcher_title_strip(self) -> None:
        """런처 페이즈 상단 스트립 설정 — 메인 제어창 없이 Intro Skip 설정 패널(설정 탭과 동일 위젯)만 팝업."""
        if self._start_tray_only:
            return
        prev = getattr(self, "_launcher_intro_skip_dialog", None)
        if prev is not None:
            try:
                if prev.isVisible():
                    prev.raise_()
                    prev.activateWindow()
                    return
            except Exception:
                pass
            self._launcher_intro_skip_dialog = None

        dlg = _IntroSkipPopupDialog(None)
        dlg.setObjectName("pipelaIntroSkipPopup")
        dlg.setWindowTitle("Intro Skip 설정")
        dlg.setModal(False)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dlg.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint,
        )
        _wi = qt_application_icon()
        if not _wi.isNull():
            dlg.setWindowIcon(_wi)
        dlg.setStyleSheet(intro_skip_settings_popup_qss())
        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_IntroSkipPopupDragHeader(dlg), 0)
        body = QWidget()
        body_l = QVBoxLayout(body)
        _mg_h = scale_px_h(12)
        _mg_v = scale_px_v(12)
        body_l.setContentsMargins(_mg_h, _mg_v, _mg_h, _mg_v)
        body_l.setSpacing(scale_px_v(8))
        panel = StartGameSettingsPanel(self._m, dlg)
        body_l.addWidget(panel, 1)
        root.addWidget(body, 1)

        w, h = get_dock_panel_wh(self._m)
        dlg.resize(max(360, int(w)), max(420, min(920, int(h))))

        app = QApplication.instance()
        if app is not None:
            scr = app.primaryScreen()
            if scr is not None:
                ag = scr.availableGeometry()
                fg = dlg.frameGeometry()
                fg.moveCenter(ag.center())
                dlg.move(fg.topLeft())

        def _on_closed() -> None:
            self._launcher_intro_skip_dialog = None
            sp = getattr(self._m, "_qt_title_bar_strip", None)
            if sp is not None:
                try:
                    sp.invalidate_chrome_layout()
                except Exception:
                    pass

        dlg.finished.connect(_on_closed)
        self._launcher_intro_skip_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        try:
            fn = getattr(panel, "apply_scaled_typography", None)
            if callable(fn):
                fn()
        except Exception:
            pass

    def _sync_pipela_qt_control_win_hwnd(self) -> None:
        """해상도/모니터 배율 표시 — 제어창이 놓인 모니터(DPI)를 쓰기 위한 native HWND."""
        m = self._m
        try:
            if self.isVisible():
                m.pipela_qt_control_win_hwnd = int(self.winId())
        except Exception:
            pass

    def _control_poll_interval_ms(self) -> int:
        """제어창 UI 폴링 — 절전 시 완화, 그 외에는 창이 있는 모니터 주사율에 맞춤."""
        m = self._m
        if getattr(m, "_game_client_power_save_active", False):
            return max(200, int(getattr(m, "GAME_CLIENT_POWER_SAVE_WIDGET_MS", 2000)))
        try:
            wid = int(self.winId())
        except Exception:
            wid = 0
        return max(28, int(display_tick_ms_for_window(wid)))

    def _sync_control_poll_interval(self) -> None:
        wanted = self._control_poll_interval_ms()
        if self._poll.interval() != wanted:
            self._poll.setInterval(wanted)

    def _flame_action_caption(self) -> str:
        m = self._m
        fl_txt = (
            f"Flame Trigger  : {m.flame_trigger_press_count} : "
            f"{m.flame_trigger_last_press_interval_sec:.2f}s"
        )
        return action_icon_label_gap() + fl_txt

    def _reload_action_caption(self) -> str:
        """`pipela_qt.cursor_hud` Flame 팝업 `Reload : 개수 (경과)` 와 같은 수치."""
        m = self._m
        r_cnt = int(getattr(m, "flame_trigger_session_reload_count", 0) or 0)
        now = time.time()
        trig_t = float(getattr(m, "flame_trigger_last_reload_trigger_time", 0.0) or 0.0)
        elapsed = (now - trig_t) if trig_t > 0.0 else 0.0
        fmt = getattr(m, "_format_flame_trigger_runtime_hms", None)
        hms = (
            fmt(elapsed)
            if callable(fmt)
            else _format_reload_hud_elapsed_hms(elapsed)
        )
        body = f"Reload : {r_cnt} ({hms})"
        b = self._btns.get("reload")
        if b is not None and not b.icon().isNull():
            return action_icon_label_gap() + body
        return body

    def _hp_refill_action_caption(self) -> str:
        m = self._m
        n = int(getattr(m, "hp_refill_trigger_total", 0) or 0)
        body = f"HP Refill · {n:,}"
        b = self._btns.get("hp")
        if b is not None and not b.icon().isNull():
            return action_icon_label_gap() + body
        return body

    def _resync_action_button_captions(self) -> None:
        gap = action_icon_label_gap()
        for key, base in self._action_btn_label_base.items():
            if base is None:
                continue
            b = self._btns.get(key)
            if b is None:
                continue
            if key == "hp":
                b.setText(self._hp_refill_action_caption())
                continue
            if b.icon().isNull():
                b.setText(base)
            else:
                b.setText(gap + base)

    def _apply_action_toggle_styles(self, m) -> None:
        _rs = T.MAIN_GLASS_BTN_RADIUS
        _design = 10.0 * control_action_label_pt_factor()
        _fpt = spt(_design)
        _tls = letter_spacing_qss()
        _pad_btn = action_button_qss_padding()
        st_on = (
            f"QPushButton {{"
            f" background: {T.MAIN_GLASS_ON_BG}; color: {T.FG}; font-weight: 600; font-size: {_fpt};"
            f" letter-spacing: {_tls}; border: 1px solid {T.MAIN_GLASS_ON_BORDER}; padding: {_pad_btn};"
            f" border-radius: {_rs};"
            f"}}"
            f"QPushButton:hover {{"
            f" background: {T.MAIN_GLASS_ON_HOVER_BG}; border: 1px solid {T.ACCENT}; color: {T.FG};"
            f"}}"
            f"QPushButton:pressed {{"
            f" background: {T.MAIN_GLASS_PRESSED_BG};"
            f" border: 1px solid {T.MAIN_GLASS_PRESSED_BORDER};"
            f"}}"
        )
        st_off = (
            f"QPushButton {{"
            f" background: {T.MAIN_GLASS_OFF_BG}; color: {T.FG_MUTED}; font-weight: 500; font-size: {_fpt};"
            f" letter-spacing: {_tls}; border: 1px solid {T.MAIN_GLASS_OFF_BORDER}; padding: {_pad_btn};"
            f" border-radius: {_rs};"
            f"}}"
            f"QPushButton:hover {{"
            f" background: {T.MAIN_GLASS_OFF_HOVER_BG}; border: 1px solid {T.ACCENT}; color: {T.FG};"
            f"}}"
            f"QPushButton:pressed {{"
            f" background: {T.MAIN_GLASS_PRESSED_BG};"
            f" border: 1px solid {T.MAIN_GLASS_PRESSED_BORDER};"
            f"}}"
        )
        st_emit = (
            f"QPushButton {{"
            f" background: {T.MAIN_GLASS_EMIT_BG}; color: {T.FG}; font-weight: 600; font-size: {_fpt};"
            f" letter-spacing: {_tls}; border: 1px solid {T.MAIN_GLASS_EMIT_BORDER}; padding: {_pad_btn};"
            f" border-radius: {_rs};"
            f"}}"
            f"QPushButton:hover {{"
            f" background: {T.MAIN_GLASS_EMIT_HOVER_BG}; border: 1px solid {T.ACCENT}; color: {T.FG};"
            f"}}"
            f"QPushButton:pressed {{"
            f" background: {T.MAIN_GLASS_PRESSED_BG};"
            f" border: 1px solid {T.MAIN_GLASS_PRESSED_BORDER};"
            f"}}"
        )

        def _tri(enabled: bool, emitting: bool) -> str:
            if not enabled:
                return st_off
            return st_emit if emitting else st_on

        lc_en = bool(m.left_click_feature_enabled)
        self._btns["left"].setStyleSheet(_tri(lc_en, lc_en and bool(m.left_click_active)))

        rh = m.right_hold_feature_enabled
        if rh:
            self._btns["right"].setStyleSheet(st_emit if m.right_hold_active else st_on)
        else:
            self._btns["right"].setStyleSheet(st_off)

        rl_en = bool(m.reload_active)
        self._btns["reload"].setStyleSheet(
            _tri(rl_en, rl_en and bool(getattr(m, "nobullet_detected", False))),
        )

        ft_en = bool(m.flame_trigger_feature_enabled)
        _ft_emit = bool(getattr(m, "flame_trigger_active", False))
        _fb = self._btns["flame"]
        if isinstance(_fb, FlameTriggerGlassButton):
            _fb.set_flame_glass(ft_en, ft_en and _ft_emit, st_off, st_on, st_emit)
        else:
            _fb.setStyleSheet(_tri(ft_en, ft_en and _ft_emit))

        ar_en = bool(m.ammo_restock_active)
        thr_bb = float(getattr(m, "ammo_restock_buybutton_threshold", 0.6))
        thr_iv = float(getattr(m, "ammo_restock_inven_threshold", 0.6))
        thr_bk = float(getattr(m, "ammo_restock_bank_threshold", 0.6))
        sc_bb = float(getattr(m, "ammo_restock_buybutton_score", 0.0))
        sc_iv = float(getattr(m, "ammo_restock_inven_score", 0.0))
        sc_bk = float(getattr(m, "ammo_restock_bank_score", 0.0))
        ammo_emit = ar_en and (
            sc_bb >= thr_bb or sc_iv >= thr_iv or sc_bk >= thr_bk
        )
        self._btns["ammo"].setStyleSheet(_tri(ar_en, ammo_emit))

        cm_en = bool(m.call_merc_active)
        self._btns["merc"].setStyleSheet(
            _tri(cm_en, cm_en and bool(getattr(m, "call_merc_sequence_busy", False))),
        )

        rd_en = bool(m.ride_feature_enabled)
        self._btns["ride"].setStyleSheet(
            _tri(rd_en, rd_en and bool(getattr(m, "capslock_state", False))),
        )

        hp_en = bool(m.hp_refill_feature_enabled)
        hp_thr = float(getattr(m, "hp_refill_threshold", 0.6))
        hp_sc = float(getattr(m, "hp_refill_detection_score", 0.0))
        self._btns["hp"].setStyleSheet(_tri(hp_en, hp_en and hp_sc >= hp_thr))

        kc_en = bool(m.kill_counter_enabled)
        kc_ph = getattr(m, "kill_counter_last_poll_phase", None)
        kc_emit = kc_en and kc_ph == "ok"
        self._btns["kc"].setStyleSheet(_tri(kc_en, kc_emit))

    def _sync_call_merc_cooldown_gauge(self, m) -> None:
        b = self._btns.get("merc")
        if b is None or not hasattr(b, "set_cooldown_fill"):
            return
        try:
            now = time.monotonic()
            until = float(getattr(m, "call_merc_arm_until_mono", 0.0) or 0.0)
            cd = float(getattr(m, "CALL_MERC_ARM_COOLDOWN_SEC", 10.0) or 10.0)
            if cd <= 0.01 or until <= 0.0 or now >= until:
                b.set_cooldown_fill(0.0)
                return
            b.set_cooldown_fill((until - now) / cd)
        except Exception:
            pass

    def _sync_reload_cooldown_gauge(self, m) -> None:
        b = self._btns.get("reload")
        if b is None or not hasattr(b, "set_cooldown_fill"):
            return
        try:
            if not bool(getattr(m, "reload_active", False)):
                b.set_cooldown_fill(0.0)
                return
            now = time.monotonic()
            until = float(getattr(m, "reload_nobullet_arm_until_mono", 0.0) or 0.0)
            cd = float(
                getattr(m, "RELOAD_NOBULLET_REARM_COOLDOWN_SEC", 10.0) or 10.0,
            )
            if cd <= 0.01 or until <= 0.0 or now >= until:
                b.set_cooldown_fill(0.0)
                return
            b.set_cooldown_fill((until - now) / cd)
        except Exception:
            pass

    def _tick_apply_game_window_screen_center(self) -> None:
        """트레이 전용 등에서 도킹 대신 게임 창을 작업 영역 중앙에 맞춤 — `_refresh` 밖에서 저빈도 호출."""
        m = self._m
        if not getattr(m, "running", True):
            return
        try:
            _agc = getattr(m, "apply_game_window_screen_center", None)
            if callable(_agc):
                _agc()
        except Exception:
            pass

    def _refresh(self) -> None:
        m = self._m
        _th0 = None
        _luh0 = None
        with ctd_span("control._refresh.uiphase_sync"):
            try:
                _th0 = m.refresh_target_hwnd_if_needed()
                _luh0 = m.refresh_smart_updater_hwnd_if_needed()
                _ph = get_ui_dock_phase_from_session(m, _th0, _luh0)
                if _ph == UI_DOCK_PHASE_CLIENT:
                    self._close_intro_skip_settings_popup_if_open()
                _prev_ui_ph = getattr(self, "_ui_dock_phase_tracked", None)
                if _prev_ui_ph != _ph:
                    try:
                        ctd_log(
                            f"DOCK_PHASE_CHANGE {_prev_ui_ph!r} -> {_ph!r} "
                            f"th_hwnd={_th0!r} launcher_hwnd={_luh0!r} "
                            f"visible={bool(self.isVisible())} minimized={bool(self.isMinimized())}",
                        )
                    except Exception:
                        pass
                    self._ui_dock_phase_tracked = _ph
                    if (
                        _prev_ui_ph == UI_DOCK_PHASE_CLIENT
                        and _ph == UI_DOCK_PHASE_LAUNCHER
                    ):
                        self._suppress_next_client_dock_burst = True
                        self._stop_client_phase_dock_burst()
                    elif (
                        _prev_ui_ph == UI_DOCK_PHASE_LAUNCHER
                        and _ph == UI_DOCK_PHASE_CLIENT
                    ):
                        _skip_burst = self._suppress_next_client_dock_burst
                        self._suppress_next_client_dock_burst = False
                        if not _skip_burst:
                            self._start_client_phase_dock_burst()
                    else:
                        self._suppress_next_client_dock_burst = False
                        if _ph != UI_DOCK_PHASE_CLIENT:
                            self._stop_client_phase_dock_burst()
                    if (
                        _ph == UI_DOCK_PHASE_STANDBY
                        and _prev_ui_ph is not None
                        and _prev_ui_ph != UI_DOCK_PHASE_STANDBY
                        and not pipela_dev_ui_standby_chrome(m)
                    ):
                        if not self._control_chrome_user_dismissed:
                            try:
                                kc = self._kc_float
                                if kc is not None and kc.isVisible():
                                    kc.hide()
                            except Exception:
                                pass
                            try:
                                if self.isVisible() or self.isMinimized():
                                    self.hide()
                            except Exception:
                                pass
                        try:
                            self._last_standby_sig = None
                        except Exception:
                            pass
                    # 폭·도킹 타이머보다 먼저 메인 표시(히든 상태 dock 스킵·스트립 기하 깨짐 방지).
                    self._sync_launcher_phase_docked_chrome()
                    try:
                        sp = getattr(m, "_qt_title_bar_strip", None)
                        if sp is not None:
                            sp.invalidate_chrome_layout()
                    except Exception:
                        pass
                    self._resync_dock_w_for_ui_phase()
                else:
                    self._sync_launcher_phase_docked_chrome()
            except Exception as e:
                ctd_log_exc("_refresh.uiphase_sync", e)
                try:
                    self._sync_launcher_phase_docked_chrome()
                except Exception as e2:
                    ctd_log_exc("_refresh.uiphase_sync.fallback_launcher_sync", e2)
        self._sync_control_poll_interval()
        self._sync_pipela_qt_control_win_hwnd()
        fl_display = self._flame_action_caption()
        if self._btns["flame"].text() != fl_display:
            self._btns["flame"].setText(fl_display)
        hp_display = self._hp_refill_action_caption()
        if self._btns["hp"].text() != hp_display:
            self._btns["hp"].setText(hp_display)
        rl_display = self._reload_action_caption()
        if self._btns["reload"].text() != rl_display:
            self._btns["reload"].setText(rl_display)

        dock_force = False
        with ctd_span("control._refresh.dock_track"):
            try:
                th = _th0 if _th0 is not None else m.refresh_target_hwnd_if_needed()
                g_iconic = bool(th and m.is_window_minimized(th))
                prev_ic = self._dock_track_game_iconic
                if prev_ic is not None and g_iconic != prev_ic:
                    dock_force = True
                    sp = getattr(m, "_qt_title_bar_strip", None)
                    if sp is not None:
                        sp.invalidate_chrome_layout()
                if (
                    sys.platform == "win32"
                    and not self._start_tray_only
                    and prev_ic is not None
                    and g_iconic
                    and not prev_ic
                    and self.isVisible()
                    and not self.isMinimized()
                ):
                    # 게임 타이틀 등 «외부» 최소화 — 스트립 버튼은 이미 제어창을 먼저 최소화함
                    try:
                        import win32gui as _wg

                        mw = int(self.winId())
                        if _wg.IsWindow(mw):
                            win32_window_minimize(mw)
                        else:
                            self.showMinimized()
                    except Exception:
                        try:
                            self.showMinimized()
                        except Exception:
                            pass
                game_just_restored = bool(
                    prev_ic is not None
                    and prev_ic
                    and not g_iconic,
                )
                self._dock_track_game_iconic = g_iconic
                if (
                    game_just_restored
                    and sys.platform == "win32"
                    and not self._start_tray_only
                ):
                    try:
                        from pipela_qt.dock_chrome_restore import (
                            restore_pipela_docked_chrome_if_needed,
                        )

                        restore_pipela_docked_chrome_if_needed(
                            m, game_just_restored=True,
                        )
                    except Exception:
                        pass

                anchor = resolve_dock_anchor_hwnd(m)
                if anchor != self._dock_track_anchor:
                    dock_force = True
                self._dock_track_anchor = anchor

                rs = _norm_outer_rect(
                    m.get_window_outer_rect_screen(anchor) if anchor else None,
                )
                if rs != self._dock_track_outer:
                    dock_force = True
                self._dock_track_outer = rs

                old_cr = getattr(self, "_dock_track_client", None)
                crs = None
                if anchor:
                    try:
                        crs = _norm_outer_rect(m.get_window_rect(int(anchor)))
                    except Exception:
                        crs = None
                    if not crs or crs[2] <= crs[0] or crs[3] <= crs[1]:
                        crs = None
                if crs != old_cr:
                    self._dock_track_client = crs
                    dock_force = True
                    if crs is not None or old_cr is not None:
                        try:
                            sp = getattr(m, "_qt_title_bar_strip", None)
                            if sp is not None:
                                sp.invalidate_chrome_layout()
                        except Exception:
                            pass
                        if old_cr is not None and crs is not None:
                            self._schedule_client_resolution_dock_retries()
                            self._maybe_extend_client_phase_dock_burst()
                        elif old_cr is not None and crs is None:
                            self._schedule_client_resolution_dock_retries()
            except Exception as e:
                ctd_log_exc("_refresh.dock_track", e)

        self._sync_call_merc_cooldown_gauge(m)
        self._sync_reload_cooldown_gauge(m)

        try:
            ctd_log(
                f"_refresh dock_ready force={dock_force} anchor="
                f"{getattr(self, '_dock_track_anchor', None)!r} "
                f"outer={getattr(self, '_dock_track_outer', None)!r} "
                f"client={getattr(self, '_dock_track_client', None)!r}",
            )
        except Exception:
            pass

        style_state = (
            m.left_click_feature_enabled,
            m.left_click_active,
            m.right_hold_feature_enabled,
            m.right_hold_active,
            m.reload_active,
            getattr(m, "nobullet_detected", False),
            m.flame_trigger_feature_enabled,
            getattr(m, "flame_trigger_active", False),
            m.ammo_restock_active,
            float(getattr(m, "ammo_restock_buybutton_score", 0.0)),
            float(getattr(m, "ammo_restock_inven_score", 0.0)),
            float(getattr(m, "ammo_restock_bank_score", 0.0)),
            m.call_merc_active,
            getattr(m, "call_merc_sequence_busy", False),
            m.ride_feature_enabled,
            getattr(m, "capslock_state", False),
            m.hp_refill_feature_enabled,
            float(getattr(m, "hp_refill_detection_score", 0.0)),
            m.kill_counter_enabled,
            getattr(m, "kill_counter_last_poll_phase", None),
            is_start_game_launcher_template1_effective_on(m, None),
        )
        if style_state == self._last_btn_style_state:
            # 킬을 먼저: 제어창 `show`/`_ensure` 뒤에 같은 틱에서 `_dock` 이 돌게 함
            # (이전: 도킹이 `isHidden()` 이면 스킵 → 킬만 뜨는 프레임·스트립 좌표 상이)
            self._sync_kill_counter_window()
            self._dock_to_anchor(force=dock_force)
            return
        self._last_btn_style_state = style_state

        self._apply_action_toggle_styles(m)
        self._sync_kill_counter_window()
        self._dock_to_anchor(force=dock_force)

    def _ensure_kc_float(self) -> PipelaQtKillCounterWindow:
        if self._kc_float is None:
            w = PipelaQtKillCounterWindow(self._m, parent=None)
            w.userDismissed.connect(self._on_kc_float_user_dismissed)
            self._kc_float = w
        return self._kc_float

    def _on_kc_float_user_dismissed(self) -> None:
        self._kc_float_user_hidden = True

    def show(self) -> None:
        """트레이/메뉴로 다시 켤 때 — 사용자는 도킹 크롬을 다시 쓰겠다는 뜻으로 본다."""
        self._control_chrome_user_dismissed = False
        super().show()

    def _ensure_control_visible_with_kill_chrome(self) -> None:
        """게임+킬 패널이 뜰 때 제어창이 숨김/최소화면 같이 복원(×로 끈 경우는 제외)."""
        if self._control_chrome_user_dismissed:
            return
        if not (self.isHidden() or self.isMinimized()):
            return
        try:
            if self.isMinimized():
                self.showNormal()
            if not self.isVisible():
                super().show()
        except Exception:
            return
        try:
            self.raise_()
        except Exception:
            pass
        self._sync_pipela_qt_control_win_hwnd()
        m = self._m
        sp = getattr(m, "_qt_title_bar_strip", None)
        if sp is not None:
            sp.invalidate_chrome_layout()
        QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
        QTimer.singleShot(120, lambda: self._dock_to_anchor(force=True))

    def _sync_kill_counter_window(self) -> None:
        """킬 카운터 floater — 이터널시티 창 오른쪽 (기능 ON·게임 연결·사용자가 ×로 숨기지 않은 경우)."""
        m = self._m
        if pipela_dev_ui_standby_chrome(m):
            if not getattr(m, "running", True):
                return
            if self._kc_float_user_hidden:
                return
            self._control_chrome_user_dismissed = False
            self._ensure_control_visible_with_kill_chrome()
            w = self._ensure_kc_float()
            if not w.isVisible():
                w.show()
            w.dock_to_standby_dev_pair()
            return
        th_chk: int | None = None
        try:
            th_chk = m.refresh_target_hwnd_if_needed()
            luh_chk = m.refresh_smart_updater_hwnd_if_needed()
            if get_ui_dock_phase_from_session(m, th_chk, luh_chk) == UI_DOCK_PHASE_LAUNCHER:
                if self._kc_float is not None and self._kc_float.isVisible():
                    self._kc_float.hide()
                return
        except Exception:
            pass
        if not getattr(m, "running", True):
            return
        if not m.kill_counter_enabled:
            if self._kc_float is not None and self._kc_float.isVisible():
                self._kc_float.hide()
            return
        if self._kc_float_user_hidden:
            return
        th = th_chk if th_chk is not None else m.refresh_target_hwnd_if_needed()
        if not th or m.is_window_minimized(th):
            if self._kc_float is not None and self._kc_float.isVisible():
                self._kc_float.hide()
            return
        # 킬 floater 를 띄우는 경로에서만: 메인×로 닫은 플래그가 남으면 제어만 숨고 킬만 뜨는 현상
        # → 킬 창 `show`/`dock` 과 같이 제어창도 다시 켠다(트레이 «제어창 표시» 와 동일 의도).
        self._control_chrome_user_dismissed = False
        self._ensure_control_visible_with_kill_chrome()
        w = self._ensure_kc_float()
        if not w.isVisible():
            w.show()
        w.dock_to_right_of_target_game()
        try:
            self._sync_pipela_qt_control_win_hwnd()
        except Exception:
            pass
        sp = getattr(m, "_qt_title_bar_strip", None)
        if sp is not None:
            try:
                sp.invalidate_chrome_layout()
            except Exception:
                pass
        QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))

    def _toggle_left(self) -> None:
        m = self._m
        m.left_click_feature_enabled = not m.left_click_feature_enabled
        if hasattr(m, "_state_set"):
            m._state_set("left_click_feature_enabled", bool(m.left_click_feature_enabled))
        if not m.left_click_feature_enabled:
            if hasattr(m, "_state_set"):
                m._state_set("left_click_active", False)
                m._state_set("left_pressed", False)
            else:
                m.left_click_active = False
            m.user_left_pending = False
        m.schedule_save_config()
        print(f"[LeftClick] {'ON' if m.left_click_feature_enabled else 'OFF'}")

    def _toggle_right(self) -> None:
        m = self._m
        m.right_hold_feature_enabled = not m.right_hold_feature_enabled
        if not m.right_hold_feature_enabled:
            m.right_hold_active = False
            m.mouse_right_up()
        m.schedule_save_config()
        print(f"[RightHold] {'ON' if m.right_hold_feature_enabled else 'OFF'}")

    def _toggle_reload(self) -> None:
        m = self._m
        next_reload = not bool(m.reload_active)
        if hasattr(m, "_state_set"):
            m._state_set("reload_active", next_reload)
            if not next_reload:
                m._state_set("reload_nobullet_arm_until_mono", 0.0)
        else:
            m.reload_active = next_reload
            if not next_reload:
                m.reload_nobullet_arm_until_mono = 0.0
        m._loop_print(f"[Reload] {'ON' if next_reload else 'OFF'}")
        m.schedule_save_config()

    def _toggle_flame(self) -> None:
        m = self._m
        m.flame_trigger_feature_enabled = not m.flame_trigger_feature_enabled
        if not m.flame_trigger_feature_enabled:
            if hasattr(m, "_state_set"):
                m._state_set("flame_trigger_active", False)
            else:
                m.flame_trigger_active = False
        m.schedule_save_config()
        print(f"[Flame Trigger] {'ON' if m.flame_trigger_feature_enabled else 'OFF'}")

    def _toggle_ammo(self) -> None:
        m = self._m
        next_ammo = not bool(m.ammo_restock_active)
        if hasattr(m, "_state_set"):
            m._state_set("ammo_restock_active", next_ammo)
        else:
            m.ammo_restock_active = next_ammo
        m._loop_print(f"[Ammo Restock] {'ON' if next_ammo else 'OFF'}")
        m.schedule_save_config()

    def _toggle_merc(self) -> None:
        m = self._m
        m.call_merc_active = not m.call_merc_active
        m.schedule_save_config()
        m._loop_print(f"{m._CALL_MERC_LOG_PREFIX} {'ON' if m.call_merc_active else 'OFF'}")

    def _toggle_ride(self) -> None:
        m = self._m
        m.ride_feature_enabled = not m.ride_feature_enabled
        m.schedule_save_config()
        print(f"[Ride] {'ON' if m.ride_feature_enabled else 'OFF'}")

    def _toggle_hp(self) -> None:
        m = self._m
        m.hp_refill_feature_enabled = not m.hp_refill_feature_enabled
        m.schedule_save_config()
        print(f"[HP Refill] {'ON' if m.hp_refill_feature_enabled else 'OFF'}")

    def _toggle_kc(self) -> None:
        m = self._m
        was_on = m.kill_counter_enabled
        m.kill_counter_enabled = not m.kill_counter_enabled
        if not m.kill_counter_enabled and was_on:
            m._kill_counter_reset_session_kills()
            m.kill_counter_last_poll_phase = None
            m.kill_counter_last_poll_detail = None
            self._kc_float_user_hidden = False
            if self._kc_float is not None:
                self._kc_float.hide()
        if m.kill_counter_enabled and not was_on:
            self._kc_float_user_hidden = False
        m.schedule_save_config()
        print(f"[Kill Counter] {'켜짐' if m.kill_counter_enabled else '꺼짐'}", flush=True)
        QTimer.singleShot(0, self._sync_kill_counter_window)

    def closeEvent(self, e) -> None:
        e.ignore()
        self._control_chrome_user_dismissed = True
        try:
            self.hide()
        except Exception:
            pass
