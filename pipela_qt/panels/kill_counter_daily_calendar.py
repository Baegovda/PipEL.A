"""킬 카운터 일별 캘린더 — 호버 툴팁·셀 강조."""

from __future__ import annotations

import calendar as cal_std
import time
from functools import partial
from typing import Any

from PyQt6.QtCore import QDate, QEvent, QLocale, QModelIndex, QPoint, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QTextCharFormat
from PyQt6.QtWidgets import (
    QAbstractButton,
    QBoxLayout,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from pipela_qt import theme as T
from pipela_qt.kill_counter_viewport_metrics import (
    kc_viewport_height_scale_from_widget_chain,
    kc_viewport_px_h,
    kc_viewport_px_v,
    kc_viewport_spt_v,
    kc_viewport_width_scale_from_widget_chain,
)
from pipela_qt.ui_adaptive import letter_spacing_qss


def _kc_cal_vs(owner: QWidget) -> float:
    return kc_viewport_height_scale_from_widget_chain(owner)


def _kc_cal_ws(owner: QWidget) -> float:
    return kc_viewport_width_scale_from_widget_chain(owner)

# eventFilter 핫패스 — QEvent.Type 대신 int 비교
_EV_MOUSE_MOVE = int(QEvent.Type.MouseMove)
_EV_LEAVE = int(QEvent.Type.Leave)
_EV_HOVER_LEAVE = int(QEvent.Type.HoverLeave)

_KR_LOCALE = QLocale(QLocale.Language.Korean, QLocale.Country.SouthKorea)


def _theme_accent_rgb() -> tuple[int, int, int]:
    s = (T.ACCENT or "").strip().lstrip("#")
    if len(s) >= 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return (61, 212, 201)


def daily_cal_day_mark_color() -> QColor:
    r, g, b = _theme_accent_rgb()
    return QColor(r, g, b, 50)


def _blend_colors(bottom: QColor, top: QColor) -> QColor:
    ta = top.alpha() / 255.0
    if ta <= 0:
        return QColor(bottom)
    inv = 1.0 - ta
    r = min(255, int(top.red() * ta + bottom.red() * inv))
    g = min(255, int(top.green() * ta + bottom.green() * inv))
    b = min(255, int(top.blue() * ta + bottom.blue() * inv))
    a = min(255, int(top.alpha() + bottom.alpha() * inv))
    return QColor(r, g, b, a)


def _qt_day_of_week_int(dow) -> int:
    """Qt.DayOfWeek 열거형·정수 모두 1..7 (월=1 … 일=7) 정수로."""
    if isinstance(dow, int):
        return dow
    v = getattr(dow, "value", dow)
    return int(v)


def _first_of_month_grid_column(qd_first: QDate, cal: QCalendarWidget) -> int:
    """월 1일이 데이터 행(r≥1)에서 놓인 열 — ``QTableView`` 열 0..6."""
    dow = _qt_day_of_week_int(qd_first.dayOfWeek())
    fdow = _qt_day_of_week_int(cal.firstDayOfWeek())
    return (dow - fdow + 7) % 7


def _daily_snapshot_day_delta_fg_hex(m: Any, qd: QDate, snap: dict) -> str:
    """전일 대비 diff → ``main._kill_counter_daily_calendar_delta_fg`` 와 동일 규칙의 hex."""
    key = qd.toString(Qt.DateFormat.ISODate)
    n = int(snap.get(key, 0))
    prev = int(snap.get(qd.addDays(-1).toString(Qt.DateFormat.ISODate), 0))
    diff = n - prev
    try:
        return str(m._kill_counter_daily_calendar_delta_fg(diff))
    except Exception:
        if diff > 0:
            return str(T.ACCENT)
        if diff < 0:
            return str(T.STATUS_ERR)
        return str(T.FG_MUTED)


def index_to_calendar_qdate(cal: QCalendarWidget, index: QModelIndex) -> QDate | None:
    if not index.isValid():
        return None
    r, col = index.row(), index.column()
    # 행 0: 요일 헤더. 열은 0..6 이 일~토(또는 주 시작 설정) — 열 0 을 빼면 한 칸 오른쪽으로 밀린다.
    if r <= 0 or not (0 <= col <= 6):
        return None
    y, mo = cal.yearShown(), cal.monthShown()
    first = QDate(y, mo, 1)
    if not first.isValid():
        return None
    start_col = _first_of_month_grid_column(first, cal)
    first_cell_date = first.addDays(-start_col)
    idx = (r - 1) * 7 + col
    qd = first_cell_date.addDays(idx)
    return qd if qd.isValid() else None


class DailyCalDayHoverPopup(QFrame):
    """반투명 배경의 날짜·킬·전일대비 오버레이."""

    __slots__ = (
        "_deferred_gpos",
        "_deferred_token",
        "_kc_prewarmed",
        "_l1",
        "_l2",
        "_l3",
        "_tip_radius",
        "_last_l2_qss",
        "_last_l3_qss",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        # KillCounterDailyCalendar 자식 — 별도 Tool HWND move 비용 회피(그래프 툴팁과 동일).
        super().__init__(parent)
        self.setObjectName("pipelaKcCalHoverTip")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        vs = _kc_cal_vs(self)
        ws = _kc_cal_ws(self)
        pad_h = kc_viewport_px_h(ws, 10, lo=4, hi=176)
        pad_v = kc_viewport_px_v(vs, 10, lo=4, hi=176)
        br = kc_viewport_px_v(vs, 8, lo=4, hi=176)
        self._tip_radius = int(br)
        self.setStyleSheet(
            f"QFrame#pipelaKcCalHoverTip {{ background: transparent; border: none; }}"
            f"QFrame#pipelaKcCalHoverTip QLabel {{ background: transparent; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(pad_h, pad_v, pad_h, pad_v)
        lay.setSpacing(kc_viewport_px_v(vs, 4, lo=2, hi=96))
        self._l1 = QLabel()
        self._l2 = QLabel()
        self._l3 = QLabel()
        for lb in (self._l1, self._l2, self._l3):
            lb.setWordWrap(False)
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._l1.setStyleSheet(
            f"color: {T.FG_MUTED}; font-weight: 700; font-size: {kc_viewport_spt_v(vs, 8.75)}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()};",
        )
        lay.addWidget(self._l1)
        lay.addWidget(self._l2)
        lay.addWidget(self._l3)
        shadow = QHBoxLayout()
        shadow.addStretch(1)
        lay.addLayout(shadow)
        self._deferred_token = 0
        self._deferred_gpos: QPoint | None = None
        self._kc_prewarmed = False
        self._last_l2_qss: str | None = None
        self._last_l3_qss: str | None = None

    def prewarm_offscreen(self) -> None:
        if self._kc_prewarmed:
            return
        self._kc_prewarmed = True
        try:
            self.adjustSize()
            ixw_vs = _kc_cal_vs(self)
            ixw_ws = _kc_cal_ws(self)
            self.resize(
                kc_viewport_px_h(ixw_ws, 120, lo=48, hi=864),
                max(self.height(), kc_viewport_px_v(ixw_vs, 48, lo=22, hi=348)),
            )
            self.setGeometry(-5000, -5000, self.width(), self.height())
            self.show()
            self.hide()
        except Exception:
            pass

    def _schedule_deferred_move(self, gpos: QPoint) -> None:
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
        p.fillPath(path, QColor(0, 0, 0, int(255 * 0.7)))
        ar, ag, ab = _theme_accent_rgb()
        edge = QColor(ar, ag, ab, int(255 * 1))
        p.setPen(QPen(edge, max(1.0, float(kc_viewport_px_v(_kc_cal_vs(self), 1, lo=1, hi=16)))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def update_for_day(
        self, m: Any, qd: QDate, global_pos: QPoint, snap: dict | None = None
    ) -> None:
        key = qd.toString(Qt.DateFormat.ISODate)
        if snap is None:
            try:
                snap = m._kill_counter_stats_daily_snapshot()
            except Exception:
                snap = {}
        n = int(snap.get(key, 0))
        pd = qd.addDays(-1)
        pk = pd.toString(Qt.DateFormat.ISODate)
        prev = int(snap.get(pk, 0))
        diff = n - prev
        try:
            dtxt = m._kill_counter_daily_calendar_delta_fmt(diff)
            dfg = m._kill_counter_daily_calendar_delta_fg(diff)
        except Exception:
            dtxt = f"{diff:+,}" if diff else "0"
            dfg = T.FG_MUTED
        if diff > 0:
            kfg = T.ACCENT
        elif diff < 0:
            kfg = T.STATUS_ERR
        else:
            kfg = T.FG

        vs = _kc_cal_vs(self)
        ws = _kc_cal_ws(self)
        l2q = (
            f"color: {kfg}; font-weight: 800; font-size: {kc_viewport_spt_v(vs, 10.25)}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()};"
        )
        l3q = (
            f"color: {dfg}; font-weight: 700; font-size: {kc_viewport_spt_v(vs, 9.25)}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()};"
        )
        self._l1.setText(_KR_LOCALE.toString(qd, "yyyy-MM-dd (ddd)"))
        self._l2.setText(f"{n:,} 킬")
        if l2q != self._last_l2_qss:
            self._l2.setStyleSheet(l2q)
            self._last_l2_qss = l2q
        self._l3.setText(dtxt)
        if l3q != self._last_l3_qss:
            self._l3.setStyleSheet(l3q)
            self._last_l3_qss = l3q
        self.adjustSize()
        self._schedule_deferred_move(global_pos)

    def _move_near(self, gpos: QPoint) -> None:
        m = max(
            kc_viewport_px_h(_kc_cal_ws(self), 14, lo=6, hi=260),
            kc_viewport_px_v(_kc_cal_vs(self), 14, lo=6, hi=260),
        )
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
            self._schedule_deferred_move(global_pos)

    def hide_tip(self) -> None:
        self._deferred_token += 1
        self._deferred_gpos = None
        self.hide()


class KillCounterDailyCalendar(QCalendarWidget):
    """날짜 셀 호버 시 포맷·커스텀 툴팁."""

    __slots__ = ("_hover_qdate", "_hover_repos_t", "_m", "_popup", "_tv")

    def __init__(self, pipela_mod: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QCalendarWidget.SelectionMode.NoSelection)
        self._m = pipela_mod
        self._tv: QTableView | None = None
        self._hover_qdate: QDate | None = None
        self._hover_repos_t = 0.0
        self._popup = DailyCalDayHoverPopup(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.currentPageChanged.connect(self._ensure_nav_year_before_month)
        self.currentPageChanged.connect(self._on_month_page_clear_hover)

    def _on_month_page_clear_hover(self, _y: int, _m: int) -> None:
        """다른 달로 넘어가면 호버 상태·팝업만 정리 — ``refresh_marks`` 는 패널 쪽이 호출."""
        if self._hover_qdate is not None:
            self._hover_qdate = None
        self._popup.hide_tip()

    def _ensure_nav_year_before_month(self) -> None:
        """Qt 기본은 「월 · 연」 순 — 「연 · 월」 로 맞춤."""
        nav = self.findChild(QWidget, "qt_calendar_navigationbar")
        if nav is None:
            return
        lay = nav.layout()
        if not isinstance(lay, QHBoxLayout):
            return
        month_btn = nav.findChild(QAbstractButton, "qt_calendar_monthbutton")
        year_btn = nav.findChild(QAbstractButton, "qt_calendar_yearbutton")
        if month_btn is None or year_btn is None:
            return
        idx_m = lay.indexOf(month_btn)
        idx_y = lay.indexOf(year_btn)
        if idx_m < 0 or idx_y < 0:
            return
        if idx_y < idx_m:
            return
        lay.removeWidget(month_btn)
        lay.removeWidget(year_btn)
        ins = min(idx_m, idx_y)
        lay.insertWidget(ins, year_btn)
        lay.insertWidget(ins + 1, month_btn)

    def _tighten_calendar_nav_cluster(self) -> None:
        """기본 내비에 좌·우 ``addStretch`` 가 있어 ◀·▶ 가 캘린더 양끝으로 벌어짐 — 스페이서 제거·간격 축소."""
        nav = self.findChild(QWidget, "qt_calendar_navigationbar")
        if nav is None:
            return
        lay = nav.layout()
        if not isinstance(lay, QBoxLayout):
            return
        i = 0
        while i < lay.count():
            it = lay.itemAt(i)
            if it is None:
                i += 1
                continue
            if it.spacerItem() is not None:
                lay.takeAt(i)
                continue
            i += 1
        # 한 줄에 ◀·연·월·▶ 를 최대한 붙임(기본 QHBox spacing·스페이서 제거 후 0~1px)
        vsn = _kc_cal_vs(self)
        wsn = _kc_cal_ws(self)
        lay.setSpacing(max(0, int(round(kc_viewport_px_h(wsn, 0.5, lo=0, hi=96)))))
        h = max(0, kc_viewport_px_h(wsn, 2, lo=1, hi=96))
        v = max(0, kc_viewport_px_v(vsn, 2, lo=1, hi=96))
        lay.setContentsMargins(h, v, h, v)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    def _setup_calendar_navigation_layout(self) -> None:
        """연·월 순서 맞춘 뒤 내비를 한 덩어리로 붙임."""
        self._ensure_nav_year_before_month()
        self._tighten_calendar_nav_cluster()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        QTimer.singleShot(0, self._setup_calendar_navigation_layout)
        QTimer.singleShot(80, self._tighten_calendar_nav_cluster)
        QTimer.singleShot(90, self._popup.prewarm_offscreen)
        if self._tv is None:
            self._tv = self.findChild(QTableView)
            if self._tv is not None:
                self._tv.viewport().setMouseTracking(True)
                self._tv.viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if self._tv is not None and obj is self._tv.viewport():
            et = int(event.type())
            if et == _EV_MOUSE_MOVE:
                me = event
                if isinstance(me, QMouseEvent):
                    self._on_grid_hover(me)
                return False
            if et in (_EV_LEAVE, _EV_HOVER_LEAVE):
                self._clear_hover()
                return False
        return super().eventFilter(obj, event)

    def _apply_one_day_grid_format(self, qd: QDate, snap: dict, *, hover: bool) -> None:
        """`refresh_marks` 와 동일 규칙 — 단일 ``qd`` 셀만(호버 갱신용, 42칸+월 루프 생략)."""
        if not qd.isValid():
            return
        cal = self
        hit_bg = daily_cal_day_mark_color()
        panel_bg = QColor(T.PANEL_BG)
        y, mon = cal.yearShown(), cal.monthShown()
        _last = cal_std.monthrange(y, mon)[1]
        key = qd.toString(Qt.DateFormat.ISODate)
        n = 0
        try:
            n = int(snap.get(key, 0))
        except (TypeError, ValueError):
            n = 0
        if hover:
            accent_glow = QColor(T.ACCENT)
            accent_glow.setAlpha(72)
            base = hit_bg if n > 0 else panel_bg
            bg = _blend_colors(base, accent_glow)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(_daily_snapshot_day_delta_fg_hex(self._m, qd, snap)))
            fmt.setBackground(bg)
            fmt.setFontWeight(QFont.Weight.DemiBold)
        else:
            if qd.year() == y and qd.month() == mon and 1 <= qd.day() <= _last:
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(_daily_snapshot_day_delta_fg_hex(self._m, qd, snap)))
                if n > 0:
                    fmt.setBackground(hit_bg)
            else:
                # 이전/다음 달 격자 칸 — 기본은 포맷 비움(``refresh_marks`` 의 42칸 clear 와 동일)
                fmt = QTextCharFormat()
        cal.setDateTextFormat(qd, fmt)

    def _on_grid_hover(self, me: QMouseEvent) -> None:
        if self._tv is None:
            return
        idx = self._tv.indexAt(me.position().toPoint())
        qd = index_to_calendar_qdate(self, idx)
        gpos = me.globalPosition().toPoint()
        if qd is None or not qd.isValid():
            self._clear_hover()
            return
        if self._hover_qdate != qd:
            try:
                snap = self._m._kill_counter_stats_daily_snapshot()
            except Exception:
                snap = {}
            old = self._hover_qdate
            if old is not None and old.isValid() and old != qd:
                self._apply_one_day_grid_format(old, snap, hover=False)
            self._hover_qdate = QDate(qd)
            self._apply_one_day_grid_format(self._hover_qdate, snap, hover=True)
            self.update()
            if self._tv is not None:
                self._tv.viewport().update()
            self._popup.update_for_day(self._m, qd, gpos, snap)
        else:
            t = time.monotonic()
            if t - self._hover_repos_t < 0.022:
                return
            self._hover_repos_t = t
            self._popup.reposition_only(gpos)

    def _clear_hover(self) -> None:
        if self._hover_qdate is not None:
            hq = self._hover_qdate
            self._hover_qdate = None
            try:
                snap = self._m._kill_counter_stats_daily_snapshot()
            except Exception:
                snap = {}
            self._apply_one_day_grid_format(hq, snap, hover=False)
            self.update()
            if self._tv is not None:
                self._tv.viewport().update()
        self._popup.hide_tip()

    def refresh_marks(self) -> None:
        cal = self
        y, mon = cal.yearShown(), cal.monthShown()
        first = QDate(y, mon, 1)
        if not first.isValid():
            return
        # 격자에 보이는 42일(이전·다음 달 일부 포함) 전부 포맷 초기화 — 월말만 지우면
        # 맨 위/아래 행의 전월·익월 날짜에 이전 세션의 배경(teal)이 남는다(QTableView 셀 재사용).
        start_col = _first_of_month_grid_column(first, cal)
        first_cell = first.addDays(-start_col)
        for i in range(42):
            qd = first_cell.addDays(i)
            if qd.isValid():
                cal.setDateTextFormat(qd, QTextCharFormat())
        _last = cal_std.monthrange(y, mon)[1]
        try:
            snap = self._m._kill_counter_stats_daily_snapshot()
        except Exception:
            snap = {}
        hit_bg = daily_cal_day_mark_color()
        panel_bg = QColor(T.PANEL_BG)
        accent_glow = QColor(T.ACCENT)
        accent_glow.setAlpha(72)

        for d in range(1, _last + 1):
            qd = QDate(y, mon, d)
            key = qd.toString(Qt.DateFormat.ISODate)
            try:
                n = int(snap.get(key, 0))
            except (TypeError, ValueError):
                n = 0
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(_daily_snapshot_day_delta_fg_hex(self._m, qd, snap)))
            if n > 0:
                fmt.setBackground(hit_bg)
            cal.setDateTextFormat(qd, fmt)

        if self._hover_qdate is not None and self._hover_qdate.isValid():
            hq = self._hover_qdate
            key = hq.toString(Qt.DateFormat.ISODate)
            kills = int(snap.get(key, 0))
            base = hit_bg if kills > 0 else panel_bg
            bg = _blend_colors(base, accent_glow)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(_daily_snapshot_day_delta_fg_hex(self._m, hq, snap)))
            fmt.setBackground(bg)
            fmt.setFontWeight(QFont.Weight.DemiBold)
            cal.setDateTextFormat(hq, fmt)
        cal.update()
        if self._tv is not None:
            self._tv.viewport().update()
