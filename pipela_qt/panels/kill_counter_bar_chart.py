"""킬 카운터 — 봉(버킷) 막대 그래프 (최근 누적 옆 패널용)."""

from __future__ import annotations

import datetime
import math
import time
from functools import partial

from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QRectF, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pipela_core.console_log_prefix import format_ko_coarse_ago_from_seconds

from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import panel_secondary_button_qss
from pipela_qt.kill_counter_viewport_metrics import (
    kc_viewport_height_scale_from_widget_chain,
    kc_viewport_px_h,
    kc_viewport_px_v,
    kc_viewport_spt_v,
    kc_viewport_width_scale_from_widget_chain,
)
 
from pipela_qt.ui_adaptive import letter_spacing_qss

# 봉 호버 툴팁 전체 체감 크기(패딩·글자·바깥 여백) — 기존 대비 약 40%
_GRAPH_TIP_SCALE = 0.4
# 툴팁 전용 — 앱 기본 letter-spacing 보다 붙여서
_GRAPH_TIP_LETTER_SPACING = "0.02em"


def _graph_tip_px(owner: QWidget, design_px: float) -> int:
    vs = kc_viewport_height_scale_from_widget_chain(owner)
    return max(
        3,
        kc_viewport_px_v(
            vs,
            float(design_px) * float(_GRAPH_TIP_SCALE),
            hi=240,
        ),
    )


def _graph_tip_spt(owner: QWidget, design_pt: float) -> str:
    vs = kc_viewport_height_scale_from_widget_chain(owner)
    return kc_viewport_spt_v(
        vs,
        max(5.25, float(design_pt) * float(_GRAPH_TIP_SCALE)),
    )


def _series_kills_at(series: list[dict], i: int) -> int:
    if not (0 <= i < len(series)):
        return 0
    try:
        return int(series[i].get("kills", 0))
    except (TypeError, ValueError):
        return 0


def _bar_delta(series: list[dict], i: int) -> int | None:
    if i <= 0 or not series:
        return None
    return _series_kills_at(series, i) - _series_kills_at(series, i - 1)


def _parse_hex_rgb(h: str) -> tuple[int, int, int]:
    s = (h or "").strip().lstrip("#")
    if len(s) >= 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return (61, 212, 201)


def _bucket_intrabucket_time_fraction(
    ymdhm: object, bucket_minutes: int, now: float,
) -> float:
    """현재(마지막) 봉 구간 [t0,t1) 안에서의 경과 비율 0..1 — 1분이면 1초당 1/60."""
    bounds = _ymdhm_to_bucket_bounds(ymdhm, bucket_minutes)
    if not bounds:
        return 0.0
    t0, t1 = bounds
    span = float(t1) - float(t0)
    if span <= 1e-9:
        return 0.0
    u = (float(now) - float(t0)) / span
    if u < 0.0:
        return 0.0
    if u > 1.0:
        return 1.0
    return u


def _ymdhm_to_bucket_bounds(ymdhm: object, bucket_minutes: int) -> tuple[float, float] | None:
    """로컬 시각 ymdhm 구간 [t0, t1) — t1 은 1일 버킷이면 익일 0시."""
    if ymdhm is None or not isinstance(ymdhm, (list, tuple)) or len(ymdhm) < 5:
        return None
    y, m, d, h, mi = (int(ymdhm[0]), int(ymdhm[1]), int(ymdhm[2]), int(ymdhm[3]), int(ymdhm[4]))
    try:
        t0 = time.mktime((y, m, d, h, mi, 0, 0, 0, -1))
    except (OverflowError, OSError, ValueError):
        return None
    bm = int(bucket_minutes)
    if bm >= 1440:
        d0 = datetime.date(y, m, d)
        d1 = d0 + datetime.timedelta(days=1)
        t1 = time.mktime((d1.year, d1.month, d1.day, 0, 0, 0, 0, 0, -1))
        return (t0, t1)
    t1 = t0 + float(bm) * 60.0
    return (t0, t1)


def _bucket_ago_seconds(t0: float, t1: float, now: float, bucket_minutes: int) -> int:
    """봉 기준 '경과' 초 — 진행 중 구간은 구간 시작 이후, 끝난 구간은 구간 끝 이후, 일봉(과거일)은 그날 끝 이후."""
    bm = int(bucket_minutes)
    if bm >= 1440:
        if now < t1:
            return int(max(0.0, now - t0))
        return int(max(0.0, now - t1))
    if now < t1:
        return int(max(0.0, now - t0))
    return int(max(0.0, now - t1))


def _time_line_for_bucket_bar(
    hhmm: str, ymdhm: object, bucket_minutes: int, now: float,
) -> str:
    bounds = _ymdhm_to_bucket_bounds(ymdhm, bucket_minutes)
    if not bounds:
        return hhmm
    t0, t1 = bounds
    ago_s = _bucket_ago_seconds(t0, t1, now, bucket_minutes)
    return f"{hhmm} ({format_ko_coarse_ago_from_seconds(ago_s)})"


class _BucketBarTooltipPopup(QFrame):
    """봉 호버용 큰 오버레이 — 시간 강조, 킬 수는 양봉/음봉 색."""

    __slots__ = (
        "_ago_timer",
        "_bar_canvas",
        "_deferred_gpos",
        "_deferred_token",
        "_kc_prewarmed",
        "_kills",
        "_last_gpos",
        "_time",
        "_tip_radius",
        "_tip_sig",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        # 부모(봉 차트 Pan)의 자식 — 별도 Tool HWND / 레이어드 move 비용(수십 ms) 회피.
        super().__init__(parent)
        self.setObjectName("pipelaKcBucketTip")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._bar_canvas: _KillCounterBucketChartCanvas | None = None
        self._last_gpos = QPoint(0, 0)
        self._ago_timer = QTimer(self)
        self._ago_timer.setInterval(1000)
        self._ago_timer.timeout.connect(self._on_ago_tick)
        br = _graph_tip_px(self, 10)
        self._tip_radius = max(2, int(br))
        pad = _graph_tip_px(self, 16)
        # 검정 반투명 박스는 paintEvent 에서만 칠한다.
        self.setStyleSheet(
            f"QFrame#pipelaKcBucketTip {{ background: transparent; border: none; }}"
            f"QFrame#pipelaKcBucketTip QLabel {{ background: transparent; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(pad, pad, pad, pad)
        lay.setSpacing(_graph_tip_px(self, 8))
        self._time = QLabel()
        self._kills = QLabel()
        self._tip_sig: tuple[str, str, str, str] | None = None
        for lb in (self._time, self._kills):
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setWordWrap(False)
        lay.addWidget(self._time)
        lay.addWidget(self._kills)
        self.setMinimumWidth(_graph_tip_px(self, 200))
        self._deferred_token = 0
        self._deferred_gpos: QPoint | None = None
        self._kc_prewarmed = False

    def set_bar_canvas(self, canvas: _KillCounterBucketChartCanvas) -> None:
        """``parent`` 는 Pan(부모)이라 ``ago`` 타이머는 캔버스를 이 참조로 본다."""
        self._bar_canvas = canvas

    def prewarm_offscreen(self) -> None:
        """자식이면 부모 좌표계 1회 show/hide — 레이아웃·윈도우 힌트 워밍."""
        if self._kc_prewarmed:
            return
        self._kc_prewarmed = True
        try:
            self.resize(
                max(self.minimumWidth(), _graph_tip_px(self, 80)),
                max(_graph_tip_px(self, 48), _graph_tip_px(self, 40)),
            )
            if self.parentWidget() is not None:
                self.setGeometry(
                    -min(2000, self.parentWidget().width() + 200),
                    -min(2000, self.parentWidget().height() + 200),
                    self.width(),
                    self.height(),
                )
            else:
                self.setGeometry(-5000, -5000, self.width(), self.height())
            self.show()
            self.hide()
        except Exception:
            pass

    def _schedule_deferred_move(self, gpos: QPoint) -> None:
        """show/move 를 다음 이벤트 루프로 — MouseMove 핸들러 100ms+ 블로킹 방지."""
        self._deferred_gpos = QPoint(gpos)
        self._deferred_token += 1
        t = self._deferred_token
        QTimer.singleShot(0, partial(self._flush_deferred_move, t))

    def _flush_deferred_move(self, token: int) -> None:
        if token != self._deferred_token:
            return
        g = self._deferred_gpos
        if g is None:
            return
        self._deferred_gpos = None
        self._move_near(g)

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rr = float(max(4, self._tip_radius))
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), rr, rr)
        fill = QColor(0, 0, 0, int(255 * 0.7))
        p.fillPath(path, fill)
        ar, ag, ab = _parse_hex_rgb(T.ACCENT)
        edge = QColor(ar, ag, ab, int(255 * 1))
        p.setPen(QPen(edge, max(0.5, float(_graph_tip_px(self, 1)))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def _on_ago_tick(self) -> None:
        w = self._bar_canvas
        if w is None or w._hover_idx is None:
            self._ago_timer.stop()
            return
        i = w._hover_idx
        if i is None or not (0 <= i < len(w._series)):
            self._ago_timer.stop()
            return
        self.update_for_bar(
            w._series,
            i,
            self._last_gpos,
            w._bucket_minutes,
            is_timer_tick=True,
        )

    def update_for_bar(
        self,
        series: list[dict],
        idx: int,
        global_pos: QPoint,
        bucket_minutes: int,
        *,
        is_timer_tick: bool = False,
    ) -> None:
        if not (0 <= idx < len(series)):
            return
        s = series[idx]
        hhmm = str(s.get("hhmm", "")) or "—"
        ymd = s.get("ymdhm")
        now = time.time()
        time_line = _time_line_for_bucket_bar(
            hhmm, ymd, int(bucket_minutes), now,
        )
        if not is_timer_tick:
            self._last_gpos = QPoint(global_pos)
        k = _series_kills_at(series, idx)
        d = _bar_delta(series, idx)
        if d is None:
            kcol = T.FG_MUTED
        elif d > 0:
            kcol = T.ACCENT
        elif d < 0:
            kcol = "#fca5a5"
        else:
            kcol = T.FG
        tss = (
            f"color: {T.FG}; font-weight: 800; font-size: {_graph_tip_spt(self, 15.25)}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {_GRAPH_TIP_LETTER_SPACING};"
        )
        ktxt = f"{k:,} 킬"
        kss = (
            f"color: {kcol}; font-weight: 800; font-size: {_graph_tip_spt(self, 26.0)}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {_GRAPH_TIP_LETTER_SPACING};"
        )
        sig = (time_line, ktxt, tss, kss)
        if self._tip_sig == sig:
            if is_timer_tick:
                return
            self._schedule_deferred_move(global_pos)
            if not self._ago_timer.isActive():
                self._ago_timer.start()
            return
        self._tip_sig = sig
        self._time.setText(time_line)
        self._time.setStyleSheet(tss)
        self._kills.setText(ktxt)
        self._kills.setStyleSheet(kss)
        self.adjustSize()
        if not is_timer_tick:
            self._schedule_deferred_move(global_pos)
        if not is_timer_tick and not self._ago_timer.isActive():
            self._ago_timer.start()

    def _move_near(self, gpos: QPoint) -> None:
        m = _graph_tip_px(self, 16)
        p = QPoint(gpos.x() + m, gpos.y() + m)
        scr = self.screen()
        geo = scr.availableGeometry() if scr is not None else None
        if geo is not None:
            if p.x() + self.width() > geo.right():
                p.setX(gpos.x() - self.width() - m)
            if p.y() + self.height() > geo.bottom():
                p.setY(gpos.y() - self.height() - m)
            p.setX(max(geo.left(), min(p.x(), geo.right() - self.width())))
            p.setY(max(geo.top(), min(p.y(), geo.bottom() - self.height())))
        par = self.parentWidget()
        if par is not None:
            pl = par.mapFromGlobal(p)
            tw, th = self.width(), self.height()
            pw, ph = par.width(), par.height()
            pl.setX(max(0, min(pl.x(), max(0, pw - tw))))
            pl.setY(max(0, min(pl.y(), max(0, ph - th))))
            if self.isVisible() and self.pos() == pl:
                return
            self.move(pl)
            if not self.isVisible():
                self.show()
                self.raise_()
        else:
            if self.isVisible() and self.pos() == p:
                return
            self.move(p)
            if not self.isVisible():
                self.show()
                self.raise_()

    def reposition_only(self, global_pos: QPoint) -> None:
        if self.isVisible():
            self._last_gpos = QPoint(global_pos)
            self._schedule_deferred_move(global_pos)

    def hide_tip(self) -> None:
        self._ago_timer.stop()
        self._tip_sig = None
        self._deferred_token += 1
        self._deferred_gpos = None
        self.hide()


class _KillCounterBucketChartCanvas(QWidget):
    """왼쪽(과거)→오른쪽(최신) 막대. Ctrl+휠 가로 확대, Shift+휠 가로 이동."""

    viewRangeChanged = pyqtSignal()

    __slots__ = (
        "_bucket_minutes",
        "_hover_anim",
        "_hover_idx",
        "_hover_spring",
        "_last_bar_draw_h",
        "_last_bar_h_anim",
        "_last_bar_h_anim_n",
        "_last_bar_h_inited",
        "_last_series_sig",
        "_last_series_reload_sig",
        "_pulse",
        "_pulse_anim",
        "_series",
        "_scroll_x",
        "_shimmer_phase",
        "_shimmer_timer",
        "_tip",
        "_tip_repos_t",
        "_user_panned",
        "_x_scale",
        "_zoom_drag_on",
        "_zoom_drag_start_global_x",
        "_zoom_drag_start_scale",
        "_zoom_label",
        "_kc_graph_tip_prewarm_scheduled",
        "_live_scroll_timer",
        "_pan_idle_timer",
        "_last_user_pan_mono",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._series: list[dict] = []
        self._bucket_minutes = 5
        self._x_scale = 1.0
        self._scroll_x = 0.0
        self._user_panned = False
        self._last_user_pan_mono = 0.0
        self._hover_idx: int | None = None
        self._hover_spring = 0.0
        self._shimmer_phase = 0.0
        self._pulse = 0.0
        self._last_bar_draw_h = 0.0
        self._last_bar_h_inited = False
        self._last_bar_h_anim_n = -1
        self._last_series_sig: tuple[int, ...] = ()
        self._last_series_reload_sig: tuple[int, ...] = ()
        self._tip_repos_t = 0.0
        _p = self.parent()
        self._tip = _BucketBarTooltipPopup(
            _p if isinstance(_p, QWidget) else self
        )
        self._tip.set_bar_canvas(self)
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(42)
        self._shimmer_timer.timeout.connect(self._on_shimmer_tick)
        self._live_scroll_timer = QTimer(self)
        self._live_scroll_timer.setInterval(125)
        self._live_scroll_timer.timeout.connect(self._on_live_time_scroll_tick)
        self._pan_idle_timer = QTimer(self)
        self._pan_idle_timer.setInterval(400)
        self._pan_idle_timer.timeout.connect(self._on_pan_idle_tick)
        self._pan_idle_timer.start()
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(220)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_anim_value)
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setDuration(400)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._pulse_anim.valueChanged.connect(self._on_pulse_anim_value)
        self._last_bar_h_anim = QVariantAnimation(self)
        self._last_bar_h_anim.setDuration(280)
        self._last_bar_h_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._last_bar_h_anim.valueChanged.connect(self._on_last_bar_h_anim_value)
        self.setMouseTracking(True)
        vs = kc_viewport_height_scale_from_widget_chain(self)
        self.setMinimumHeight(kc_viewport_px_v(vs, 112, lo=40, hi=320))
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._zoom_label = QLabel(self)
        self._zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._zoom_drag_on = False
        self._zoom_drag_start_global_x = 0.0
        self._zoom_drag_start_scale = 1.0
        self._zoom_label.installEventFilter(self)
        self._restyle_zoom_label()
        self._refresh_zoom_label_text()
        self._zoom_label.raise_()
        self._kc_graph_tip_prewarm_scheduled = False

    def _on_pan_idle_tick(self) -> None:
        if not self._user_panned or not self._series:
            return
        t0 = float(self._last_user_pan_mono)
        if t0 <= 0.0:
            return
        if time.monotonic() - t0 < 30.0:
            return
        self._user_panned = False
        self._scroll_to_end()
        self._sync_shimmer_timer()
        self.update()
        self._emit_view_changed()

    def _apply_x_scale(self, new_scale: float) -> None:
        """가로 막대 스케일만 갱신하고 스크롤 위치를 휠 줌과 동일 규칙으로 보정."""
        cl = max(0.25, min(5.0, float(new_scale)))
        if abs(cl - self._x_scale) < 1e-6:
            return
        n, _bw_old, _gap, content_w_old, _ = self._layout_metrics()
        vw = max(1, self.width())
        self._x_scale = cl
        _, _, _, content_w_new, _ = self._layout_metrics()
        if not self._user_panned:
            self._scroll_to_end()
        else:
            cw_o = content_w_old if n else float(vw)
            cw_n = content_w_new if n else float(vw)
            center = self._scroll_x + float(vw) * 0.5
            frac = center / cw_o if cw_o > 1e-6 else 0.5
            self._scroll_x = frac * cw_n - float(vw) * 0.5
            self._clamp_scroll()
        self._refresh_zoom_label_text()
        self.update()
        self._emit_view_changed()

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:
        if obj is self._zoom_label and ev.type() == QEvent.Type.MouseButtonPress:
            me = ev
            if me.button() == Qt.MouseButton.LeftButton:  # type: ignore[union-attr]
                self._zoom_drag_on = True
                self._zoom_drag_start_global_x = float(me.globalPosition().x())  # type: ignore[union-attr]
                self._zoom_drag_start_scale = float(self._x_scale)
                self.grabMouse()
                return True
        return super().eventFilter(obj, ev)

    def _viewport_vs(self) -> float:
        return kc_viewport_height_scale_from_widget_chain(self)

    def _viewport_ws(self) -> float:
        return kc_viewport_width_scale_from_widget_chain(self)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._kc_graph_tip_prewarm_scheduled:
            self._kc_graph_tip_prewarm_scheduled = True
            QTimer.singleShot(80, self._tip.prewarm_offscreen)

    def _restyle_zoom_label(self) -> None:
        fs = kc_viewport_spt_v(self._viewport_vs(), 6.75)
        self._zoom_label.setStyleSheet(
            f"QLabel {{ color: {T.FG_MUTED}; font-weight: 600; font-size: {fs}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; "
            f"background: transparent; border: none; padding: 0; margin: 0; }}"
        )

    def _refresh_zoom_label_text(self) -> None:
        pct = int(round(self._x_scale * 100.0))
        self._zoom_label.setText(f"{pct}%")
        self._zoom_label.adjustSize()

    def apply_scaled_chart_chrome(self) -> None:
        """부모 ``apply_scaled_style``에서 DPI/폰트 스케일에 맞춰 라벨만 갱신."""
        self._restyle_zoom_label()
        self._refresh_zoom_label_text()

    def _on_shimmer_tick(self) -> None:
        self._shimmer_phase += 0.13
        if self._shimmer_phase > math.tau:
            self._shimmer_phase -= math.tau
        self.update()

    def _on_hover_anim_value(self, v: object) -> None:
        try:
            self._hover_spring = float(v)
        except (TypeError, ValueError):
            self._hover_spring = 0.0
        self.update()

    def _on_pulse_anim_value(self, v: object) -> None:
        try:
            self._pulse = float(v)
        except (TypeError, ValueError):
            self._pulse = 0.0
        self.update()

    def _on_last_bar_h_anim_value(self, v: object) -> None:
        try:
            self._last_bar_draw_h = float(v)
        except (TypeError, ValueError):
            pass
        self.update()

    def _compute_last_bar_target_height_px(
        self,
        kills_override: tuple[int, ...] | None = None,
    ) -> int | None:
        """``paintEvent`` 과 동일 규칙으로 마지막 봉의 목표 막대 높이(px)."""
        n = len(self._series)
        if n <= 0:
            return None
        _n, _bw, _gap, _cw, axis_h = self._layout_metrics()
        plot_h = self.height() - axis_h
        if plot_h < 1:
            return None
        vs = self._viewport_vs()
        if kills_override is not None and len(kills_override) == n:
            kills_list = list(kills_override)
        else:
            sig = self._last_series_sig
            if len(sig) == n:
                kills_list = list(sig)
            else:
                kills_list = []
                for s in self._series:
                    try:
                        kills_list.append(int(s.get("kills", 0)))
                    except (TypeError, ValueError):
                        kills_list.append(0)
        mx_raw = max(kills_list) if kills_list else 0
        mx = max(1, int(mx_raw))
        usable_h = max(1, plot_h - kc_viewport_px_v(vs, 4, lo=2, hi=96))
        min_bar_floor = kc_viewport_px_v(vs, 3, lo=2, hi=36)
        k = kills_list[-1]
        h, _z = self._bar_height_px(
            k, mx, usable_h, mx_raw=mx_raw, min_bar_floor=min_bar_floor,
        )
        return int(h)

    def _sync_last_bar_height_anim_after_series_update(
        self,
        sig_k: tuple[int, ...],
    ) -> None:
        n = len(self._series)
        if n <= 0:
            self._last_bar_h_anim.stop()
            self._last_bar_h_anim_n = -1
            self._last_bar_h_inited = False
            return
        h_t = self._compute_last_bar_target_height_px(kills_override=sig_k)
        if h_t is None:
            return
        if self._last_bar_h_anim_n != n:
            self._last_bar_h_anim.stop()
            self._last_bar_draw_h = float(h_t)
            self._last_bar_h_anim_n = n
            self._last_bar_h_inited = True
            return
        if not self._last_bar_h_inited:
            self._last_bar_draw_h = float(h_t)
            self._last_bar_h_inited = True
            return
        if abs(float(h_t) - self._last_bar_draw_h) < 0.5:
            return
        self._last_bar_h_anim.stop()
        self._last_bar_h_anim.setStartValue(self._last_bar_draw_h)
        self._last_bar_h_anim.setEndValue(float(h_t))
        self._last_bar_h_anim.start()

    def _snap_last_bar_height_to_target(self) -> None:
        n = len(self._series)
        if n <= 0:
            return
        h_t = self._compute_last_bar_target_height_px()
        if h_t is None:
            return
        self._last_bar_h_anim.stop()
        self._last_bar_draw_h = float(h_t)
        self._last_bar_h_anim_n = n
        self._last_bar_h_inited = True

    def _sync_shimmer_timer(self) -> None:
        if len(self._series) > 0:
            if not self._shimmer_timer.isActive():
                self._shimmer_timer.start()
        else:
            self._shimmer_timer.stop()
        self._sync_live_scroll_timer()

    def _live_time_drift_px(self) -> float:
        """Trailing 뷰일 때 현재 봉 구간 경과에 따라 (5분봉이면 1초당 1/300 슬롯 폭)."""
        if self._user_panned or not self._series:
            return 0.0
        n, bw, gap, _, _ = self._layout_metrics()
        if n <= 0:
            return 0.0
        slot = float(bw + gap)
        last = self._series[-1]
        ymdhm = last.get("ymdhm")
        frac = _bucket_intrabucket_time_fraction(
            ymdhm, int(self._bucket_minutes), time.time(),
        )
        return frac * slot

    def _effective_scroll_x(self) -> float:
        return float(self._scroll_x) + self._live_time_drift_px()

    def _on_live_time_scroll_tick(self) -> None:
        if self._user_panned or not self._series:
            return
        self.update()

    def _sync_live_scroll_timer(self) -> None:
        if len(self._series) > 0 and not self._user_panned:
            if not self._live_scroll_timer.isActive():
                self._live_scroll_timer.start()
        else:
            self._live_scroll_timer.stop()

    def _kick_data_pulse(self) -> None:
        if not self._series:
            self._pulse_anim.stop()
            self._pulse = 0.0
            return
        self._pulse_anim.stop()
        self._pulse = 1.0
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.0)
        self._pulse_anim.start()

    def _animate_hover(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_spring)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _emit_view_changed(self) -> None:
        self.viewRangeChanged.emit()

    def indicator_thumb_px(self, track_w: int) -> tuple[int, int]:
        """가로 인디케이터 트랙 너비(track_w) 기준 썸 (left_x, thumb_w). 스크롤 조작 없음."""
        tw = max(1, int(track_w))
        n, _bw, _gap, content_w, _ = self._layout_metrics()
        vw = float(max(1, self.width()))
        if n <= 0 or content_w <= vw + 1e-6:
            return (0, tw)
        mx = max(1e-6, content_w - vw)
        t_w = int(round((vw / content_w) * float(tw)))
        ws = self._viewport_ws()
        t_w = max(kc_viewport_px_h(ws, 5, lo=4, hi=80), min(t_w, tw))
        span = tw - t_w
        eff = self._effective_scroll_x()
        ratio = eff / mx if mx > 1e-6 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        x0 = int(round(ratio * float(span)))
        x0 = max(0, min(x0, span))
        return (x0, t_w)

    def bucket_minutes(self) -> int:
        return self._bucket_minutes

    def set_bucket_minutes(self, bm: int) -> None:
        bm = int(bm)
        if bm == self._bucket_minutes:
            return
        self._bucket_minutes = bm
        self._user_panned = False
        self._x_scale = 1.0
        self._hover_idx = None
        self._tip.hide_tip()
        self._animate_hover(0.0)
        self._refresh_zoom_label_text()
        self.update()
        self._sync_shimmer_timer()
        self._emit_view_changed()

    def set_series(self, series: list[dict]) -> None:
        news = list(series) if series else []
        try:
            sig_k = tuple(_series_kills_at(news, j) for j in range(len(news)))
            sig_r = tuple(
                1 if bool(news[j].get("reload_mark")) else 0
                for j in range(len(news))
            )
        except Exception:
            sig_k = ()
            sig_r = ()
        if (
            not self._user_panned
            and sig_k == self._last_series_sig
            and sig_r == self._last_series_reload_sig
            and len(news) == len(self._series)
        ):
            # main 그래프 캐시 히트 등 — 값 동일해도 실시간 봉-경과 오프셋은 repaint
            self._series = news
            self._sync_live_scroll_timer()
            self.update()
            return
        self._series = news
        self._sync_last_bar_height_anim_after_series_update(sig_k)
        if not self._user_panned:
            self._scroll_to_end()
        else:
            self._clamp_scroll()
        self._sync_shimmer_timer()
        if sig_k != self._last_series_sig or sig_r != self._last_series_reload_sig:
            self._last_series_sig = sig_k
            self._last_series_reload_sig = sig_r
            self._kick_data_pulse()
        self.update()
        self._emit_view_changed()

    def _layout_metrics(self) -> tuple[int, int, int, float, int]:
        n = len(self._series)
        ws = self._viewport_ws()
        vs = self._viewport_vs()
        gap = max(1, kc_viewport_px_h(ws, 2, lo=1, hi=22))
        bw = max(3, int(round(kc_viewport_px_h(ws, 6, lo=3, hi=40) * self._x_scale)))
        vw = max(1, self.width())
        if n <= 0:
            content_w = float(vw)
        else:
            content_w = float(gap + n * (bw + gap))
        axis_h = kc_viewport_px_v(vs, 16, lo=9, hi=48)
        return n, bw, gap, content_w, axis_h

    def _max_scroll(self) -> float:
        _, _, _, content_w, _ = self._layout_metrics()
        vw = max(1, self.width())
        return max(0.0, content_w - float(vw))

    def _scroll_to_end(self) -> None:
        self._scroll_x = self._max_scroll()

    def _clamp_scroll(self) -> None:
        mx = self._max_scroll()
        self._scroll_x = max(0.0, min(float(self._scroll_x), mx))

    def _bar_color(self, i: int) -> QColor:
        if i <= 0 or not self._series:
            return QColor(T.FG_DIM)
        try:
            prev = int(self._series[i - 1].get("kills", 0))
            curr = int(self._series[i].get("kills", 0))
        except (TypeError, ValueError):
            return QColor(T.FG_DIM)
        if curr > prev:
            return QColor(T.ACCENT)
        if curr < prev:
            return QColor("#fca5a5")
        return QColor(T.FG_DIM)

    def _bar_height_px(
        self,
        k: int,
        mx: int,
        usable_h: int,
        *,
        mx_raw: int,
        min_bar_floor: int,
    ) -> tuple[int, bool]:
        """(막대 높이, 0킬 버킷 여부). 0킬 막대는 항상 1킬 막대보다 낮게(얇은 자리 표시)."""
        uh = max(1, int(usable_h))
        kk = max(0, int(k))
        min_non = max(2, int(min_bar_floor))
        if kk <= 0:
            if mx_raw <= 0:
                z = max(2, min_bar_floor)
                return (min(z, uh), True)
            mscale = max(1, int(mx))
            h_one = max(min_non, min(int(round(float(uh) / float(mscale))), uh))
            if h_one <= 1:
                z = 1
            else:
                z = max(1, min(int(round(float(h_one) * 0.38)), h_one - 1))
            return (max(1, min(z, uh)), True)
        m = max(1, int(mx))
        h = int(round(float(uh) * (float(kk) / float(m))))
        return (max(min_non, min(h, uh)), False)

    def _hit_test(self, pos: QPoint) -> int | None:
        n, bw, gap, _, axis_h = self._layout_metrics()
        if n <= 0:
            return None
        plot_h = self.height() - axis_h
        if pos.y() < 0 or pos.y() > plot_h:
            return None
        xv = float(pos.x()) + self._effective_scroll_x()
        if xv < float(gap):
            return None
        slot = float(bw + gap)
        rel = xv - float(gap)
        i = int(rel // slot)
        rem = rel - float(i) * slot
        if rem > float(bw):
            return None
        if 0 <= i < n:
            return i
        return None

    def _paint_zero_kill_bar(
        self,
        p: QPainter,
        x: float,
        plot_bottom: float,
        w: int,
        h: int,
        *,
        accent_rgb: tuple[int, int, int],
        is_hover: bool,
        sp5: float,
    ) -> None:
        """0킬 구간 — 액센트 틴트 + 선명한 테두리(배경 대비). 글래스 경로/조기 return 없음."""
        hs = self._hover_spring if is_hover else 0.0
        pad = 1.0 + 1.25 * hs
        xo = float(x) - pad * 0.5
        wo = max(2.0, float(w) + pad * 2.0)
        ho = max(3.0, float(h) + 5.0 * hs)
        yo = float(plot_bottom) - ho
        r, g, b = accent_rgb
        fill_a = int(72 + 100 * hs)
        edge_a = int(165 + 75 * hs)
        rz = float(max(1.5, min(sp5, wo * 0.38, ho * 0.5)))
        rr = QRectF(xo, yo, wo, ho)
        fc = QColor(r, g, b, min(255, fill_a))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fc)
        p.drawRoundedRect(rr, rz, rz)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(r, g, b, min(255, edge_a)), max(1.25, 1.35 + 0.65 * hs)))
        p.drawRoundedRect(rr, rz, rz)

    def _paint_glass_bar(
        self,
        p: QPainter,
        x: float,
        y: float,
        w: int,
        h: int,
        base: QColor,
        *,
        bi: int,
        is_hover: bool,
    ) -> None:
        hs = self._hover_spring if is_hover else 0.0
        pulse = self._pulse
        phase = self._shimmer_phase
        pad = 2.0 * hs
        lift = 5.0 * hs
        xo = x - pad * 0.5
        wo = max(2.0, float(w) + pad)
        ho = max(2.0, float(h) + lift)
        yo = float(y) - lift
        vs = self._viewport_vs()
        corner_cap = float(kc_viewport_px_v(vs, 4, lo=2, hi=48))
        r = float(max(1, min(corner_cap, int(wo) // 2, int(ho) // 3)))

        col = QColor(base)
        if pulse > 0.001:
            t = 0.13 * pulse
            col = QColor(
                min(255, int(col.red() + (255 - col.red()) * t)),
                min(255, int(col.green() + (255 - col.green()) * t)),
                min(255, int(col.blue() + (255 - col.blue()) * t)),
            )
        top_c = QColor(
            min(255, col.red() + 26),
            min(255, col.green() + 30),
            min(255, col.blue() + 24),
        )
        mid_c = QColor(col)
        bot_c = QColor(
            max(0, col.red() - 20),
            max(0, col.green() - 22),
            max(0, col.blue() - 18),
        )
        path = QPainterPath()
        path.addRoundedRect(xo, yo, wo, ho, r, r)

        body = QLinearGradient(xo, yo, xo, yo + ho)
        body.setColorAt(0.0, top_c)
        body.setColorAt(0.48, mid_c)
        body.setColorAt(1.0, bot_c)
        p.fillPath(path, body)

        sh = 0.5 + 0.5 * math.sin(phase + float(bi) * 0.42)
        ga = int(30 + 42 * sh + 22 * pulse)
        gloss = QLinearGradient(xo, yo, xo, yo + ho * 0.58)
        gloss.setColorAt(0.0, QColor(255, 255, 255, min(130, ga)))
        gloss.setColorAt(0.32, QColor(255, 255, 255, int(16 + 22 * sh)))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, gloss)

        edge = QLinearGradient(xo, yo, xo + wo, yo)
        edge.setColorAt(0.0, QColor(255, 255, 255, 0))
        edge.setColorAt(0.85, QColor(255, 255, 255, 0))
        edge.setColorAt(1.0, QColor(255, 255, 255, int(28 + 72 * hs)))
        p.fillPath(path, edge)

        rim = int(52 + 130 * hs + 70 * pulse)
        p.setPen(
            QPen(
                QColor(255, 255, 255, min(200, rim)),
                max(1.0, 1.0 + 0.8 * hs),
            ),
        )
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def _paint_reload_marker(
        self,
        p: QPainter,
        cx: float,
        bar_top: float,
        bw: int,
    ) -> None:
        """막대 상단 중앙에 아래를 가리키는 작은 빨간 역삼각형 (Reload 완료 구간)."""
        vs = self._viewport_vs()
        wbar = max(1.0, float(bw))
        h_tri = float(
            max(3.0, min(float(kc_viewport_px_v(vs, 6, lo=3, hi=64)), wbar * 0.9)),
        )
        half_w = max(3.0, min(wbar * 0.4, h_tri * 0.75))
        tip_y = float(bar_top)
        path = QPainterPath()
        path.moveTo(cx, tip_y)
        path.lineTo(cx - half_w, tip_y - h_tri)
        path.lineTo(cx + half_w, tip_y - h_tri)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 68, 68, 255))
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen_w = float(kc_viewport_px_v(vs, 1, lo=1, hi=6)) * 0.32
        p.setPen(
            QPen(
                QColor(120, 23, 31, 228),
                max(0.6, pen_w),
            ),
        )
        p.drawPath(path)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        n, bw, gap, content_w, axis_h = self._layout_metrics()
        plot_h = self.height() - axis_h
        plot_bottom = self.height() - axis_h

        vs = self._viewport_vs()
        divider_w = max(1, kc_viewport_px_v(vs, 1, lo=1, hi=6) // 2 or 1)

        bg = QColor(T.SURFACE)
        p.fillRect(self.rect(), bg)

        p.setPen(QPen(QColor(T.DIVIDER), divider_w))
        p.drawLine(0, plot_bottom, self.width(), plot_bottom)

        if n <= 0:
            p.setPen(QColor(T.FG_MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "데이터 없음")
            p.end()
            return

        # Hot path: reuse series signature from set_series — avoid per-paint dict scans (cProfile-heavy)
        sig = self._last_series_sig
        if len(sig) == n and n > 0:
            kills_list = list(sig)
        else:
            kills_list = []
            for s in self._series:
                try:
                    kills_list.append(int(s.get("kills", 0)))
                except (TypeError, ValueError):
                    kills_list.append(0)
        mx_raw = max(kills_list) if kills_list else 0
        mx = max(1, int(mx_raw))

        usable_h = max(1, plot_h - kc_viewport_px_v(vs, 4, lo=2, hi=96))
        sx = self._effective_scroll_x()
        vw = self.width()
        min_bar_floor = kc_viewport_px_v(vs, 3, lo=2, hi=36)

        sp5f = float(kc_viewport_px_v(vs, 5, lo=3, hi=60))
        accent_rgb = _parse_hex_rgb(T.ACCENT)
        hi = self._hover_idx
        visible: list[tuple[int, float, int, int, bool, bool]] = []
        last_i = n - 1
        uh_cap = max(1, usable_h)
        for i in range(n):
            x0 = float(gap) + float(i) * float(bw + gap) - sx
            if x0 + float(bw) < 0.0 or x0 > float(vw):
                continue
            k = kills_list[i]
            h, is_zero = self._bar_height_px(
                k, mx, usable_h, mx_raw=mx_raw, min_bar_floor=min_bar_floor
            )
            if i == last_i and self._last_bar_h_inited:
                h = int(
                    round(max(1.0, min(float(self._last_bar_draw_h), float(uh_cap)))),
                )
            rmk = False
            try:
                rmk = bool(self._series[i].get("reload_mark"))
            except Exception:
                pass
            visible.append((i, x0, k, h, is_zero, rmk))

        def _paint_entry(
            i: int, x0: float, k: int, h: int, is_zero: bool, *, hover: bool,
        ) -> None:
            if is_zero:
                self._paint_zero_kill_bar(
                    p,
                    x0,
                    float(plot_bottom),
                    bw,
                    h,
                    accent_rgb=accent_rgb,
                    is_hover=hover,
                    sp5=sp5f,
                )
            else:
                y1 = float(plot_bottom - h)
                col = self._bar_color(i)
                self._paint_glass_bar(
                    p,
                    x0,
                    y1,
                    bw,
                    h,
                    col,
                    bi=i,
                    is_hover=hover,
                )

        rest = [t for t in visible if hi is None or t[0] != hi]
        hi_tup = next((t for t in visible if hi is not None and t[0] == hi), None)
        rest_nz = [t for t in rest if not t[4]]
        rest_z = [t for t in rest if t[4]]
        for i, x0, k, h, is_z, _rmk in rest_nz:
            _paint_entry(i, x0, k, h, is_z, hover=False)
        for i, x0, k, h, is_z, _rmk in rest_z:
            _paint_entry(i, x0, k, h, is_z, hover=False)
        if hi_tup is not None:
            i, x0, k, h, is_z, _rmk = hi_tup
            _paint_entry(i, x0, k, h, is_z, hover=True)

        for i, x0, _k, h, _is_z, rmk in visible:
            if not rmk:
                continue
            cx = x0 + float(bw) * 0.5
            top = float(plot_bottom - h)
            self._paint_reload_marker(p, cx, top, bw)

        p.end()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._snap_last_bar_height_to_target()
        zm_x = kc_viewport_px_h(self._viewport_ws(), 4, lo=2, hi=96)
        zm_y = kc_viewport_px_v(self._viewport_vs(), 4, lo=2, hi=96)
        self._zoom_label.move(zm_x, zm_y)
        self._clamp_scroll()
        self._emit_view_changed()

    def mouseMoveEvent(self, e) -> None:
        if self._zoom_drag_on:
            dx = float(e.globalPosition().x()) - float(self._zoom_drag_start_global_x)
            self._apply_x_scale(
                float(self._zoom_drag_start_scale) * math.exp(0.002 * dx),
            )
            e.accept()
            return
        idx = self._hit_test(e.position().toPoint())
        gpos = e.globalPosition().toPoint()
        if idx != self._hover_idx:
            self._hover_idx = idx
            if idx is not None and 0 <= idx < len(self._series):
                self._animate_hover(1.0)
                self._tip.update_for_bar(
                    self._series, idx, gpos, self._bucket_minutes,
                )
            else:
                self._animate_hover(0.0)
                self._tip.hide_tip()
            self.update()
        elif idx is not None and 0 <= idx < len(self._series):
            t = time.monotonic()
            if t - self._tip_repos_t < 0.022:
                super().mouseMoveEvent(e)
                return
            self._tip_repos_t = t
            self._tip.reposition_only(gpos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._zoom_drag_on and e.button() == Qt.MouseButton.LeftButton:
            self._zoom_drag_on = False
            self.releaseMouse()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e) -> None:
        self._hover_idx = None
        self._tip.hide_tip()
        self._animate_hover(0.0)
        self.update()
        super().leaveEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        mods = e.modifiers()

        if mods & Qt.KeyboardModifier.ControlModifier:
            delta = e.angleDelta().y()
            if delta == 0:
                e.ignore()
                return
            factor = 1.12 if delta > 0 else 1.0 / 1.12
            new_scale = max(0.25, min(5.0, self._x_scale * factor))
            if abs(new_scale - self._x_scale) < 1e-6:
                e.accept()
                return
            self._apply_x_scale(new_scale)
            e.accept()
            return

        if mods & Qt.KeyboardModifier.ShiftModifier:
            self._user_panned = True
            self._last_user_pan_mono = float(time.monotonic())
            delta = e.angleDelta().y()
            step = float(kc_viewport_px_h(self._viewport_ws(), 40, lo=14, hi=420))
            self._scroll_x -= (delta / 120.0) * step
            self._clamp_scroll()
            self._sync_shimmer_timer()
            e.accept()
            self.update()
            self._emit_view_changed()
            return

        super().wheelEvent(e)


class _KillCounterChartHRangeIndicator(QWidget):
    """차트 가로 뷰 위치만 표시(스크롤바 형태, 입력 없음)."""

    __slots__ = ("_canvas",)

    def __init__(
        self,
        canvas: _KillCounterBucketChartCanvas,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        vs0 = canvas._viewport_vs()
        self.setFixedHeight(kc_viewport_px_v(vs0, 6, lo=4, hi=96))
        canvas.viewRangeChanged.connect(self.update)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            p.end()
            return
        vs = self._canvas._viewport_vs()
        r = max(1, min(h // 2, kc_viewport_px_v(vs, 3, lo=2, hi=72)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T.DIVIDER))
        p.drawRoundedRect(0, 0, w, h, r, r)
        tx, t_w = self._canvas.indicator_thumb_px(w)
        ac = QColor(T.ACCENT)
        ac.setAlpha(140)
        p.setBrush(ac)
        p.drawRoundedRect(tx, 0, t_w, h, r, r)
        p.end()


def _bucket_button_qss_initial(vs: float, ws: float) -> str:
    """첫 프레임용 — 이후 `_refit_bucket_button_typography` 가 폭 맞춤 pt로 덮어씀."""
    pv = kc_viewport_px_v(vs, 6, lo=4, hi=96)
    pv = max(1, int(round(float(pv) * 0.7)))
    return (
        panel_secondary_button_qss(
            font_size=kc_viewport_spt_v(vs, 10.5),
            letter_spacing="0px",
            vertical_padding_px=pv,
            horizontal_padding_px=0,
        )
        + f"QPushButton:checked {{ background: {T.BTN_ON}; border: 1px solid {T.BTN_ON_BORDER}; }}"
    )


class KillCounterBucketChartPane(QWidget):
    """봉 선택 버튼 + 캔버스. ``refresh_from_mod()``로 ``main`` 시리즈 갱신."""

    __slots__ = ("_btn_group", "_bucket_btn_row", "_canvas", "_h_range_ind", "_m", "_pane_outer_lay")

    def __init__(self, pipela_mod, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        v = QVBoxLayout(self)
        self._pane_outer_lay = v
        v.setContentsMargins(0, 0, 0, 0)
        vs = kc_viewport_height_scale_from_widget_chain(self)
        ws = kc_viewport_width_scale_from_widget_chain(self)
        sp_v = kc_viewport_px_v(vs, 4, lo=2, hi=96)
        sp_h = kc_viewport_px_h(ws, 4, lo=2, hi=96)
        v.setSpacing(sp_v)
        row = QHBoxLayout()
        self._bucket_btn_row = row
        row.setSpacing(sp_h)
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        qss = _bucket_button_qss_initial(vs, ws)
        first_checked: QPushButton | None = None
        for bm, label in (
            (5, "5분"),
            (30, "30분"),
            (60, "1시간"),
            (360, "6시간"),
            (720, "12시간"),
        ):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setStyleSheet(qss)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setProperty("bucket_minutes", bm)
            self._btn_group.addButton(b)
            row.addWidget(b, 1)
            if bm == 5:
                first_checked = b
        v.addLayout(row)
        self._canvas = _KillCounterBucketChartCanvas(self)
        v.addWidget(self._canvas, 1)
        self._h_range_ind = _KillCounterChartHRangeIndicator(self._canvas, self)
        v.addWidget(self._h_range_ind, 0)
        self._btn_group.buttonClicked.connect(self._on_bucket_button)
        if first_checked is not None:
            first_checked.setChecked(True)
        self._canvas.set_bucket_minutes(5)
        self._h_range_ind.update()
        QTimer.singleShot(0, self._refit_bucket_button_typography)

    def _refit_bucket_button_typography(self) -> None:
        vs = kc_viewport_height_scale_from_widget_chain(self)
        ws = kc_viewport_width_scale_from_widget_chain(self)
        pv = kc_viewport_px_v(vs, 6, lo=4, hi=96)
        pv = max(1, int(round(float(pv) * 0.7)))
        buttons = self._btn_group.buttons()
        n = len(buttons)
        if n <= 0:
            return
        fs = kc_viewport_spt_v(vs, 10.5)
        # Bucket 버튼은 폭이 좁을 수 있어 letter-spacing을 0으로 고정해 좌우 클리핑을 줄인다.
        ls = "0px"
        chk = f"QPushButton:checked {{ background: {T.BTN_ON}; border: 1px solid {T.BTN_ON_BORDER}; }}"
        for b in buttons:
            b.setStyleSheet(
                panel_secondary_button_qss(
                    font_size=fs,
                    letter_spacing=ls,
                    vertical_padding_px=pv,
                    horizontal_padding_px=0,
                )
                + chk
            )

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._refit_bucket_button_typography()
        # 폭-피팅 제거: 추가 리핏 불필요

    def refresh_viewport_dependent_chrome(self) -> None:
        vs = kc_viewport_height_scale_from_widget_chain(self)
        ws = kc_viewport_width_scale_from_widget_chain(self)
        sp_v = kc_viewport_px_v(vs, 4, lo=2, hi=96)
        sp_h = kc_viewport_px_h(ws, 4, lo=2, hi=96)
        self._pane_outer_lay.setSpacing(sp_v)
        self._bucket_btn_row.setSpacing(sp_h)
        self._refit_bucket_button_typography()
        self._canvas.setMinimumHeight(kc_viewport_px_v(vs, 112, lo=40, hi=320))
        self._h_range_ind.setFixedHeight(kc_viewport_px_v(vs, 6, lo=4, hi=96))
        self._canvas._restyle_zoom_label()
        self._canvas._refresh_zoom_label_text()
        self._h_range_ind.update()
        self._canvas.update()

    def apply_scaled_style(self) -> None:
        self.refresh_viewport_dependent_chrome()
        self._canvas.apply_scaled_chart_chrome()

    def _on_bucket_button(self, btn: QAbstractButton) -> None:
        v = btn.property("bucket_minutes")
        try:
            bm = int(v)
        except (TypeError, ValueError):
            return
        self._canvas.set_bucket_minutes(bm)
        self.refresh_from_mod()

    def refresh_from_mod(self) -> None:
        m = self._m
        bm = self._canvas.bucket_minutes()
        series = m._kill_counter_graph_bucket_series(bm)
        self._canvas.set_series(series)
