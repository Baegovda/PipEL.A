"""QPushButton — 배경·테두리는 QSS, 아이콘·라벨은 직접 그림(검은 휘도 + 본문색).

QSS `color` 는 `QPalette::ButtonText`에 안 내려오는 경우가 많고,
`strokePath`+클리핑은 윤곽이 안 보이기 쉬움.
→ 8방×2겹 오프셋으로 검은 `fillPath` 쌓고 마지막에 테마 `T` 색(제어창 `echActionTone`과 동기)으로 덮는다.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, QRect
from PyQt6.QtGui import QIcon, QPainter, QPainterPath, QColor, QPaintEvent
from PyQt6.QtWidgets import QPushButton, QStyle, QStyleOptionButton

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


def _halo_offset_pairs() -> list[tuple[int, int]]:
    """윤곽용 (dx,dy) — 2px~3px 느낌 + 스케일."""
    s = max(1, int(scale_px_v(1)))
    out: list[tuple[int, int]] = []
    for r in (1, 2):
        k = s * r
        for dx, dy in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ):
            out.append((dx * k, dy * k))
    return out


def _action_label_fill(btn: QPushButton) -> QColor:
    """QSS `color`에 맞춤 — `control_main`이 `setProperty` 함."""
    if not btn.isEnabled():
        return QColor(T.FG_DIM)
    t = str(btn.property("echActionTone") or "")
    if t == "off":
        return QColor(T.FG_MUTED)
    if t in ("on", "emit"):
        return QColor(T.FG)
    return QColor(T.FG)


class PipelaActionOutlineButton(QPushButton):
    """기능 그리드: 검은 휘도 후 `T` 본문. 배경은 `CE_PushButton`+QSS."""

    def paintEvent(self, _e: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        cr = self.style().subElementRect(
            QStyle.SubElement.SE_PushButtonContents,
            opt,
            self,
        )
        text = self.text()
        ico = self.icon()
        opt.text = ""
        opt.icon = QIcon()
        self.style().drawControl(
            QStyle.ControlElement.CE_PushButton,
            opt,
            p,
            self,
        )
        p.setClipping(False)

        isz = self.iconSize()
        has_i = (not ico.isNull() and isz.isValid() and isz.width() > 0 and isz.height() > 0)
        has_t = bool(text)
        if not has_i and not has_t:
            return

        fm = self.fontMetrics()
        tw = int(fm.horizontalAdvance(text)) if has_t else 0
        iw, ih = (isz.width(), isz.height()) if has_i else (0, 0)
        pm = int(
            self.style().pixelMetric(
                QStyle.PixelMetric.PM_LayoutHorizontalSpacing,
                opt,
                self,
            )
            or 0,
        )
        gap = max(scale_px_v(3), min(scale_px_v(10), pm if pm > 0 else scale_px_v(4)))

        if has_i and has_t:
            total = iw + gap + tw
            x0 = int(cr.x() + (cr.width() - total) // 2)
            icon_x = x0
            text_x = int(x0 + iw + gap)
        elif has_t:
            icon_x = 0
            text_x = int(cr.x() + (cr.width() - tw) // 2)
        else:
            icon_x = int(cr.x() + (cr.width() - iw) // 2)
            text_x = 0

        if has_i:
            iy = int(cr.y() + (cr.height() - ih) // 2)
            mode = QIcon.Mode.Disabled if not self.isEnabled() else QIcon.Mode.Normal
            ico.paint(
                p,
                QRect(int(icon_x), int(iy), int(iw), int(ih)),
                Qt.AlignmentFlag.AlignCenter,
                mode,
                QIcon.State.Off,
            )
        if not has_t:
            return

        y_top = int(cr.y() + (cr.height() - fm.height()) // 2)
        baseline = float(y_top + fm.ascent()) + 0.5
        font = self.font()
        fill = _action_label_fill(self)
        outline = QColor(0, 0, 0, 255)

        for dx, dy in _halo_offset_pairs():
            pp = QPainterPath()
            pp.addText(QPointF(float(text_x + dx), float(baseline + dy)), font, text)
            p.fillPath(pp, outline)
        pth = QPainterPath()
        pth.addText(QPointF(float(text_x), baseline), font, text)
        p.fillPath(pth, fill)
