"""읽기 전용/입력 텍스트 위젯 — 우하단 모서리를 드래그해 크기 조절."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit, QSizePolicy

from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


def _in_corner(pos: QPointF, w: int, h: int, margin: int) -> bool:
    return pos.x() >= w - margin and pos.y() >= h - margin


class ResizablePlainTextEdit(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rz_margin = scale_px_v(10)
        self._rz_active = False
        self._rz_start: QPointF | None = None
        self._rz_h0 = 0
        self.setMinimumHeight(scale_px_v(72))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)

    def _corner_hot(self, pos: QPointF) -> bool:
        return _in_corner(pos, self.width(), self.height(), self._rz_margin)

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
            self.setMaximumHeight(16777215)
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

    def leaveEvent(self, e: QEvent) -> None:
        if not self._rz_active:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().leaveEvent(e)


class ResizableLineEdit(QLineEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rz_margin = scale_px_v(10)
        self._rz_active = False
        self._rz_start: QPointF | None = None
        self._rz_w0 = 0
        self._rz_h0 = 0
        self.setMinimumWidth(scale_px_h(48))
        self.setMinimumHeight(scale_px_v(26))
        self.setMouseTracking(True)

    def _corner_hot(self, pos: QPointF) -> bool:
        return _in_corner(pos, self.width(), self.height(), self._rz_margin)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._corner_hot(e.position()):
            self._rz_active = True
            self._rz_start = QPointF(e.globalPosition())
            self._rz_w0 = self.width()
            self._rz_h0 = self.height()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._rz_active and self._rz_start is not None:
            dx = e.globalPosition().x() - self._rz_start.x()
            dy = e.globalPosition().y() - self._rz_start.y()
            nw = max(self.minimumWidth(), int(self._rz_w0 + dx))
            nh = max(self.minimumHeight(), int(self._rz_h0 + dy))
            self.setMinimumWidth(nw)
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

    def leaveEvent(self, e: QEvent) -> None:
        if not self._rz_active:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().leaveEvent(e)


class ResizableTextEdit(QTextEdit):
    """Tesseract 안내 등 — QTextEdit."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rz_margin = scale_px_v(10)
        self._rz_active = False
        self._rz_start: QPointF | None = None
        self._rz_h0 = 0
        self.setMinimumHeight(scale_px_v(80))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)

    def _corner_hot(self, pos: QPointF) -> bool:
        return _in_corner(pos, self.width(), self.height(), self._rz_margin)

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

    def leaveEvent(self, e: QEvent) -> None:
        if not self._rz_active:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().leaveEvent(e)


class ResizableTerminalLog(ResizableTextEdit):
    """제어창 터미널 탭 — HTML 로그. `setReadOnly`·`setAcceptRichText` 는 호출 측에서 설정."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(scale_px_v(120))
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
