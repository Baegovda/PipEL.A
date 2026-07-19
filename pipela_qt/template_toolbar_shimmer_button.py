"""템플릿 툴바 버튼 — 패널 베이스 위 역할색 광택이 은은히 퍼지며 일렁임(`TemplateProbeSectionFrame` 계열)."""

from __future__ import annotations

import math
import time
from typing import Final

from PyQt6.QtCore import QEvent, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QPushButton

from pipela_core.display_timing import ui_anim_tick_ms_for_qwidget
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import TemplateToolbarRole
from pipela_qt.kill_counter_viewport_metrics import (
    KC_VIEWPORT_MIN_PT,
    KC_VIEWPORT_TOOLBAR_MAX_PT,
    kc_viewport_design_pt_eff,
    kc_viewport_px,
)
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v, scaled_design_pt

# 역할별 애니 위상 — 나란히 두면 리듬이 겹치지 않게
_ROLE_T_PHASE: Final[dict[TemplateToolbarRole, float]] = {
    "capture": 0.0,
    "test": 0.9,
    "preview": 1.7,
    "region": 2.45,
    "clear": 3.15,
}


def _toolbar_design_pt() -> float:
    return max(8.0, min(22.0, scaled_design_pt(9)))


def _btn_radius_px() -> int:
    return max(5, scale_px_v(9))


def _shimmer_alpha_scale() -> float:
    """광택 레이어 — 과하지 않게 살짝 낮춤."""
    return 0.82


class PipelaTemplateToolbarButton(QPushButton):
    """`panel_template_toolbar_button_qss` 대체 — 저수준 페인트로 확산·일렁임."""

    def __init__(self, text: str, role: TemplateToolbarRole, parent=None) -> None:
        super().__init__(text, parent)
        self._role: TemplateToolbarRole = role
        self._phase0 = _ROLE_T_PHASE[role]
        self._shimmer_t0 = 0.0
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setStyleSheet("border: none; background: transparent;")
        self._toolbar_kc_iso: float | None = None
        self.apply_toolbar_typography()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def _toolbar_padding_and_extra(self) -> tuple[int, int, int, int]:
        """세로·가로 패딩, sizeHint 가로·세로 여유(px). KC 모드는 뷰포트 배율 패딩."""
        iso = getattr(self, "_toolbar_kc_iso", None)
        if iso is not None:
            ix = float(iso)
            pv = kc_viewport_px(ix, 6.0, lo=3, hi=112)
            ph = kc_viewport_px(ix, 12.0, lo=6, hi=216)
            ex_w = kc_viewport_px(ix, 8.0, lo=4, hi=176)
            ex_h = kc_viewport_px(ix, 5.0, lo=3, hi=96)
            return pv, ph, ex_w, ex_h
        return scale_px_v(6), scale_px_h(12), scale_px_h(8), scale_px_v(5)

    def set_kc_viewport_iso_for_padding(self, iso: float | None) -> None:
        """킬 플로터 ROI: `_toolbar_padding_and_extra` 만 KC 배율로 맞추고 폰트는 건드리지 않음.

        피팅 전에 `apply_toolbar_typography(kc_iso)` 를 쓰면 sizeHint 가 과대 → 레이아웃이 버튼을 넓게 배치해
        `fit_qpushbutton_text_width_qss` 가 폭을 과대 평가한다."""
        self._toolbar_kc_iso = float(iso) if iso is not None else None
        self.updateGeometry()

    def apply_toolbar_fit_qss_font(self, font_size_qss: str, letter_spacing_qss_str: str) -> None:
        """`fit_qpushbutton_text_width_qss` 산출(pt·px 자간)을 커스텀 페인트용 QFont 로 반영."""
        f = app_default_qfont(11)
        f.setWeight(QFont.Weight.DemiBold)
        raw_pt = (font_size_qss or "").strip()
        if raw_pt.lower().endswith("pt"):
            raw_pt = raw_pt[:-2].strip()
        try:
            f.setPointSizeF(float(raw_pt))
        except ValueError:
            f.setPointSizeF(_toolbar_design_pt())
        ls = (letter_spacing_qss_str or "").strip().lower()
        if ls.endswith("px"):
            try:
                f.setLetterSpacing(
                    QFont.SpacingType.AbsoluteSpacing,
                    float(ls[:-2].strip()),
                )
            except ValueError:
                f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)
        else:
            f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)
        self.setFont(f)
        self.updateGeometry()

    def apply_toolbar_typography(
        self,
        *,
        kc_iso: float | None = None,
    ) -> None:
        self._toolbar_kc_iso = float(kc_iso) if kc_iso is not None else None
        f = app_default_qfont(11)
        f.setWeight(QFont.Weight.DemiBold)
        if kc_iso is not None:
            eff = float(kc_viewport_design_pt_eff(float(kc_iso), 9.0))
            pt = max(
                KC_VIEWPORT_MIN_PT,
                min(KC_VIEWPORT_TOOLBAR_MAX_PT, eff),
            )
        else:
            pt = _toolbar_design_pt()
        f.setPointSizeF(pt)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)

        self.setFont(f)
        self.updateGeometry()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self.isEnabled():
            self._shimmer_t0 = time.monotonic()
            # High-Hz displays: cap ~15fps for decorative shimmer (profile: paint hot).
            self._timer.setInterval(
                max(66, ui_anim_tick_ms_for_qwidget(self)),
            )
            self._timer.start()

    def hideEvent(self, e) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def changeEvent(self, e: QEvent) -> None:
        if e.type() == QEvent.Type.EnabledChange:
            if self.isEnabled() and self.isVisible():
                self._shimmer_t0 = time.monotonic()
                self._timer.setInterval(
                    max(66, ui_anim_tick_ms_for_qwidget(self)),
                )
                self._timer.start()
            else:
                self._timer.stop()
            self.update()
        super().changeEvent(e)

    def enterEvent(self, e) -> None:
        self._hover = True
        super().enterEvent(e)
        self.update()

    def leaveEvent(self, e) -> None:
        self._hover = False
        super().leaveEvent(e)
        self.update()

    def _on_tick(self) -> None:
        self.update()

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        tw = fm.horizontalAdvance(self.text())
        th = fm.height()
        pv, ph, ex_w, ex_h = self._toolbar_padding_and_extra()
        return QSize(tw + ph * 2 + ex_w, th + pv * 2 + ex_h)

    def minimumSizeHint(self) -> QSize:
        sh = self.sizeHint()
        if getattr(self, "_pipela_kc_flexible_width", False):
            return QSize(0, sh.height())
        return sh

    def paintEvent(self, _e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        rect = self.rect()
        r = float(_btn_radius_px())
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), r, r)

        p.setPen(Qt.PenStyle.NoPen)
        if self.isEnabled():
            base_g = QLinearGradient(
                0.0,
                float(rect.top()),
                0.0,
                float(rect.bottom()),
            )
            if self._hover:
                base_g.setColorAt(0.0, QColor(T.CARD_ACCENT))
                base_g.setColorAt(0.42, QColor(T.CARD_HOVER))
                base_g.setColorAt(1.0, QColor(T.PANEL_BG))
            else:
                base_g.setColorAt(0.0, QColor(T.SURFACE))
                base_g.setColorAt(0.35, QColor(T.CARD_BG))
                base_g.setColorAt(1.0, QColor(T.PANEL_BG))
            p.fillPath(path, QBrush(base_g))
            self._paint_shimmer_layer(p, rect)
            p.setClipPath(path)
            band = float(scale_px_v(12))
            rim = QLinearGradient(0.0, rect.top(), 0.0, rect.top() + band)
            rim.setColorAt(0.0, QColor(255, 255, 255, 36 if self._hover else 22))
            rim.setColorAt(0.5, QColor(255, 255, 255, 6))
            rim.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(
                QRectF(rect.left(), rect.top(), float(rect.width()), band),
                QBrush(rim),
            )
            p.setClipping(False)
        else:
            p.fillPath(path, QColor(T.PANEL_BG))

        if self.isDown() and self.isEnabled():
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(path, QColor(0, 0, 0, 44))

        bd = QColor(T.BORDER_HAIR)
        bd.setAlpha(200)
        if self._hover and self.isEnabled():
            bd = QColor(T.ACCENT)
            bd.setAlpha(95)
        elif not self.isEnabled():
            bd = QColor(T.BORDER_HAIR)
            bd.setAlpha(140)
        pen = QPen(bd)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), r, r)

        if self.isEnabled() and not self._hover:
            inner = QColor(255, 255, 255, 14)
            ip = QPen(inner)
            ip.setWidth(1)
            p.setPen(ip)
            p.drawRoundedRect(QRectF(rect).adjusted(1.5, 1.5, -1.5, -1.5), r - 1, r - 1)

        if self.hasFocus():
            fa = QColor(T.ACCENT)
            fa.setAlpha(72)
            p.setPen(QPen(fa, 1))
            p.drawRoundedRect(QRectF(rect).adjusted(2.5, 2.5, -2.5, -2.5), max(2.0, r - 2), max(2.0, r - 2))

        fg = QColor(T.FG if self.isEnabled() else T.FG_DIM)
        p.setPen(fg)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setFont(self.font())
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

    def _paint_shimmer_layer(self, p: QPainter, rect) -> None:
        w, h = max(1, rect.width()), max(1, rect.height())
        # 76ms·0.088틱과 동일 속도로 monotonic 위상 — 프레임 간 보간이 매끈함
        t = self._phase0 + (time.monotonic() - float(self._shimmer_t0)) * (0.088 / 0.076)
        ox = 0.06 * w + 0.48 * w * (0.5 + 0.5 * math.sin(t * 0.79 + 0.15))
        oy = 0.05 * h + 0.38 * h * (0.5 + 0.5 * math.cos(t * 0.57 + 0.35))
        # 색이 넓게 퍼지도록 그라데이션 축을 위젯 밖으로 길게 뻗음
        span = math.hypot(w, h) * 1.48
        ang = 0.52 + 0.12 * math.sin(t * 0.61)
        x2 = ox + span * math.cos(ang)
        y2 = oy + span * math.sin(ang)
        g = QLinearGradient(ox, oy, x2, y2)

        a0 = 0.14 + 0.11 * math.sin(t * 1.62)
        a1 = 0.22 + 0.13 * math.sin(t * 1.08 + 0.9)
        pulse = abs(math.sin(t * 0.91))
        hb = 1.22 if self._hover else 1.0

        sa = _shimmer_alpha_scale()

        def al(x: float) -> int:
            return max(0, min(255, int(x * hb * sa)))

        role = self._role
        if role == "capture":
            g.setColorAt(0.0, QColor(18, 72, 82, al(8 + 22 * a0)))
            g.setColorAt(0.28, QColor(0, 168, 158, al(58 + 105 * a1)))
            g.setColorAt(0.48, QColor(72, 218, 205, al(52 + 100 * a0)))
            g.setColorAt(0.68, QColor(32, 145, 185, al(48 + 88 * pulse)))
            g.setColorAt(1.0, QColor(12, 48, 58, 0))
        elif role == "test":
            g.setColorAt(0.0, QColor(28, 78, 82, al(10 + 20 * a0)))
            g.setColorAt(0.24, QColor(0, 165, 152, al(55 + 102 * a1)))
            g.setColorAt(0.42, QColor(64, 210, 205, al(58 + 98 * a0)))
            g.setColorAt(0.56, QColor(88, 185, 228, al(52 + 92 * pulse)))
            g.setColorAt(0.72, QColor(150, 128, 210, al(46 + 85 * a1)))
            g.setColorAt(0.88, QColor(40, 95, 115, al(28 + 40 * pulse)))
            g.setColorAt(1.0, QColor(20, 55, 65, 0))
        elif role == "preview":
            g.setColorAt(0.0, QColor(38, 58, 95, al(10 + 18 * a0)))
            g.setColorAt(0.32, QColor(55, 115, 205, al(62 + 108 * a1)))
            g.setColorAt(0.52, QColor(105, 155, 235, al(58 + 102 * a0)))
            g.setColorAt(0.72, QColor(65, 110, 185, al(50 + 85 * pulse)))
            g.setColorAt(1.0, QColor(28, 40, 68, 0))
        elif role == "region":
            g.setColorAt(0.0, QColor(88, 62, 38, al(10 + 20 * a0)))
            g.setColorAt(0.30, QColor(205, 145, 58, al(60 + 105 * a1)))
            g.setColorAt(0.50, QColor(228, 175, 82, al(68 + 100 * a0)))
            g.setColorAt(0.70, QColor(175, 115, 48, al(52 + 82 * pulse)))
            g.setColorAt(1.0, QColor(62, 48, 32, 0))
        else:  # clear
            g.setColorAt(0.0, QColor(92, 48, 62, al(10 + 20 * a0)))
            g.setColorAt(0.32, QColor(205, 95, 118, al(58 + 105 * a1)))
            g.setColorAt(0.52, QColor(225, 125, 145, al(64 + 102 * a0)))
            g.setColorAt(0.72, QColor(165, 78, 98, al(50 + 85 * pulse)))
            g.setColorAt(1.0, QColor(58, 38, 45, 0))

        r = float(_btn_radius_px())
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), r, r)
        p.setClipPath(clip)
        p.fillRect(rect, QBrush(g))
        p.setClipping(False)
