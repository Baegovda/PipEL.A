"""등록한 QDialog: 다이얼로그 밖(다른 UI·게임) 클릭·앱 비활성 시 닫기.

공통으로 ``register_dialog_dismiss_on_outside_click`` 를 한 번만 호출하면 되며,
``CardFramelessDialog`` 는 자동 등록된다.

비활성/파생 이벤트는 ``QApplication.applicationStateChanged``(다른 앱·게임으로 포커스 이동)과
``QEvent.MouseButtonPress``(동일 앱의 다른 Qt 위젯 클릭)을 사용한다. 메뉴/콤보 팝업이 열린
동안( ``activePopupWidget()`` )은 닫지 않는다.
"""

from __future__ import annotations

import builtins
import os
import time
import weakref

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

from pipela_qt.frame_timing import append_notify_frame_timing_ns

_CTRL: "PipelaDialogDismissOnOutsideController | None" = None
# cProfile: 모든 이벤트가 notify 통과 — 카운트 0 일 때 최소 분기, 보일 때만 MouseButtonPress 처리
# int compare avoids Enum dispatch on every event when comparing to MouseButtonPress
_QMI = int(QEvent.Type.MouseButtonPress)
_UI_FRAME_TIMING_OK = frozenset({"1", "true", "yes"})
# PipelaApplication.notify is on every QEvent — getenv every time cost ~200k+ lookups/sec when profiling FT.
_NOTIFY_UI_FT_STARTED = False
_NOTIFY_UI_FT_ON = False


class PipelaApplication(QApplication):
    """``notify`` 에서 다이얼로그 외부 클릭 감지(전역) — ``QApplication`` 은 기본로 자식의 마우스를 받지 않는다."""

    @builtins.profile
    def notify(self, receiver: QObject, event: QEvent) -> bool:  # noqa: N802
        global _NOTIFY_UI_FT_STARTED, _NOTIFY_UI_FT_ON
        if not _NOTIFY_UI_FT_STARTED:
            _NOTIFY_UI_FT_ON = (
                os.environ.get("PIPELA_UI_FRAME_TIMING", "").strip().lower()
                in _UI_FRAME_TIMING_OK
            )
            _NOTIFY_UI_FT_STARTED = True
        _dbg_ft = _NOTIFY_UI_FT_ON
        _t0_ns = time.perf_counter_ns() if _dbg_ft else None
        try:
            c = _CTRL
            if c is None or c._visible_dismissible_count <= 0:
                return super().notify(receiver, event)
            if int(event.type()) != _QMI:
                return super().notify(receiver, event)
            if c.handle_global_mouse_in_notify(event):
                return True
            return super().notify(receiver, event)
        finally:
            if _t0_ns is not None:
                append_notify_frame_timing_ns(time.perf_counter_ns() - _t0_ns)


def register_dialog_dismiss_on_outside_click(dialog: QDialog) -> None:
    """QDialog마다 1회 — 기본으로 바깥 클릭/앱 비활성 시 ``close()``.

    끄려면 ``dialog.setProperty("pipela_no_dismiss_outside", True)`` (부모 생성 후) 또는
    ``dialog._pipela_no_dismiss_outside = True`` 를 쓴다.
    """
    if getattr(dialog, "_pipela_dismiss_outside_reg", False):
        return
    app = QApplication.instance()
    if app is None:
        return
    if dialog.property("pipela_no_dismiss_outside") or getattr(
        dialog,
        "_pipela_no_dismiss_outside",
        False,
    ):
        return
    dialog._pipela_dismiss_outside_reg = True  # type: ignore[attr-defined]
    _PipelaDismissTracker(dialog, _ensure_ctrl(app))


def _no_dismiss(d: QDialog) -> bool:
    return bool(d.property("pipela_no_dismiss_outside") or getattr(d, "_pipela_no_dismiss_outside", False))


def _ensure_ctrl(app: QApplication) -> "PipelaDialogDismissOnOutsideController":
    global _CTRL
    if _CTRL is None:
        _CTRL = PipelaDialogDismissOnOutsideController(app)
    return _CTRL


def _is_inside_dialog(d: QDialog, w: QWidget | None, gpos: QPoint) -> bool:
    if w is not None and d.isVisible():
        if d.isAncestorOf(w):
            return True
        cw = w.window()
        if cw is d:
            return True
    if d.isVisible():
        if d.frameGeometry().contains(gpos):
            return True
    return False


def _top_tracked(refs: list, *, visible_only: bool, skip_no_dismiss: bool) -> QDialog | None:
    for r in reversed(refs):
        d = r()
        if d is None:
            continue
        if visible_only and not d.isVisible():
            continue
        if skip_no_dismiss and _no_dismiss(d):
            continue
        return d
    return None


class _PipelaDismissTracker(QObject):
    def __init__(self, d: QDialog, ctrl: "PipelaDialogDismissOnOutsideController") -> None:
        super().__init__(d)
        self._d = d
        self._ctrl = ctrl
        d.installEventFilter(self)
        d.destroyed.connect(self._on_destroyed)
        if d.isVisible():
            self._ctrl._on_dialog_shown(d)

    def _on_destroyed(self) -> None:
        self._ctrl._on_dialog_gone(self._d)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is not self._d:
            return False
        if event.type() == QEvent.Type.Show:
            self._ctrl._on_dialog_shown(self._d)
        elif event.type() == QEvent.Type.Hide:
            self._ctrl._on_dialog_hidden(self._d)
        return False


class PipelaDialogDismissOnOutsideController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._order: list[weakref.ref[QDialog]] = []
        # ``notify`` 핫패스: Show/Hide/Gone 시에만 갱신 (이벤트마다 weakref/visible 루프 금지)
        self._visible_dismissible_count: int = 0
        app._pipela_dismiss_on_outside_controller = self
        app.applicationStateChanged.connect(self._on_app_state)

    def _prune(self) -> None:
        self._order = [r for r in self._order if r() is not None]

    def _sync_visible_dismissible_count(self) -> None:
        self._prune()
        n = 0
        for r in self._order:
            d = r()
            if d is not None and d.isVisible() and not _no_dismiss(d):
                n += 1
        self._visible_dismissible_count = n

    def _on_dialog_shown(self, d: QDialog) -> None:
        if _no_dismiss(d):
            return
        self._prune()
        self._order = [r for r in self._order if r() is not d]
        self._order.append(weakref.ref(d))
        self._sync_visible_dismissible_count()

    def _on_dialog_hidden(self, d: QDialog) -> None:
        self._order = [r for r in self._order if r() is not d]
        self._prune()
        self._sync_visible_dismissible_count()

    def _on_dialog_gone(self, d: QDialog) -> None:
        self._order = [r for r in self._order if r() is not d]
        self._prune()
        self._sync_visible_dismissible_count()

    def _on_app_state(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationState.ApplicationInactive:
            return
        if QApplication.activePopupWidget() is not None:
            return
        # 다음 틱: 일시적 포커스/모달이 정리될 때까지
        QTimer.singleShot(0, self._close_top_after_inactive)

    def _close_top_after_inactive(self) -> None:
        if QApplication.activePopupWidget() is not None:
            return
        self._prune()
        d = _top_tracked(self._order, visible_only=True, skip_no_dismiss=True)
        if d is None:
            self._sync_visible_dismissible_count()
            return
        if d.isActiveWindow():
            return
        d.close()
        self._sync_visible_dismissible_count()

    def handle_global_mouse_in_notify(self, event: QEvent) -> bool:
        """``QApplication.notify`` 전용: True 이면 이벤트 소비(다이얼로그를 닫음)."""
        if not isinstance(event, QMouseEvent):
            return False
        if QApplication.activePopupWidget() is not None:
            return False
        self._prune()
        d_top = _top_tracked(self._order, visible_only=True, skip_no_dismiss=True)
        if d_top is None or not d_top.isVisible():
            return False
        gpos = event.globalPosition().toPoint()
        w = QApplication.widgetAt(gpos)
        if _is_inside_dialog(d_top, w, gpos):
            return False
        d_top.close()
        return True
