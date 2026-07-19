"""템플릿 섹션 사이 ‘↓’ — 평소 흐린 색, 실시간 유사도가 임계을 넘는 순간(상승 에지) 액센트 펄스."""

from __future__ import annotations

import math

from PyQt6.QtCore import QEasingCurve, QVariantAnimation
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel

from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import settings_label_align_center_h, settings_path_connector_qss


class TemplatePathConnectorArrow(QLabel):
    """이전 단계 `score >= threshold` 가 False→True 될 때 한 번 빛남."""

    def __init__(self, parent=None) -> None:
        super().__init__("↓", parent)
        self._primed = False
        self._last_ok = False
        self._pulse_active = False
        self._muted_qss = ""
        self._dim = QColor()
        self._acc = QColor()
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1050)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.InOutSine))
        self._anim.valueChanged.connect(self._on_pulse_frame)
        self._anim.finished.connect(self._on_pulse_finished)
        settings_label_align_center_h(self)
        self.refresh_for_scale()

    def refresh_for_scale(self) -> None:
        self._dim = QColor(T.FG_DIM)
        self._acc = QColor(T.ACCENT)
        self._muted_qss = settings_path_connector_qss(color=T.FG_DIM)
        if not self._pulse_active:
            self.setStyleSheet(self._muted_qss)

    def reset_edge_state(self) -> None:
        """패널을 다시 열었을 때 이미 매칭 중이어도 펄스가 나가지 않도록."""
        self._primed = False
        self._last_ok = False

    def hide_idle(self) -> None:
        if self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()
        self._pulse_active = False
        self.setStyleSheet(self._muted_qss)

    def feed_threshold_edge(self, score: float, threshold: float) -> None:
        ok = float(score) >= float(threshold)
        if not self._primed:
            self._primed = True
            self._last_ok = ok
            return
        if ok and not self._last_ok:
            self._start_pulse()
        self._last_ok = ok

    def _start_pulse(self) -> None:
        if self._anim.state() == QVariantAnimation.State.Running:
            self._anim.stop()
        self._pulse_active = True
        self._anim.start()

    def _on_pulse_frame(self, v) -> None:
        t = float(v)
        u = max(0.0, min(1.0, math.sin(math.pi * t)))
        c = QColor(
            int(self._dim.red() + (self._acc.red() - self._dim.red()) * u),
            int(self._dim.green() + (self._acc.green() - self._dim.green()) * u),
            int(self._dim.blue() + (self._acc.blue() - self._dim.blue()) * u),
        )
        self.setStyleSheet(settings_path_connector_qss(color=c.name()))

    def _on_pulse_finished(self) -> None:
        self._pulse_active = False
        self.setStyleSheet(self._muted_qss)
