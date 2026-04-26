"""템플릿 파일 썸네일 아래 — 기준(임계값)을 넘긴 직전 인게임 매칭 미리보기."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from pipela_qt import theme as T
from pipela_qt.panels.image_preview import pixmap_from_bgr
from pipela_qt.panels.settings_chrome import settings_footnote_style, settings_label_align_center_h
from pipela_qt.ui_adaptive import scale_px

LAST_MATCH_CAPTION = "기준 이상이었을 때 · 게임에서 잡힌 영역"

_THUMB_STYLE = f"background: {T.SURFACE}; border-radius: {scale_px(4)}px;"


def create_last_match_thumb_row() -> tuple[QLabel, QLabel]:
    cap = QLabel(LAST_MATCH_CAPTION)
    cap.setStyleSheet(settings_footnote_style())
    cap.setWordWrap(True)
    settings_label_align_center_h(cap)
    thumb = QLabel()
    thumb.setMinimumSize(scale_px(120), scale_px(72))
    thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    thumb.setStyleSheet(_THUMB_STYLE)
    return cap, thumb


def update_last_match_thumbnail(thumb: QLabel, pipela_mod, hit_kind: str) -> None:
    getr = getattr(pipela_mod, "get_template_last_match_patch_bgr", None)
    if not callable(getr):
        thumb.clear()
        thumb.setText("—")
        thumb.setStyleSheet(
            f"{_THUMB_STYLE} color: {T.FG_DIM};",
        )
        return
    bgr = getr(str(hit_kind))
    if bgr is None or (isinstance(bgr, np.ndarray) and bgr.size == 0):
        thumb.clear()
        thumb.setText("—")
        thumb.setStyleSheet(
            f"{_THUMB_STYLE} color: {T.FG_DIM};",
        )
        return
    pm = pixmap_from_bgr(bgr, scale_px(200), scale_px(120))
    if pm:
        thumb.setText("")
        thumb.setPixmap(pm)
        thumb.setStyleSheet(_THUMB_STYLE)
    else:
        thumb.clear()
        thumb.setText("—")
        thumb.setStyleSheet(
            f"{_THUMB_STYLE} color: {T.FG_DIM};",
        )
