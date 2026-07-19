"""킬 카운터 패널 — 현재 킬·통계·랩·목표·캘린더(일별)."""

from __future__ import annotations

import html
import math
import time

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QDate,
    QPropertyAnimation,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsColorizeEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pipela_core.display_timing import display_tick_ms
from pipela_core.ui_fonts import FONT_QT_FAMILY_STACK
from pipela_core.kill_counter_tier_colors import kill_counter_tier_fg_hex_for_rank_title
from pipela_core.registry_config_snapshot import sync_registry_snapshot_from_module
from pipela_qt import theme as T
from pipela_qt.card_popup_shell import confirm_card_dialog
from pipela_qt.panels.kill_counter_bar_chart import KillCounterBucketChartPane
from pipela_qt.panels.kill_counter_daily_calendar import KillCounterDailyCalendar
from pipela_qt.panels.kill_counter_tier_table_dialog import show_kill_counter_tier_table_dialog
from pipela_qt.panels.settings_chrome import (
    kill_counter_permanent_wipe_button_qss,
    kill_counter_session_reset_button_qss,
    panel_primary_button_qss,
    panel_secondary_button_qss,
    panel_template_toolbar_button_qss,
)
from pipela_qt.qt_capture import attach_kill_counter_region_toolbar
from pipela_qt.kill_counter_viewport_metrics import (
    kc_viewport_height_scale,
    kc_viewport_height_scale_from_widget_chain,
    kc_viewport_px_h,
    kc_viewport_px_v,
    kc_viewport_spt_v,
    kc_viewport_wh_valid,
    kc_viewport_width_scale,
)
from pipela_qt.kill_counter_viewport_typography import (
    LAP_ELAPSED_BENCHMARK_TIME_PART,
    elapsed_eff_pt_clip,
    elapsed_eff_pt_css,
    gauge_overlay_pct_pts,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_typography import letter_spacing_qss


def _lap_elapsed_rich_ideal_width_px(html: str) -> float:
    doc = QTextDocument()
    doc.setDocumentMargin(0.0)
    doc.setHtml(html)
    iw = doc.idealWidth()
    try:
        w = float(iw)
    except Exception:
        w = float(doc.size().width())
    return max(1.0, w)


def _lap_right_frame_qss() -> str:
    """스톱워치 프레임 — 틸 하이라이트 + 유리 느낌 그라데이션."""
    g = (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(61, 212, 201, 0.11), stop:0.42 {T.SURFACE}, stop:1 {T.PANEL_BG})"
    )
    return (
        f"QFrame#pipelaKcLapRight {{"
        f"  background: {g};"
        f"  border: 1px solid {T.BORDER_HAIR};"
        f"  border-left: 3px solid {T.ACCENT};"
        f"  border-radius: {T.RADIUS_SM};"
        f"}}"
    )


def _lap_right_elapsed_rich_html(
    time_part: str, fg_time: str, pt_lab_eff: float, pt_time_eff: float,
) -> str:
    """경과(작은 캡션) + 시간(굵·탭딱 느낌) — time_part 이스케이프, pt*_eff 는 kc_viewport_spt 와 같은 하한 규칙."""
    t = html.escape((time_part or "").strip() or "—")
    fe = T.FONT_CSS_UI
    ll = T.METER_LABEL
    fs_lab = elapsed_eff_pt_css(pt_lab_eff)
    fs_t = elapsed_eff_pt_css(pt_time_eff)
    # line-height 여유 — 디센더/한글 하단 잘림 완화
    # NOTE: Qt RichText 렌더링은 글자가 위젯 경계에 붙으면 1~몇 px 잘리는 경우가 있어
    #       상/하 padding + box-sizing으로 “그리는 캔버스”를 안정화한다.
    return (
        f"<div style='"
        f"display:block; width:100%; box-sizing:border-box;"
        f"padding:6px 0 6px 0;"
        f"text-align:center; line-height:1.42;'>"
        f"<span style='color:{ll}; font-size:{fs_lab}; font-weight:700; font-family:{fe};"
        f" letter-spacing:0.04em;'>경과</span>"
        f"<span style='color:{T.FG_DIM};'>&nbsp;&nbsp;</span>"
        f"<span style='color:{fg_time}; font-size:{fs_t}; font-weight:800; font-family:{fe};"
        f" letter-spacing:0.02em; font-variant-numeric:tabular-nums;'>"
        f"{t}</span></div>"
    )


def _lap_right_elapsed_rich_html_compact(
    time_part: str, fg_time: str, pt_time_eff: float,
) -> str:
    """아주 좁을 때(폭 부족) 폴백: 시간만 표기."""
    t = html.escape((time_part or "").strip() or "—")
    fe = T.FONT_CSS_UI
    fs_t = elapsed_eff_pt_css(pt_time_eff)
    return (
        f"<div style='"
        f"display:block; width:100%; box-sizing:border-box;"
        f"padding:6px 0 6px 0;"
        f"text-align:center; line-height:1.35;'>"
        f"<span style='color:{fg_time}; font-size:{fs_t}; font-weight:800; font-family:{fe};"
        f" letter-spacing:0.02em; font-variant-numeric:tabular-nums;'>"
        f"{t}</span></div>"
    )


def _goal_transition_line_rich_html(
    line: str, *, muted_fallback: bool,
) -> str:
    """«현재호칭 → 다음호칭» 한 줄 — 등급 구간 표와 동일한 호칭 색(RichText HTML)."""
    ff = T.FONT_CSS_UI
    fw = 500
    fallback = T.FG_MUTED if muted_fallback else T.FG
    arrow_c = T.FG_MUTED
    sep = " → "

    def span_fragment(text: str, color: str) -> str:
        return (
            f'<span style="color:{color};font-weight:{fw};font-family:{ff};">'
            f"{html.escape(text)}</span>"
        )

    if sep not in line:
        return span_fragment(line, fallback)

    left, right = line.split(sep, 1)
    left, right = left.strip(), right.strip()
    h_l = kill_counter_tier_fg_hex_for_rank_title(left)
    c_l = h_l if h_l else fallback
    if right == "—":
        c_r = T.FG_MUTED
    elif right == "달성":
        c_r = T.ACCENT
    else:
        h_r = kill_counter_tier_fg_hex_for_rank_title(right)
        c_r = h_r if h_r else fallback
    return (
        f"{span_fragment(left, c_l)}"
        f'<span style="color:{arrow_c};font-weight:{fw};font-family:{ff};"> → </span>'
        f"{span_fragment(right, c_r)}"
    )


def _goal_gauge_text_on_accent() -> str:
    """ACCENT 청록 청크 위에 올릴 글자색(담백한 대비)."""
    return "#061312"


def _goal_gauge_hex_to_qcolor(hex_s: str) -> QColor:
    s = (hex_s or "").strip().lstrip("#")
    if len(s) >= 6:
        try:
            return QColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return QColor(61, 212, 201)


class _GoalProgressGauge(QWidget):
    """진행률 바 + 내부 오른쪽 정렬 n%% — 애니메이션·유리 질감 페인트."""

    __slots__ = ("_anim", "_display_pct", "_pct", "_radius_px", "_raw_pct")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pct = QLabel(self)
        self._pct.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._pct.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pct.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self._raw_pct: float | None = None
        self._display_pct: float = 0.0
        vs = kc_viewport_height_scale_from_widget_chain(self)
        self._radius_px: int = kc_viewport_px_v(vs, 4, lo=3, hi=80)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(780)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)
        self.refresh_geometry_and_style()

    def _on_anim_value(self, v: object) -> None:
        try:
            self._display_pct = float(v)
        except (TypeError, ValueError):
            self._display_pct = 0.0
        self.update()
        self._update_label_contrast()

    def refresh_geometry_and_style(self) -> None:
        vs = kc_viewport_height_scale_from_widget_chain(self)
        h = kc_viewport_px_v(vs, 22, lo=14, hi=120)
        self.setMinimumHeight(h)
        self._radius_px = kc_viewport_px_v(vs, 4, lo=3, hi=80)
        self._update_label_contrast()

    def set_pct(self, pct: float | None) -> None:
        if self._anim.state() == QAbstractAnimation.State.Running:
            try:
                start = float(self._anim.currentValue())
            except (TypeError, ValueError):
                start = self._display_pct
        else:
            start = self._display_pct
        self._anim.stop()

        self._raw_pct = pct
        if pct is None:
            end = 0.0
            self._pct.setText("—")
        else:
            end = max(0.0, min(100.0, float(pct)))
            self._pct.setText(f"{int(round(end))}%")

        if abs(start - end) < 0.05:
            self._display_pct = end
            self.update()
            self._update_label_contrast()
            return

        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = max(1, self.width()), max(1, self.height())
        r = float(self._radius_px)
        path_track = QPainterPath()
        path_track.addRoundedRect(0.0, 0.0, float(w), float(h), r, r)

        g_track = QLinearGradient(0.0, 0.0, 0.0, float(h))
        base = QColor(T.PANEL_BG)
        hi = QColor(255, 255, 255, 22)
        lo = QColor(0, 0, 0, 38)
        g_track.setColorAt(0.0, hi)
        g_track.setColorAt(0.35, base)
        g_track.setColorAt(1.0, lo)
        p.fillPath(path_track, g_track)
        vs = kc_viewport_height_scale_from_widget_chain(self)
        p.setPen(QPen(QColor(T.BORDER_HAIR), max(1, kc_viewport_px_v(vs, 1, lo=1, hi=6) // 2 or 1)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path_track)

        if self._raw_pct is None:
            p.end()
            return

        fill_ratio = max(0.0, min(1.0, self._display_pct / 100.0))
        fill_w = float(w) * fill_ratio
        if fill_w < 0.5:
            p.end()
            return

        clip_r = QPainterPath()
        clip_r.addRoundedRect(0.0, 0.0, float(w), float(h), r, r)
        p.setClipPath(clip_r)

        fw = max(fill_w, min(r * 2.0, float(w)))
        path_fill = QPainterPath()
        path_fill.addRoundedRect(0.0, 0.0, fw, float(h), r, r)

        ac = _goal_gauge_hex_to_qcolor(T.ACCENT)
        top = QColor(
            min(255, ac.red() + 52),
            min(255, ac.green() + 58),
            min(255, ac.blue() + 48),
        )
        mid = QColor(ac)
        bot = QColor(
            max(0, ac.red() - 32),
            max(0, ac.green() - 36),
            max(0, ac.blue() - 28),
        )
        g_fill = QLinearGradient(0.0, 0.0, 0.0, float(h))
        g_fill.setColorAt(0.0, top)
        g_fill.setColorAt(0.42, mid)
        g_fill.setColorAt(1.0, bot)
        p.fillPath(path_fill, g_fill)

        gloss = QLinearGradient(0.0, 0.0, 0.0, float(h) * 0.62)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 118))
        gloss.setColorAt(0.22, QColor(255, 255, 255, 38))
        gloss.setColorAt(0.55, QColor(255, 255, 255, 0))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path_fill, gloss)

        edge = QLinearGradient(0.0, 0.0, float(fw), 0.0)
        edge.setColorAt(0.0, QColor(255, 255, 255, 0))
        edge.setColorAt(0.88, QColor(255, 255, 255, 0))
        edge.setColorAt(1.0, QColor(255, 255, 255, 55))
        p.fillPath(path_fill, edge)

        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(int(r * 0.35), 1, int(max(0.0, fill_w - r * 0.35)), 1)
        p.end()

    def _update_label_contrast(self) -> None:
        vs = kc_viewport_height_scale_from_widget_chain(self)
        pad = kc_viewport_px_v(vs, 6, lo=4, hi=96)
        txt = self._pct.text() or "—"
        w = max(1, int(self.width()))
        hi, _lk = gauge_overlay_pct_pts(vs)
        f = QFont()
        f.setFamilies(list(FONT_QT_FAMILY_STACK))
        f.setWeight(QFont.Weight.ExtraBold)
        f.setPointSizeF(float(hi))
        self._pct.setFont(f)
        try:
            tw = int(QFontMetrics(self._pct.font()).horizontalAdvance(txt))
        except Exception:
            tw = w // 2
        text_left = float(w - pad - tw)
        fill_w = (
            (float(w) * float(self._display_pct)) / 100.0
            if self._raw_pct is not None
            else 0.0
        )
        on_accent = fill_w >= text_left - float(kc_viewport_px_v(vs, 2, lo=1, hi=24))
        if self._raw_pct is None:
            col = T.FG_MUTED
        elif on_accent:
            col = _goal_gauge_text_on_accent()
        else:
            col = T.FG
        self._pct.setStyleSheet(
            f"color: {col}; background: transparent; padding: 0 {pad}px 0 0;",
        )

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._pct.setGeometry(0, 0, self.width(), self.height())
        self._update_label_contrast()


class _GoalTierTableLinkLabel(QLabel):
    """호칭 전환 한 줄 — 클릭 시 등급 구간 표."""

    __slots__ = ("_cb",)

    def __init__(self, cb, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cb = cb
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("클릭하면 등급 구간 표")

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._cb()
            e.accept()
            return
        super().mousePressEvent(e)


class KillCounterPanel(QWidget):
    """킬 카운터 본문 — 창 크기 비례로 내부 간격·타이포를 다시 적용."""

    # ===== 중요도 기반 타이포 토큰(단일 소스: 패널) =====
    # design-pt 기준이며 실제 pt는 `_kc_spt()`로 iso 스케일 적용됨.
    KC_PT_HERO = 32.0          # Tier0: 헤더 메인 값(킬)
    KC_PT_SECTION_TITLE = 15.0 # Tier3: 섹션 타이틀
    KC_PT_PRIMARY = 22.0       # Tier1: 핵심 값(랩 누적 총합/경과시간)
    KC_PT_GOAL_LINE = 11.0     # Tier1.5: 목표 라벨(남은 킬/남은 시간) — KC_PT_PRIMARY 의 절반
    KC_PT_SECONDARY = 16.0     # Tier2: 타일 값(최근 누적/랩 타일)
    KC_PT_LABEL = 10.0         # Tier4: 라벨/캡션
    KC_PT_BUTTON = 10.5        # Tier5: 버튼

    def _kc_vs(self) -> float:
        return kc_viewport_height_scale(self._kc_vw, self._kc_vh)

    def _kc_ws(self) -> float:
        return kc_viewport_width_scale(self._kc_vw, self._kc_vh)

    def _kc_px_v(self, design_px: float, *, lo: int = 1, hi: int = 320) -> int:
        return kc_viewport_px_v(self._kc_vs(), float(design_px), lo=lo, hi=hi)

    def _kc_px_h(self, design_px: float, *, lo: int = 1, hi: int = 320) -> int:
        return kc_viewport_px_h(self._kc_ws(), float(design_px), lo=lo, hi=hi)

    def _kc_spt(self, design_pt: float, *, clamp_min_pt: bool = True) -> str:
        return kc_viewport_spt_v(self._kc_vs(), float(design_pt), clamp_min_pt=clamp_min_pt)

    def _lap_right_caption_face_qss(self) -> str:
        ch = float(self.KC_PT_LABEL)
        pt = int(self._kc_px_v(2, lo=1, hi=48))
        pb = int(self._kc_px_v(2, lo=1, hi=48))
        return (
            f"color: {T.METER_LABEL}; letter-spacing: 0.11em; background: transparent;"
            f" font-size: {self._kc_spt(ch)}; font-weight: 700; font-family: {T.FONT_CSS_UI};"
            f" padding-top: {pt}px; padding-bottom: {pb}px;"
        )

    def _lap_right_kills_face_qss(self) -> str:
        hk = float(self.KC_PT_PRIMARY)
        pt = int(self._kc_px_v(2, lo=1, hi=48))
        pb = int(self._kc_px_v(2, lo=1, hi=48))
        return (
            f"color: {T.ACCENT}; letter-spacing: -0.04em; background: transparent;"
            f" font-size: {self._kc_spt(hk)}; font-weight: 800; font-family: {T.FONT_CSS_UI};"
            f" padding-top: {pt}px; padding-bottom: {pb}px;"
        )

    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._kc_vw, self._kc_vh = kc_viewport_wh_valid(440, 740)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()
        self._resize_typo_timer = QTimer(self)
        self._resize_typo_timer.setSingleShot(True)
        self._resize_typo_timer.setInterval(48)
        self._resize_typo_timer.timeout.connect(self._on_resize_typo_timer)
        self._slow_tick_mono: float = 0.0
        self._recent_roll_last_display: list[str | None] = [None, None, None, None]
        self._kc_stat_tile_vboxes: list[QVBoxLayout] = []
        self._kc_lap_cell_vboxes: list[QVBoxLayout] = []

        root = QVBoxLayout(self)
        self._root = root
        # 비율 레이아웃: 섹션 컨테이너 고정 높이로 계산하므로 루트 spacing은 0.
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # —— 섹션 컨테이너(비율 고정) ——
        self._sec_header = QWidget()
        self._sec_graph = QWidget()
        self._sec_recent = QWidget()
        self._sec_goal = QWidget()
        self._sec_lap = QWidget()
        self._sec_calendar = QWidget()
        self._sec_bottom = QWidget()

        for w in (
            self._sec_header,
            self._sec_graph,
            self._sec_recent,
            self._sec_goal,
            self._sec_lap,
            self._sec_calendar,
            self._sec_bottom,
        ):
            w.setContentsMargins(0, 0, 0, 0)
            root.addWidget(w, 0)

        # —— Header (ratio=1): 히어로 숫자 ——
        # Kill Counter 라벨·등급 아이콘은 게임 타이틀 스트립
        header_outer = QVBoxLayout(self._sec_header)
        header_outer.setContentsMargins(0, 0, 0, 0)
        header_outer.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(self._kc_px_h(8, lo=4, hi=144))
        self._prog_big = QLabel("—")
        self._prog_big.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        self._typo.add(self._refresh_prog_big_hero_style)
        head.addStretch(1)
        head.addWidget(
            self._prog_big,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        head.addStretch(1)
        header_outer.addLayout(head)
        self._refresh_prog_big_hero_style()

        # —— Graph (ratio=2) ——
        graph_outer = QVBoxLayout(self._sec_graph)
        graph_outer.setContentsMargins(0, 0, 0, 0)
        graph_outer.setSpacing(0)
        graph_outer.addWidget(self._section_rule("그래프"))
        graph_fr = self._make_card()
        g_inner = QVBoxLayout(graph_fr)
        g_inner.setContentsMargins(self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112), self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112))
        g_inner.setSpacing(self._kc_px_v(4, lo=2, hi=96))
        self._kc_bucket_chart = KillCounterBucketChartPane(pipela_mod, graph_fr)
        g_inner.addWidget(self._kc_bucket_chart, 1)
        graph_outer.addWidget(graph_fr, 1)

        # —— Recent roll (ratio=2) ——
        recent_outer = QVBoxLayout(self._sec_recent)
        recent_outer.setContentsMargins(0, 0, 0, 0)
        recent_outer.setSpacing(0)
        recent_outer.addWidget(self._section_rule("최근 누적"))
        roll_fr = self._make_card()
        rg = QGridLayout(roll_fr)
        rg.setContentsMargins(self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112), self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112))
        rg.setHorizontalSpacing(self._kc_px_h(6, lo=3, hi=112))
        rg.setVerticalSpacing(self._kc_px_v(4, lo=2, hi=96))
        self._r1, w1 = self._stat_pair("1시간", rg, 0, 0)
        self._r6, w2 = self._stat_pair("6시간", rg, 0, 1)
        self._r24, w3 = self._stat_pair("24시간", rg, 1, 0)
        self._rkph, w4 = self._stat_pair("1H 평균", rg, 1, 1)
        self._recent_roll_val_labels = (
            self._r1,
            self._r6,
            self._r24,
            self._rkph,
        )
        for t in (w1, w2, w3, w4):
            self._typo.add(t)
        recent_outer.addWidget(roll_fr, 1)

        # —— Goal (ratio=2) ——
        goal_outer = QVBoxLayout(self._sec_goal)
        goal_outer.setContentsMargins(0, 0, 0, 0)
        goal_outer.setSpacing(0)
        goal_outer.addWidget(self._section_rule("다음 구간까지"))
        goal_fr = self._make_card()
        gg = QGridLayout(goal_fr)
        gg.setContentsMargins(self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112), self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112))
        gg.setHorizontalSpacing(self._kc_px_h(10, lo=5, hi=176))
        gg.setVerticalSpacing(self._kc_px_v(2, lo=1, hi=64))
        c1 = QLabel("다음")
        c1.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {self._kc_spt(self.KC_PT_LABEL)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        c2 = QLabel("킬작 졸업")
        _choin_hex = kill_counter_tier_fg_hex_for_rank_title("초인") or T.FG_MUTED
        c2.setStyleSheet(
            f"color: {_choin_hex}; font-size: {self._kc_spt(self.KC_PT_LABEL)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(lambda w=c1: w.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {self._kc_spt(self.KC_PT_LABEL)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        ))
        self._typo.add(lambda w=c2: w.setStyleSheet(
            f"color: {_choin_hex}; font-size: {self._kc_spt(self.KC_PT_LABEL)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        ))
        gg.addWidget(c1, 0, 0)
        gg.addWidget(c2, 0, 1)
        _g_font_ss_fn = (
            lambda: f"font-size: {self._kc_spt(self.KC_PT_LABEL)}; font-weight: 500; font-family: {T.FONT_CSS_UI};"
        )
        self._gtr = _GoalTierTableLinkLabel(self._on_tier_table_clicked, self)
        self._gtr.setWordWrap(False)
        self._gtr.setTextFormat(Qt.TextFormat.RichText)
        self._gtr.setStyleSheet(_g_font_ss_fn())
        self._typo.add(lambda w=self._gtr: w.setStyleSheet(_g_font_ss_fn()))
        gg.addWidget(self._gtr, 1, 0)
        self._grem = QLabel("")
        self._geta = QLabel("")
        self._gtier_g = _GoalProgressGauge(self)
        for row_i, lb in enumerate((self._grem, self._geta), start=2):
            lb.setWordWrap(False)
            gg.addWidget(lb, row_i, 0)
        self._gch_tr = _GoalTierTableLinkLabel(self._on_tier_table_clicked, self)
        self._gch_tr.setWordWrap(False)
        self._gch_tr.setTextFormat(Qt.TextFormat.RichText)
        self._gch_tr.setStyleSheet(_g_font_ss_fn())
        self._typo.add(lambda w=self._gch_tr: w.setStyleSheet(_g_font_ss_fn()))
        gg.addWidget(self._gch_tr, 1, 1)
        self._gcrm = QLabel("")
        self._gcel = QLabel("")
        self._gchp_g = _GoalProgressGauge(self)
        self._goal_plain_labels = (
            self._grem,
            self._geta,
            self._gcrm,
            self._gcel,
        )
        for row_i, lb in enumerate((self._gcrm, self._gcel), start=2):
            lb.setWordWrap(False)
            gg.addWidget(lb, row_i, 1)
        self._reapply_goal_plain_labels_typography()
        self._typo.add(self._reapply_goal_plain_labels_typography)
        self._kc_goal_eta_gap_widget = QWidget()
        self._kc_goal_eta_gap_widget.setFixedHeight(self._kc_px_v(6, lo=3, hi=112))
        self._kc_goal_eta_gap_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        gg.addWidget(self._kc_goal_eta_gap_widget, 4, 0, 1, 2)
        gg.addWidget(self._gtier_g, 5, 0)
        gg.addWidget(self._gchp_g, 5, 1)
        goal_outer.addWidget(goal_fr, 1)

        # —— Lap (ratio=2) ——
        lap_outer_sec = QVBoxLayout(self._sec_lap)
        lap_outer_sec.setContentsMargins(0, 0, 0, 0)
        lap_outer_sec.setSpacing(0)
        lap_outer_sec.addWidget(self._section_rule("랩"))
        lap_fr = self._make_card()
        lap_outer = QVBoxLayout(lap_fr)
        lap_outer.setContentsMargins(self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112), self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112))
        lap_outer.setSpacing(self._kc_px_v(4, lo=2, hi=96))

        lap_grid = QGridLayout()
        lap_grid.setHorizontalSpacing(self._kc_px_h(4, lo=2, hi=96))
        lap_grid.setVerticalSpacing(self._kc_px_v(2, lo=1, hi=64))
        self._lap_r1, t1 = self._lap_cell("랩 1H", lap_grid, 0, 0)
        self._lap_r6, t2 = self._lap_cell("랩 6H", lap_grid, 0, 1)
        self._lap_r12, t3 = self._lap_cell("랩 12H", lap_grid, 1, 0)
        self._lap_r24, t4 = self._lap_cell("랩 24H", lap_grid, 1, 1)
        for t in (t1, t2, t3, t4):
            self._typo.add(t)
        self._lap_tile_val_labels = (
            self._lap_r1,
            self._lap_r6,
            self._lap_r12,
            self._lap_r24,
        )

        self._lap_right_box = QFrame()
        self._lap_right_box.setObjectName("pipelaKcLapRight")
        self._lap_right_box.setStyleSheet(_lap_right_frame_qss())
        lap_rv = QGridLayout(self._lap_right_box)
        lap_rv.setContentsMargins(
            self._kc_px_h(8, lo=4, hi=144),
            self._kc_px_v(8, lo=4, hi=144),
            self._kc_px_h(8, lo=4, hi=144),
            self._kc_px_v(8, lo=4, hi=144),
        )
        lap_rv.setHorizontalSpacing(0)
        lap_rv.setVerticalSpacing(0)
        lap_rv.setRowStretch(0, 1)
        lap_rv.setRowStretch(1, 1)
        self._lap_right_caption = QLabel("랩 누적")
        self._lap_right_caption.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self._lap_right_caption.setStyleSheet(self._lap_right_caption_face_qss())
        self._lap_right_kills = QLabel("—")
        self._lap_right_kills.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self._lap_right_kills.setStyleSheet(self._lap_right_kills_face_qss())
        self._typo.add(self._reapply_lap_runsheet_typography)
        self._lap_right_elapsed = QLabel()
        self._lap_right_elapsed.setTextFormat(Qt.TextFormat.RichText)
        # 블럭 하단 쪽으로 더 내려가 보이도록 내부 정렬도 Bottom으로 이동
        self._lap_right_elapsed.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )
        iso0 = self._kc_vs()
        self._lap_elapsed_pt_lab = float(self.KC_PT_LABEL)
        self._lap_elapsed_pt_time = float(self.KC_PT_PRIMARY)
        self._lap_right_elapsed.setText(
            _lap_right_elapsed_rich_html(
                "—", T.METER_LABEL, self._lap_elapsed_pt_lab, self._lap_elapsed_pt_time,
            ),
        )
        self._lap_right_top_row = QWidget()
        self._lap_right_top_row.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        lap_top_h = QHBoxLayout(self._lap_right_top_row)
        lap_top_h.setContentsMargins(0, 0, 0, 0)
        lap_top_h.setSpacing(0)
        lap_top_h.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lap_top_h.addStretch(1)
        lap_top_h.addWidget(self._lap_right_caption, 0)
        lap_top_h.addSpacing(self._kc_px_h(6, lo=3, hi=112))
        lap_top_h.addWidget(self._lap_right_kills, 0)
        lap_top_h.addStretch(1)
        lap_rv.addWidget(
            self._lap_right_top_row,
            0,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        lap_rv.addWidget(
            self._lap_right_elapsed,
            1,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )

        # 한 행·두 열 `QGridLayout` — 셀 높이가 같아져 왼쪽(킬/경과) 박스 높이 = 오른쪽 2×2 랩 셀 블록 합과 동일
        self._lap_right_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        lap_kills_time_row = QGridLayout()
        lap_kills_time_row.setContentsMargins(0, 0, 0, 0)
        lap_kills_time_row.setHorizontalSpacing(self._kc_px_h(8, lo=4, hi=144))
        lap_kills_time_row.setColumnStretch(0, 6)
        lap_kills_time_row.setColumnStretch(1, 4)
        lap_kills_time_row.addWidget(self._lap_right_box, 0, 0)
        lap_kills_time_row.addLayout(lap_grid, 0, 1)
        lap_outer.addLayout(lap_kills_time_row)
        lap_row = QHBoxLayout()
        lap_row.setSpacing(self._kc_px_h(4, lo=2, hi=96))
        self._lap_main = QPushButton()
        self._lap_main.clicked.connect(self._lap_toggle)
        lap_row.addWidget(self._lap_main, 1)
        self._lap_clear_btn = QPushButton("초기화")
        self._lap_clear_btn.setToolTip("랩 누적을 지금 기준으로 다시 시작")
        self._lap_clear_btn.clicked.connect(self._lap_clear)
        lap_row.addWidget(self._lap_clear_btn)
        self._lap_end_btn = QPushButton("종료")
        self._lap_end_btn.setToolTip("랩 세그먼트 종료")
        self._lap_end_btn.clicked.connect(self._lap_end)
        lap_row.addWidget(self._lap_end_btn)
        lap_outer.addLayout(lap_row)
        lap_outer_sec.addWidget(lap_fr, 1)

        # —— Calendar (ratio=2) ——
        cal_outer_sec = QVBoxLayout(self._sec_calendar)
        cal_outer_sec.setContentsMargins(0, 0, 0, 0)
        cal_outer_sec.setSpacing(0)
        cal_outer_sec.addWidget(self._section_rule("캘린더"))
        daily_fr = self._make_card()
        dv_daily = QVBoxLayout(daily_fr)
        dv_daily.setContentsMargins(self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112), self._kc_px_h(8, lo=4, hi=144), self._kc_px_v(6, lo=3, hi=112))
        dv_daily.setSpacing(0)
        self._daily_cal = KillCounterDailyCalendar(pipela_mod, daily_fr)
        self._daily_cal.setGridVisible(True)
        self._daily_cal.setVerticalHeaderFormat(
            KillCounterDailyCalendar.VerticalHeaderFormat.NoVerticalHeader,
        )
        self._style_daily_cal()
        self._daily_cal.currentPageChanged.connect(self._on_daily_cal_page_changed)
        dv_daily.addWidget(self._daily_cal, 1)
        _td = QDate.currentDate()
        self._daily_cal.setCurrentPage(_td.year(), _td.month())
        self._apply_daily_cal_marks()
        cal_outer_sec.addWidget(daily_fr, 1)

        # —— Bottom toolbar (ratio=0.5) ——
        bottom_outer_sec = QVBoxLayout(self._sec_bottom)
        bottom_outer_sec.setContentsMargins(0, 0, 0, 0)
        bottom_outer_sec.setSpacing(0)
        bottom_bar_host = QWidget()
        bottom_bar_host.setContentsMargins(0, 0, 0, 0)
        bottom_outer_sec.addWidget(bottom_bar_host, 1)
        # ROI(미리보기·영역·해제) + 세션/영구 삭제 — 한 줄, 가운데 여백으로 양쪽 균형
        bottom_bar = QHBoxLayout(bottom_bar_host)
        bottom_bar.setSpacing(self._kc_px_h(8, lo=4, hi=144))
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        self._str_sess_reset = "세션 킬 삭제"
        self._str_stats_wipe = "영구 통계 삭제"
        self._sess_reset_btn = QPushButton(self._str_sess_reset)
        self._sess_reset_btn.setToolTip(
            "세션 누적 킬 표시·기준을 지웁니다. 저장된 영구 통계(그래프·캘린더 등)는 바뀌지 않습니다.",
        )
        self._sess_reset_btn.clicked.connect(self._on_session_reset_clicked)
        self._stats_reset_btn = QPushButton(self._str_stats_wipe)
        self._stats_reset_btn.setToolTip(
            "그래프·캘린더·랩 등 저장된 킬 통계와 세션·OCR 표시를 모두 비웁니다. 되돌릴 수 없습니다.",
        )
        self._stats_reset_btn.clicked.connect(self._on_stats_reset_clicked)
        # 랩 줄 초기화/종료: 최소만. 세션·영구 삭제는 슬랙을 일부 받아 폭 피팅이 패널과 같이 회복되게 함.
        for b in (self._lap_clear_btn, self._lap_end_btn):
            b.setSizePolicy(
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )
            b.setMinimumSize(0, 0)
        for b in (self._sess_reset_btn, self._stats_reset_btn):
            b.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
            b.setMinimumSize(0, 0)
        self._kc_region_toolbar_btns = attach_kill_counter_region_toolbar(
            root,
            pipela_mod,
            merge_hbox=bottom_bar,
        )
        for _roi_tb in self._kc_region_toolbar_btns:
            _roi_tb.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
            _roi_tb.setMinimumSize(0, 0)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self._sess_reset_btn, 1)
        bottom_bar.addWidget(self._stats_reset_btn, 1)
        # (bottom bar is inside bottom section host)

        self._kc_head_layout = head
        self._kc_graph_inner = g_inner
        self._kc_roll_grid = rg
        self._kc_goal_grid = gg
        self._kc_lap_outer = lap_outer
        self._kc_lap_tiles_grid = lap_grid
        self._kc_lap_rv = lap_rv
        self._kc_lap_ktr = lap_kills_time_row
        self._kc_lap_btn_row = lap_row
        self._kc_daily_outer = dv_daily
        self._kc_bottom_bar = bottom_bar

        self._refresh_kc_viewport_layout_metrics()
        QTimer.singleShot(0, self._apply_section_heights_by_ratio)

        self._inner_lay = root  # apply_scaled compatibility
        self._apply_kill_panel_button_styles()
        QTimer.singleShot(0, self._apply_kill_lap_buttons_delayed_typography)
        self._timer.setInterval(max(16, int(display_tick_ms())))
        self._timer.start()
        self._kc_bucket_chart.refresh_from_mod()

    def _kc_card_outer_margins(self) -> tuple[int, int]:
        return (
            self._kc_px_h(8, lo=4, hi=144),
            self._kc_px_v(6, lo=3, hi=112),
        )

    def _refresh_kc_viewport_layout_metrics(self) -> None:
        hm, vm = self._kc_card_outer_margins()
        g4 = self._kc_px_v(4, lo=2, hi=96)
        gv2 = self._kc_px_v(2, lo=1, hi=64)
        gh6 = self._kc_px_h(6, lo=3, hi=112)
        gx8 = self._kc_px_h(8, lo=4, hi=144)
        gs10 = self._kc_px_h(10, lo=5, hi=176)

        # 섹션 컨테이너 고정 높이 방식이라 루트 spacing은 0 유지.
        self._kc_head_layout.setSpacing(gx8)
        self._kc_bottom_bar.setSpacing(gx8)

        self._kc_graph_inner.setContentsMargins(hm, vm, hm, vm)
        self._kc_graph_inner.setSpacing(g4)

        self._kc_roll_grid.setContentsMargins(hm, vm, hm, vm)
        self._kc_roll_grid.setHorizontalSpacing(gh6)
        self._kc_roll_grid.setVerticalSpacing(g4)

        self._kc_goal_grid.setContentsMargins(hm, vm, hm, vm)
        self._kc_goal_grid.setHorizontalSpacing(gs10)
        self._kc_goal_grid.setVerticalSpacing(gv2)

        self._kc_goal_eta_gap_widget.setFixedHeight(self._kc_px_v(6, lo=3, hi=112))

        self._kc_lap_outer.setContentsMargins(hm, vm, hm, vm)
        self._kc_lap_outer.setSpacing(g4)

        self._kc_lap_tiles_grid.setHorizontalSpacing(g4)
        self._kc_lap_tiles_grid.setVerticalSpacing(gv2)

        self._kc_lap_rv.setContentsMargins(gs10, gs10, gs10, gs10)
        # 랩 누적 카드(우측) 내부: 2-row Grid로 표준화(위/아래 1:1)
        try:
            self._kc_lap_rv.setRowStretch(0, 1)
            self._kc_lap_rv.setRowStretch(1, 1)
        except Exception:
            pass

        self._kc_lap_ktr.setHorizontalSpacing(gx8)
        self._kc_lap_btn_row.setSpacing(g4)
        self._kc_daily_outer.setContentsMargins(hm, vm, hm, vm)

        h64 = self._kc_px_h(6, lo=3, hi=112)
        v41 = self._kc_px_v(4, lo=2, hi=96)
        h44 = self._kc_px_h(4, lo=2, hi=96)
        v21 = self._kc_px_v(2, lo=1, hi=56)
        for vbox in self._kc_stat_tile_vboxes:
            vbox.setContentsMargins(h64, v41, h64, v41)
            vbox.setSpacing(self._kc_px_v(1, lo=1, hi=56))
        for vbox in self._kc_lap_cell_vboxes:
            vbox.setContentsMargins(h44, v21, h44, v21)

    def _apply_section_heights_by_ratio(self) -> None:
        """킬카창 섹션을 비율(합=11.5)로 고정 높이 배치."""
        try:
            total_h = int(self.contentsRect().height())
        except Exception:
            total_h = 0
        if total_h <= 8:
            return

        ratios: list[tuple[QWidget, float]] = [
            (self._sec_header, 1.0),
            (self._sec_graph, 2.0),
            (self._sec_recent, 2.0),
            (self._sec_goal, 2.0),
            (self._sec_lap, 2.0),
            (self._sec_calendar, 2.0),
            (self._sec_bottom, 0.5),
        ]
        denom = 11.5
        unit = float(total_h) / denom
        heights = [max(1, int(round(unit * r))) for (_w, r) in ratios]
        diff = int(total_h) - int(sum(heights))
        # 잔여 픽셀은 캘린더 섹션에 몰아 총합을 맞춤.
        if diff != 0:
            heights[-2] = max(1, heights[-2] + diff)

        for (w, _r), h in zip(ratios, heights):
            try:
                w.setFixedHeight(int(h))
            except Exception:
                pass

    @staticmethod
    def _make_card() -> QFrame:
        """제어창 설정 허브와 동일 `QFrame#hubCard` 규칙(`app_shell.hub_card_qss_block`)."""
        fr = QFrame()
        fr.setObjectName("hubCard")
        return fr

    def _section_rule(self, title: str) -> QLabel:
        """섹션 구분 — 한 줄 제목 + 머지 구분 느낌."""
        base_pt = float(self.KC_PT_SECTION_TITLE)

        lb = QLabel(title)
        lb.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {self._kc_spt(base_pt)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.12em; margin-top: {self._kc_px_v(2, lo=0, hi=96)}px;",
        )
        self._typo.add(
            lambda w=lb: w.setStyleSheet(
                f"color: {T.FG_MUTED}; font-size: {self._kc_spt(base_pt)}; font-weight: 800; "
                f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.12em; margin-top: {self._kc_px_v(2, lo=0, hi=96)}px;",
            ),
        )
        return lb

    def _stat_pair(self, caption: str, grid: QGridLayout, r: int, c: int) -> tuple[QLabel, callable]:
        box = QFrame()
        box.setObjectName("pipelaKcTile")
        box.setStyleSheet(
            f"QFrame#pipelaKcTile {{"
            f"  background: {T.PANEL_BG}; border: 1px solid {T.BORDER_HAIR}; "
            f"border-radius: {T.RADIUS_SM}; padding: 0;"
            f"}}"
        )
        v = QVBoxLayout(box)
        self._kc_stat_tile_vboxes.append(v)
        v.setContentsMargins(self._kc_px_h(6, lo=3, hi=112), self._kc_px_v(4, lo=2, hi=96), self._kc_px_h(6, lo=3, hi=112), self._kc_px_v(4, lo=2, hi=96))
        v.setSpacing(self._kc_px_v(1, lo=1, hi=48))
        cap = QLabel(caption)
        cap.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {self._kc_spt(7.75 * 2.0)}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        val.setStyleSheet(f"color: {T.FG};")
        v.addWidget(cap)
        v.addWidget(val)
        grid.addWidget(box, r, c)
        return val, (lambda: self._reapply_stat_tile_cap(cap, val))

    def _reapply_stat_tile_cap(self, cap: QLabel, val: QLabel) -> None:
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {self._kc_spt(7.75 * 2.0)}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val.setStyleSheet(
            f"color: {T.FG}; font-size: {self._kc_spt(self.KC_PT_SECONDARY)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: -0.03em;",
        )

    def _lap_cell(self, caption: str, grid: QGridLayout, r: int, c: int) -> tuple[QLabel, callable]:
        box = QFrame()
        box.setObjectName("pipelaKcLapCell")
        box.setStyleSheet(
            f"QFrame#pipelaKcLapCell {{"
            f"  background: {T.PANEL_BG}; border: 1px solid {T.BORDER_HAIR}; "
            f"border-radius: {T.RADIUS_SM}; }}"
        )
        v = QVBoxLayout(box)
        self._kc_lap_cell_vboxes.append(v)
        v.setContentsMargins(self._kc_px_h(4, lo=2, hi=96), self._kc_px_v(2, lo=1, hi=64), self._kc_px_h(4, lo=2, hi=96), self._kc_px_v(2, lo=1, hi=64))
        cap = QLabel(caption)
        cap.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {self._kc_spt(7.75)}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        val.setStyleSheet(f"color: {T.METER_LABEL};")
        v.addWidget(cap)
        v.addWidget(val)
        grid.addWidget(box, r, c)
        return val, (lambda: self._reapply_lap_cap(cap, val))

    def _reapply_lap_cap(self, cap: QLabel, val: QLabel) -> None:
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {self._kc_spt(7.75)}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {self._kc_spt(self.KC_PT_SECONDARY)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: -0.02em;",
        )

    def _apply_kill_panel_button_styles(self) -> None:
        self._lap_main.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_kill_roi_toolbar_typography_fit(self) -> None:
        """역할별 툴바 QSS — `goal_plain_subval_pts` 고정 pt."""
        ph = int(self._kc_px_h(9, lo=4, hi=160))
        pv = int(self._kc_px_v(6, lo=3, hi=112))
        fs = self._kc_spt(self.KC_PT_BUTTON)
        ls = letter_spacing_qss()
        roles: tuple[str, str, str] = ("preview", "region", "clear")
        btns = getattr(self, "_kc_region_toolbar_btns", ())
        for btn, role in zip(btns, roles):
            btn.setStyleSheet(
                panel_template_toolbar_button_qss(
                    role,
                    omit_inline_font=False,
                    font_size=fs,
                    letter_spacing=ls,
                    vertical_padding_px=pv,
                    horizontal_padding_px=ph,
                ),
            )

    def _apply_kill_lap_primary_button_style(self) -> None:
        pv = self._kc_px_v(6, lo=3, hi=112)
        ph = self._kc_px_h(14, lo=8, hi=224)
        self._lap_main.setStyleSheet(
            panel_primary_button_qss(
                font_size=self._kc_spt(9.5),
                letter_spacing=letter_spacing_qss(),
                vertical_padding_px=int(pv),
                horizontal_padding_px=int(ph),
            ),
        )

    def _apply_kill_lap_buttons_delayed_typography(self) -> None:
        self._apply_kill_roi_toolbar_typography_fit()
        self._apply_kill_lap_primary_button_style()
        self._apply_kill_lap_and_delete_row_button_styles()

    def _apply_kill_lap_and_delete_row_button_styles(self) -> None:
        """역할색 QSS + 목표 서브 줄과 동일한 고정 폰트 밴드."""
        _ph_lap = int(self._kc_px_h(12, lo=6, hi=216))
        _ph_del = int(self._kc_px_h(9, lo=4, hi=160))
        _pv_btn = int(self._kc_px_v(6, lo=3, hi=112))
        fs_goal = self._kc_spt(self.KC_PT_BUTTON)
        ls_goal = letter_spacing_qss()

        self._lap_clear_btn.setStyleSheet(
            panel_secondary_button_qss(
                omit_inline_font=False,
                font_size=fs_goal,
                letter_spacing=ls_goal,
                vertical_padding_px=_pv_btn,
                horizontal_padding_px=_ph_lap,
            ),
        )
        self._lap_end_btn.setStyleSheet(
            panel_secondary_button_qss(
                omit_inline_font=False,
                font_size=fs_goal,
                letter_spacing=ls_goal,
                vertical_padding_px=_pv_btn,
                horizontal_padding_px=_ph_lap,
            ),
        )
        self._sess_reset_btn.setStyleSheet(
            kill_counter_session_reset_button_qss(
                omit_inline_font=False,
                font_size=fs_goal,
                letter_spacing=ls_goal,
                vertical_padding_px=_pv_btn,
                horizontal_padding_px=_ph_del,
            ),
        )
        self._stats_reset_btn.setStyleSheet(
            kill_counter_permanent_wipe_button_qss(
                omit_inline_font=False,
                font_size=fs_goal,
                letter_spacing=ls_goal,
                vertical_padding_px=_pv_btn,
                horizontal_padding_px=_ph_del,
            ),
        )
        for b in (self._lap_clear_btn, self._lap_end_btn, self._sess_reset_btn, self._stats_reset_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

    def _refresh_prog_big_hero_style(self) -> None:
        self._prog_big.setStyleSheet(
            f"color: {T.ACCENT}; letter-spacing: -0.02em; font-size: {self._kc_spt(self.KC_PT_HERO)}; "
            f"font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )

    def _pulse_recent_roll_label(self, lbl: QLabel) -> None:
        eff = lbl.graphicsEffect()
        if not isinstance(eff, QGraphicsColorizeEffect):
            eff = QGraphicsColorizeEffect(lbl)
            eff.setColor(QColor(255, 255, 255))
            lbl.setGraphicsEffect(eff)
        anim = getattr(lbl, "_pipela_kc_roll_pulse", None)
        if anim is None:
            anim = QPropertyAnimation(eff, b"strength", self)
            lbl._pipela_kc_roll_pulse = anim  # type: ignore[attr-defined]
        anim.stop()
        peak = 0.42
        eff.setStrength(peak)
        anim.setDuration(400)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.setStartValue(peak)
        anim.setEndValue(0.0)
        anim.start()

    def _reapply_lap_elapsed_pts_from_viewport(self) -> None:
        self._lap_elapsed_pt_lab = float(elapsed_eff_pt_clip(self.KC_PT_LABEL))
        self._lap_elapsed_pt_time = float(elapsed_eff_pt_clip(self.KC_PT_PRIMARY))

    def _reapply_lap_elapsed_rich_display(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            time_part = "—"
        else:
            time_part = m._kill_counter_lap_header_meta_text()
        fg_sw = m._kill_counter_lap_stopwatch_label_fg()
        self._lap_right_elapsed.setText(self._fit_lap_elapsed_rich_to_available_width(time_part, fg_sw))

    def _reapply_lap_right_rich_typography(self) -> None:
        self._lap_right_caption.setStyleSheet(self._lap_right_caption_face_qss())
        self._lap_right_kills.setStyleSheet(self._lap_right_kills_face_qss())
        self._reapply_lap_elapsed_pts_from_viewport()
        self._reapply_lap_elapsed_rich_display()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._kc_vw, self._kc_vh = kc_viewport_wh_valid(self.width(), self.height())
        self._refresh_kc_viewport_layout_metrics()
        self._kc_bucket_chart.refresh_viewport_dependent_chrome()
        self._apply_section_heights_by_ratio()
        # 폭 변화에 따라 RichText 경과 표시를 폭-피팅
        self._reapply_lap_elapsed_rich_display()
        # 섹션 타이틀 등 타이포(StyleSheet)를 리사이즈에 맞춰 재적용(디바운스)
        try:
            self._resize_typo_timer.start()
        except Exception:
            pass

    def _on_resize_typo_timer(self) -> None:
        try:
            self._typo.apply()
        except Exception:
            pass

    def _on_tier_table_clicked(self) -> None:
        show_kill_counter_tier_table_dialog(self, pipela_mod=self._m)

    def _style_daily_cal(self) -> None:
        br = self._kc_px_v(8, lo=4, hi=144)
        fs = self._kc_px_v(10, lo=5, hi=176)
        self._daily_cal.setStyleSheet(
            f"QCalendarWidget {{"
            f"background: {T.PANEL_BG}; color: {T.FG};"
            f"font-family: {T.FONT_CSS_UI}; font-size: {fs}px;"
            f"border: 1px solid {T.BORDER_HAIR}; border-radius: {br}px;"
            f"}}"
            f"QCalendarWidget QWidget#qt_calendar_navigationbar {{"
            f"background: {T.SURFACE}; border-bottom: 1px solid {T.BORDER_HAIR};"
            f"padding: 0; margin: 0;"
            f"}}"
            f"QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton {{"
            f"color: {T.FG}; background: {T.PANEL_BG}; border: 1px solid {T.BORDER_HAIR};"
            f"border-radius: {max(3, self._kc_px_v(4, lo=2, hi=96))}px; padding: {max(0, self._kc_px_v(1, lo=1, hi=48))}px {max(0, self._kc_px_h(2, lo=1, hi=64))}px;"
            f"font-weight: 600; min-height: 0; margin: 0;"
            f"}}"
            f"QCalendarWidget QToolButton:hover {{ background: {T.CARD_HOVER}; }}"
            f"QCalendarWidget QAbstractItemView {{"
            f"background: {T.PANEL_BG}; selection-background-color: {T.ACCENT_SOFT};"
            f"selection-color: {T.FG}; outline: none;"
            f"}}"
            f"QCalendarWidget QAbstractItemView:enabled {{ color: {T.FG}; }}"
            f"QCalendarWidget QAbstractItemView:disabled {{ color: {T.FG_DIM}; }}",
        )

    def _apply_daily_cal_marks(self) -> None:
        self._daily_cal.refresh_marks()

    def _on_daily_cal_page_changed(self, _y: int, _m: int) -> None:
        self._apply_daily_cal_marks()

    def apply_scaled_typography(self) -> None:
        self._refresh_kc_viewport_layout_metrics()
        self._gtier_g.refresh_geometry_and_style()
        self._gchp_g.refresh_geometry_and_style()
        self._style_daily_cal()
        self._typo.apply()
        self._apply_kill_panel_button_styles()
        self._kc_bucket_chart.apply_scaled_style()
        self._apply_section_heights_by_ratio()
        self._tick()
        QTimer.singleShot(0, self._apply_kill_lap_buttons_delayed_typography)

    def _reapply_goal_plain_labels_typography(self) -> None:
        fs = self._kc_spt(self.KC_PT_GOAL_LINE)
        ff = T.FONT_CSS_UI
        fw = "500"
        self._grem.setStyleSheet(
            f"color: {T.FG}; font-size: {fs}; font-weight: {fw}; font-family: {ff};",
        )
        self._geta.setStyleSheet(
            f"color: {T.FG}; font-size: {fs}; font-weight: {fw}; font-family: {ff};",
        )
        self._gcrm.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {fs}; font-weight: {fw}; font-family: {ff};",
        )
        self._gcel.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {fs}; font-weight: {fw}; font-family: {ff};",
        )

    def _reapply_lap_runsheet_typography(self) -> None:
        self._lap_right_box.setStyleSheet(_lap_right_frame_qss())
        self._lap_right_caption.setStyleSheet(self._lap_right_caption_face_qss())
        self._lap_right_kills.setStyleSheet(self._lap_right_kills_face_qss())

    def _sync_lap_meta_min_width(self) -> None:
        try:
            cap_txt = (self._lap_right_caption.text() or "랩 누적").strip()
            w_c = self._lap_right_caption.fontMetrics().horizontalAdvance(cap_txt)
            wk = self._lap_right_kills.fontMetrics().horizontalAdvance("9,999,999")
            hsp = self._kc_px_h(6, lo=3, hi=112)
            w_top = w_c + hsp + wk
            html_bench = _lap_right_elapsed_rich_html(
                LAP_ELAPSED_BENCHMARK_TIME_PART,
                T.FG,
                float(self._lap_elapsed_pt_lab),
                float(self._lap_elapsed_pt_time),
            )
            wem = int(math.ceil(_lap_elapsed_rich_ideal_width_px(html_bench)))
            # NOTE: 과거에는 카드 폭을 고정(min-width)해 클리핑을 방지했지만,
            #       이는 창 가로 리사이즈에 반응하지 않는 문제를 유발.
            #       여기서는 측정만 유지하고 실제 폭은 RichText 폭-피팅으로 해결한다.
            _ = max(w_top, wem)
        except Exception:
            pass

    def _fit_lap_elapsed_rich_to_available_width(self, time_part: str, fg_sw: str) -> str:
        """`랩 누적` 카드의 '경과 + 시간' RichText가 폭에 맞게 축소/폴백되도록 HTML을 생성."""
        try:
            # QLabel은 RichText를 QTextDocument로 렌더링하므로 idealWidth 기반으로 폭-피팅.
            avail = int(self._lap_right_box.contentsRect().width())
            if avail <= 0:
                avail = int(self._lap_right_elapsed.contentsRect().width())
            if avail <= 0:
                return _lap_right_elapsed_rich_html(
                    time_part,
                    fg_sw,
                    float(self._lap_elapsed_pt_lab),
                    float(self._lap_elapsed_pt_time),
                )

            # content margins(좌/우) 제외: lap_rv.setContentsMargins(...)와 동일한 값
            pad_lr = int(self._kc_px_h(8, lo=4, hi=144)) * 2
            avail = max(24, avail - pad_lr)

            base_lab = float(self._lap_elapsed_pt_lab)
            base_time = float(self._lap_elapsed_pt_time)

            def build_html(pt_lab: float, pt_time: float) -> str:
                return _lap_right_elapsed_rich_html(time_part, fg_sw, pt_lab, pt_time)

            html0 = build_html(base_lab, base_time)
            w0 = float(_lap_elapsed_rich_ideal_width_px(html0))
            # 안전 여유: 폭이 넓어질수록 조금 증가(비례), 과도해지지 않게 clamp
            safety_px = int(max(4, min(12, int(round(float(avail) * 0.01)))))
            target = float(max(12, int(avail) - int(safety_px)))

            if w0 <= target:
                return html0

            # 연속 비율 피팅 + 이분탐색으로 1px 단위 오차까지 수렴
            # lab은 time보다 약간 덜 줄어드는 편이 시각적으로 안정적
            lab_bias = 0.92

            def width_for(scale: float) -> tuple[float, str]:
                s = float(max(0.05, min(1.0, scale)))
                pt_t = elapsed_eff_pt_clip(base_time * s)
                pt_l = elapsed_eff_pt_clip(base_lab * (1.0 - (1.0 - s) * lab_bias))
                h = build_html(float(pt_l), float(pt_t))
                return float(_lap_elapsed_rich_ideal_width_px(h)), h

            # 초기 하한 추정
            lo_s = max(0.05, min(0.98, target / max(1.0, w0)))
            hi_s = 1.0
            best_html = html0
            best_w = w0

            # lo_s가 충분히 작지 않으면 0.5씩 더 내려가며 보장
            for _k in range(6):
                w_lo, h_lo = width_for(lo_s)
                if w_lo <= target:
                    best_html, best_w = h_lo, w_lo
                    break
                lo_s = max(0.05, lo_s * 0.7)

            # 이분 탐색으로 최대한 크게(덜 줄이게) 맞춤
            for _i in range(12):
                mid = (lo_s + hi_s) * 0.5
                w_mid, h_mid = width_for(mid)
                if w_mid <= target:
                    best_html, best_w = h_mid, w_mid
                    lo_s = mid
                else:
                    hi_s = mid

            # 3) 최후 폴백: 시간만 표기
            if best_w <= target:
                return best_html

            # 그래도 안 맞으면 compact 폴백
            # time pt는 현재 스케일(lo_s) 기반으로 사용
            pt_time = elapsed_eff_pt_clip(base_time * float(lo_s))
            html_c = _lap_right_elapsed_rich_html_compact(time_part, fg_sw, float(pt_time))
            return html_c
        except Exception:
            return _lap_right_elapsed_rich_html(
                time_part,
                fg_sw,
                float(getattr(self, "_lap_elapsed_pt_lab", 10.0)),
                float(getattr(self, "_lap_elapsed_pt_time", 12.0)),
            )

    def _on_session_reset_clicked(self) -> None:
        if not confirm_card_dialog(
            self,
            title="세션 킬 삭제",
            message=(
                "세션 누적 킬 표시와 기준을 지울까요?\n"
                "저장된 영구 통계(그래프·캘린더 등)는 바뀌지 않습니다."
            ),
            message_tone="warn",
            default_confirm=False,
        ):
            return
        self._m._kill_counter_reset_session_kills()
        print("[Kill Counter] 세션 킬 삭제", flush=True)
        self._tick()

    def _on_stats_reset_clicked(self) -> None:
        if not confirm_card_dialog(
            self,
            title="영구 통계 삭제",
            message=(
                "저장된 킬 통계(그래프·캘린더·랩)와 세션·OCR 표시를 모두 지울까요?\n"
                "이 작업은 되돌릴 수 없습니다."
            ),
            message_tone="danger",
            default_confirm=False,
        ):
            return
        m = self._m
        m._kill_counter_reset_all_counts()
        sync_registry_snapshot_from_module(m)
        self._kc_bucket_chart.refresh_from_mod()
        self._apply_daily_cal_marks()
        self._tick()

    def _lap_toggle(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            m.kill_counter_lap_pause_segments = []
            m.kill_counter_lap_start_ts = time.time()
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 시작", flush=True)
        elif m._kill_counter_lap_is_paused():
            segs = m.kill_counter_lap_pause_segments
            if segs and segs[-1][1] is None:
                segs[-1][1] = time.time()
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 재개", flush=True)
        else:
            m.kill_counter_lap_pause_segments.append([time.time(), None])
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 일시중지", flush=True)
        self._sync_lap_buttons()

    def _lap_clear(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            return
        m.kill_counter_lap_pause_segments = []
        m.kill_counter_lap_start_ts = time.time()
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        print("[Kill Counter] 랩 초기화(재시작)", flush=True)

    def _lap_end(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            return
        m.kill_counter_lap_start_ts = None
        m.kill_counter_lap_pause_segments = []
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        print("[Kill Counter] 랩 종료", flush=True)

    def _sync_lap_buttons(self) -> None:
        m = self._m
        has = m.kill_counter_lap_start_ts is not None
        paused = m._kill_counter_lap_is_paused()
        if not has:
            label = "시작"
        elif paused:
            label = "재개"
        else:
            label = "일시중지"
        if self._lap_main.text() != label:
            self._lap_main.setText(label)
            QTimer.singleShot(0, self._apply_kill_lap_buttons_delayed_typography)
        self._lap_clear_btn.setEnabled(has)
        self._lap_end_btn.setEnabled(has)

    def _tick(self) -> None:
        m = self._m
        prog = m._kill_counter_panel_progress_value_text(m.kill_counter_last_progress)
        self._prog_big.setText(prog)
        try:
            win = self.window()
            if win is not None and win.objectName() == "pipelaKcFrameless":
                win.setWindowTitle(f"Kill Counter · {prog}")
        except Exception:
            pass
        # 통계·랩·목표/그래프 스핀: 구간 합·strftime 루프가 무거움 — ~0.35s 마다 갱신.
        now = time.monotonic()
        if self._slow_tick_mono == 0.0 or (now - self._slow_tick_mono) >= 0.35:
            self._slow_tick_mono = now
            k1 = m._kill_counter_stats_sum_last_seconds(3600.0)
            k6 = m._kill_counter_stats_sum_last_seconds(21600.0)
            k24 = m._kill_counter_stats_sum_last_seconds(86400.0)
            kph = (k24 / 24.0) if k24 else 0.0
            roll_txts = (f"{k1:,}", f"{k6:,}", f"{k24:,}", f"{kph:.1f}")
            for idx, lbl in enumerate(self._recent_roll_val_labels):
                new_txt = roll_txts[idx]
                prev = self._recent_roll_last_display[idx]
                if prev == new_txt:
                    continue
                lbl.setText(new_txt)
                if prev is not None:
                    self._pulse_recent_roll_label(lbl)
                self._recent_roll_last_display[idx] = new_txt

            self._gtr.setText(
                _goal_transition_line_rich_html(
                    m._kill_counter_goal_transition_line(),
                    muted_fallback=False,
                ),
            )
            self._grem.setText(m._kill_counter_goal_rem_line())
            self._geta.setText(m._kill_counter_goal_eta_line(float(k1), float(kph)))
            pct_f = m._kill_counter_goal_tier_pct_float()
            self._gtier_g.set_pct(pct_f)
            self._gch_tr.setText(
                _goal_transition_line_rich_html(
                    m._kill_counter_goal_choin_transition_line(),
                    muted_fallback=True,
                ),
            )
            self._gcrm.setText(m._kill_counter_goal_choin_rem_line())
            self._gcel.setText(m._kill_counter_goal_choin_eta_line(float(k1), float(kph)))
            pct_ch = m._kill_counter_goal_choin_pct_float()
            self._gchp_g.set_pct(pct_ch)

            self._apply_daily_cal_marks()

            self._kc_bucket_chart.refresh_from_mod()

            if m.kill_counter_lap_start_ts is None:
                for lb in (self._lap_r1, self._lap_r6, self._lap_r12, self._lap_r24):
                    lb.setText("—")
            else:
                a = m._kill_counter_stats_sum_lap_in_last_seconds(3600.0)
                b = m._kill_counter_stats_sum_lap_in_last_seconds(21600.0)
                c = m._kill_counter_stats_sum_lap_in_last_seconds(43200.0)
                dlap = m._kill_counter_stats_sum_lap_in_last_seconds(86400.0)
                self._lap_r1.setText(f"{a:,}")
                self._lap_r6.setText(f"{b:,}")
                self._lap_r12.setText(f"{c:,}")
                self._lap_r24.setText(f"{dlap:,}")

        if m.kill_counter_lap_start_ts is None:
            self._lap_right_kills.setText("—")
        else:
            self._lap_right_kills.setText(f"{m._kill_counter_stats_sum_lap_total():,}")
        self._reapply_lap_right_rich_typography()
        self._sync_lap_buttons()

