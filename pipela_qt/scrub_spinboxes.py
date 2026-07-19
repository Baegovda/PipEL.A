"""QSpinBox / QDoubleSpinBox — 편집란에서 왼쪽 버튼 드래그로 값 스크럽."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QLineEdit, QSpinBox

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


class _ScrubSpinLineEdit(QLineEdit):
    """스핀박스 전용 라인에디트: 작은 이동은 기본(캐럿·선택), 그 이상은 값 조절."""

    def __init__(
        self,
        owner: QAbstractSpinBox,
        *,
        scrub_pixels_scale: float = 1.0,
        pre_step_highlight_start: float = 0.0,
    ) -> None:
        super().__init__(owner)
        self._owner = owner
        self._scrub = False
        self._press_global: QPointF | None = None
        self._last_global: QPointF | None = None
        self._acc = 0.0
        self._scrub_px_scale = max(0.4, min(8.0, float(scrub_pixels_scale)))
        # 0 = 비활성. 0.65~0.85: 한 단계 전에 |누적|/px 비율이 이 값 이상이면 강조
        self._pre_hl0 = max(0.0, min(0.99, float(pre_step_highlight_start)))
        self._pre_hl_on = False

    def _threshold_px(self) -> float:
        return float(scale_px_v(4))

    def _pixels_per_step(self) -> float:
        base = float(max(scale_px_v(5), 4))
        return base * self._scrub_px_scale

    def _set_pre_step_highlight(self, on: bool) -> None:
        if on == self._pre_hl_on:
            return
        self._pre_hl_on = on
        if on:
            self.setStyleSheet(
                f"QLineEdit {{"
                f"  border: 1px solid {T.ACCENT};"
                f"  background: {T.ACCENT_SOFT};"
                f"  border-radius: 2px;"
                f"}}"
            )
        else:
            self.setStyleSheet("")

    def _refresh_pre_step_highlight(self) -> None:
        t0 = self._pre_hl0
        if t0 <= 0.0 or not self._scrub:
            self._set_pre_step_highlight(False)
            return
        px = self._pixels_per_step()
        if px <= 0.0:
            return
        ap = abs(self._acc) / px
        on = t0 <= ap < 1.0 - 1e-5
        self._set_pre_step_highlight(on)

    def _apply_accumulated(self) -> None:
        px = self._pixels_per_step()
        while self._acc >= px:
            self._owner.stepBy(1)
            self._acc -= px
            self._set_pre_step_highlight(False)
        while self._acc <= -px:
            self._owner.stepBy(-1)
            self._acc += px
            self._set_pre_step_highlight(False)
        self._refresh_pre_step_highlight()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._scrub = False
            self._press_global = QPointF(e.globalPosition())
            self._last_global = QPointF(e.globalPosition())
            self._acc = 0.0
            self._set_pre_step_highlight(False)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if (
            e.buttons() & Qt.MouseButton.LeftButton
            and self._press_global is not None
            and self._last_global is not None
        ):
            g = QPointF(e.globalPosition())
            if not self._scrub:
                delta = g - self._press_global
                if delta.manhattanLength() >= self._threshold_px():
                    self._scrub = True
                    self.deselect()
                    self._last_global = g
                    self._acc = 0.0
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
            if self._scrub:
                dx = g.x() - self._last_global.x()
                dy = g.y() - self._last_global.y()
                self._last_global = g
                self._acc += dx - dy
                self._apply_accumulated()
                e.accept()
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._scrub = False
        self._press_global = None
        self._last_global = None
        self._acc = 0.0
        self._set_pre_step_highlight(False)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseReleaseEvent(e)


class DragSpinBox(QSpinBox):
    def __init__(
        self,
        parent=None,
        *,
        scrub_pixels_scale: float = 1.0,
        pre_step_highlight_start: float = 0.0,
    ) -> None:
        super().__init__(parent)
        self.setLineEdit(
            _ScrubSpinLineEdit(
                self,
                scrub_pixels_scale=scrub_pixels_scale,
                pre_step_highlight_start=pre_step_highlight_start,
            ),
        )


class DragDoubleSpinBox(QDoubleSpinBox):
    def __init__(
        self,
        parent=None,
        *,
        scrub_pixels_scale: float = 1.0,
        pre_step_highlight_start: float = 0.0,
    ) -> None:
        super().__init__(parent)
        self.setLineEdit(
            _ScrubSpinLineEdit(
                self,
                scrub_pixels_scale=scrub_pixels_scale,
                pre_step_highlight_start=pre_step_highlight_start,
            ),
        )
