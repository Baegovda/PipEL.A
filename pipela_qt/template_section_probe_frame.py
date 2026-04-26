"""템플릿 설정: 이미지 템플릿별 섹션 — 매칭 시도 중일 때 은은한 광택·웨이브."""

from __future__ import annotations

import math
import re
import time
from typing import Any, Final

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFontMetricsF,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import settings_root_vertical_spacing
from pipela_qt.ui_adaptive import scale_px

# `main._template_probe_last_mono` 키 — `CAPTURE_KIND_TO_PROBE_KEY` 와 일치
CAPTURE_KIND_TO_PROBE_KEY: Final[dict[str, tuple[str, str]]] = {
    "ride_target": ("ride", "target"),
    "hp_zkey": ("hp_refill", "zkey"),
    "reload_nobullet": ("reload", "nobullet"),
    "reload_bullet": ("reload", "bullet"),
    "reload_vault": ("reload", "vault"),
    "call_merc_1": ("call_merc", "call_merc_1"),
    "call_merc_2": ("call_merc", "call_merc_2"),
    "call_merc_3": ("call_merc", "call_merc_3"),
    "call_merc_4": ("call_merc", "call_merc_4"),
    "ammo_buybutton": ("ammo_restock", "buybutton"),
    "ammo_inven": ("ammo_restock", "inven"),
    "ammo_bank": ("ammo_restock", "bank"),
    "start_game_launcher": ("start_game", "launcher"),
    "start_game_intro_skip": ("start_game", "intro_skip"),
    "start_game_accept": ("start_game", "accept"),
}


def is_template_probe_active(pipela_mod: Any, capture_kind: str) -> bool:
    key = CAPTURE_KIND_TO_PROBE_KEY.get(capture_kind)
    if not key:
        return False
    d = getattr(pipela_mod, "_template_probe_last_mono", None)
    if not isinstance(d, dict):
        return False
    t0 = d.get(key)
    if t0 is None:
        return False
    stale = float(getattr(pipela_mod, "_SETTINGS_PROBE_STALE_SEC", 1.5))
    return (time.monotonic() - float(t0)) < stale


# 프로브「실시간」구간: 지나가는 그라데이션(터콰이즈·시어·라벤더) — _ProbeCurrentSegment 전용
_TQ_RGB: tuple[int, int, int] = (0x3E, 0xC4, 0xBA)
_LV_RGB: tuple[int, int, int] = (0xB6, 0xA0, 0xD2)
_SH0 = QColor(0x4E, 0xE8, 0xD8)  # 광 밴드(그라데이션 중심)
_SH1 = QColor(0xC4, 0xD8, 0xF2)

_PROBE_SCORE_TEXT_RE: Final[re.Pattern[str]] = re.compile(
    r"^실시간 (?P<num>[-+]?[\d.]+) / 기준\s*$",
    re.ASCII,
)


class _ProbeCurrentSegment(QWidget):
    """`실시간 n.nn` 만 표시 — 프로브 중 터콰이즈·시어·라벤더가 **가로로 흐르는** 그라데이션."""

    def __init__(self, pipela_mod: Any, capture_kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._kind = capture_kind
        self._score = "0.00"
        self._fallback: str | None = None
        self._phase = 0.0
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setObjectName("TemplateProbeCurrentSegment")

    def set_score_str(self, s: str) -> None:
        if self._fallback is not None or self._score != s:
            self._score = s
            self._fallback = None
            self.updateGeometry()
            self.update()

    def set_fallback_line(self, line: str) -> None:
        if self._fallback != line:
            self._fallback = line
            self.updateGeometry()
            self.update()

    def set_phase(self, phase: float) -> None:
        self._phase = phase

    def _line(self) -> str:
        if self._fallback is not None:
            return self._fallback
        return f"실시간 {self._score}"

    def sizeHint(self) -> QSize:
        fm = QFontMetricsF(self.font())
        w = int(fm.horizontalAdvance(self._line()) + 2.0)
        h = int(fm.height() + 2.0)
        return QSize(max(1, w), max(1, h))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, e: QPaintEvent) -> None:
        text = self._line()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = self.font()
        p.setFont(font)
        fm = QFontMetricsF(font)
        h = float(self.height())
        y_base = (h - fm.height()) * 0.5 + float(fm.ascent())
        path = QPainterPath()
        path.addText(0.0, y_base, font, text)
        tw = max(1.0, float(fm.horizontalAdvance(text)))
        on = is_template_probe_active(self._m, self._kind)
        if on and self._fallback is None:
            t = self._phase
            span = max(10.0, tw * 0.9)
            x0 = 0.5 * tw * (1.0 + 0.92 * math.sin(t * 0.62 + 0.2))
            g = QLinearGradient(x0 - span, 0.0, x0 + span, 0.0)
            g.setColorAt(0.0, QColor(_TQ_RGB[0], _TQ_RGB[1], _TQ_RGB[2]))
            g.setColorAt(0.35, QColor(_SH0))
            g.setColorAt(0.52, QColor(_SH1))
            g.setColorAt(0.68, QColor(_LV_RGB[0], _LV_RGB[1], _LV_RGB[2]))
            g.setColorAt(1.0, QColor(_TQ_RGB[0], _TQ_RGB[1], _TQ_RGB[2]))
            p.fillPath(path, QBrush(g))
        else:
            c = QColor(T.FG)
            p.fillPath(path, QBrush(c))


class TemplateLiveScoreReadout(QWidget):
    """설정 행 **실시간 유사도 숫자** — 탐지 시도(프로브) 중 터콰이즈·시어·라벤더 그라데이션이 흐름."""

    def __init__(self, pipela_mod: Any, capture_kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._kind = capture_kind
        self._score = "0.00"
        self._phase = 0.0
        self._active_last = False
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setObjectName("TemplateLiveScoreReadout")
        self._anim = QTimer(self)
        self._anim.setInterval(72)
        self._anim.timeout.connect(self._on_tick)
        self.setStyleSheet(f"font-family: {T.FONT_CSS_UI};")

    def setText(self, s: str) -> None:  # noqa: N802 — Qt idiom
        t = (s or "").strip()
        if self._score != t:
            self._score = t
            self.updateGeometry()
            self.update()

    def text(self) -> str:
        return self._score

    def _on_tick(self) -> None:
        on = is_template_probe_active(self._m, self._kind)
        if on:
            self._active_last = True
            self._phase += 0.082
            self.update()
        elif self._active_last:
            self._active_last = False
            self.update()

    def sizeHint(self) -> QSize:
        fm = QFontMetricsF(self.font())
        w = int(fm.horizontalAdvance(self._score) + 2.0)
        h = int(fm.height() + 2.0)
        return QSize(max(1, w), max(1, h))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, e: QPaintEvent) -> None:
        text = self._score
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = self.font()
        p.setFont(font)
        fm = QFontMetricsF(font)
        h = float(self.height())
        y_base = (h - fm.height()) * 0.5 + float(fm.ascent())
        path = QPainterPath()
        path.addText(0.0, y_base, font, text)
        tw = max(1.0, float(fm.horizontalAdvance(text)))
        on = is_template_probe_active(self._m, self._kind)
        if on:
            t = self._phase
            span = max(10.0, tw * 0.9)
            x0 = 0.5 * tw * (1.0 + 0.92 * math.sin(t * 0.62 + 0.2))
            g = QLinearGradient(x0 - span, 0.0, x0 + span, 0.0)
            g.setColorAt(0.0, QColor(_TQ_RGB[0], _TQ_RGB[1], _TQ_RGB[2]))
            g.setColorAt(0.35, QColor(_SH0))
            g.setColorAt(0.52, QColor(_SH1))
            g.setColorAt(0.68, QColor(_LV_RGB[0], _LV_RGB[1], _LV_RGB[2]))
            g.setColorAt(1.0, QColor(_TQ_RGB[0], _TQ_RGB[1], _TQ_RGB[2]))
            p.fillPath(path, QBrush(g))
        else:
            c = QColor(T.FG)
            p.fillPath(path, QBrush(c))

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._anim.start()

    def hideEvent(self, e) -> None:
        self._anim.stop()
        super().hideEvent(e)


class TemplateProbeScoreLabel(QWidget):
    """「실시간 n.nn」만 프로브 애니·흐르는 색, 「 / 기준 」는 항상 일반 본문색."""

    def __init__(self, pipela_mod: Any, capture_kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._kind = capture_kind
        self._raw = "실시간 0.00 / 기준 "
        self._phase = 0.0
        self._active_last = False
        self.setObjectName("TemplateProbeScoreLabel")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._seg = _ProbeCurrentSegment(pipela_mod, capture_kind, self)
        self._suffix = QLabel(" / 기준 ", self)
        self._suffix.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self._seg, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._suffix, 0, Qt.AlignmentFlag.AlignVCenter)
        self._anim = QTimer(self)
        self._anim.setInterval(72)
        self._anim.timeout.connect(self._on_tick)
        self.setText(self._raw)
        self.apply_typography()

    def text(self) -> str:
        return self._raw

    def setText(self, s: str) -> None:  # noqa: N802 — Qt idiom
        self._raw = s
        m = _PROBE_SCORE_TEXT_RE.match(s)
        if m is not None:
            self._suffix.setVisible(True)
            self._seg.set_score_str(m.group("num"))
        else:
            self._suffix.setVisible(False)
            self._seg.set_fallback_line(s)
        self.updateGeometry()
        self.apply_typography()

    def apply_typography(self) -> None:
        fn = f"font-family: {T.FONT_CSS_UI};"
        self.setStyleSheet(fn)
        self._suffix.setStyleSheet(f"color: {T.FG}; {fn}")
        self._seg.setStyleSheet(fn)
        # 접미사·프로브 구간 동일 글꼴(위젯 스타일 반영 뒤 `QLabel` 쪽이 안정적)
        self._seg.setFont(self._suffix.font())
        on = is_template_probe_active(self._m, self._kind)
        if on:
            self._seg.set_phase(self._phase)
        self._seg.update()
        self._suffix.update()

    def _on_tick(self) -> None:
        on = is_template_probe_active(self._m, self._kind)
        if on:
            self._active_last = True
            self._phase += 0.082
            self._seg.set_phase(self._phase)
            self._seg.update()
        elif self._active_last:
            self._active_last = False
            self._seg.update()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._anim.start()
        self.apply_typography()

    def hideEvent(self, e) -> None:
        self._anim.stop()
        super().hideEvent(e)


class TemplateProbeSectionFrame(QFrame):
    """한 이미지 템플릿 섹션 — 감지 시도(프로브) 시 배경이 은은히 빛남(애니)."""

    def __init__(
        self,
        pipela_mod: Any,
        capture_kind: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._kind = capture_kind
        self._phase = 0.0
        self._active_last = False
        self.setObjectName("TemplateProbeSectionFrame")
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self.setMinimumWidth(scale_px(240))
        self._vbox = QVBoxLayout(self)
        self._apply_margins()
        self._vbox.setSpacing(settings_root_vertical_spacing())

        self._anim = QTimer(self)
        self._anim.setInterval(42)
        self._anim.timeout.connect(self._on_anim_tick)

    def _apply_margins(self) -> None:
        p = scale_px(10)
        self._vbox.setContentsMargins(p, p, p, p)

    def content_layout(self) -> QVBoxLayout:
        return self._vbox

    def apply_scale_margins(self) -> None:
        self._apply_margins()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._anim.start()

    def hideEvent(self, e) -> None:
        self._anim.stop()
        super().hideEvent(e)

    def _on_anim_tick(self) -> None:
        now = is_template_probe_active(self._m, self._kind)
        if now:
            self._phase += 0.11
            self._active_last = True
            self.update()
        elif self._active_last:
            self._active_last = False
            self._phase = 0.0
            self.update()

    def paintEvent(self, e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        r = float(scale_px(8))
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), r, r)
        base = QColor(T.PANEL_BG)
        p.setPen(Qt.PenStyle.NoPen)
        p.setClipPath(path)
        p.fillPath(path, base)

        if is_template_probe_active(self._m, self._kind):
            w, h = max(1, rect.width()), max(1, rect.height())
            t = self._phase
            # 대각 흐름 + sin 일렁임 — 이전(알파 ~0.04~0.1대)보다 **대비·채도**를 올려 “감지 시도”가 한눈에 보이게
            ox = 0.35 * w * (0.5 + 0.5 * math.sin(t * 0.85))
            oy = 0.25 * h * (0.5 + 0.5 * math.cos(t * 0.62 + 0.4))
            g = QLinearGradient(ox, oy, ox + w * 0.9, oy + h * 0.4)
            a0 = 0.10 + 0.08 * math.sin(t * 1.7)
            a1 = 0.18 + 0.10 * math.sin(t * 1.1 + 1.0)
            pulse = abs(math.sin(t * 0.9))
            g.setColorAt(0.0, QColor(20, 55, 70, int(6 + 18 * a0)))
            g.setColorAt(0.32, QColor(0, 170, 200, int(45 + 95 * a1)))
            g.setColorAt(0.52, QColor(100, 220, 255, int(40 + 90 * a0)))
            g.setColorAt(0.72, QColor(40, 150, 220, int(35 + 70 * pulse)))
            g.setColorAt(1.0, QColor(15, 40, 55, 0))
            p.setOpacity(1.0)
            p.fillRect(rect, QBrush(g))

        p.setClipping(False)
        p.setOpacity(1.0)
        border = QColor(T.DIVIDER)
        border.setAlpha(110)
        pen = QPen(border)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), r, r)