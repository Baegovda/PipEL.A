"""(템플릿) 썸네일 클릭 시 원본·해상도·크기를 보여주는 프레임리스 팝업."""

from __future__ import annotations

import os
from typing import Callable

import numpy as np
from PyQt6.QtCore import QEvent, QFileInfo, QObject, Qt
from PyQt6.QtGui import (
    QGuiApplication,
    QImage,
    QImageReader,
    QMouseEvent,
    QPixmap,
)
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget

from pipela_qt import theme as T
from pipela_qt.card_popup_shell import CardFramelessDialog, center_card_popup, dialog_body_html
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


def _show_message_card(
    parent: QWidget | None,
    title: str,
    message: str,
    *,
    tone: str = "info",
) -> None:
    """안내·경고 — ``QMessageBox`` 대신 ``CardFramelessDialog`` 로 통일."""
    parent_win = parent.window() if parent is not None else None
    dlg = CardFramelessDialog(parent_win, title=title)
    dlg.setMinimumWidth(scale_px_h(360))
    lay = dlg.content_layout()
    lbl = QLabel()
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    col = T.STATUS_WARN if tone == "warn" else T.FG_MUTED
    lbl.setText(
        dialog_body_html(message, color=col, font_px=scale_px_v(11)),
    )
    lay.addWidget(lbl)
    center_card_popup(dlg, parent)
    dlg.exec()


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


def _popup_image_max() -> tuple[int, int]:
    scr = QGuiApplication.primaryScreen()
    if scr is None:
        return 1100, 720
    ag = scr.availableGeometry()
    pad = scale_px_v(48)
    return max(160, ag.width() - pad), max(160, ag.height() - pad)


def _fit_display_size(w0: int, h0: int, max_w: int, max_h: int) -> tuple[int, int]:
    if w0 <= 0 or h0 <= 0:
        return 1, 1
    if w0 <= max_w and h0 <= max_h:
        return w0, h0
    s = min(max_w / float(w0), max_h / float(h0))
    return max(1, int(w0 * s)), max(1, int(h0 * s))


def _make_image_inspect_card_dialog(
    parent_win: QWidget | None,
    header: str,
    pixmap: QPixmap,
    pixel_w: int,
    pixel_h: int,
    size_line: str,
    sub_line: str | None = None,
) -> CardFramelessDialog:
    dlg = CardFramelessDialog(parent_win, title=header)
    lay = dlg.content_layout()
    lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    max_w, max_h = _popup_image_max()
    dw, dh = _fit_display_size(pixmap.width(), pixmap.height(), max_w, max_h)
    if pixmap.width() != dw or pixmap.height() != dh:
        disp = pixmap.scaled(
            dw,
            dh,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        disp = pixmap

    im = QLabel()
    im.setPixmap(disp)
    im.setFixedSize(disp.size())
    im.setAlignment(Qt.AlignmentFlag.AlignCenter)
    im.setStyleSheet(
        f"background: {T.PANEL_BG}; border-radius: {scale_px_v(8)}px;",
    )
    im.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    lay.addWidget(im, 0, Qt.AlignmentFlag.AlignHCenter)

    meta_lines = [
        f"해상도  {pixel_w} × {pixel_h}",
        size_line,
    ]
    if sub_line:
        meta_lines.append(sub_line)
    meta = QLabel()
    meta.setWordWrap(True)
    meta.setTextFormat(Qt.TextFormat.RichText)
    meta.setText(
        dialog_body_html("\n".join(meta_lines), color=T.FG_MUTED, font_px=scale_px_v(11)),
    )
    meta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    meta.setAlignment(
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
    )
    lay.addWidget(meta, 0, Qt.AlignmentFlag.AlignHCenter)
    dlg._pipela_inspect_im = im
    dlg._pipela_inspect_meta = meta
    dlg._pipela_inspect_meta_lines = tuple(meta_lines)
    return dlg


def refresh_open_image_inspect_cards_content_if_any() -> None:
    """열린 이미지 상세 카드 본문(테두리·RichText 폰트) — ``refresh_pipela_typography`` 호환."""
    from PyQt6.QtWidgets import QApplication

    from pipela_qt.card_popup_shell import CardFramelessDialog

    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        if (
            isinstance(w, CardFramelessDialog)
            and w.isVisible()
            and getattr(w, "_pipela_inspect_meta", None) is not None
        ):
            try:
                im = getattr(w, "_pipela_inspect_im", None)
                meta = getattr(w, "_pipela_inspect_meta", None)
                lines = getattr(w, "_pipela_inspect_meta_lines", None)
                if im is not None:
                    im.setStyleSheet(
                        f"background: {T.PANEL_BG}; border-radius: {scale_px_v(8)}px;",
                    )
                if meta is not None and lines:
                    meta.setText(
                        dialog_body_html(
                            "\n".join(str(x) for x in lines),
                            color=T.FG_MUTED,
                            font_px=scale_px_v(11),
                        ),
                    )
            except Exception:
                pass


def show_template_image_detail_dialog(parent: QWidget | None, path: str) -> None:
    path = os.path.normpath(os.path.expandvars(str(path).strip()))
    if not path or not os.path.isfile(path):
        _show_message_card(
            parent,
            "이미지 없음",
            "저장된 이미지 파일 경로가 없거나 파일을 찾을 수 없습니다.",
        )
        return

    qimg = QImage(path)
    if qimg.isNull():
        _show_message_card(
            parent,
            "이미지 읽기 실패",
            "이미지를 불러올 수 없습니다.",
            tone="warn",
        )
        return

    fi = QFileInfo(path)
    size_b = int(fi.size())
    w0, h0 = qimg.width(), qimg.height()
    base = os.path.basename(path)
    kind_lbl = _image_format_label(path)

    pm = QPixmap.fromImage(qimg)
    parent_win = parent.window() if parent is not None else None
    dlg = _make_image_inspect_card_dialog(
        parent_win,
        "템플릿 이미지",
        pm,
        w0,
        h0,
        f"파일 크기  {_format_bytes(size_b)}",
        f"{kind_lbl} · {base}",
    )
    center_card_popup(dlg, parent)
    dlg.exec()


def show_match_patch_bgr_dialog(parent: QWidget | None, bgr: object) -> None:
    """인게임 매칭으로 잘라 낸 BGR 패치(파일 없음)."""
    if bgr is None:
        _show_message_card(
            parent,
            "매칭 없음",
            "아직 기준(임계값)을 넘긴 인게임 매칭이 없습니다.",
        )
        return
    if isinstance(bgr, np.ndarray) and bgr.size == 0:
        _show_message_card(
            parent,
            "매칭 없음",
            "아직 기준(임계값)을 넘긴 인게임 매칭이 없습니다.",
        )
        return

    from pipela_qt.panels.image_preview import pixmap_from_bgr

    arr = bgr
    try:
        h0, w0 = int(arr.shape[0]), int(arr.shape[1])
    except Exception:
        _show_message_card(
            parent,
            "표시 실패",
            "이미지 형식을 읽을 수 없습니다.",
            tone="warn",
        )
        return
    nbytes = int(arr.nbytes) if hasattr(arr, "nbytes") else w0 * h0 * 3

    pm = pixmap_from_bgr(arr, max(1, w0), max(1, h0))
    if pm is None or pm.isNull():
        _show_message_card(
            parent,
            "표시 실패",
            "이미지를 표시할 수 없습니다.",
            tone="warn",
        )
        return

    parent_win = parent.window() if parent is not None else None
    dlg = _make_image_inspect_card_dialog(
        parent_win,
        "매칭된 이미지",
        pm,
        w0,
        h0,
        f"데이터 크기  {_format_bytes(nbytes)} (메모리)",
        "감지 루프에서 임계값 이상일 때 잘라 낸 게임 화면 영역입니다.",
    )
    center_card_popup(dlg, parent)
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
                _show_message_card(
                    parent_win,
                    "이미지 없음",
                    "미리볼 수 있는 이미지 파일이 없습니다.",
                )
        return False


def attach_template_thumbnail_click_preview(
    thumb_label: QWidget,
    get_path: Callable[[], str | None],
) -> None:
    """썸네일 ``QLabel``에 클릭 핸들러(원본·해상도·파일 크기 팝업)를 연결."""
    thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
    thumb_label.setToolTip("클릭하면 이미지·해상도·파일 크기를 봅니다")
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
    """인게임 마지막 매칭 BGR 썸네일 — 클릭 시 프레임리스 상세 팝업."""
    thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
    thumb_label.setToolTip("클릭하면 매칭 영역·해상도·크기를 봅니다")
    thumb_label.installEventFilter(_MatchBgrClickFilter(thumb_label, get_bgr))
