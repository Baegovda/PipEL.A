"""Qt 제어창 — 토글·해상도·터미널·설정 스택."""

from __future__ import annotations

import html
import os
import sys
import threading
import time
from collections import deque

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPalette,
    QResizeEvent,
    QShowEvent,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProxyStyle,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyleOptionTab,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pipela_core.console_log_constants import (
    CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    CONSOLE_LOG_TIME_MODE_RELATIVE,
)
from pipela_core.console_log_prefix import (
    format_console_log_prefix,
    format_terminal_log_stored_prefix,
)
from pipela_core.display_timing import display_tick_ms_for_window
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
    dock_outer_rect_touch_client_left,
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
    scale_px,
    scaled_design_pt,
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
from pipela_qt.dpi import get_dock_panel_wh, win32_dpi_scale_for_hwnd
from pipela_qt.main_window import HUB_ENTRIES

_HUB_TITLE_BY_PID: dict[str, str] = dict(HUB_ENTRIES)
from pipela_qt.qt_dock_anchor import resolve_dock_anchor_hwnd
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
from pipela_qt.kill_counter_window import PipelaQtKillCounterWindow
from pipela_qt.resizable_text_widgets import ResizableTerminalLog
from pipela_qt.terminal_log_html import format_terminal_log_line_html

# 앱 전역 eventFilter 핫패스 — 매 이벤트마다 `QEvent.Type` 조회를 한 번으로 고정
_EV_MOUSE_BUTTON_PRESS = QEvent.Type.MouseButtonPress


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

    def _decorate_line_body_html(self, body: str, line_mono: float) -> str:
        try:
            tp = format_console_log_prefix(self._m, line_mono=line_mono)
        except Exception:
            return html.escape(body, quote=False)
        raw = body.strip("\r\n")
        if not raw.strip():
            return (
                f'<span style="color:{T.TERMINAL_FG}; opacity:0.88;">'
                f"{html.escape(tp)}</span>"
            )
        ipx = max(12, min(22, scale_px(14)))
        return format_terminal_log_line_html(tp, raw, icon_px=ipx)

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
                html_chunks.append(self._decorate_line_body_html(line, _lm) + "<br/>")
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
            self.text.emit(self._decorate_line_body_html(pending, _lm))
        try:
            self._orig.flush()
        except Exception:
            pass


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


class _IntroSkipPopupDialog(QDialog):
    """OS 타이틀 없음 — Esc 로 닫기."""

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
        hl.setContentsMargins(scale_px(10), scale_px(6), scale_px(6), scale_px(6))
        hl.setSpacing(scale_px(8))
        ttl = QLabel("Intro Skip 설정")
        ttl.setObjectName("pipelaIntroSkipPopupTitle")
        hl.addWidget(ttl, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch(1)
        btn = QPushButton()
        btn.setObjectName("pipelaIntroSkipPopupClose")
        btn.setFlat(True)
        st = dialog.style()
        btn.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        iz = max(10, min(22, scale_px(14)))
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


class _ClusterTabLabelStyle(QProxyStyle):
    """탭이 넓을 때 기본 스타일이 아이콘·텍스트를 양끝으로 벌리는 것을 막고, 기능 버튼처럼 붙여서 가운데 배치."""

    def __init__(self, base: QStyle, bar: QTabBar) -> None:
        super().__init__(base)
        self._bar = bar

    def drawControl(
        self,
        element: QStyle.ControlElement,
        opt,
        p: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        if (
            element != QStyle.ControlElement.CE_TabBarTabLabel
            or widget is not self._bar
            or not isinstance(opt, QStyleOptionTab)
        ):
            super().drawControl(element, opt, p, widget)
            return
        tab: QStyleOptionTab = opt
        if tab.icon.isNull():
            super().drawControl(element, opt, p, widget)
            return

        rect = QRect(tab.rect)
        p.save()

        icon_sz = tab.iconSize
        if icon_sz.width() <= 0 or icon_sz.height() <= 0:
            _pm = QStyle.PixelMetric.PM_SmallIconSize
            _s = max(16, self.pixelMetric(_pm, tab, widget))
            icon_sz = QSize(_s, _s)
        en = bool(tab.state & QStyle.StateFlag.State_Enabled)
        icon_mode = QIcon.Mode.Normal if en else QIcon.Mode.Disabled
        icon_state = QIcon.State.On if (tab.state & QStyle.StateFlag.State_Selected) else QIcon.State.Off
        # QSS·QStyleSheetStyle는 CE_TabBarTabLabel에 넘기는 `opt.rect`가
        # `QTabBar.tabRect`와 달리 잘려 아이콘만 한쪽(대개 왼쪽)에 남는 것처럼 보일 수 있음.
        # 실제 셀은 tabRect 기준 + 아이콘은 setIconSize 슬롯에 맞게 그려 클러스터 폭이 흔들리지 않게 함.
        _ix = int(getattr(tab, "tabIndex", -1))
        _from_cell = False
        try:
            if 0 <= _ix < int(self._bar.count()):
                r_cell = self._bar.tabRect(_ix)
                if r_cell.isValid() and r_cell.width() > 0 and r_cell.height() > 0:
                    rect = r_cell
                    _from_cell = True
        except Exception:
            pass
        if not _from_cell:
            try:
                c = tab.rect.center()
                for j in range(int(self._bar.count())):
                    r2 = self._bar.tabRect(j)
                    if r2.isValid() and r2.contains(c):
                        rect = r2
                        break
            except Exception:
                pass

        pm = tab.icon.pixmap(icon_sz, icon_mode, icon_state)

        gap = ctc.main_tabs_icon_label_gap_px()
        _gap = int(gap)

        text = tab.text
        try:
            _font = QFont(tab.font)
            if _font.pointSizeF() == 0 and _font.pixelSize() == 0:
                _font = self._bar.font()
        except Exception:
            _font = self._bar.font()
        p.setFont(_font)
        fm = p.fontMetrics()
        tw = int(fm.horizontalAdvance(text))
        if tw < 0:
            tw = 0

        icon_w = max(1, int(icon_sz.width()))
        icon_h = max(1, int(icon_sz.height()))
        cluster = icon_w + _gap + tw
        _left = int(rect.left())
        _w = int(rect.width())
        x0 = _left + max(0, (_w - cluster) // 2)
        y_c = int(rect.center().y())
        p.drawPixmap(
            int(x0),
            y_c - icon_h // 2,
            int(icon_w),
            int(icon_h),
            pm,
        )

        tr = QRect(
            int(x0 + icon_w + _gap),
            int(rect.top()),
            tw,
            int(rect.height()),
        )
        tf = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if tw > 0:
            self.drawItemText(
                p,
                tr,
                tf,
                tab.palette,
                en,
                text,
                QPalette.ColorRole.WindowText,
            )
        p.restore()


class _PairedControlTabBar(QTabBar):
    """터미널·설정 두 탭 — 가로 폭에 맞춘 **균등(50/50)** 세그먼트 + 고정 간격."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
        _th = int(ctc.main_tabs_min_height_px()) + int(scale_px(6))
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
        self._dock_rect_miss_count: int = 0
        self._typography_flush_scheduled = False
        self._last_typography_layout_w: int | None = None
        self._last_docked_w_log: int | None = None
        self._tabs: QTabWidget | None = None
        self._tab_area: QWidget | None = None
        self._actions_tabs_sep: QWidget | None = None
        self._settings_wrap: QWidget | None = None
        self._terminal_log_memory: deque[tuple[float, float, str]] = deque()
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
        self._last_typography_layout_w = int(self._dock_w)
        self.resize(self._dock_w, _dh)
        self.setFixedWidth(self._dock_w)
        set_typography_layout_width_px(self._dock_w)
        self.setMenuBar(None)
        self.setStyleSheet(control_frameless_window_qss())

        root = QWidget()
        root.setObjectName("pipelaRoot")
        self.setCentralWidget(root)
        out = QVBoxLayout(root)
        out.setContentsMargins(0, 0, 0, 0)
        out.setSpacing(scale_px(0))

        cw = QWidget()
        cw.setObjectName("pipelaBody")
        out.addWidget(cw, 1)
        main_l = QVBoxLayout(cw)
        _ml, _mt, _mr, _mb = main_shell_margins_lr_tb()
        main_l.setContentsMargins(_ml, _mt, _mr, _mb)
        main_l.setSpacing(shell_hub_inner_gutter_px())

        btn_grid = QGridLayout()
        self._btn_grid = btn_grid
        btn_grid.setSpacing(scale_px(8))
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
            b = QPushButton()
            b.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
            b.setMinimumHeight(scale_px(30))
            self._action_btn_label_base[key] = None if key == "flame" else label
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
                    lambda _p, panel_id=pid: self._open_settings_panel(panel_id, ""),
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
        _ag_l.setContentsMargins(0, 0, 0, 0)
        _ag_l.setSpacing(0)
        _ag_l.addLayout(btn_grid)
        main_l.addWidget(self._action_btn_panel, 0)

        sep_wrap = QWidget()
        sep_wrap.setObjectName("pipelaActionsTabsSep")
        sep_l = QVBoxLayout(sep_wrap)
        _sep_vm = scale_px(12)
        sep_l.setContentsMargins(0, _sep_vm, 0, _sep_vm)
        sep_l.setSpacing(0)
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setFixedHeight(max(1, scale_px(1)))
        sep_line.setStyleSheet(
            f"background: {T.DIVIDER}; color: {T.DIVIDER}; border: none; "
            f"min-height: 1px; max-height: 1px;",
        )
        sep_l.addWidget(sep_line)
        self._actions_tabs_sep = sep_wrap
        main_l.addWidget(sep_wrap)

        tabs = QTabWidget()
        tabs.setObjectName("pipelaMainTabs")
        tabs.setDocumentMode(True)
        tabs.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tabs.setTabBar(_PairedControlTabBar(tabs))
        _main_tabs_bar = tabs.tabBar()
        _main_tabs_bar.setUsesScrollButtons(False)
        self._tabs = tabs
        log = ResizableTerminalLog()
        log.setObjectName("pipelaTerminalLog")
        log.setReadOnly(True)
        log.setAcceptRichText(True)
        self._log = log

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
        _bread_l.setSpacing(0)
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
        iv = QGridLayout(inner)
        self._settings_hub_iv = iv
        _hub_gap = scale_px(8)
        iv.setHorizontalSpacing(_hub_gap)
        iv.setVerticalSpacing(_hub_gap)
        iv.setColumnStretch(0, 1)
        iv.setColumnStretch(1, 1)
        self._panel_placeholders: dict[str, int] = {}
        self._settings_hub_style_buttons: list[QPushButton] = []
        st_hub = settings_hub_entry_button_qss()
        for i, (pid, title) in enumerate(HUB_ENTRIES):
            hb = QPushButton(title)
            hb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hb.setCursor(Qt.CursorShape.PointingHandCursor)
            hb.clicked.connect(
                lambda _checked=False, p=pid, t=title: self._open_settings_panel(p, t),
            )
            hb.setStyleSheet(st_hub)
            self._settings_hub_style_buttons.append(hb)
            iv.addWidget(hb, i // 2, i % 2)
        iv.setRowStretch((len(HUB_ENTRIES) + 1) // 2, 1)
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
        main_l.addWidget(tab_area, 1)
        tabs.currentChanged.connect(self._on_main_tab_changed)
        self._apply_main_tabs_cluster_label_style()
        self._terminal_rel_timer = QTimer(self)
        self._terminal_rel_timer.setInterval(1000)
        self._terminal_rel_timer.timeout.connect(self._on_terminal_relative_tick)
        self._sync_terminal_relative_timer()

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
        self._typography_debounce = QTimer(self)
        self._typography_debounce.setSingleShot(True)
        self._typography_debounce.setInterval(95)
        self._typography_debounce.timeout.connect(self._flush_coalesced_typography)
        self._last_settings_breadcrumb_sig: object | None = None
        self._last_hub_entry_qss: str | None = None
        self._sync_action_button_icon_sizes()
        self._apply_shell_layout_metrics()
        self._sync_terminal_settings_tab_chrome()
        # 종료: 시스템 트레이 → «종료» (시스템 메뉴바 없음, 프레임리스)

        if start_tray_only:
            self.hide()
        else:
            self._control_chrome_user_dismissed = False
            self.show()
            self._sync_launcher_phase_docked_chrome()
            QTimer.singleShot(0, self._bring_qt_control_to_front)
        QTimer.singleShot(0, self._pin_action_button_panel_height)
        QTimer.singleShot(100, self._pin_action_button_panel_height)

    def _pin_action_button_panel_height(self) -> None:
        """탭 콘텐츠마다 `QTabWidget` 최소 높이가 달라질 때 상단 기능 그리드가 눌리는 것을 막는다."""
        p = getattr(self, "_action_btn_panel", None)
        if p is None:
            return
        lay = p.layout()
        if lay is None:
            return
        try:
            p.setMaximumHeight(16777215)
            p.setMinimumHeight(0)
            p.updateGeometry()
            lay.update()
            lay.activate()
            h = max(
                int(lay.totalMinimumSize().height()),
                int(lay.minimumSize().height()),
                int(lay.sizeHint().height()),
                int(p.sizeHint().height()),
            )
            if h < 8:
                return
            p.setFixedHeight(h)
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
                        scale_px(10),
                        0,
                        scale_px(14),
                    )
            ta = getattr(self, "_tab_area", None)
            if ta is not None:
                tal = ta.layout()
                if isinstance(tal, QVBoxLayout):
                    tal.setContentsMargins(0, 0, 0, 0)
            bg = getattr(self, "_btn_grid", None)
            if bg is not None:
                bg.setSpacing(scale_px(8))
            sw = getattr(self, "_settings_wrap", None)
            if sw is not None:
                sl = sw.layout()
                if isinstance(sl, QVBoxLayout):
                    sl.setSpacing(shell_hub_inner_gutter_px())
            iv = getattr(self, "_settings_hub_iv", None)
            if iv is not None:
                _hg = scale_px(8)
                if isinstance(iv, QGridLayout):
                    iv.setHorizontalSpacing(_hg)
                    iv.setVerticalSpacing(_hg)
                else:
                    iv.setSpacing(_hg)
        except Exception:
            pass

    def _sync_typography_width(self) -> None:
        try:
            w = int(self.width())
        except Exception:
            return
        prev = self._last_typography_layout_w
        if prev is not None and abs(w - prev) < 2:
            return
        self._last_typography_layout_w = w
        try:
            set_typography_layout_width_px(w)
        except Exception:
            return
        self._last_btn_style_state = None
        self.apply_scaled_typography()

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
        self._apply_action_toggle_styles(self._m)
        self._sync_terminal_settings_tab_chrome()
        self._sync_terminal_relative_timer()
        QTimer.singleShot(0, self._pin_action_button_panel_height)

    def _apply_main_tabs_cluster_label_style(self) -> None:
        tabs = getattr(self, "_tabs", None)
        if tabs is None:
            return
        tb = tabs.tabBar()
        tb.setStyle(None)
        base = tb.style()
        if base is None:
            _app = QApplication.instance()
            base = _app.style() if _app is not None else None
        if base is not None:
            tb.setStyle(_ClusterTabLabelStyle(base, tb))

    def _sync_terminal_settings_tab_chrome(self) -> None:
        """터미널 로그·탭바·설정 탭 — QSS와 동일 폭·루트 pt 스케일을 QFont 등으로 맞춤."""
        try:
            log = getattr(self, "_log", None)
            if log is not None:
                lf = app_default_qfont(11)
                lf.setPointSizeF(max(7.5, min(22.0, scaled_design_pt(9.25))))
                log.setFont(lf)
                log.document().setDocumentMargin(float(scale_px(4)))
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

    def _sync_terminal_relative_timer(self) -> None:
        t = getattr(self, "_terminal_rel_timer", None)
        if t is None:
            return
        if (
            getattr(
                self._m,
                "console_log_time_display_mode",
                CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            )
            == CONSOLE_LOG_TIME_MODE_RELATIVE
        ):
            t.start()
        else:
            t.stop()

    def sync_console_time_display_chrome(self) -> None:
        """`console_log_time_display_mode` 등 변경 후 — 상대 1s 타이머·뷰 갱신(레지/설정 패널에서 호출)."""
        self._sync_terminal_relative_timer()
        self.rebuild_terminal_log_display_for_time_mode()

    def _on_terminal_relative_tick(self) -> None:
        if (
            getattr(
                self._m,
                "console_log_time_display_mode",
                CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            )
            != CONSOLE_LOG_TIME_MODE_RELATIVE
        ):
            return
        tabs = self._tabs
        if tabs is not None and tabs.currentIndex() != 0:
            return
        self.rebuild_terminal_log_display_for_time_mode()

    def rebuild_terminal_log_display_for_time_mode(self) -> None:
        """절대/상대 전환·1초 틱 — 저장 시각·줄 monotonic으로 기존 줄 전부 다시 렌더."""
        _ln = len(self._terminal_log_memory)
        try:
            log = self._log
            m = self._m
            sb = log.verticalScrollBar()
            at_bottom = sb.maximum() <= 0 or sb.value() >= sb.maximum() - 3
            saved_v = sb.value()
            ipx = max(12, min(22, scale_px(14)))
            parts: list[str] = []
            for wall_t, line_mono, raw in self._terminal_log_memory:
                tp = format_terminal_log_stored_prefix(
                    m, wall_time=wall_t, line_monotonic=line_mono,
                )
                parts.append(format_terminal_log_line_html(tp, raw, icon_px=ipx) + "<br/>")
            log.clear()
            if parts:
                log.setHtml("".join(parts))
            if at_bottom:
                c = log.textCursor()
                c.movePosition(QTextCursor.MoveOperation.End)
                log.setTextCursor(c)
            else:
                new_max = sb.maximum()
                sb.setValue(min(saved_v, new_max))
        except Exception:
            pass

    def _append_terminal_log_html(self, fragment: str) -> None:
        if not fragment:
            return
        try:
            log = self._log
            c = log.textCursor()
            c.movePosition(QTextCursor.MoveOperation.End)
            c.insertHtml(fragment)
            log.setTextCursor(c)
            self._trim_terminal_log_blocks()
        except Exception:
            pass

    def _trim_terminal_log_blocks(self) -> None:
        try:
            doc = self._log.document()
            max_blocks = 5000
            guard = 0
            mem = self._terminal_log_memory
            while doc.blockCount() > max_blocks and guard < max_blocks + 50:
                guard += 1
                if mem:
                    mem.popleft()
                c = QTextCursor(doc)
                c.movePosition(QTextCursor.MoveOperation.Start)
                c.select(QTextCursor.SelectionType.BlockUnderCursor)
                if not c.hasSelection():
                    break
                c.removeSelectedText()
        except Exception:
            pass

    def _bring_qt_control_to_front(self) -> None:
        if self._start_tray_only or self.isHidden():
            return
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def _resync_dock_w_for_ui_phase(self) -> None:
        """런처 ↔ 클라이언트 페이즈 전환 시 `self._dock_w`·고정 폭이 도킹 기준과 맞게."""
        w, _h = get_dock_panel_wh(self._m)
        self._dock_w = max(8, int(w))
        try:
            self.setFixedWidth(self._dock_w)
        except Exception:
            pass
        self._last_dock_sig = None
        self._last_standby_sig = None
        self._last_btn_style_state = None
        QTimer.singleShot(0, self.apply_scaled_typography)
        QTimer.singleShot(0, lambda: self._dock_to_anchor(force=True))
        QTimer.singleShot(120, lambda: self._dock_to_anchor(force=True))

    def _dock_to_standby_centered(self, *, force: bool = False) -> None:
        """게임·런처 앵커 없음(대기) — 제어창을 주 모니터 작업 영역 중앙에 둔다(도킹 좌표 잔상 방지)."""
        if self._start_tray_only or self.isHidden():
            return
        m = self._m
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
            w_log, h_log = get_dock_panel_wh(m)
            w_log = max(8, int(w_log))
            h_log = max(8, int(h_log))
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
            try:
                set_typography_layout_width_px(int(self.width()))
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
            QTimer.singleShot(0, self.apply_scaled_typography)
        except Exception:
            pass

    def _sync_launcher_phase_docked_chrome(self) -> None:
        """런처 UI 페이즈: 상단 스트립만 — 제어창·킬 floater 는 숨김. 그 외 페이즈는(×로 닫지 않은 경우) 복원."""
        if self._start_tray_only:
            return
        m = self._m
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

    def _dock_to_anchor(self, *, force: bool = False) -> None:
        """도킹: 메인창(제어) Win32 **외곽 오른쪽** = 앵커 **클라이언트 영역 왼쪽** ``cr[0]`` (화면 좌표).
        런처 등 ``cr`` 없을 때만 외곽 ``ol`` 폴백. 세로·높이는 클라."""
        if self._start_tray_only or self.isHidden():
            return
        m = self._m
        if not getattr(m, "running", True):
            return
        try:
            anchor = resolve_dock_anchor_hwnd(m)
            if not anchor:
                self._dock_to_standby_centered(force=force)
                return
            self._last_standby_sig = None
            gr = m.get_window_outer_rect_screen(anchor)
            cr = m.get_window_rect(anchor)
            # 런처→클라 직후 한두 프레임은 GetWindowRect(외곽)만 비는 경우가 있음.
            # 도킹을 스킵하면 show() 직후 OS가 제어창을 «주 모니터 중앙»에 두어 멀티 모니터에서 어긋난다.
            if not gr and cr and cr[2] > cr[0] and cr[3] > cr[1]:
                gr = (int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3]))
            if not gr:
                self._dock_rect_miss_count = min(
                    int(getattr(self, "_dock_rect_miss_count", 0)) + 1,
                    10_000,
                )
                if self._dock_rect_miss_count <= 32:
                    QTimer.singleShot(48, lambda: self._dock_to_anchor(force=True))
                return
            ol, ot, o_right, ob = (int(x) for x in gr)
            self.update()
            scale = win32_dpi_scale_for_hwnd(m, int(anchor))
            dock_w_log = max(8, int(self._dock_w))
            fw_phys = max(8, int(round(dock_w_log * scale)))
            fh_phys = max(1, int(cr[3] - cr[1]) if cr and (cr[2] > cr[0]) else int(ob - ot))
            y_phys = int(cr[1]) if cr and (cr[2] > cr[0]) else int(ot)
            if fw_phys < 8 or fh_phys < 8:
                self._dock_rect_miss_count = min(
                    int(getattr(self, "_dock_rect_miss_count", 0)) + 1,
                    10_000,
                )
                if self._dock_rect_miss_count <= 32:
                    QTimer.singleShot(48, lambda: self._dock_to_anchor(force=True))
                return
            snap_right_to_x = int(cr[0]) if cr and (cr[2] > cr[0]) else int(ol)
            x_phys, y_phys, fw_phys, fh_phys = dock_outer_rect_touch_client_left(
                anchor,
                snap_right_to_x,
                y_phys,
                fw_phys,
                fh_phys,
            )
            sig = (snap_right_to_x, ol, ot, o_right, x_phys, y_phys, fw_phys, fh_phys)
            if not force and sig == self._last_dock_sig:
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
            if sys.platform == "win32":
                try:
                    win32_set_window_outer_rect(
                        int(self.winId()), x_phys, y_phys, fw_phys, fh_phys,
                    )
                except Exception:
                    pass
            try:
                set_typography_layout_width_px(int(self.width()))
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
        except Exception:
            pass

    def _quit_app(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        try:
            if e.oldSize().width() != self.width():
                self._sync_typography_width()
        except Exception:
            pass

    def showEvent(self, e: QShowEvent) -> None:
        super().showEvent(e)
        self._sync_pipela_qt_control_win_hwnd()
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
        if index == 0:
            self._sync_terminal_relative_timer()
            if (
                getattr(
                    self._m,
                    "console_log_time_display_mode",
                    CONSOLE_LOG_TIME_MODE_ABSOLUTE,
                )
                == CONSOLE_LOG_TIME_MODE_RELATIVE
            ):
                self.rebuild_terminal_log_display_for_time_mode()
        if index == 1:
            QTimer.singleShot(0, self._flush_settings_layout)
            QTimer.singleShot(50, self._flush_settings_layout)
            # 터미널에서 설정으로 올 때 이미 스택이 «업데이트»면 스택 시그널이 안 올 수 있음
            QTimer.singleShot(0, self._try_auto_update_manifest_check)
            # 보이는 설정 패널만 이전에 터미널 전용 경로로 스킵됐을 수 있음 — 한 번 동기화
            QTimer.singleShot(0, self.apply_scaled_typography)
        QTimer.singleShot(0, self._pin_action_button_panel_height)

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

        b0 = QPushButton("설정")
        b0.setObjectName("pipelaBreadcrumbSeg")
        b0.setFlat(True)
        b0.setCursor(Qt.CursorShape.PointingHandCursor)
        b0.setToolTip("설정 허브로 이동")
        b0.clicked.connect(self._on_breadcrumb_goto_hub)
        lay.addWidget(b0, 0, Qt.AlignmentFlag.AlignLeft)

        if idx <= 0:
            lay.addStretch(1)
            return
        for pid, i in self._panel_placeholders.items():
            if int(i) == idx:
                title = _HUB_TITLE_BY_PID.get(pid, pid)
                sep = QLabel(">")
                sep.setObjectName("pipelaBreadcrumbSep")
                lay.addWidget(sep, 0, Qt.AlignmentFlag.AlignLeft)
                b1 = QPushButton(title)
                b1.setObjectName("pipelaBreadcrumbSeg")
                b1.setFlat(True)
                b1.setCursor(Qt.CursorShape.PointingHandCursor)
                b1.setToolTip(f"«{title}»(으)로 이동 (현재 화면)")
                b1.clicked.connect(
                    lambda _c=False, stack_i=int(i): self._on_breadcrumb_goto_index(int(stack_i)),
                )
                lay.addWidget(b1, 0, Qt.AlignmentFlag.AlignLeft)
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
        # QApplication 전역 필터 — MouseButtonPress 가 아닌 이벤트는 즉시 통과( super 호출 제거).
        if event.type() != _EV_MOUSE_BUTTON_PRESS:
            return False
        if self._settings_wrap is None or not isinstance(watched, QWidget):
            return False
        me = event
        if not isinstance(me, QMouseEvent):
            return False
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

    def _open_settings_panel(self, panel_id: str, _title: str) -> None:
        if self._tabs is not None and self._tabs.currentIndex() != 1:
            self._tabs.setCurrentIndex(1)
        idx = self._panel_placeholders.get(panel_id)
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
        _mg = scale_px(12)
        body_l.setContentsMargins(_mg, _mg, _mg, _mg)
        body_l.setSpacing(scale_px(8))
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
        _rs = T.RADIUS_SM
        _line_inactive = T.BORDER
        _line_hair = T.BORDER_HAIR
        _design = 10.0 * control_action_label_pt_factor()
        _fpt = spt(_design)
        _tls = letter_spacing_qss()
        _pad_btn = action_button_qss_padding()
        st_on = (
            f"QPushButton {{ background-color: {T.BTN_ON}; color: {T.FG}; font-weight: 600; font-size: {_fpt};"
            f"letter-spacing: {_tls}; border: 1px solid {T.BTN_ON_BORDER}; padding: {_pad_btn}; border-radius: {_rs}; }}"
            f"QPushButton:hover {{ background-color: {T.BTN_ON_HOVER}; border: 1px solid {T.ACCENT}; color: {T.FG}; }}"
            f"QPushButton:pressed {{ background-color: {T.BTN_PRESSED}; border-color: {T.BTN_ON_BORDER}; }}"
        )
        st_off = (
            f"QPushButton {{ background-color: {T.CARD_BG}; color: {T.FG_MUTED}; font-weight: 500; font-size: {_fpt};"
            f"letter-spacing: {_tls}; border: 1px solid {_line_inactive}; padding: {_pad_btn}; border-radius: {_rs}; }}"
            f"QPushButton:hover {{ background-color: {T.CARD_HOVER}; border: 1px solid {T.ACCENT}; color: {T.FG}; }}"
            f"QPushButton:pressed {{ background-color: {T.BTN_PRESSED}; border-color: {_line_hair}; color: {T.FG}; }}"
        )
        st_emit = (
            f"QPushButton {{ background-color: {T.BTN_EMIT_BG}; color: {T.FG}; font-weight: 600; font-size: {_fpt};"
            f"letter-spacing: {_tls}; border: 1px solid {T.BTN_EMIT_BORDER}; padding: {_pad_btn}; border-radius: {_rs}; }}"
            f"QPushButton:hover {{ background-color: {T.BTN_EMIT_HOVER}; border: 1px solid {T.ACCENT}; color: {T.FG}; }}"
            f"QPushButton:pressed {{ background-color: {T.BTN_PRESSED}; border-color: {T.BTN_EMIT_BORDER}; }}"
        )

        self._btns["left"].setStyleSheet(st_on if m.left_click_feature_enabled else st_off)
        rh = m.right_hold_feature_enabled
        if rh:
            self._btns["right"].setStyleSheet(st_emit if m.right_hold_active else st_on)
        else:
            self._btns["right"].setStyleSheet(st_off)
        self._btns["reload"].setStyleSheet(st_on if m.reload_active else st_off)
        self._btns["flame"].setStyleSheet(st_on if m.flame_trigger_feature_enabled else st_off)
        self._btns["ammo"].setStyleSheet(st_on if m.ammo_restock_active else st_off)
        self._btns["merc"].setStyleSheet(st_on if m.call_merc_active else st_off)
        self._btns["ride"].setStyleSheet(st_on if m.ride_feature_enabled else st_off)
        self._btns["hp"].setStyleSheet(st_on if m.hp_refill_feature_enabled else st_off)
        self._btns["kc"].setStyleSheet(st_on if m.kill_counter_enabled else st_off)

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
        try:
            _th0 = m.refresh_target_hwnd_if_needed()
            _luh0 = m.refresh_smart_updater_hwnd_if_needed()
            _ph = get_ui_dock_phase_from_session(m, _th0, _luh0)
            if _ph == UI_DOCK_PHASE_CLIENT:
                self._close_intro_skip_settings_popup_if_open()
            _prev_ui_ph = getattr(self, "_ui_dock_phase_tracked", None)
            if _prev_ui_ph != _ph:
                self._ui_dock_phase_tracked = _ph
                if (
                    _ph == UI_DOCK_PHASE_STANDBY
                    and _prev_ui_ph is not None
                    and _prev_ui_ph != UI_DOCK_PHASE_STANDBY
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
        except Exception:
            try:
                self._sync_launcher_phase_docked_chrome()
            except Exception:
                pass
        self._sync_control_poll_interval()
        self._sync_pipela_qt_control_win_hwnd()
        fl_display = self._flame_action_caption()
        if self._btns["flame"].text() != fl_display:
            self._btns["flame"].setText(fl_display)
        hp_display = self._hp_refill_action_caption()
        if self._btns["hp"].text() != hp_display:
            self._btns["hp"].setText(hp_display)

        dock_force = False
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
        except Exception:
            pass

        style_state = (
            m.left_click_feature_enabled,
            m.right_hold_feature_enabled,
            m.right_hold_active,
            m.reload_active,
            m.flame_trigger_feature_enabled,
            m.ammo_restock_active,
            m.call_merc_active,
            m.ride_feature_enabled,
            m.hp_refill_feature_enabled,
            m.kill_counter_enabled,
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
        if not m.left_click_feature_enabled:
            m.left_click_active = False
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
        m.reload_active = not m.reload_active
        m._loop_print(f"[Reload] {'ON' if m.reload_active else 'OFF'}")

    def _toggle_flame(self) -> None:
        m = self._m
        m.flame_trigger_feature_enabled = not m.flame_trigger_feature_enabled
        if not m.flame_trigger_feature_enabled:
            m.flame_trigger_active = False
        m.schedule_save_config()
        print(f"[Flame Trigger] {'ON' if m.flame_trigger_feature_enabled else 'OFF'}")

    def _toggle_ammo(self) -> None:
        m = self._m
        m.ammo_restock_active = not m.ammo_restock_active
        m._loop_print(f"[Ammo Restock] {'ON' if m.ammo_restock_active else 'OFF'}")

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
