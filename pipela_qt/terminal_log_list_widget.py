"""터미널 로그 — 줄 단위 QLabel, 맨 앞 줄 제거 시 높이 축소로 아래 줄이 올라오는 애니메이션."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

_WSIZE_MAX = 16777215

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v

LineKey = tuple[float, float]


def _strip_trailing_br(html: str) -> str:
    h = html.rstrip()
    if h.lower().endswith("<br/>"):
        return h[:-5].rstrip()
    return h


class _LogLineRow(QWidget):
    def __init__(self, key: LineKey, parent=None) -> None:
        super().__init__(parent)
        self._key = key
        self._nh_cache: int | None = None
        self._lbl = QLabel()
        self._lbl.setTextFormat(Qt.TextFormat.RichText)
        self._lbl.setWordWrap(True)
        self._lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(self)
        m = scale_px_v(4)
        lay.setContentsMargins(m, 0, m, scale_px_v(2))
        lay.setSpacing(0)
        lay.addWidget(self._lbl)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_html(self, html: str) -> None:
        t = _strip_trailing_br(html)
        # 페이드 중엔 접두 색만 바뀌는 틱이 잦음 — 캐시를 매번 지우면 sizeHint 가 흔들려 줄 높이가 드르륵 거림.
        # mh==0 인 «이미 접힌» 행에서 캐시를 지우면 다음 틱에 nh 가 다시 커졌다 작아졌다 하며 부르르 떨림.
        mh = int(self.maximumHeight())
        collapsing = 0 < mh < _WSIZE_MAX
        collapsed = mh <= 0
        if not collapsing and not collapsed:
            self._nh_cache = None
        self._lbl.setText(t)

    def key(self) -> LineKey:
        return self._key

    def set_log_font(self, font: QFont) -> None:
        self._nh_cache = None
        self._lbl.setFont(font)

    def reset_height_constraint(self) -> None:
        self._nh_cache = None
        self.setVisible(True)
        self.setMaximumHeight(_WSIZE_MAX)
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def apply_height_factor(self, factor: float) -> None:
        fk = max(0.0, min(1.0, float(factor)))
        if fk >= 0.999:
            self.reset_height_constraint()
            return
        if fk <= 0.0005:
            self.setMinimumHeight(0)
            self.setMaximumHeight(0)
            self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            self.setVisible(False)
            return
        self.setVisible(True)
        if self._nh_cache is None:
            self.setMaximumHeight(_WSIZE_MAX)
            self.setMinimumHeight(0)
            self._nh_cache = max(self.sizeHint().height(), scale_px_v(14))
        nh = self._nh_cache
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(0)
        mh = max(1, round(nh * fk))
        self.setMaximumHeight(mh)


class ResizableTerminalLogList(QWidget):
    """`QTextEdit` 대체 — `apply_log_rows` / `append_terminal_html_row` · 우하단 리사이즈."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._base_font: QFont | None = None
        self._rz_margin = scale_px_v(10)
        self._rz_active = False
        self._rz_start: QPointF | None = None
        self._rz_h0 = 0
        self.setMinimumHeight(scale_px_v(120))
        self.setMouseTracking(True)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._vlay = QVBoxLayout(self._content)
        self._vlay.setContentsMargins(0, 0, 0, 0)
        self._vlay.setSpacing(0)
        self._vlay.addStretch(1)
        self._scroll.setWidget(self._content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll, 1)

        self._rows: list[_LogLineRow] = []
        self._strip_front_count_remaining = 0
        self._pending_after_strip: list[tuple[LineKey, str]] | None = None
        self._active_strip_anim: QPropertyAnimation | None = None

        bg = T.TERMINAL_BG
        self._content.setStyleSheet(f"background-color: {bg};")
        self._scroll.setStyleSheet(f"QScrollArea {{ background-color: {bg}; border: none; }}")

    def verticalScrollBar(self):
        return self._scroll.verticalScrollBar()

    def flush_terminal_log_layout(self) -> None:
        """스크롤 영역이 접힌 행 제거 직후 남는 빈 공간을 정리."""
        self._content.adjustSize()
        self._scroll.updateGeometry()

    @staticmethod
    def _row_is_layout_gone(row: _LogLineRow) -> bool:
        return (not row.isVisible()) or int(row.maximumHeight()) <= 0

    def setReadOnly(self, _ro: bool) -> None:
        pass

    def setAcceptRichText(self, _rich: bool) -> None:
        pass

    def set_log_inner_margin_px(self, px: int) -> None:
        m = max(0, int(px))
        for r in self._rows:
            lay = r.layout()
            if lay is not None:
                lay.setContentsMargins(m, 0, m, scale_px_v(2))

    def setFont(self, font: QFont) -> None:
        self._base_font = QFont(font)
        for r in self._rows:
            r.set_log_font(self._base_font)

    def _apply_font_to_row(self, row: _LogLineRow) -> None:
        if self._base_font is not None:
            row.set_log_font(self._base_font)

    def _insert_row_before_stretch(self, row: _LogLineRow) -> None:
        idx = max(0, self._vlay.count() - 1)
        self._vlay.insertWidget(idx, row)

    def append_terminal_html_row(self, key: LineKey, html: str) -> None:
        html = _strip_trailing_br(html)
        if self._rows and self._rows[-1].key() == key:
            self._rows[-1].set_html(html)
            return
        row = _LogLineRow(key, self._content)
        self._apply_font_to_row(row)
        self._insert_row_before_stretch(row)
        row.set_html(html)
        self._rows.append(row)
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _apply_row_height_factors(self, factors: list[float] | None) -> None:
        if not factors or len(factors) != len(self._rows):
            for r in self._rows:
                r.reset_height_constraint()
            return
        for r, f in zip(self._rows, factors):
            r.apply_height_factor(f)

    def apply_log_rows(
        self,
        entries: list[tuple[LineKey, str]],
        *,
        row_height_factors: list[float] | None = None,
        allow_animate: bool = True,
    ) -> None:
        new_keys = [k for k, _ in entries]
        old_keys = [r.key() for r in self._rows]

        if new_keys == old_keys:
            for r, (_, h) in zip(self._rows, entries):
                r.set_html(h)
            self._apply_row_height_factors(row_height_factors)
            self._prune_stale_prefix_rows(new_keys)
            return

        n_drop = len(old_keys) - len(new_keys)
        if (
            allow_animate
            and 0 < n_drop <= 24
            and old_keys[n_drop:] == new_keys
        ):
            self._cancel_strip_chain()
            self._pending_after_strip = entries
            self._strip_front_count_remaining = n_drop
            # 페이드 종료 후 이미 maxH=0·숨김인 행은 레이아웃에 남기지 않고 즉시 제거
            while (
                self._strip_front_count_remaining > 0
                and self._rows
                and self._row_is_layout_gone(self._rows[0])
            ):
                r = self._rows.pop(0)
                self._vlay.removeWidget(r)
                r.deleteLater()
                self._strip_front_count_remaining -= 1
            if self._strip_front_count_remaining <= 0:
                self._pending_after_strip = None
                self.apply_log_rows(
                    entries,
                    row_height_factors=row_height_factors,
                    allow_animate=False,
                )
                return
            nd = self._strip_front_count_remaining
            # 앞줄만 접는 동안에도 페이드 틱(수십 ms)마다 rebuild가 들어옴. 이 경로에서는
            # 꼬리 줄 QLabel을 갱신하지 않아 시간·나이 숫자가 멈춘 것처럼 보였음.
            for i in range(nd, len(self._rows)):
                ei = i - nd
                if ei >= len(entries):
                    break
                ek, eh = entries[ei]
                r = self._rows[i]
                if r.key() == ek:
                    r.set_html(eh)
                if (
                    row_height_factors is not None
                    and ei < len(row_height_factors)
                    and r.key() == ek
                ):
                    r.apply_height_factor(row_height_factors[ei])
            self._continue_front_strip_chain()
            return

        self._cancel_strip_chain()
        self._full_reset_rows(entries, row_height_factors=row_height_factors)

    def _cancel_strip_chain(self) -> None:
        self._strip_front_count_remaining = 0
        self._pending_after_strip = None
        anim = self._active_strip_anim
        self._active_strip_anim = None
        if anim is None:
            return
        try:
            anim.finished.disconnect()
        except TypeError:
            pass
        try:
            anim.stop()
        except Exception:
            pass
        try:
            tgt = anim.targetObject()
            if isinstance(tgt, _LogLineRow):
                tgt.reset_height_constraint()
        except Exception:
            pass
        try:
            anim.deleteLater()
        except Exception:
            pass

    def _continue_front_strip_chain(self) -> None:
        if self._strip_front_count_remaining <= 0:
            ent = self._pending_after_strip or []
            self._pending_after_strip = None
            self.apply_log_rows(ent, row_height_factors=None, allow_animate=False)
            return
        if not self._rows:
            self._strip_front_count_remaining = 0
            ent = self._pending_after_strip or []
            self._pending_after_strip = None
            self.apply_log_rows(ent, row_height_factors=None, allow_animate=False)
            return
        while (
            self._strip_front_count_remaining > 0
            and self._rows
            and self._row_is_layout_gone(self._rows[0])
        ):
            r = self._rows.pop(0)
            self._vlay.removeWidget(r)
            r.deleteLater()
            self._strip_front_count_remaining -= 1
        if self._strip_front_count_remaining <= 0:
            ent = self._pending_after_strip or []
            self._pending_after_strip = None
            self.apply_log_rows(ent, row_height_factors=None, allow_animate=False)
            return
        if not self._rows:
            self._strip_front_count_remaining = 0
            ent = self._pending_after_strip or []
            self._pending_after_strip = None
            self.apply_log_rows(ent, row_height_factors=None, allow_animate=False)
            return

        row = self._rows[0]
        h_pre = max(row.sizeHint().height(), row.height(), 0)
        if h_pre <= 2:
            if not self._rows or self._rows[0] is not row:
                self._strip_front_count_remaining = 0
                self._pending_after_strip = None
                return
            self._vlay.removeWidget(row)
            row.deleteLater()
            self._rows.pop(0)
            self._strip_front_count_remaining -= 1
            self._continue_front_strip_chain()
            return
        row.reset_height_constraint()
        h = max(row.sizeHint().height(), row.height(), scale_px_v(14))
        if h <= 2:
            if not self._rows or self._rows[0] is not row:
                self._strip_front_count_remaining = 0
                self._pending_after_strip = None
                return
            self._vlay.removeWidget(row)
            row.deleteLater()
            self._rows.pop(0)
            self._strip_front_count_remaining -= 1
            self._continue_front_strip_chain()
            return
        row.setMaximumHeight(h)
        row.setMinimumHeight(0)
        anim = QPropertyAnimation(row, b"maximumHeight", self)
        anim.setDuration(300)
        anim.setStartValue(int(h))
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._active_strip_anim = anim

        def _done() -> None:
            if self._active_strip_anim is not anim:
                return
            self._active_strip_anim = None
            if not self._rows or self._rows[0] is not row:
                self._strip_front_count_remaining = 0
                self._pending_after_strip = None
                return
            self._vlay.removeWidget(row)
            row.deleteLater()
            self._rows.pop(0)
            self._strip_front_count_remaining -= 1
            self._continue_front_strip_chain()

        anim.finished.connect(_done)
        anim.start()

    def _full_reset_rows(
        self,
        entries: list[tuple[LineKey, str]],
        *,
        row_height_factors: list[float] | None = None,
    ) -> None:
        self._cancel_strip_chain()
        for r in self._rows:
            self._vlay.removeWidget(r)
            r.deleteLater()
        self._rows.clear()
        for k, h in entries:
            row = _LogLineRow(k, self._content)
            self._apply_font_to_row(row)
            self._insert_row_before_stretch(row)
            row.set_html(h)
            self._rows.append(row)
        self._apply_row_height_factors(row_height_factors)

    def _prune_stale_prefix_rows(self, keys: list[LineKey]) -> None:
        if self._active_strip_anim or self._strip_front_count_remaining:
            return
        while self._rows and keys and self._rows[0].key() != keys[0]:
            r = self._rows.pop(0)
            self._vlay.removeWidget(r)
            r.deleteLater()

    def _corner_hot(self, pos: QPointF) -> bool:
        return pos.x() >= self.width() - self._rz_margin and pos.y() >= self.height() - self._rz_margin

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._corner_hot(e.position()):
            self._rz_active = True
            self._rz_start = QPointF(e.globalPosition())
            self._rz_h0 = self.height()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._rz_active and self._rz_start is not None:
            dy = e.globalPosition().y() - self._rz_start.y()
            nh = max(self.minimumHeight(), int(self._rz_h0 + dy))
            self.setMinimumHeight(nh)
            e.accept()
            return
        if self._corner_hot(e.position()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._rz_active = False
        self._rz_start = None
        super().mouseReleaseEvent(e)
