"""QScrollArea + wordWrap QLabel: 첫 레이아웃에서 너비 미확정으로 높이가 0에 가까워지는 현상 완화."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QScrollArea, QWidget


class _ScrollInnerMinWidthSync(QObject):
    def __init__(self, scroll: QScrollArea) -> None:
        super().__init__(scroll)
        self._scroll = scroll

    def eventFilter(self, obj, event):
        if event.type() != QEvent.Type.Resize:
            return False
        self._apply()
        return False

    def _apply(self) -> None:
        sa = self._scroll
        inner = sa.widget()
        if inner is None:
            return
        vw = sa.viewport().width()
        if vw > 0:
            inner.setMinimumWidth(vw)


def tie_scroll_content_min_width(scroll: QScrollArea) -> None:
    """뷰포트 리사이즈 시 스크롤 내용 위젯 최소 너비를 맞춰 QLabel 줄바꿈 높이가 계산되게 한다."""
    filt = _ScrollInnerMinWidthSync(scroll)
    scroll.viewport().installEventFilter(filt)
    filt._apply()


def relayout_scroll_areas_under(root: QWidget) -> None:
    """탭 전환·창 표시 직후 등: 스크롤 뷰포트 폭이 확정된 뒤 줄바꿈·높이를 즉시 다시 계산."""
    if not root.isVisible():
        return
    for sa in root.findChildren(QScrollArea):
        inner = sa.widget()
        if inner is None:
            continue
        vw = sa.viewport().width()
        if vw <= 0:
            continue
        inner.setMinimumWidth(vw)
        inner.updateGeometry()
        sa.updateGeometry()
    lay = root.layout()
    if lay is not None:
        lay.activate()
    root.updateGeometry()
