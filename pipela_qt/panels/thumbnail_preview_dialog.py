"""(템플릿) 썸네일 클릭 시 원본 픽셀·파일 정보를 보여주는 다이얼로그."""

from __future__ import annotations

import os
from typing import Callable

from PyQt6.QtCore import QEvent, QObject, QFileInfo, Qt
from PyQt6.QtGui import QGuiApplication, QImage, QImageReader, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px


def _format_bytes(n: int) -> str:
    s = float(max(0, int(n)))
    u = 0
    units = ("B", "KB", "MB", "GB", "TB")
    while s >= 1024.0 and u < len(units) - 1:
        s /= 1024.0
        u += 1
    if u == 0:
        return f"{int(s)} {units[u]}"
    return f"{s:.2f} {units[u]}"


def _image_format_label(path: str) -> str:
    try:
        fmt = QImageReader.imageFormat(path)
    except Exception:
        fmt = b""
    if fmt:
        try:
            return bytes(fmt).decode("ascii", errors="replace").upper()
        except Exception:
            return str(fmt)
    suf = os.path.splitext(path)[1].lstrip(".").upper()
    return suf if suf else "—"


def show_template_image_detail_dialog(parent: QWidget | None, path: str) -> None:
    path = os.path.normpath(os.path.expandvars(str(path).strip()))
    if not path or not os.path.isfile(path):
        QMessageBox.information(
            parent,
            "이미지 없음",
            "저장된 이미지 파일 경로가 없거나 파일을 찾을 수 없습니다.",
        )
        return

    qimg = QImage(path)
    if qimg.isNull():
        QMessageBox.warning(parent, "이미지 읽기 실패", "이미지를 불러올 수 없습니다.")
        return

    fi = QFileInfo(path)
    size_b = int(fi.size())
    w0, h0 = qimg.width(), qimg.height()
    base = os.path.basename(path)
    mtime = fi.lastModified().toString("yyyy-MM-dd hh:mm")
    kind_lbl = _image_format_label(path)

    scr = QGuiApplication.primaryScreen()
    if scr is not None:
        ag = scr.availableGeometry()
        max_w = max(200, int(ag.width() * 0.92))
        max_h = max(200, int(ag.height() * 0.62))
    else:
        max_w, max_h = 1200, 800

    dlg = QDialog(parent)
    dlg.setWindowTitle("템플릿 이미지")
    dlg.setModal(True)
    dlg.setMinimumWidth(scale_px(400))
    root = QVBoxLayout(dlg)
    m = scale_px(10)
    root.setContentsMargins(m, m, m, m)
    root.setSpacing(scale_px(8))

    pm = QPixmap.fromImage(qimg)
    im_lbl = QLabel()
    im_lbl.setPixmap(pm)
    im_lbl.setFixedSize(pm.size())
    im_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    im_lbl.setStyleSheet(f"background: {T.PANEL_BG};")
    im_lbl.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )

    sa = QScrollArea()
    sa.setWidget(im_lbl)
    sa.setWidgetResizable(False)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setStyleSheet(f"background: {T.PANEL_BG};")
    sa.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cap_w = min(w0 + 2, max_w)
    cap_h = min(h0 + 2, max_h)
    sa.setFixedSize(cap_w, cap_h)

    root.addWidget(sa, 0, Qt.AlignmentFlag.AlignHCenter)

    form = QFormLayout()
    form.setSpacing(scale_px(4))
    form.setHorizontalSpacing(scale_px(10))
    form.addRow("파일 정보", QLabel(kind_lbl))
    form.addRow("파일 크기", QLabel(_format_bytes(size_b)))
    form.addRow("픽셀", QLabel(f"{w0} × {h0}"))
    form.addRow("수정 시각", QLabel(mtime))
    form.addRow("파일명", QLabel(base))
    pe = QLineEdit(path)
    pe.setReadOnly(True)
    pe.setMinimumWidth(min(scale_px(480), cap_w + scale_px(80)))
    pe.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard,
    )
    form.addRow("이미지 파일 경로", pe)
    root.addLayout(form)

    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    bb.rejected.connect(dlg.reject)
    root.addWidget(bb)

    dlg.resize(
        min(dlg.sizeHint().width(), max_w + m * 2),
        min(dlg.sizeHint().height(), int(max_h * 1.5)),
    )
    dlg.exec()


def show_match_patch_bgr_dialog(parent: QWidget | None, bgr) -> None:
    """기준(임계값)을 넘긴 **직전** 템플릿 매칭이 잘라 낸 BGR 패치(파일 경로 없음)."""
    try:
        if bgr is None or getattr(bgr, "size", 0) == 0:
            raise ValueError("empty")
    except Exception:
        QMessageBox.information(
            parent,
            "매칭 없음",
            "아직 기준(임계값)을 넘긴 인게임 매칭이 없습니다.",
        )
        return

    from pipela_qt.panels.image_preview import pixmap_from_bgr

    h0, w0 = int(bgr.shape[0]), int(bgr.shape[1])
    pm = pixmap_from_bgr(bgr, max(1, w0), max(1, h0))
    if pm is None or pm.isNull():
        QMessageBox.warning(parent, "표시 실패", "이미지를 표시할 수 없습니다.")
        return

    scr = QGuiApplication.primaryScreen()
    if scr is not None:
        ag = scr.availableGeometry()
        max_ww = max(200, int(ag.width() * 0.92))
        max_hh = max(200, int(ag.height() * 0.55))
    else:
        max_ww, max_hh = 1200, 800

    dlg = QDialog(parent)
    dlg.setWindowTitle("인게임 마지막 매칭")
    dlg.setModal(True)
    dlg.setMinimumWidth(scale_px(400))
    root = QVBoxLayout(dlg)
    m = scale_px(10)
    root.setContentsMargins(m, m, m, m)
    root.setSpacing(scale_px(8))

    im_lbl = QLabel()
    im_lbl.setPixmap(pm)
    im_lbl.setFixedSize(pm.size())
    im_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    im_lbl.setStyleSheet(f"background: {T.PANEL_BG};")
    im_lbl.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    sa = QScrollArea()
    sa.setWidget(im_lbl)
    sa.setWidgetResizable(False)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setStyleSheet(f"background: {T.PANEL_BG};")
    sa.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cap_w = min(w0 + 2, max_ww)
    cap_h = min(h0 + 2, max_hh)
    sa.setFixedSize(cap_w, cap_h)
    root.addWidget(sa, 0, Qt.AlignmentFlag.AlignHCenter)

    form = QFormLayout()
    form.setSpacing(scale_px(4))
    form.setHorizontalSpacing(scale_px(10))
    form.addRow("픽셀", QLabel(f"{w0} × {h0}"))
    info = QLabel(
        "감지 루프에서 점수가 기준(임계값) 이상이었을 때, 그 순간의 게임 화면을 "
        "템플릿과 동일한 크기로 잘라 낸 영역입니다. (파일이 아닌 메모리 캡처)",
    )
    info.setWordWrap(True)
    form.addRow("설명", info)
    root.addLayout(form)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    bb.rejected.connect(dlg.reject)
    root.addWidget(bb)
    dlg.resize(
        min(dlg.sizeHint().width(), max_ww + m * 2),
        min(dlg.sizeHint().height(), int(max_hh * 1.6)),
    )
    dlg.exec()


class _ThumbClickOpenFilter(QObject):
    def __init__(self, host: QWidget, get_path: Callable[[], str | None]) -> None:
        super().__init__(host)
        self._get_path = get_path

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(
            event,
            QMouseEvent,
        ):
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            w = self.parent()
            parent_win = w.window() if isinstance(w, QWidget) else None
            p = (self._get_path() or "").strip()
            if p and os.path.isfile(p):
                show_template_image_detail_dialog(parent_win, p)
            else:
                QMessageBox.information(
                    parent_win,
                    "이미지 없음",
                    "미리볼 수 있는 이미지 파일이 없습니다.",
                )
        return False


def attach_template_thumbnail_click_preview(
    thumb_label: QWidget,
    get_path: Callable[[], str | None],
) -> None:
    """썸네일 ``QLabel``에 클릭 핸들러(원본·파일 정보)를 연결."""
    thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
    thumb_label.setToolTip("클릭하면 원본 크기·파일 정보를 표시합니다")
    flt = _ThumbClickOpenFilter(thumb_label, get_path)
    thumb_label.installEventFilter(flt)


class _MatchBgrClickFilter(QObject):
    def __init__(self, host: QWidget, get_bgr: Callable[[], object]) -> None:
        super().__init__(host)
        self._get_bgr = get_bgr

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(
            event,
            QMouseEvent,
        ):
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            w = self.parent()
            parent_win = w.window() if isinstance(w, QWidget) else None
            try:
                bgr = self._get_bgr()
            except Exception:
                bgr = None
            show_match_patch_bgr_dialog(parent_win, bgr)
        return False


def attach_match_patch_click_preview(
    thumb_label: QWidget,
    get_bgr: Callable[[], object],
) -> None:
    """인게임 마지막 매칭 BGR 썸네일 — 클릭 시 ``show_match_patch_bgr_dialog``."""
    thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
    thumb_label.setToolTip("클릭하면 인게임 매칭 영역을 원본 크기로 봅니다")
    thumb_label.installEventFilter(_MatchBgrClickFilter(thumb_label, get_bgr))
