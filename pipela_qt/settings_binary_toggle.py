"""설정 전용 iOS·Android 스타일 토글 — 가로 트랙 + 이동하는 원."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPoint, QRectF, Qt, QTimer, QVariantAnimation, QSize
from PyQt6.QtGui import QColor, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QSizePolicy,
    QStyle,
    QStyleOptionFocusRect,
)

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


def _lerp_f(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_c(c0: QColor, c1: QColor, t: float) -> QColor:
    u = max(0.0, min(1.0, t))
    return QColor(
        int(_lerp_f(c0.red(), c1.red(), u)),
        int(_lerp_f(c0.green(), c1.green(), u)),
        int(_lerp_f(c0.blue(), c1.blue(), u)),
    )


class SettingsBinaryToggleSwitch(QCheckBox):
    """`ms / 초`·`절대 / 상대` 등 — 캡슐 트랙 + 원 썸이 슬라이드."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setText("")
        self.setTristate(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 기본 시스템 인디케이터 숨김 — 전면 `paintEvent`로만 그림
        self.setStyleSheet(
            "QCheckBox { spacing: 0px; padding: 0px; background: transparent; border: none; }"
            "QCheckBox::indicator { width: 0px; height: 0px; border: none; }"
        )
        self._t = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self)
        # 짧고(110ms) 이징이 끝으로만 휘어지면(OutCubic) 끊겨 보임 — 여유 ms + InOutCubic, 노브는 QRectF
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.InOutCubic))
        self._anim.valueChanged.connect(self._on_anim_value)
        self.toggled.connect(self._on_toggled)
        w, h = self._sw_size()
        self.setFixedSize(w, h)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

    def hitButton(self, pos: QPoint) -> bool:  # noqa: N802
        # 인디케이터를 0×0으로 숨기면 기본 hit 영역이 비어 클릭이 무시됨 — 그린 트랙 전체를 받음
        return self.rect().contains(pos)

    def _sw_size(self) -> tuple[int, int]:
        return scale_px_v(44), scale_px_v(24)

    def sizeHint(self) -> QSize:
        w, h = self._sw_size()
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def refresh_for_scale(self) -> None:
        """루트 DPI·pt 변경 후 호출 — 트랙·썸 크기 재계산."""
        self._resync_size()
        self.update()

    def setChecked(self, a0: bool) -> None:  # noqa: N802
        self._anim.stop()
        super().setChecked(a0)
        if self.signalsBlocked():
            self._t = 1.0 if a0 else 0.0
            self.update()

    def _on_anim_value(self, v: object) -> None:
        try:
            self._t = max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        if self.signalsBlocked():
            self._t = 1.0 if checked else 0.0
            self.update()
            return
        target = 1.0 if checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(target)
        self._anim.start()

    def _metrics(self) -> tuple[int, int, int, int, float, int]:
        w, h = self._sw_size()
        pad = max(1, scale_px_v(2))
        knob = max(10, h - 2 * pad)
        r_track = h // 2
        r_knob = int(knob * 0.5)
        return w, h, pad, knob, r_track, r_knob

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, pad, knob, r_track, r_knob = self._metrics()
        t = self._t
        c_off = QColor(T.BORDER_HAIR)
        c_on = QColor(T.ACCENT)
        c_track = _lerp_c(c_off, c_on, t)
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        rect = self.rect()
        p.translate(x, y)
        p.setPen(Qt.PenStyle.NoPen)
        if not self.isEnabled():
            p.setOpacity(0.5)
        p.setBrush(c_track)
        p.drawRoundedRect(0, 0, w, h, r_track, r_track)
        c0 = QColor(220, 224, 230)
        c1 = QColor(245, 246, 248)
        knob_fill = _lerp_c(c0, c1, t)
        cx_left = float(pad + r_knob)
        cx_right = float(w - pad - r_knob)
        cx = _lerp_f(cx_left, cx_right, t)
        cy = float(h) * 0.5
        p.setBrush(knob_fill)
        p.setPen(QPen(QColor(40, 44, 52, 90), 1.0))
        d0 = 2.0 * float(r_knob)
        p.drawEllipse(
            QRectF(
                float(cx) - float(r_knob),
                float(cy) - float(r_knob),
                d0,
                d0,
            )
        )
        p.setOpacity(1.0)
        p.resetTransform()
        if self.hasFocus() and self.isEnabled():
            opt = QStyleOptionFocusRect()
            opt.rect = rect.adjusted(1, 1, -1, -1)
            opt.state = QStyle.StateFlag.State_None
            if self.isEnabled():
                opt.state |= QStyle.StateFlag.State_Enabled
            if self.hasFocus():
                opt.state |= QStyle.StateFlag.State_HasFocus
            self.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_FrameFocusRect,
                opt,
                p,
                self,
            )

    def showEvent(self, e) -> None:
        super().showEvent(e)
        QTimer.singleShot(0, self._resync_size)

    def _resync_size(self) -> None:
        w, h = self._sw_size()
        self.setFixedSize(w, h)
        self.updateGeometry()
