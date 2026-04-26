"""Qt 기본 UI 폰트 — `pipela_core.ui_fonts` 정책과 동일한 family 스택."""

from __future__ import annotations

from PyQt6.QtGui import QFont

from pipela_core.ui_fonts import FONT_QT_FAMILY_STACK


def app_default_qfont(
    point_size: int = 11,
    weight: QFont.Weight = QFont.Weight.Normal,
) -> QFont:
    f = QFont()
    f.setPointSize(max(1, int(point_size)))
    f.setWeight(weight)
    f.setFamilies(list(FONT_QT_FAMILY_STACK))
    return f
