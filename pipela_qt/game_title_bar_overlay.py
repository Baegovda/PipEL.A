"""게임(또는 런처) 타이틀 영역 상단 바 — Win32 소유 창(owner)으로 앵커보다 위, 전역 TOPMOST 없음."""

from __future__ import annotations

import os
import sys
import time

import win32con
import win32gui

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem, QStyle, QWidget

from pipela_core.display_timing import display_tick_ms_for_window
from pipela_core.paths import UI_ICON_SETTINGS_PATH
from pipela_core.win32_window_ops import (
    dock_outer_rect_touch_client_left,
    is_window_maximized,
    set_window_z_order_directly_above,
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
from pipela_qt.qt_dock_anchor import (
    resolve_dock_anchor_from_session,
    resolve_dock_anchor_hwnd,
)
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.resolution_chrome import (
    STRIP_RESOLUTION_PALETTE,
    apply_resolution_rich_label_fit,
    resolution_block_content_key,
    resolution_block_html,
)
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_vh, scale_px, scaled_design_pt

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
# 해상도 크롬·클라 정렬은 Win32/레이아웃 비용이 있어 기하가 안정일 때 틱당 호출을 피한다.
_STRIP_RES_CHROME_MIN_SEC = 1.45
# 앵커 외곽/클라 양자화가 같을 때 제어·킬 GetWindowRect 를 매 틱 하지 않음(도킹 중엔 50ms 이내 재사용).
_STRIP_GEOM_AUX_MAX_AGE_SEC = 0.072
# 기하 안정 시 제어/킬 GetWindowRect 재조회 간격(더 넓게 → 스트립 틱 ms↓)
_STRIP_GEOM_AUX_MAX_AGE_STABLE_SEC = 0.34
# 부제 엘리드 — 레이아웃 sizeHint 루프는 수 ms~수십 ms; 기하 안 바뀔 때는 스로틀.
_STRIP_SUBTITLE_ELIDE_MIN_SEC = 0.14
# ShowWindow 복원은 매 8ms 틱보다 드물게 — 앵커/기하 변화 시에는 즉시.
_STRIP_WIN32_LIFT_MIN_SEC = 1.25
# 최소화된 창은 Win32 외곽 좌표가 (-32000,) 근처로 나와 스트립이 화면 밖으로 감.
_STRIP_RECT_SANE_MIN = -2000
_STRIP_SUBTITLE_FULL = "EternalCity Helper"
# 게임 타이틀 영역 상단 바 — 브랜드(아이콘 옆 큰 글씨)
_STRIP_BRAND_TITLE = "PIP EL.A"
# 프로그램 제목 / 부제 / 버전 / 해상도 라벨 사이 가로 여백 (논리 px, 루트 pt 스케일).
def _strip_text_cluster_gap_px() -> int:
    return max(scale_px(24), 18)


# 앱 아이콘 ↔ 프로그램 제목(브랜드) 사이.
def _strip_icon_to_brand_gap_px() -> int:
    return max(scale_px(10), 8)


# 버전(v…) ↔ 해상도(클라·템플릿·DPI) 블록 사이 — 부제/버전 간보다 넓게.
def _strip_ver_to_resolution_gap_px() -> int:
    return max(scale_px(72), 40)


def _pipela_game_title_strip_stylesheet() -> str:
    _g = _strip_text_cluster_gap_px()
    _ib = _strip_icon_to_brand_gap_px()
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
        f"  margin: 0 0 0 {_ib}px;"
        f"}}"
        f"QLabel#pipelaStripRes {{"
        f"  background: transparent;"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  padding: 0;"
        f"  margin: 0;"
        f"}}"
        f"QLabel#pipelaStripSub {{"
        f"  color: {T.STRIP_FG_MUTED};"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  font-size: {T.spt(8.125)};"
        f"  font-weight: 500;"
        f"  letter-spacing: {letter_spacing_qss()};"
        f"  background: transparent;"
        f"  padding: 0;"
        f"  margin: 0 0 0 {_g}px;"
        f"}}"
        f"QLabel#pipelaStripVer {{"
        f"  color: {T.STRIP_FG_MUTED};"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  font-size: {T.spt(8.75)};"
        f"  font-weight: 500;"
        f"  background: transparent;"
        f"  padding: 0;"
        f"  margin: 0 0 0 {_g}px;"
        f"}}"
        f"QWidget#pipelaStripResSlot {{"
        f"  background: transparent;"
        f"  border: none;"
        f"  margin: 0;"
        f"  padding: 0;"
        f"}}"
        f"QPushButton#pipelaStripCaptionBtn, QPushButton#pipelaStripCloseBtn {{"
        f"  background: transparent;"
        f"  border: none;"
        f"  border-radius: {T.STRIP_RADIUS_BTN};"
        f"  padding: {qss_pad_vh(2, 6)};"
        f"  min-width: {scale_px(22)}px;"
        f"  min-height: {scale_px(18)}px;"
        f"}}"
        f"QPushButton#pipelaStripCaptionBtn:hover {{ background: {T.STRIP_BTN_HOVER}; }}"
        f"QPushButton#pipelaStripCloseBtn:hover {{ background: {T.STRIP_BTN_HOVER_CLOSE}; }}"
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
        lay.setContentsMargins(scale_px(8), 0, scale_px(6), 0)
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
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._lbl_res.setMinimumWidth(0)
        self._res_fill = QWidget()
        self._res_fill.setObjectName("pipelaStripResSlot")
        self._res_fill.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._res_fill_lay = QHBoxLayout(self._res_fill)
        self._res_fill_lay.setContentsMargins(0, 0, 0, 0)
        self._res_fill_lay.setSpacing(0)
        self._lbl_sub = QLabel(_STRIP_SUBTITLE_FULL)
        self._lbl_sub.setObjectName("pipelaStripSub")
        self._lbl_sub.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._lbl_sub.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        self._lbl_sub.setMinimumWidth(0)
        self._lbl_sub.setWordWrap(False)
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
        self._strip_ver_label_base = self._lbl_ver.text()
        _vr0 = _strip_ver_to_resolution_gap_px()
        # QSS `margin` on QWidget(해상도 슬롯)은 QHBoxLayout 기하에 안정적으로 반영되지 않는다.
        # 버전↔해상도 틈은 `QSpacerItem`으로 고정(스케일 변경 시 `changeSize` 갱신).
        self._spacer_ver_to_res = QSpacerItem(
            _vr0,
            1,
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Minimum,
        )
        lay.addWidget(self._lbl_app_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._lbl_brand, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._lbl_sub, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._lbl_ver, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addItem(self._spacer_ver_to_res)
        # 뒤에 addStretch(1) 를 두면 해상도 라벨이 **최소 폭**만 받아 fit 이 글자를 줄이고, 최소 폭이
        # 다시 줄어드는 **피드백**이 난다. stretch 1 을 라벨에 줘 _res_fill 가로를 쓰게 한다.
        self._res_fill_lay.addWidget(
            self._lbl_res,
            1,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        lay.addWidget(self._res_fill, 1, Qt.AlignmentFlag.AlignVCenter)
        st = self.style()
        _isz = QSize(scale_px(14), scale_px(14))
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
        self._res_align_left_margin: int | None = None
        self._last_strip_res_chrome_mono: float = 0.0
        self._last_win32_lift_mono: float = 0.0
        self._geom_compute_cache_key: object | None = None
        self._geom_compute_cache_val: tuple[int, int, int, int, int] | None = None
        # 픽셀 단위 잡음으로 매 틱 geom_changed → 도킹·타이포 전체 갱신되는 것 완화
        self._last_geom_cmp: tuple[int, int, int, int, int] | None = None
        self._last_res_ck: object | None = None
        self._last_res_block: str | None = None
        self._strip_elide_dock_ph: str | None = None
        self._last_strip_geom_prim: object | None = None
        self._strip_geom_aux_mono: float = 0.0
        self._strip_cached_ch_rect: tuple[int, int, int, int] | None = None
        self._strip_cached_kr: int | None = None
        self._last_res_margin_sync_mono: float = 0.0
        self._strip_tick_geom_sig: object | None = None
        self._resolution_chrome_scheduled: bool = False
        self._resolution_chrome_wants_force_margin: bool = False
        self._strip_geom_stable_streak: int = 0
        self._last_subtitle_elide_mono: float = 0.0
        self._last_subtitle_elide_sig: tuple[int, int] | None = None
        self._last_win32_strip_rect_phys: tuple[int, int, int, int, int] | None = None
        self._z_stack_key: tuple[int, int, int] | None = None  # (anchor, strip_wid, ov_wid|0) — Z만 동일면 SetWindowPos 생략

    def _set_res_fill_client_align_margin(self, m: int) -> None:
        """해상도 라벨을 앵커 창 **클라이언트 좌측**(화면)에 맞추기 위한 내부 왼쪽 여백(논리 px, 음수 가능)."""
        if self._res_align_left_margin is not None and m == self._res_align_left_margin:
            return
        self._res_align_left_margin = m
        lay = getattr(self, "_res_fill_lay", None)
        if lay is not None:
            lay.setContentsMargins(m, 0, 0, 0)

    def _sync_resolution_text_to_client_left(self) -> None:
        """스트립 왼쪽(Win32)과 앵커 **클라이언트** 왼쪽의 차이만큼 해상도 블록 안쪽 여백을 맞춘다."""
        if sys.platform != "win32" or not getattr(self, "_strip_active", False):
            self._set_res_fill_client_align_margin(0)
            return
        m = self._pl
        a = self._last_anchor
        sl = self._strip_left_phys
        if not a or sl is None:
            self._set_res_fill_client_align_margin(0)
            return
        try:
            cr = m.get_window_rect(int(a))
            if not cr:
                self._set_res_fill_client_align_margin(0)
                return
            cl_phys = int(cr[0])
        except Exception:
            self._set_res_fill_client_align_margin(0)
            return
        try:
            sc = float(win32_dpi_scale_for_hwnd(m, int(a)))
        except Exception:
            sc = 1.0
        if sc <= 0.01:
            sc = 1.0
        delta_log = (cl_phys - int(sl)) / sc
        try:
            u = float(self._res_fill.x())
        except Exception:
            return
        m_left = int(round(delta_log - u))
        m_left = max(-3000, min(3000, m_left))
        self._set_res_fill_client_align_margin(m_left)

    def _update_strip_resolution_chrome(self, *, force_margin_sync: bool = False) -> None:
        """게임/런처 타이틀 바 안 — 클라·템플릿·DPI 한 줄(제어창에서 이전)."""
        m = self._pl
        lbl = self._lbl_res
        # lbl.width() 는 레이아웃·최대폭 영향으로 틱마다 줄어 `apply_resolution` 이 글자를 계속 축소할 수 있음.
        # _res_fill (가변 영역) 폭 = 실제 쓸 수 있는 가로(논리 px).
        try:
            aw = int(self._res_fill.width())
        except Exception:
            aw = 0
        if aw < 40:
            aw = max(48, int(self.width()) * 2 // 5)
        # 1~2px 레이아웃 잡음마다 QTextDocument 피팅 전체가 도는 것 방지
        aw_q = max(48, (int(aw) // 6) * 6)
        try:
            ck = resolution_block_content_key(m)
            if ck != self._last_res_ck or not self._last_res_block:
                self._last_res_ck = ck
                self._last_res_block = resolution_block_html(m, STRIP_RESOLUTION_PALETTE)
            block = self._last_res_block
            if not block:
                if force_margin_sync or (
                    time.monotonic() - self._last_res_margin_sync_mono >= 0.22
                ):
                    self._last_res_margin_sync_mono = time.monotonic()
                    self._sync_resolution_text_to_client_left()
                return
            sig = (block, aw_q)
            if sig != self._last_res_chrome_sig:
                apply_resolution_rich_label_fit(
                    lbl,
                    m,
                    float(aw_q),
                    palette=STRIP_RESOLUTION_PALETTE,
                    design_scale=0.66,
                    block_html=block,
                )
                self._last_res_chrome_sig = sig
        except Exception:
            pass
        if force_margin_sync or (
            time.monotonic() - self._last_res_margin_sync_mono >= 0.22
        ):
            self._last_res_margin_sync_mono = time.monotonic()
            self._sync_resolution_text_to_client_left()

    def _schedule_resolution_chrome(self, *, force_margin_sync: bool) -> None:
        """해상도 리치 라벨·클라 여백 — 다음 이벤트 루프로 미루어 `title_strip.tick` 본문을 짧게 유지."""
        self._resolution_chrome_wants_force_margin = (
            self._resolution_chrome_wants_force_margin or bool(force_margin_sync)
        )
        if self._resolution_chrome_scheduled:
            return
        self._resolution_chrome_scheduled = True
        QTimer.singleShot(0, self._run_deferred_resolution_chrome)

    def _run_deferred_resolution_chrome(self) -> None:
        self._resolution_chrome_scheduled = False
        fm = self._resolution_chrome_wants_force_margin
        self._resolution_chrome_wants_force_margin = False
        try:
            self._update_strip_resolution_chrome(force_margin_sync=fm)
        except Exception:
            pass

    def _apply_strip_app_icon_pixmap(self) -> None:
        lbl = getattr(self, "_lbl_app_icon", None)
        if lbl is None:
            return
        _cell = max(14, min(26, scale_px(18)))
        _inset = max(1, scale_px(2))
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
        _ss = _pipela_game_title_strip_stylesheet()
        if _ss != getattr(self, "_last_strip_stylesheet", None):
            self._last_strip_stylesheet = _ss
            self.setStyleSheet(_ss)
        rl = getattr(self, "_root_lay", None)
        if rl is not None:
            rl.setContentsMargins(scale_px(8), 0, scale_px(6), 0)
            rl.setSpacing(0)
        spc = getattr(self, "_spacer_ver_to_res", None)
        if spc is not None:
            _vrn = _strip_ver_to_resolution_gap_px()
            spc.changeSize(
                _vrn,
                1,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Minimum,
            )
            if rl is not None:
                rl.invalidate()
        self._apply_strip_app_icon_pixmap()
        iz = max(10, min(22, scale_px(14)))
        _isz = QSize(iz, iz)
        for btn in (self._btn_min, self._btn_max, self._btn_launcher_settings, self._btn_close):
            btn.setIconSize(_isz)
        rf = app_default_qfont(10, QFont.Weight.Medium)
        rf.setPointSizeF(max(8.0, min(16.0, scaled_design_pt(9.5))))
        self._lbl_res.setFont(rf)
        self._last_res_chrome_sig = None
        try:
            delattr(self._lbl_res, "_pipela_res_fit_cache_k")
        except AttributeError:
            pass
        self._elide_subtitle_if_needed()
        self._update_strip_resolution_chrome(force_margin_sync=True)

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
        self._elide_subtitle_if_needed()
        self._update_strip_resolution_chrome(force_margin_sync=True)

    def _subtitle_elide_cap_px(self) -> int:
        """부제 최대 폭 — 해상도·창 버튼 영역을 남긴다."""
        try:
            rl = self._root_lay
            _mg = rl.contentsMargins()
            ml, mr = int(_mg.left()), int(_mg.right())
            sp = int(rl.spacing())
            _g = _strip_text_cluster_gap_px()
            _vr = _strip_ver_to_resolution_gap_px()
            inner = max(0, int(self.width()) - ml - mr)
            used = 0
            # 부제(_lbl_sub)는 이 cap으로 폭이 정해지므로 used에 넣으면 가로를 이중 차감해
            # (특히 런처처럼 스트립이 좁을 때) 말줄임이 과해진다.
            for w in (
                self._lbl_app_icon,
                self._lbl_brand,
                self._lbl_ver,
                self._btn_min,
                self._btn_max,
                self._btn_launcher_settings,
                self._btn_close,
            ):
                if w is not None and w.isVisible():
                    used += int(w.sizeHint().width()) + sp
            used += sp  # 브랜드↔부제↔버전 사이: 루프만으로는 부제 양쪽 gap 하나가 빠짐
            used += sp * 2
            # QSpacerItem(ver↔해상도) = _vr. 부제/버전 QSS margin-left(_g)는 sizeHint 쪽이 이미 흡수하는 경우가 많아
            # 2*_g 는 힌트만 보강(부제 엘리드 상한).
            used += 2 * _g + _vr
            res_min = max(scale_px(72), scale_px(56))
            try:
                pl = self._pl
                dp = getattr(pl, "pipela_ui_dock_phase", None)
                if dp is None:
                    dp = get_ui_dock_phase(pl)
                if dp == UI_DOCK_PHASE_LAUNCHER:
                    # 런처 타이틀 폭이 좁음 — 해상도 블록은 fit으로 더 줄일 수 있어 부제에 조금 더 양보
                    res_min = max(scale_px(52), scale_px(44))
            except Exception:
                pass
            cap = inner - used - res_min
            return max(scale_px(40), cap)
        except Exception:
            return scale_px(120)

    def _elide_subtitle_if_needed(self) -> None:
        try:
            cap = int(self._subtitle_elide_cap_px())
            if cap < 24:
                return
            _sig = (int(self.width()), cap)
            if _sig == self._last_subtitle_elide_sig:
                return
            self._last_subtitle_elide_sig = _sig
            self._lbl_sub.setMaximumWidth(cap)
            fm = self._lbl_sub.fontMetrics()
            self._lbl_sub.setText(
                fm.elidedText(
                    _STRIP_SUBTITLE_FULL,
                    Qt.TextElideMode.ElideRight,
                    cap,
                ),
            )
        except Exception:
            pass

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
        self._last_subtitle_elide_sig = None
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
            if _win32_outer_left_top_sane_for_strip(gl, gt):
                left_x = int(gl)
                used_control_hwnd_for_left = True
        if not used_control_hwnd_for_left and sys.platform == "win32":
            try:
                scale = win32_dpi_scale_for_hwnd(m, int(anchor_int))
                dock_w_log, _dh0 = get_dock_panel_wh(m)
                dock_w_log = max(8, int(dock_w_log))
                fw_phys = max(8, int(round(dock_w_log * scale)))
                fh_phys = max(1, int(cr[3] - cr[1]))
                y_phys = int(cr[1])
                snap = int(cr[0]) if (cr[2] > cr[0]) else int(ol)
                x_phys, _yp, _wfp, _hfp = dock_outer_rect_touch_client_left(
                    int(anchor_int),
                    snap,
                    y_phys,
                    fw_phys,
                    fh_phys,
                )
                if _win32_outer_left_top_sane_for_strip(int(x_phys), int(ot)):
                    left_x = int(x_phys)
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
        if sys.platform != "win32":
            return
        now = time.monotonic()
        ah = int(anchor)
        if not force:
            if (
                getattr(self, "_strip_max_icon_last_anchor", None) == ah
                and (now - getattr(self, "_strip_max_icon_last_mono", 0.0)) < 0.35
            ):
                return
        self._strip_max_icon_last_mono = now
        self._strip_max_icon_last_anchor = ah
        try:
            st = self.style()
            if is_window_maximized(anchor):
                self._btn_max.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
                self._btn_max.setToolTip("창 크기 복원")
            else:
                self._btn_max.setIcon(st.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
                self._btn_max.setToolTip("최대화")
        except Exception:
            pass

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

    def _sync_strip_launcher_caption_buttons(
        self,
        m,
        *,
        dock_phase: str | None = None,
    ) -> None:
        """런처 페이즈: 최대화 대신 설정 버튼 — 가벼움(부제 엘리드는 별도)."""
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
                self._btn_max.show()
        except Exception:
            pass

    def _sync_strip_max_vs_settings_buttons(
        self,
        m,
        *,
        dock_phase: str | None = None,
        subtitle_layout_dirty: bool = True,
    ) -> None:
        """런처 캡션 버튼 + (선택) 부제 엘리드 — 문서·호환용 래퍼."""
        self._sync_strip_launcher_caption_buttons(m, dock_phase=dock_phase)
        if subtitle_layout_dirty:
            try:
                self._elide_subtitle_if_needed()
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

    def _apply_z_stack_relative(self, wid: int, anchor: int, *, force: bool = False) -> None:
        """게임 < 오버레이 < 타이틀 바.
        `force` 가 아니고 (앵커, 스트립, 오버레이) 키가 직전과 같으면 중복 `SetWindowPos` 생략.
        `force` 는 주기 `z_stale`·`reassert_z_order` 시 외부가 Z를 가져갔을 수 있을 때.
        """
        ah = int(anchor)
        w = int(wid)
        m = self._pl
        ov = getattr(m, "_qt_game_overlay", None)
        if ov is not None:
            try:
                oid = int(ov.winId())
                if win32gui.IsWindow(oid):
                    key = (ah, w, oid)
                    if not force and key == self._z_stack_key:
                        return
                    set_window_z_order_directly_above(oid, ah)
                    set_window_z_order_directly_above(w, oid)
                    self._z_stack_key = key
                    return
            except Exception:
                pass
        key = (ah, w, 0)
        if not force and key == self._z_stack_key:
            return
        set_window_z_order_directly_above(w, ah)
        self._z_stack_key = key

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
        if set_owner:
            win32_set_window_owner(wid, int(anchor))
        win32_set_window_topmost(wid, False)
        self._apply_z_stack_relative(wid, anchor, force=force_z_restack)

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
            phase_ch = self._strip_elide_dock_ph != dock_phase
            subtitle_dirty = (
                geom_changed or anchor_changed or phase_ch
            )
            if subtitle_dirty:
                _elide_now = (
                    geom_changed
                    or anchor_changed
                    or phase_ch
                    or (
                        now - self._last_subtitle_elide_mono
                        >= _STRIP_SUBTITLE_ELIDE_MIN_SEC
                    )
                )
                if _elide_now:
                    self._last_subtitle_elide_mono = now
                    try:
                        self._elide_subtitle_if_needed()
                    except Exception:
                        pass
            self._strip_elide_dock_ph = dock_phase
            res_tick = (
                geom_changed
                or anchor_changed
                or (now - self._last_strip_res_chrome_mono)
                >= _STRIP_RES_CHROME_MIN_SEC
            )
            if res_tick:
                self._last_strip_res_chrome_mono = now
                self._schedule_resolution_chrome(
                    force_margin_sync=bool(
                        geom_changed or anchor_changed,
                    ),
                )
            if geom_changed:
                self._strip_geom_stable_streak = 0
            else:
                self._strip_geom_stable_streak = min(
                    10_000,
                    int(self._strip_geom_stable_streak) + 1,
                )
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
        self._z_stack_key = None
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
        self._resolution_chrome_wants_force_margin = False
        self._geom_compute_cache_key = None
        self._geom_compute_cache_val = None
        self._set_res_fill_client_align_margin(0)
        x, y, w, h = _HIDDEN
        self.setGeometry(x, y, w, h)
        if sys.platform != "win32":
            self._strip_hidden_applied = True
            return
        try:
            wid = int(self.winId())
            win32_set_window_outer_rect(wid, x, y, w, h)
            win32_set_window_owner(wid, 0)
            win32_set_window_topmost(wid, False)
        except Exception:
            pass
        self._strip_hidden_applied = True
