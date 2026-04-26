"""Windows: Pipela Qt 최상위 창을 작업 표시줄·Alt+Tab 일반 목록에서 제외(WS_EX_TOOLWINDOW)."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QWidget

from pipela_core.win32_window_ops import win32_force_toolwindow_exstyle

_QT_SHOW = QEvent.Type.Show


def qt_win32_hide_top_level_from_taskbar(widget: QWidget | None) -> None:
    if sys.platform != "win32" or widget is None:
        return
    try:
        if not widget.isWindow():
            return
        hid = int(widget.winId())
        if hid:
            win32_force_toolwindow_exstyle(hid)
    except Exception:
        pass


class PipelaTaskbarHideFilter(QObject):
    """``QApplication.installEventFilter`` — Show 될 때마다 해당 최상위 창에 적용."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != _QT_SHOW:
            return False
        if isinstance(watched, QWidget) and watched.isWindow():
            w = watched
            # 네이티브 HWND는 Show 직후 한 틱 늦게 잡히는 경우가 있어 지연 1회도 수행.
            qt_win32_hide_top_level_from_taskbar(w)
            QTimer.singleShot(0, lambda ww=w: qt_win32_hide_top_level_from_taskbar(ww))
        return False
