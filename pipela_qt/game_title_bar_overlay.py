"""게임(또는 런처) 타이틀 영역 상단 바 — Win32 소유 창(owner)으로 앵커보다 위, 전역 TOPMOST 없음."""

from __future__ import annotations

import os
import sys
import time

import win32con
import win32gui

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QWidget,
)

from pipela_core.display_timing import display_tick_ms_for_window
from pipela_core.paths import UI_ICON_KILL_COUNTER_PATH, UI_ICON_SETTINGS_PATH
from pipela_core.win32_window_ops import (
    win32_set_window_outer_rect,
    win32_set_window_owner,
    win32_set_window_topmost,
    win32_window_maximize_or_restore,
    win32_window_minimize,
    win32_window_post_close,
    win32_window_restore_normal,
)
from pipela_qt import theme as T
from pipela_qt.dock_ui_phase import (
    UI_DOCK_PHASE_CLIENT,
    UI_DOCK_PHASE_LAUNCHER,
    get_ui_dock_phase,
    get_ui_dock_phase_from_session,
)
from pipela_qt.dpi import (
    get_dock_panel_wh,
    win32_dpi_scale_for_hwnd,
    win32_physical_screen_rect_to_qt_overlay_geometry,
)
from pipela_qt.qt_dock_z_stack import clear_docked_chrome_z_stack_state, sync_docked_chrome_z_order
from pipela_qt.qt_side_dock import chrome_outer_rect_plausible_for_left_dock, compute_side_dock_layout
from pipela_qt.qt_dock_anchor import (
    resolve_dock_anchor_from_session,
    resolve_dock_anchor_hwnd,
    resolve_game_only_anchor_hwnd,
)
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.panels.kill_counter_tier_table_dialog import show_kill_counter_tier_table_dialog
from pipela_qt.resolution_chrome import (
    STRIP_RESOLUTION_PALETTE,
    apply_resolution_rich_label_fixed,
    resolution_block_content_key,
    resolution_block_html,
)
from pipela_qt.ui_adaptive import (
    letter_spacing_qss,
    qss_pad_vh,
    scale_px_h,
    scale_px_v,
    scaled_design_pt,
    set_typography_layout_height_px,
)

_HIDDEN = (-10000, -10000, 1, 1)
_MIN_TITLE_FRAME_PX = 4


def _strip_geom_snap_grid(n: int, step: int = 2) -> int:
    v = int(n)
    s = max(1, int(step))
    return (v // s) * s


def _geom_cache_quant_rect(
    r: tuple[int, int, int, int] | tuple[int, ...] | None,
    step: int = 4,
) -> tuple[int, int, int, int] | None:
    """Win32 사각형 1px 잡음으로 ``_compute_strip_geometry`` 캐시가 매 틱 미스 나는 것 완화."""
    if not r or len(r) < 4:
        return None
    s = max(1, int(step))
    return tuple((int(r[i]) // s) * s for i in range(4))
# 캡션(ct−ot)이 0에 가깝거나 복구 직후 DWM이 아직 안 줄 때 — 킬창은 클라만 쓰면 되지만 스트립은 높이가 필요함.
_STRIP_FALLBACK_BAR_H = 26
# Z 재정렬 — 너무 자주 하면 SetWindowPos 연쇄로 틱이 100ms 단위로 붙는다.
_Z_REAPPLY_MIN_SEC = 9.5
# 기하(geom)만 흔들릴 때는 Z-order 를 매 틱 돌리지 않음 — 앵커 교체·z_stale 은 즉시.
_STRIP_Z_ON_GEOM_MIN_SEC = max(
    0.0,
    float(os.environ.get("PIPELA_STRIP_Z_ON_GEOM_MIN_SEC", "0.48") or 0.48),
)
# 해상도 크롬 HTML 갱신은 Win32 비용을 줄이기 위해 기하가 안정일 때 틱당 호출을 피한다.
_STRIP_RES_CHROME_MIN_SEC = 1.45
# 앵커 외곽/클라 양자화가 같을 때 제어·킬 GetWindowRect 를 매 틱 하지 않음(도킹 중엔 50ms 이내 재사용).
_STRIP_GEOM_AUX_MAX_AGE_SEC = 0.072
# 기하 안정 시 제어/킬 GetWindowRect 재조회 간격(더 넓게 → 스트립 틱 ms↓)
_STRIP_GEOM_AUX_MAX_AGE_STABLE_SEC = 0.34
# ShowWindow 복원은 매 8ms 틱보다 드물게 — 앵커/기하 변화 시에는 즉시.
_STRIP_WIN32_LIFT_MIN_SEC = 1.25
# 최소화된 창은 Win32 외곽 좌표가 (-32000,) 근처로 나와 스트립이 화면 밖으로 감.
_STRIP_RECT_SANE_MIN = -2000
# 게임 타이틀 영역 상단 바 — 브랜드 텍스트(아이콘 옆)
_STRIP_BRAND_TITLE = "PIP EL.A"
# 브랜드 ↔ 버전 `move()` 간격(논리 px).
def _strip_text_cluster_gap_px() -> int:
    return max(scale_px_h(24), 18)


# 앱 아이콘 ↔ 프로그램 제목(브랜드) 사이.
def _strip_icon_to_brand_gap_px() -> int:
    return max(scale_px_h(10), 8)


# 플로팅 타이틀 클러스터(아이콘·브랜드·버전) 스트립 왼쪽 여백(논리 px).
def _strip_title_cluster_left_inset_px() -> int:
    return max(scale_px_h(20), 16)


# 스트립 루트 QHBox 여백(좌)·캡션 버튼 쪽(우) — 플로팅 타이틀이 좌측을 쓰므로 좌우 대칭에 가깝게.
def _strip_root_outer_margin_lr_px() -> tuple[int, int]:
    return scale_px_h(6), scale_px_h(6)


def _pipela_game_title_strip_stylesheet() -> str:
    return (
        f"QWidget#pipelaGameTitleStripRoot {{"
        f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        f"    stop:0 {T.STRIP_BG_TOP}, stop:1 {T.STRIP_BG});"
        f"  border: none;"
        f"  border-bottom: 1px solid {T.STRIP_BORDER};"
        f"}}"
        f"QLabel#pipelaStripAppIcon {{"
        f"  background: transparent;"
        f"  padding: 0px;"
        f"}}"
        f"QLabel#pipelaStripBrand {{"
        f"  color: {T.STRIP_ACCENT};"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  font-size: {T.spt(11.75)};"
        f"  font-weight: 700;"
        f"  letter-spacing: {letter_spacing_qss()};"
        f"  background: transparent;"
        f"  padding: 0;"
        f"  margin: 0;"
        f"}}"
        f"QLabel#pipelaStripRes {{"
        f"  background: transparent;"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  padding: 0;"
        f"  margin: 0;"
        f"}}"
        f"QLabel#pipelaStripVer {{"
        f"  color: {T.STRIP_FG_MUTED};"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  font-size: {T.spt(8.75)};"
        f"  font-weight: 500;"
        f"  background: transparent;"
        f"  padding: 0;"
        f"  margin: 0;"
        f"}}"
        f"QPushButton#pipelaStripCaptionBtn, QPushButton#pipelaStripCloseBtn {{"
        f"  background: transparent;"
        f"  border: none;"
        f"  border-radius: {T.STRIP_RADIUS_BTN};"
        f"  padding: {qss_pad_vh(2, 6)};"
        f"  min-width: {scale_px_h(22)}px;"
        f"  min-height: {scale_px_v(18)}px;"
        f"}}"
        f"QPushButton#pipelaStripCaptionBtn:hover {{ background: {T.STRIP_BTN_HOVER}; }}"
        f"QPushButton#pipelaStripCloseBtn:hover {{ background: {T.STRIP_BTN_HOVER_CLOSE}; }}"
        f"QToolButton#pipelaStripKillCounterBtn {{"
        f"  color: {T.STRIP_FG_MUTED};"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  font-size: {T.spt(8.125)};"
        f"  font-weight: 600;"
        f"  letter-spacing: {letter_spacing_qss()};"
        f"  background: transparent;"
        f"  border: none;"
        f"  border-radius: {T.STRIP_RADIUS_BTN};"
        f"  padding: {qss_pad_vh(2, 6)};"
        f"  margin: 0;"
        f"}}"
        f"QToolButton#pipelaStripKillCounterBtn:hover {{ background: {T.STRIP_BTN_HOVER}; }}"
    )


def _win32_outer_left_top_sane_for_strip(gl: int, gt: int) -> bool:
    return int(gl) >= _STRIP_RECT_SANE_MIN and int(gt) >= _STRIP_RECT_SANE_MIN


class QtGameTitleBarStrip(QWidget):
    """앵커를 `GWLP_HWNDPARENT` 소유자로 두어 항상 게임보다 위 Z. 다른 앱은 일반 규칙대로 위에 올 수 있음."""

    def __init__(self, pipela_mod) -> None:
        super().__init__()
        self._pl = pipela_mod
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setObjectName("pipelaGameTitleStripRoot")
        self.setStyleSheet(_pipela_game_title_strip_stylesheet())
        lay = QHBoxLayout(self)
        self._root_lay = lay
        _mgl, _mgr = _strip_root_outer_margin_lr_px()
        lay.setContentsMargins(_mgl, 0, _mgr, 0)
        lay.setSpacing(0)
        self._lbl_app_icon = QLabel()
        self._lbl_app_icon.setObjectName("pipelaStripAppIcon")
        self._lbl_app_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        self._apply_strip_app_icon_pixmap()
        self._lbl_brand = QLabel(_STRIP_BRAND_TITLE)
        self._lbl_brand.setObjectName("pipelaStripBrand")
        self._lbl_brand.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._lbl_res = QLabel()
        self._lbl_res.setObjectName("pipelaStripRes")
        self._lbl_res.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_res.setWordWrap(False)
        self._lbl_res.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._lbl_res.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        self._lbl_res.setMinimumWidth(0)
        _strip_ver = str(
            getattr(pipela_mod, "PIPELA_STRIP_DISPLAY_VERSION", "") or "",
        ).strip()
        _app_ver = str(getattr(pipela_mod, "PIPELA_APP_VERSION", "") or "").strip()
        if not _strip_ver:
            _strip_ver = "—"
        self._lbl_ver = QLabel(f"v{_strip_ver}" if _strip_ver != "—" else "—")
        self._lbl_ver.setObjectName("pipelaStripVer")
        self._lbl_ver.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        if _app_ver:
            self._lbl_ver.setToolTip(
                f"UI 개정 v{_strip_ver} · 릴리스 {_app_ver} (고정)",
            )
        else:
            self._lbl_ver.setToolTip(f"UI 개정 v{_strip_ver}")
        self._btn_kill_counter = QToolButton()
        self._btn_kill_counter.setObjectName("pipelaStripKillCounterBtn")
        self._btn_kill_counter.setAutoRaise(True)
        self._btn_kill_counter.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
        )
        self._btn_kill_counter.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_kill_counter.setToolTip("등급·몬스터킬 구간 표")
        _kc_ic = (
            QIcon(UI_ICON_KILL_COUNTER_PATH)
            if UI_ICON_KILL_COUNTER_PATH and os.path.isfile(str(UI_ICON_KILL_COUNTER_PATH))
            else QIcon()
        )
        self._btn_kill_counter.setIcon(_kc_ic)
        self._btn_kill_counter.setText("Kill Counter")
        self._btn_kill_counter.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_kill_counter.hide()
        self._btn_kill_counter.clicked.connect(self._on_strip_kill_counter_clicked)
        # Not in root layout — pinch to game client right (cr[2]) in `_layout_kill_counter_strip_button_geom`.
        self._btn_kill_counter.setParent(self)
        lay.addStretch(1)
        st = self.style()
        _isz = QSize(scale_px_h(14), scale_px_v(14))
        self._btn_min = QPushButton()
        self._btn_min.setObjectName("pipelaStripCaptionBtn")
        self._btn_min.setFlat(True)
        self._btn_min.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self._btn_min.setIconSize(_isz)
        self._btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_min.setToolTip("최소화 (연결된 게임/런처 창)")
        self._btn_min.clicked.connect(self._on_sys_min)
        self._btn_max = QPushButton()
        self._btn_max.setObjectName("pipelaStripCaptionBtn")
        self._btn_max.setFlat(True)
        self._btn_max.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self._btn_max.setIconSize(_isz)
        self._btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_max.setToolTip("최대화")
        self._btn_max.clicked.connect(self._on_sys_max)
        self._btn_max.setVisible(False)
        self._btn_launcher_settings = QPushButton()
        self._btn_launcher_settings.setObjectName("pipelaStripCaptionBtn")
        self._btn_launcher_settings.setFlat(True)
        _set_ic = QIcon(UI_ICON_SETTINGS_PATH) if UI_ICON_SETTINGS_PATH and os.path.isfile(
            UI_ICON_SETTINGS_PATH,
        ) else QIcon()
        if _set_ic.isNull():
            self._btn_launcher_settings.setIcon(
                st.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            )
        else:
            self._btn_launcher_settings.setIcon(_set_ic)
        self._btn_launcher_settings.setIconSize(_isz)
        self._btn_launcher_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_launcher_settings.setToolTip("설정 (런처 전용)")
        self._btn_launcher_settings.clicked.connect(self._on_launcher_strip_settings)
        self._btn_launcher_settings.hide()
        self._btn_close = QPushButton()
        self._btn_close.setObjectName("pipelaStripCloseBtn")
        self._btn_close.setFlat(True)
        self._btn_close.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self._btn_close.setIconSize(_isz)
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.setToolTip("닫기 (게임/런처에 WM_CLOSE)")
        self._btn_close.clicked.connect(self._on_sys_close)
        lay.addWidget(self._btn_min, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._btn_max, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._btn_launcher_settings, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._btn_close, 0, Qt.AlignmentFlag.AlignVCenter)
        if sys.platform != "win32":
            self._btn_min.hide()
            self._btn_max.hide()
            self._btn_launcher_settings.hide()
            self._btn_close.hide()
        for _w in (self._lbl_app_icon, self._lbl_brand, self._lbl_ver):
            _w.setParent(self)
        # Not in root layout — pin client-left (cr[0]) vs strip phys-left in `_layout_resolution_strip_label_geom`.
        self._lbl_res.setParent(self)
        self._lbl_res.hide()
        self.setGeometry(*_HIDDEN)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(int(self._strip_poll_interval_ms()))
        self._strip_active = False
        # `_move_hidden` 매 틱 SetWindowPos 폭주 차단 — 첫 호출에서 한 번 적용 후 단락
        self._strip_hidden_applied = False
        self._last_anchor: int | None = None
        self._last_geom_sig: tuple[int, int, int, int, int] | None = None
        self._last_z_anchor: int | None = None
        self._last_z_apply_mono: float = 0.0
        self._tick_track_game_iconic: bool | None = None
        self._bad_geom_streak = 0
        self._last_res_chrome_sig: object | None = None
        self._strip_left_phys: int | None = None
        self._last_strip_res_chrome_mono: float = 0.0
        self._last_win32_lift_mono: float = 0.0
        self._geom_compute_cache_key: object | None = None
        self._geom_compute_cache_val: tuple[int, int, int, int, int] | None = None
        # 픽셀 단위 잡음으로 매 틱 geom_changed → 도킹·타이포 전체 갱신되는 것 완화
        self._last_geom_cmp: tuple[int, int, int, int, int] | None = None
        self._last_res_ck: object | None = None
        self._last_res_block: str | None = None
        self._last_strip_geom_prim: object | None = None
        self._strip_geom_aux_mono: float = 0.0
        self._strip_cached_ch_rect: tuple[int, int, int, int] | None = None
        self._strip_cached_kr: int | None = None
        self._strip_tick_geom_sig: object | None = None
        self._resolution_chrome_scheduled: bool = False
        self._strip_geom_stable_streak: int = 0
        self._last_win32_strip_rect_phys: tuple[int, int, int, int, int] | None = None

    def _strip_main_ui_left_phys(self) -> int | None:
        """제어창 외곽 왼쪽(우선) 또는 `_compute_strip_geometry`와 같은 strip-left X(물리)."""
        if sys.platform != "win32":
            return None
        m = self._pl
        ai = getattr(self, "_last_anchor", None)
        if not ai:
            return None
        try:
            dp = getattr(m, "pipela_ui_dock_phase", None)
            if dp is None:
                dp = get_ui_dock_phase(m)
        except Exception:
            dp = UI_DOCK_PHASE_CLIENT
        try:
            gr = m.get_window_outer_rect_screen(int(ai))
            cr = m.get_window_rect(int(ai))
        except Exception:
            return None
        if not gr or not cr or int(cr[2]) <= int(cr[0]):
            return None
        if dp == UI_DOCK_PHASE_LAUNCHER:
            return int(cr[0])
        ol, ot = int(gr[0]), int(gr[1])
        qt_main = getattr(m, "_qt_control_main", None)
        ch = getattr(m, "pipela_qt_control_win_hwnd", None)
        ch_rect, _ = self._win32_strip_aux_control_kill_rects(qt_main, ch)
        left_x = int(ol)
        used_ctl = False
        if ch_rect is not None:
            gl, gt, _, _ = ch_rect
            if _win32_outer_left_top_sane_for_strip(gl, gt) and chrome_outer_rect_plausible_for_left_dock(
                ch_rect, cr,
            ):
                left_x = int(gl)
                used_ctl = True
        if not used_ctl:
            try:
                dock_w_log, _dh0 = get_dock_panel_wh(m)
                lay = compute_side_dock_layout(
                    m,
                    int(ai),
                    dock_w_log=max(8, int(dock_w_log)),
                    side="left",
                    gr=gr,
                    cr=cr,
                )
                if lay is not None and _win32_outer_left_top_sane_for_strip(int(lay.x_phys), int(ot)):
                    left_x = int(lay.x_phys)
            except Exception:
                pass
        return int(left_x)

    def _strip_title_cluster_dpi_hwnd(
        self,
        m,
        cr: tuple[int, int, int, int],
    ) -> int:
        qt_main = getattr(m, "_qt_control_main", None)
        ch = getattr(m, "pipela_qt_control_win_hwnd", None)
        ch_rect, _ = self._win32_strip_aux_control_kill_rects(qt_main, ch)
        ai = getattr(self, "_last_anchor", None)
        if ch_rect is not None and ch:
            gl, gt, _, _ = ch_rect
            if _win32_outer_left_top_sane_for_strip(gl, gt) and chrome_outer_rect_plausible_for_left_dock(
                ch_rect, cr,
            ):
                try:
                    return int(ch)
                except (TypeError, ValueError):
                    pass
        return int(ai) if ai else int(self.winId())

    def _layout_strip_title_cluster_geom(self) -> None:
        """메인 UI(제어창) 물리 왼쪽 대비 스트립 물리 왼쪽 차이로 아이콘·브랜드·버전 `move`(해상도/KC 패턴)."""
        ic = getattr(self, "_lbl_app_icon", None)
        br = getattr(self, "_lbl_brand", None)
        ver = getattr(self, "_lbl_ver", None)
        if ic is None or br is None or ver is None:
            return
        mw = max(16, int(self.width()))
        h_st = max(8, int(self.height()))
        gap_ib = _strip_icon_to_brand_gap_px()
        gap_bv = _strip_text_cluster_gap_px()
        if sys.platform != "win32":
            x = max(0, _strip_title_cluster_left_inset_px())
            pm = ic.pixmap()
            ic_ok_nl = ic.isVisible() and pm is not None and not pm.isNull()
            if ic_ok_nl:
                ic.adjustSize()
                w_ic_nl = max(8, ic.width())
                h_ic_nl = max(8, ic.height())
                y_ic_nl = max(0, int((h_st - h_ic_nl) / 2))
                x_pl = max(0, min(x, mw - w_ic_nl))
                ic.move(x_pl, y_ic_nl)
                ic.show()
                x = x_pl + w_ic_nl + gap_ib
            else:
                ic.hide()
            br.adjustSize()
            w_br_nl = max(8, int(br.sizeHint().width()))
            h_br_nl = max(8, int(br.sizeHint().height()))
            x_pl = max(0, min(x, mw - w_br_nl))
            br.move(x_pl, max(0, int((h_st - h_br_nl) / 2)))
            br.show()
            x = x_pl + w_br_nl + gap_bv
            ver.adjustSize()
            wv = max(8, int(ver.sizeHint().width()))
            hv = max(8, int(ver.sizeHint().height()))
            x_pl = max(0, min(x, mw - wv))
            ver.move(x_pl, max(0, int((h_st - hv) / 2)))
            ver.show()
            return
        sl = self._strip_left_phys
        if sl is None:
            gs = getattr(self, "_last_geom_sig", None)
            if gs is not None and len(gs) >= 1:
                try:
                    sl = int(gs[0])
                except (TypeError, ValueError):
                    sl = None
        if sl is None:
            return
        m = self._pl
        ml = self._strip_main_ui_left_phys()
        ai = getattr(self, "_last_anchor", None)
        if not ai:
            return
        try:
            cr = m.get_window_rect(int(ai))
            if not cr or len(cr) < 4 or int(cr[2]) <= int(cr[0]):
                return
        except Exception:
            return
        dpi_hwnd = self._strip_title_cluster_dpi_hwnd(m, cr)
        try:
            sc = float(win32_dpi_scale_for_hwnd(m, int(dpi_hwnd)))
        except Exception:
            sc = 1.0
        if sc <= 0.01:
            sc = 1.0
        pad = _strip_title_cluster_left_inset_px()
        if ml is None:
            x_icon = pad
        else:
            x_icon = int(round(float(int(ml) - int(sl)) / sc)) + pad
        ic_ok = ic.isVisible()
        pm0 = ic.pixmap()
        if not ic_ok or pm0 is None or pm0.isNull():
            ic_ok = False
        ic.adjustSize()
        w_ic = max(0, int(ic.width())) if ic_ok else 0
        h_ic = max(8, int(ic.height())) if ic_ok else 0
        br.adjustSize()
        w_br = max(8, int(br.sizeHint().width()))
        h_br = max(8, int(br.sizeHint().height()))
        ver.adjustSize()
        w_ver = max(8, int(ver.sizeHint().width()))
        h_ver = max(8, int(ver.sizeHint().height()))
        if ic_ok:
            y_ic = max(0, int((h_st - h_ic) / 2))
            x_ic = max(0, min(x_icon, mw - max(8, w_ic)))
            ic.move(x_ic, y_ic)
            ic.show()
            x_after_ic = x_ic + max(8, w_ic) + gap_ib
        else:
            ic.hide()
            x_after_ic = x_icon
        x_br = max(0, min(x_after_ic, mw - w_br))
        y_br = max(0, int((h_st - h_br) / 2))
        br.move(x_br, y_br)
        br.show()
        x_ver = x_br + w_br + gap_bv
        x_ver = max(0, min(x_ver, mw - w_ver))
        y_ver = max(0, int((h_st - h_ver) / 2))
        ver.move(x_ver, y_ver)
        ver.show()
        res_lbl = getattr(self, "_lbl_res", None)
        if res_lbl is not None and res_lbl.isVisible():
            for w in (ic, br, ver):
                if w.isVisible():
                    try:
                        w.stackUnder(res_lbl)
                    except Exception:
                        pass
        else:
            try:
                ver.raise_()
                br.raise_()
                ic.raise_()
            except Exception:
                pass

    def _strip_resolution_rect_hwnd(self) -> int | None:
        """클라 좌측 정렬에 쓰는 `get_window_rect` 대상 — 게임 클라이언트 페이즈는 게임 우선."""
        m = self._pl
        a = getattr(self, "_last_anchor", None)
        try:
            dock_phase = getattr(m, "pipela_ui_dock_phase", None)
            if dock_phase is None:
                dock_phase = get_ui_dock_phase(m)
        except Exception:
            dock_phase = UI_DOCK_PHASE_CLIENT
        if dock_phase == UI_DOCK_PHASE_CLIENT:
            gh = resolve_game_only_anchor_hwnd(m)
            rh = gh if gh else a
        else:
            rh = a
        try:
            return int(rh) if rh else None
        except (TypeError, ValueError):
            return None

    def _layout_resolution_strip_label_geom(self) -> None:
        """앵커 클라이언트 왼쪽(cr[0])과 스트립 물리 왼쪽 차이로 X 배치 — KC cr[2] 배치와 동일 패턴."""
        lbl = getattr(self, "_lbl_res", None)
        if lbl is None or not lbl.isVisible():
            return
        if sys.platform != "win32":
            return
        sl = self._strip_left_phys
        if sl is None:
            gs = getattr(self, "_last_geom_sig", None)
            if gs is not None and len(gs) >= 1:
                try:
                    sl = int(gs[0])
                except (TypeError, ValueError):
                    sl = None
        if sl is None:
            return
        m = self._pl
        rect_hwnd = self._strip_resolution_rect_hwnd()
        if not rect_hwnd:
            return
        try:
            cr = m.get_window_rect(int(rect_hwnd))
            if not cr or len(cr) < 4 or int(cr[2]) <= int(cr[0]):
                return
            cr_l = int(cr[0])
        except Exception:
            return
        try:
            sc = float(win32_dpi_scale_for_hwnd(m, int(rect_hwnd)))
        except Exception:
            sc = 1.0
        if sc <= 0.01:
            sc = 1.0
        x_left = int(round(float(cr_l - int(sl)) / sc))
        lbl.adjustSize()
        bw = max(8, int(lbl.sizeHint().width()))
        bh = max(8, int(lbl.sizeHint().height()))
        h_st = max(8, int(self.height()))
        y_top = max(0, int((h_st - bh) / 2))
        mw = max(16, int(self.width()))
        x_left = max(0, min(x_left, mw - bw))
        try:
            lbl.raise_()
        except Exception:
            pass
        lbl.move(x_left, y_top)
        lbl.show()

    def _update_strip_resolution_chrome(self) -> None:
        """게임/런처 타이틀 바 안 — 클라·템플릿·DPI 한 줄(제어창에서 이전)."""
        m = self._pl
        lbl = self._lbl_res
        try:
            ck = resolution_block_content_key(m)
            if ck != self._last_res_ck or not self._last_res_block:
                self._last_res_ck = ck
                self._last_res_block = resolution_block_html(m, STRIP_RESOLUTION_PALETTE)
            block = self._last_res_block
            if not block:
                lbl.hide()
                return
            sig = (block,)
            if sig != self._last_res_chrome_sig:
                apply_resolution_rich_label_fixed(
                    lbl,
                    block_html=block,
                    design_scale=0.66,
                )
                self._last_res_chrome_sig = sig
            lbl.show()
            try:
                self._layout_resolution_strip_label_geom()
            except Exception:
                pass
        except Exception:
            pass

    def _schedule_resolution_chrome(self) -> None:
        """해상도 리치 라벨 — 다음 이벤트 루프로 미루어 `title_strip.tick` 본문을 짧게 유지."""
        if self._resolution_chrome_scheduled:
            return
        self._resolution_chrome_scheduled = True
        QTimer.singleShot(0, self._run_deferred_resolution_chrome)

    def _run_deferred_resolution_chrome(self) -> None:
        self._resolution_chrome_scheduled = False
        try:
            self._update_strip_resolution_chrome()
        except Exception:
            pass

    def _apply_strip_app_icon_pixmap(self) -> None:
        lbl = getattr(self, "_lbl_app_icon", None)
        if lbl is None:
            return
        _cell = max(14, min(26, scale_px_v(18)))
        _inset = max(1, scale_px_v(2))
        _pm_side = max(10, _cell - 2 * _inset)
        ic = qt_application_icon()
        if ic.isNull():
            lbl.clear()
            lbl.hide()
            return
        pm = ic.pixmap(QSize(_pm_side, _pm_side))
        if pm.isNull():
            lbl.clear()
            lbl.hide()
            return
        try:
            pm = pm.scaled(
                _pm_side,
                _pm_side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception:
            pass
        try:
            pm.setDevicePixelRatio(1.0)
        except Exception:
            pass
        lbl.setPixmap(pm)
        lbl.setFixedSize(_cell, _cell)
        lbl.setScaledContents(False)
        lbl.show()

    def apply_scaled_typography(self) -> None:
        m = self._pl
        h_ref = None
        try:
            ah = resolve_dock_anchor_hwnd(m)
            if ah:
                from pipela_qt.qt_side_dock import anchor_client_inner_height_logical_qt

                h_ref = anchor_client_inner_height_logical_qt(m, int(ah))
        except Exception:
            h_ref = None
        if h_ref is None:
            try:
                _w0, _h0 = get_dock_panel_wh(m)
                h_ref = max(8, int(_h0))
            except Exception:
                h_ref = None
        if h_ref is not None:
            try:
                set_typography_layout_height_px(int(h_ref))
            except Exception:
                pass
        _ss = _pipela_game_title_strip_stylesheet()
        if _ss != getattr(self, "_last_strip_stylesheet", None):
            self._last_strip_stylesheet = _ss
            self.setStyleSheet(_ss)
        rl = getattr(self, "_root_lay", None)
        if rl is not None:
            _mgl, _mgr = _strip_root_outer_margin_lr_px()
            rl.setContentsMargins(_mgl, 0, _mgr, 0)
            rl.setSpacing(0)
        self._apply_strip_app_icon_pixmap()
        iz = max(10, min(22, scale_px_v(14)))
        _isz = QSize(iz, iz)
        for btn in (self._btn_min, self._btn_max, self._btn_launcher_settings, self._btn_close):
            btn.setIconSize(_isz)
        _kc_sz = max(12, min(28, scale_px_v(20)))
        self._btn_kill_counter.setIconSize(QSize(_kc_sz, _kc_sz))
        rf = app_default_qfont(10, QFont.Weight.Medium)
        rf.setPointSizeF(max(8.0, min(16.0, scaled_design_pt(9.5))))
        self._lbl_res.setFont(rf)
        self._last_res_chrome_sig = None
        try:
            delattr(self._lbl_res, "_pipela_res_fit_cache_k")
        except AttributeError:
            pass
        try:
            self._layout_strip_title_cluster_geom()
        except Exception:
            pass
        self._update_strip_resolution_chrome()

    def _win32_lift_strip_visible(self) -> None:
        """소유 창이 게임과 함께 iconic 이 되면 Qt만으로는 안 올라올 때가 있어 Win32로 복원."""
        if sys.platform != "win32":
            return
        try:
            wid = int(self.winId())
            if not win32gui.IsWindow(wid):
                return
            if win32gui.IsIconic(wid):
                win32_window_restore_normal(wid)
                win32gui.ShowWindow(wid, win32con.SW_SHOWNA)
            elif not win32gui.IsWindowVisible(wid):
                win32gui.ShowWindow(wid, win32con.SW_SHOWNA)
        except Exception:
            pass

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._last_res_chrome_sig = None
        try:
            self._layout_strip_title_cluster_geom()
        except Exception:
            pass
        self._update_strip_resolution_chrome()
        try:
            self._layout_resolution_strip_label_geom()
        except Exception:
            pass
        try:
            self._layout_kill_counter_strip_button_geom()
        except Exception:
            pass

    def _layout_kill_counter_strip_button_geom(self) -> None:
        """킬 플로터 도킹 기준 게임 클라 오른쪽(cr[2])과 같은 세로줄 위에 스트립 KC 배치."""
        btn = getattr(self, "_btn_kill_counter", None)
        if btn is None or not btn.isVisible():
            return
        if sys.platform != "win32":
            return
        sl = self._strip_left_phys
        if sl is None:
            gs = getattr(self, "_last_geom_sig", None)
            if gs is not None and len(gs) >= 1:
                try:
                    sl = int(gs[0])
                except (TypeError, ValueError):
                    sl = None
        if sl is None:
            return
        m = self._pl
        try:
            game_hw = resolve_game_only_anchor_hwnd(m)
            if not game_hw:
                return
            a_rect = int(game_hw)
            cr = m.get_window_rect(a_rect)
            if not cr or len(cr) < 4 or int(cr[2]) <= int(cr[0]):
                return
            cr_r = int(cr[2])
        except Exception:
            return
        try:
            sc = float(win32_dpi_scale_for_hwnd(m, a_rect))
        except Exception:
            sc = 1.0
        if sc <= 0.01:
            sc = 1.0
        x_left = int(round(float(cr_r - int(sl)) / sc))
        btn.adjustSize()
        bw = max(8, int(btn.sizeHint().width()))
        bh = max(8, int(btn.sizeHint().height()))
        h_st = max(8, int(self.height()))
        y_top = max(0, int((h_st - bh) / 2))
        mw = max(16, int(self.width()))
        x_left = max(0, min(x_left, mw - bw))
        try:
            btn.stackUnder(self._btn_min)
        except Exception:
            pass
        btn.move(x_left, y_top)
        btn.show()

    def invalidate_chrome_layout(self) -> None:
        """제어창·킬 패널 최소화/복구 직후 다음 틱에 기하·소유·Z 를 다시 맞춤."""
        self._last_geom_sig = None
        self._last_geom_cmp = None
        self._last_z_anchor = None
        self._bad_geom_streak = 0
        self._last_res_chrome_sig = None
        self._geom_compute_cache_key = None
        self._geom_compute_cache_val = None
        self._strip_max_icon_last_anchor = None
        self._last_res_ck = None
        self._last_res_block = None
        self._last_strip_geom_prim = None
        self._strip_geom_aux_mono = 0.0
        self._strip_cached_ch_rect = None
        self._strip_cached_kr = None
        self._strip_tick_geom_sig = None
        self._strip_geom_stable_streak = 0
        self._last_win32_strip_rect_phys = None

    def _strip_sysmenu_anchor_hwnd(self) -> int | None:
        """캡션 버튼 클릭 시점의 앵커 — ``_last_anchor`` 캐시만 쓰면 HWND가 비었거나 낡은 경우가 있음."""
        m = self._pl
        try:
            m.refresh_target_hwnd_if_needed()
            m.refresh_smart_updater_hwnd_if_needed()
        except Exception:
            pass
        try:
            a = resolve_dock_anchor_hwnd(m)
            if a and win32gui.IsWindow(int(a)):
                return int(a)
        except Exception:
            pass
        la = self._last_anchor
        try:
            if la and win32gui.IsWindow(int(la)):
                return int(la)
        except Exception:
            pass
        return None

    def _win32_strip_aux_control_kill_rects(
        self,
        qt_main,
        ch,
    ) -> tuple[tuple[int, int, int, int] | None, int | None]:
        """스트립 가로(제어 왼쪽·킬 오른쪽) — 클라이언트 페이즈 전용 보조 Win32."""
        ch_rect: tuple[int, int, int, int] | None = None
        kr: int | None = None
        if (
            qt_main is not None
            and qt_main.isVisible()
            and not qt_main.isMinimized()
            and ch
            and win32gui.IsWindow(int(ch))
        ):
            try:
                gl, gt, grt, gb = win32gui.GetWindowRect(int(ch))
                ch_rect = (int(gl), int(gt), int(grt), int(gb))
            except Exception:
                ch_rect = None
        if qt_main is not None:
            kc = getattr(qt_main, "_kc_float", None)
            if kc is not None and kc.isVisible() and not kc.isMinimized():
                try:
                    kh = int(kc.winId())
                    if win32gui.IsWindow(kh):
                        _kl, _kt, krr, _kb = win32gui.GetWindowRect(kh)
                        if _win32_outer_left_top_sane_for_strip(int(_kl), int(_kt)):
                            kr = int(krr)
                except Exception:
                    pass
        return ch_rect, kr

    def _compute_strip_geometry(
        self,
        m,
        anchor: int,
        *,
        dock_phase: str | None = None,
        gr: tuple[int, int, int, int] | None = None,
        cr: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int, int, int, int] | None:
        """(x, y, w, bar_h, anchor_int). 실패 시 None — 킬 패널 도킹과 달리 비클라/외곽이 필요."""
        anchor_int = int(anchor)
        if dock_phase is None:
            dock_phase = getattr(m, "pipela_ui_dock_phase", None)
            if dock_phase is None:
                dock_phase = get_ui_dock_phase(m)
        if gr is None:
            gr = m.get_window_outer_rect_screen(anchor_int)
        if cr is None:
            cr = m.get_window_rect(anchor_int)
        if not gr or not cr or not (cr[2] > cr[0]) or not (cr[3] > cr[1]):
            return None
        qk_gr = _geom_cache_quant_rect((int(gr[0]), int(gr[1]), int(gr[2]), int(gr[3])))
        qk_cr = _geom_cache_quant_rect((int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3])))
        ol, ot, o_right, _ob = (int(x) for x in gr)
        ct = int(cr[1])
        raw_title_h = int(ct - ot)
        if raw_title_h >= _MIN_TITLE_FRAME_PX:
            bar_h = raw_title_h
        else:
            bar_h = int(_STRIP_FALLBACK_BAR_H)
        bar_h_q = _strip_geom_snap_grid(bar_h, 4)
        # 런처 페이즈: 가로는 **클라이언트**[cr]에 맞춤 — 외곽(o_right−ol)만 쓰면
        # 좌·우 창 테두리(DWM)만큼 스트립이 런처 «보이는 본문»보다 넓어 보임.
        if dock_phase == UI_DOCK_PHASE_LAUNCHER:
            cache_key = ("L", anchor_int, qk_gr, qk_cr, bar_h_q)
            if cache_key == self._geom_compute_cache_key:
                v = self._geom_compute_cache_val
                if v is not None:
                    return v
            cl, _c0, cr_r, _c1 = (int(x) for x in cr)
            w0 = int(cr_r) - int(cl)
            w0 = max(8, w0)
            if bar_h < 8 or w0 < 8:
                return None
            val = (int(cl), int(ot), w0, bar_h, anchor_int)
            self._geom_compute_cache_key = cache_key
            self._geom_compute_cache_val = val
            return val

        qt_main = getattr(m, "_qt_control_main", None)
        ch = getattr(m, "pipela_qt_control_win_hwnd", None)
        prim = (dock_phase, anchor_int, qk_gr, qk_cr, bar_h_q)
        _now_aux = time.monotonic()
        _streak = int(getattr(self, "_strip_geom_stable_streak", 0))
        _aux_max = (
            _STRIP_GEOM_AUX_MAX_AGE_STABLE_SEC
            if _streak >= 10
            else (
                0.2
                if _streak >= 4
                else _STRIP_GEOM_AUX_MAX_AGE_SEC
            )
        )
        aux_stale = (
            prim != self._last_strip_geom_prim
            or (_now_aux - self._strip_geom_aux_mono) >= _aux_max
        )
        if aux_stale:
            self._last_strip_geom_prim = prim
            self._strip_geom_aux_mono = _now_aux
            ch_rect, kr = self._win32_strip_aux_control_kill_rects(qt_main, ch)
            self._strip_cached_ch_rect = ch_rect
            self._strip_cached_kr = kr
        else:
            ch_rect = self._strip_cached_ch_rect
            kr = self._strip_cached_kr

        qk_ch = _geom_cache_quant_rect(ch_rect)
        qk_kr = _strip_geom_snap_grid(int(kr), 4) if kr is not None else None
        cache_key = ("C", dock_phase, anchor_int, qk_gr, qk_cr, bar_h_q, qk_ch, qk_kr)
        if cache_key == self._geom_compute_cache_key:
            v = self._geom_compute_cache_val
            if v is not None:
                return v

        left_x = int(ol)
        # 스트립 오른끝: **클라이언트** `cr[2]` — `o_right`(외곽)만 쓰면 DWM 프레임만큼
        # 킬이 꺼진 설정에서 본문보다 스트립이 오른쪽으로 살짝 나온다. 킬 켬이면 `kr`까지.
        cl_r = int(cr[2])
        right_x = cl_r
        used_control_hwnd_for_left = False
        if ch_rect is not None:
            gl, gt, _gr, _gb = ch_rect
            if (
                _win32_outer_left_top_sane_for_strip(gl, gt)
                and chrome_outer_rect_plausible_for_left_dock(ch_rect, cr)
            ):
                left_x = int(gl)
                used_control_hwnd_for_left = True
        if not used_control_hwnd_for_left and sys.platform == "win32":
            try:
                dock_w_log, _dh0 = get_dock_panel_wh(m)
                lay = compute_side_dock_layout(
                    m,
                    int(anchor_int),
                    dock_w_log=max(8, int(dock_w_log)),
                    side="left",
                    gr=gr,
                    cr=cr,
                )
                if lay is not None and _win32_outer_left_top_sane_for_strip(
                    int(lay.x_phys), int(ot),
                ):
                    left_x = int(lay.x_phys)
            except Exception:
                pass
        if kr is not None:
            right_x = max(right_x, int(kr))
        w = max(8, right_x - left_x)
        x = left_x
        y = int(ot)
        if bar_h < 8 or w < 8:
            return None
        val = (x, y, w, bar_h, anchor_int)
        self._geom_compute_cache_key = cache_key
        self._geom_compute_cache_val = val
        return val

    def _set_strip_rect_from_win32_phys(
        self,
        m,
        wid: int,
        x: int,
        y: int,
        w: int,
        h: int,
        anchor_hwnd: int,
    ) -> None:
        """``GetWindowRect`` 물리값 → Win32 `SetWindowPos` + Qt `setGeometry` 논리(DIP) — 제어창 도킹과 동일."""
        phys = (int(x), int(y), int(w), int(h), int(anchor_hwnd))
        if phys == self._last_win32_strip_rect_phys:
            return
        self._last_win32_strip_rect_phys = phys
        self._strip_left_phys = int(x)
        x_l, y_l, w_l, h_l = win32_physical_screen_rect_to_qt_overlay_geometry(
            m, int(anchor_hwnd), int(x), int(y), int(w), int(h),
        )
        self.setGeometry(x_l, y_l, w_l, h_l)
        win32_set_window_outer_rect(wid, int(x), int(y), int(w), int(h))

    def _apply_strip_geometry_now(
        self,
        m,
        x: int,
        y: int,
        w: int,
        bar_h: int,
        anchor_int: int,
        *,
        force_owner: bool,
    ) -> None:
        """Win32·Qt 즉시 반영 + Z(필요 시 소유자 재연결)."""
        wid = int(self.winId())
        if not win32gui.IsWindow(wid):
            return
        self._win32_lift_strip_visible()
        self._set_strip_rect_from_win32_phys(
            m, wid, x, y, w, bar_h, int(anchor_int),
        )
        geom_sig = (x, y, w, bar_h, anchor_int)
        self._last_geom_sig = geom_sig
        self._strip_active = True
        self._strip_left_phys = int(x)
        self._last_anchor = anchor_int
        self._last_z_anchor = anchor_int
        now = time.monotonic()
        self._last_z_apply_mono = now
        self._sync_z(
            wid, anchor_int, set_owner=force_owner, force_z_restack=True,
        )
        self._update_max_button_icon(anchor_int, force=True)
        self._strip_hidden_applied = False
        self.show()
        self.raise_()

    def _update_max_button_icon(self, anchor: int, *, force: bool = False) -> None:
        """최대화 버튼 비표시 — 틱에서의 호출만 유지(no-op)."""
        return

    def _minimize_pipela_chrome_with_game(self) -> None:
        """게임 최소화 시 도킹된 Pipela 제어창·킬 패널은 그대로 두면 어색하므로 같이 최소화/숨김."""
        m = self._pl
        qt_main = getattr(m, "_qt_control_main", None)
        if qt_main is None:
            return
        try:
            if qt_main.isVisible():
                if sys.platform == "win32":
                    try:
                        mw = int(qt_main.winId())
                        if win32gui.IsWindow(mw):
                            win32_window_minimize(mw)
                        else:
                            qt_main.showMinimized()
                    except Exception:
                        qt_main.showMinimized()
                else:
                    qt_main.showMinimized()
            kc = getattr(qt_main, "_kc_float", None)
            if kc is not None and kc.isVisible():
                kc.hide()
        except Exception:
            pass

    def _on_sys_min(self) -> None:
        if sys.platform != "win32":
            return
        a = self._strip_sysmenu_anchor_hwnd()
        if not a:
            return
        m = self._pl
        qt_main = getattr(m, "_qt_control_main", None)
        unify_restore = (
            qt_main is not None
            and qt_main.isVisible()
            and not qt_main.isMinimized()
        )
        win32_window_minimize(int(a))
        self._minimize_pipela_chrome_with_game()
        if unify_restore:
            try:
                m._pipela_chrome_minimized_with_game = True
            except Exception:
                pass

    def _restore_pipela_chrome_if_anchor_back(
        self,
        m,
        *,
        anchor: int | None,
        th0,
        luh0,
        dock_phase: str,
    ) -> None:
        """앵커가 다시 보일 때 제어창·킬·스트립을 되살림 — `dock_chrome_restore` 와 동일 조건."""
        from pipela_qt.dock_chrome_restore import restore_pipela_docked_chrome_if_needed

        if anchor is None:
            return
        if not restore_pipela_docked_chrome_if_needed(
            m,
            anchor_hwnd=int(anchor),
            target_hwnd=th0,
            launcher_hwnd=luh0,
            dock_phase=dock_phase,
        ):
            return
        self.invalidate_chrome_layout()
        ah = int(anchor)
        geom = self._compute_strip_geometry(m, ah, dock_phase=dock_phase)
        if geom is not None:
            x, y, w, bar_h, anchor_int = geom
            try:
                self._apply_strip_geometry_now(
                    m, x, y, w, bar_h, anchor_int, force_owner=True,
                )
            except Exception:
                pass
        try:
            self._win32_lift_strip_visible()
            if not self.isVisible():
                self.show()
            self.raise_()
        except Exception:
            pass

    def _on_launcher_strip_settings(self) -> None:
        m = self._pl
        qtm = getattr(m, "_qt_control_main", None)
        if qtm is None:
            return
        try:
            qtm.open_settings_from_launcher_title_strip()
        except Exception:
            pass

    def _on_strip_kill_counter_clicked(self) -> None:
        try:
            show_kill_counter_tier_table_dialog(self, pipela_mod=self._pl)
        except Exception:
            pass

    def _sync_kill_counter_strip_cluster(
        self, th0: int | None, dock_phase: str,
    ) -> None:
        """Kill Counter 헤더(아이콘+글자) 표시 — 킬 패널과 동일 게이트(STANDBY 등에선 숨김)."""
        btn = getattr(self, "_btn_kill_counter", None)
        if btn is None:
            return
        m = self._pl
        try:
            if dock_phase != UI_DOCK_PHASE_CLIENT:
                vis = False
            elif not bool(getattr(m, "kill_counter_enabled", False)):
                vis = False
            elif not th0 or bool(m.is_window_minimized(th0)):
                vis = False
            else:
                ctrl = getattr(m, "_qt_control_main", None)
                vis = not (
                    ctrl is not None and bool(getattr(ctrl, "_kc_float_user_hidden", False))
                )
        except Exception:
            vis = False
        prev = btn.isVisible()
        if prev != vis:
            btn.setVisible(vis)
        if vis:
            try:
                self._layout_kill_counter_strip_button_geom()
            except Exception:
                pass

    def _sync_strip_launcher_caption_buttons(
        self,
        m,
        *,
        dock_phase: str | None = None,
    ) -> None:
        """런처 페이즈: 최대화 대신 설정 버튼."""
        if sys.platform != "win32":
            return
        try:
            if dock_phase is None:
                dock_phase = getattr(m, "pipela_ui_dock_phase", None)
            if dock_phase is None:
                dock_phase = get_ui_dock_phase(m)
            if dock_phase == UI_DOCK_PHASE_LAUNCHER:
                self._btn_max.hide()
                self._btn_launcher_settings.show()
            else:
                self._btn_launcher_settings.hide()
                self._btn_max.hide()
        except Exception:
            pass

    def _on_sys_max(self) -> None:
        if sys.platform != "win32":
            return
        a = self._strip_sysmenu_anchor_hwnd()
        if not a:
            return
        win32_window_maximize_or_restore(int(a))
        self._update_max_button_icon(int(a), force=True)
        self.invalidate_chrome_layout()
        QTimer.singleShot(160, self.invalidate_chrome_layout)

    def _on_sys_close(self) -> None:
        if sys.platform != "win32":
            return
        a = self._strip_sysmenu_anchor_hwnd()
        if not a:
            return
        win32_window_post_close(int(a))

    def _sync_z(
        self,
        wid: int,
        anchor: int,
        *,
        set_owner: bool,
        force_z_restack: bool = False,
    ) -> None:
        """소유자(선택) + TOPMOST 해제 + 오버레이·게임과의 상대 Z.

        ``set_owner`` 는 앵커 HWND가 **바뀔 때만** True — 매 프레임 GWLP_HWNDPARENT 를 다시 쓰면
        포커스·타이틀 그리기와 충돌해 번쩍임이 난다.
        """
        sync_docked_chrome_z_order(
            self._pl,
            int(wid),
            int(anchor),
            set_owner=set_owner,
            force_z_restack=force_z_restack,
        )

    def reassert_z_order(self) -> None:
        """오버레이 등에서 호출. 과도한 Z 재적용 방지(스로틀)."""
        if sys.platform != "win32" or not self._strip_active or self._last_anchor is None:
            return
        now = time.monotonic()
        if (now - self._last_z_apply_mono) < _Z_REAPPLY_MIN_SEC:
            return
        self._last_z_apply_mono = now
        try:
            self._sync_z(
                int(self.winId()), self._last_anchor, set_owner=False, force_z_restack=True,
            )
        except Exception:
            pass

    def _strip_poll_interval_ms(self) -> int:
        m = self._pl
        if getattr(m, "_game_client_power_save_active", False):
            return max(280, int(m.pipela_overlay_tick_ms()))
        try:
            wid = int(self.winId())
        except Exception:
            wid = 0
        base = max(50, int(display_tick_ms_for_window(wid)))
        st = int(getattr(self, "_strip_geom_stable_streak", 0))
        # 기하 안정 시 폴링을 크게 늦춤 — 틱 본문이 80~150ms 나오면 메인 스레드가 설정·타이포와 경쟁
        if st >= 22:
            return min(440, max(base, 340))
        if st >= 15:
            return min(400, max(base, 300))
        if st >= 10:
            return min(360, max(base, 260))
        if st >= 6:
            return min(320, max(base, 220))
        if st >= 3:
            return max(base, 165)
        if st >= 1:
            return max(base, 125)
        return max(base, 98)

    def _sync_strip_poll_interval(self) -> None:
        wanted = self._strip_poll_interval_ms()
        if self._timer.interval() != wanted:
            self._timer.setInterval(wanted)

    def _tick(self) -> None:
        m = self._pl
        if not getattr(m, "running", True):
            self.close()
            return
        if sys.platform != "win32":
            return
        try:
            th0 = m.refresh_target_hwnd_if_needed()
            luh0 = m.refresh_smart_updater_hwnd_if_needed()
            dock_phase = get_ui_dock_phase_from_session(m, th0, luh0)
            try:
                m.pipela_ui_dock_phase = dock_phase
            except Exception:
                pass
            self._sync_strip_launcher_caption_buttons(m, dock_phase=dock_phase)
            self._sync_kill_counter_strip_cluster(th0, dock_phase)
            g_ic = bool(th0 and m.is_window_minimized(th0))
            prev_ic = self._tick_track_game_iconic
            if prev_ic is not None and g_ic != prev_ic and not g_ic:
                self.invalidate_chrome_layout()
            self._tick_track_game_iconic = g_ic
            anchor = resolve_dock_anchor_from_session(m, th0, luh0)
            self._restore_pipela_chrome_if_anchor_back(
                m,
                anchor=anchor,
                th0=th0,
                luh0=luh0,
                dock_phase=dock_phase,
            )
            if not anchor:
                self._bad_geom_streak = 0
                self._move_hidden()
                return
            # 런처 HWND → 게임 HWND 등 앵커 교체 직후: 이전 (x,y,w,h) 시그가 남으면 한 틱 엉망
            try:
                la = self._last_anchor
                if la is not None and int(la) != int(anchor):
                    self._last_geom_sig = None
                    self._geom_compute_cache_key = None
                    self._geom_compute_cache_val = None
                    self._last_strip_geom_prim = None
                    self._strip_tick_geom_sig = None
            except Exception:
                pass
            anchor_int_pre = int(anchor)
            gr = m.get_window_outer_rect_screen(anchor_int_pre)
            cr = m.get_window_rect(anchor_int_pre)
            if (
                not gr
                or not cr
                or not (cr[2] > cr[0])
                or not (cr[3] > cr[1])
            ):
                geom_t = self._compute_strip_geometry(
                    m, anchor, dock_phase=dock_phase,
                )
                self._strip_tick_geom_sig = None
            else:
                qk_gr = _geom_cache_quant_rect(
                    (int(gr[0]), int(gr[1]), int(gr[2]), int(gr[3])),
                )
                qk_cr = _geom_cache_quant_rect(
                    (int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3])),
                )
                ot = int(gr[1])
                ct = int(cr[1])
                raw_title_h = int(ct - ot)
                if raw_title_h >= _MIN_TITLE_FRAME_PX:
                    bar_h = raw_title_h
                else:
                    bar_h = int(_STRIP_FALLBACK_BAR_H)
                bar_h_q = _strip_geom_snap_grid(bar_h, 4)
                prim = (dock_phase, anchor_int_pre, qk_gr, qk_cr, bar_h_q)
                _now_fp = time.monotonic()
                aux_ok = (
                    prim == self._last_strip_geom_prim
                    and (_now_fp - self._strip_geom_aux_mono)
                    < _STRIP_GEOM_AUX_MAX_AGE_SEC
                )
                if (
                    prim == self._strip_tick_geom_sig
                    and aux_ok
                    and self._geom_compute_cache_val is not None
                ):
                    geom_t = self._geom_compute_cache_val
                else:
                    geom_t = self._compute_strip_geometry(
                        m,
                        anchor,
                        dock_phase=dock_phase,
                        gr=gr,
                        cr=cr,
                    )
                    if geom_t is not None:
                        self._strip_tick_geom_sig = prim
                    else:
                        self._strip_tick_geom_sig = None
            if geom_t is None:
                self._bad_geom_streak += 1
                if self._bad_geom_streak >= 24:
                    self._bad_geom_streak = 0
                    self._move_hidden()
                return
            self._bad_geom_streak = 0
            x, y, w, bar_h, anchor_int = geom_t
            wid = int(self.winId())
            geom_sig = (x, y, w, bar_h, anchor_int)
            # 16px 스냅은 DWM/폭 잡음으로 매 틱 geom_changed → SetWindowPos·Z·ShowWindow 폭주(cProfile)
            _gs = 32
            geom_cmp = (
                _strip_geom_snap_grid(x, _gs),
                _strip_geom_snap_grid(y, _gs),
                _strip_geom_snap_grid(w, _gs),
                _strip_geom_snap_grid(bar_h, _gs),
                anchor_int,
            )
            geom_changed = self._last_geom_cmp != geom_cmp
            if geom_changed:
                self._last_geom_cmp = geom_cmp
            anchor_changed = self._last_z_anchor != anchor_int
            now = time.monotonic()
            z_stale = (now - self._last_z_apply_mono) >= _Z_REAPPLY_MIN_SEC

            if geom_changed:
                self._set_strip_rect_from_win32_phys(
                    m, wid, x, y, w, bar_h, anchor_int,
                )
                self._last_geom_sig = geom_sig

            if not self.isVisible():
                self.show()
            lift_tick = (
                geom_changed
                or anchor_changed
                or (now - self._last_win32_lift_mono) >= _STRIP_WIN32_LIFT_MIN_SEC
            )
            if lift_tick:
                self._last_win32_lift_mono = now
                self._win32_lift_strip_visible()

            self._strip_active = True
            self._strip_hidden_applied = False
            self._last_anchor = anchor_int
            if anchor_changed:
                self._last_z_anchor = anchor_int

            z_apply = bool(anchor_changed or z_stale)
            if not z_apply and geom_changed:
                if _STRIP_Z_ON_GEOM_MIN_SEC <= 0.0:
                    z_apply = True
                elif (
                    now - getattr(self, "_last_strip_z_geom_coarse_mono", 0.0)
                ) >= _STRIP_Z_ON_GEOM_MIN_SEC:
                    z_apply = True
            if z_apply:
                self._last_strip_z_geom_coarse_mono = now
                self._last_z_apply_mono = now
                self._sync_z(
                    wid,
                    anchor_int,
                    set_owner=anchor_changed,
                    force_z_restack=z_stale,
                )

            self._update_max_button_icon(
                anchor_int,
                force=bool(anchor_changed or geom_changed),
            )

            if anchor_changed or geom_changed:
                qtm = getattr(m, "_qt_control_main", None)
                if (
                    qtm is not None
                    and not qtm.isHidden()
                    and not getattr(qtm, "_start_tray_only", False)
                ):
                    # 최소화 중에도 Win32 외곽을 맞춰 두면 복구 후 위치가 어긋나지 않음
                    QTimer.singleShot(0, lambda q=qtm: q._dock_to_anchor(force=True))
            res_tick = (
                geom_changed
                or anchor_changed
                or (now - self._last_strip_res_chrome_mono)
                >= _STRIP_RES_CHROME_MIN_SEC
            )
            if res_tick:
                self._last_strip_res_chrome_mono = now
                self._schedule_resolution_chrome()
            if geom_changed:
                self._strip_geom_stable_streak = 0
            else:
                self._strip_geom_stable_streak = min(
                    10_000,
                    int(self._strip_geom_stable_streak) + 1,
                )
            try:
                self._layout_strip_title_cluster_geom()
            except Exception:
                pass
            try:
                self._layout_resolution_strip_label_geom()
            except Exception:
                pass
            if self._btn_kill_counter.isVisible():
                try:
                    self._layout_kill_counter_strip_button_geom()
                except Exception:
                    pass
            self._sync_strip_poll_interval()
        except Exception:
            self._move_hidden()

    def _move_hidden(self) -> None:
        # 앵커 없는 동안 매 틱(_tick → _move_hidden) 호출되며, 이 안에서 SetWindowPos·SetWindowOwner·
        # SetWindowTopmost 3 회씩 폭발한다. 이미 HIDDEN 으로 처리된 상태면 즉시 단락 — DWM 큐가
        # 끊임없이 흔들려 다른 창의 커서 표시까지 깜빡거리게 보이던 증상을 차단한다.
        if getattr(self, "_strip_hidden_applied", False):
            return
        self._strip_active = False
        self._strip_left_phys = None
        self._last_anchor = None
        self._last_geom_sig = None
        self._last_geom_cmp = None
        self._last_z_anchor = None
        self._last_res_chrome_sig = None
        self._last_res_ck = None
        self._last_res_block = None
        self._last_strip_geom_prim = None
        self._strip_geom_aux_mono = 0.0
        self._strip_cached_ch_rect = None
        self._strip_cached_kr = None
        self._strip_tick_geom_sig = None
        self._strip_geom_stable_streak = 0
        self._last_strip_z_geom_coarse_mono = 0.0
        self._resolution_chrome_scheduled = False
        self._geom_compute_cache_key = None
        self._geom_compute_cache_val = None
        try:
            self._lbl_res.hide()
        except Exception:
            pass
        for _lbl in ("_lbl_app_icon", "_lbl_brand", "_lbl_ver"):
            try:
                getattr(self, _lbl).hide()
            except Exception:
                pass
        x, y, w, h = _HIDDEN
        self.setGeometry(x, y, w, h)
        if sys.platform != "win32":
            self._strip_hidden_applied = True
            return
        try:
            wid = int(self.winId())
            clear_docked_chrome_z_stack_state(wid)
            win32_set_window_outer_rect(wid, x, y, w, h)
            win32_set_window_owner(wid, 0)
            win32_set_window_topmost(wid, False)
        except Exception:
            pass
        self._strip_hidden_applied = True
