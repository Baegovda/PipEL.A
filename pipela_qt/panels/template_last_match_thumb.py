"""템플릿 파일 썸네일 아래 — 매칭으로 판정된 순간의 인게임 패치 미리보기."""

from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pipela_qt import theme as T
from pipela_qt.panels.image_preview import pixmap_from_bgr
from pipela_qt.panels.settings_chrome import (
    settings_label_align_center_h,
    settings_template_thumb_match_caption_style,
    settings_template_thumb_target_caption_style,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v

TARGET_TEMPLATE_CAPTION = "목표 이미지"
LAST_MATCH_CAPTION = "매칭된 이미지"


def append_template_target_image_caption(
    parent_lay: QVBoxLayout,
    typo: TypographyStyleBundle,
) -> QLabel:
    """원본 템플릿 썸네일 바로 위 — 「목표 이미지」."""
    lbl = QLabel(TARGET_TEMPLATE_CAPTION)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(settings_template_thumb_target_caption_style())
    typo.add(lambda w=lbl: w.setStyleSheet(settings_template_thumb_target_caption_style()))
    settings_label_align_center_h(lbl)
    parent_lay.addWidget(lbl, 0, Qt.AlignmentFlag.AlignHCenter)
    return lbl


def _format_last_match_caption(pipela_mod: Any, hit_kind: str) -> str:
    get_sc = getattr(pipela_mod, "get_template_last_match_score", None)
    if not callable(get_sc):
        return f"{LAST_MATCH_CAPTION} · —"
    sc = get_sc(str(hit_kind))
    if sc is None:
        return f"{LAST_MATCH_CAPTION} · —"
    return f"{LAST_MATCH_CAPTION} · {float(sc):.2f}"

# 원본 템플릿 파일·매칭 패치 미리보기 공통 — 디자인 px, `scale_px` 로 환산
THUMB_PREVIEW_MAX_W = 148
THUMB_PREVIEW_MAX_H = 90
THUMB_PREVIEW_SLOT_MIN_W = 92
THUMB_PREVIEW_SLOT_MIN_H = 56


def _thumb_slot_base_qss() -> str:
    """빈 칸·플레이스홀더 테두리 — import 시점 고정 px 회피."""
    return f"background: {T.PANEL_BG}; border-radius: {scale_px_v(4)}px;"


def thumb_preview_max_wh() -> tuple[int, int]:
    """`pixmap_from_bgr` / `_scaled_pixmap` 등 미리보기 스케일 상한."""
    return scale_px_h(THUMB_PREVIEW_MAX_W), scale_px_v(THUMB_PREVIEW_MAX_H)


def thumb_preview_slot_min_wh() -> tuple[int, int]:
    """이미지 없을 때 플레이스홀더 박스(원본·매칭 동일)."""
    return scale_px_h(THUMB_PREVIEW_SLOT_MIN_W), scale_px_v(THUMB_PREVIEW_SLOT_MIN_H)


def thumb_empty_size_from_orig_template_label(orig: QLabel | None) -> tuple[int, int] | None:
    """원본 템플릿 썸네일 라벨과 같은 빈 칸 크기 — 레이아웃 전이면 `sizeHint` 시도."""
    if orig is None:
        return None
    w, h = int(orig.width()), int(orig.height())
    if w > 0 and h > 0:
        return (w, h)
    sh = orig.sizeHint()
    sw, shh = int(sh.width()), int(sh.height())
    if sw > 0 and shh > 0:
        return (sw, shh)
    return None


def fit_template_thumb_label_to_pixmap(
    lbl: QLabel,
    pm: QPixmap | None,
    *,
    min_w: int | None = None,
    min_h: int | None = None,
    empty_text: str = "없음",
    empty_fixed_wh: tuple[int, int] | None = None,
) -> None:
    """`PANEL_BG` 배경이 픽스맵과 동일 크기가 되도록 맞춤. 없을 때만 최소 박스."""
    smw, smh = thumb_preview_slot_min_wh()
    mw = smw if min_w is None else min_w
    mh = smh if min_h is None else min_h
    base = _thumb_slot_base_qss()
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if pm is not None and not pm.isNull():
        lbl.setText("")
        lbl.setPixmap(pm)
        lbl.setFixedSize(pm.size())
        lbl.setStyleSheet(base)
    else:
        lbl.clear()
        lbl.setText(empty_text)
        if empty_fixed_wh is not None:
            fw, fh = int(empty_fixed_wh[0]), int(empty_fixed_wh[1])
            if fw > 0 and fh > 0:
                lbl.setFixedSize(fw, fh)
            else:
                lbl.setFixedSize(mw, mh)
        else:
            lbl.setFixedSize(mw, mh)
        lbl.setStyleSheet(f"{base} color: {T.FG_DIM};")


def create_last_match_thumb_row(
    typo: TypographyStyleBundle | None = None,
) -> tuple[QLabel, QLabel]:
    cap = QLabel(f"{LAST_MATCH_CAPTION} · —")
    cap.setStyleSheet(settings_template_thumb_match_caption_style())
    cap.setWordWrap(True)
    settings_label_align_center_h(cap)
    mw, mh = thumb_preview_slot_min_wh()
    thumb = QLabel()
    thumb.setMinimumSize(mw, mh)
    thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    thumb.setStyleSheet(_thumb_slot_base_qss())
    if typo is not None:
        typo.add(lambda w=thumb: w.setStyleSheet(_thumb_slot_base_qss()))
    return cap, thumb


def append_side_by_side_target_and_match_previews(
    parent_lay: QVBoxLayout,
    typo: TypographyStyleBundle,
    target_thumb: QLabel,
    *,
    pipela_mod: Any | None = None,
    hit_kind: str,
) -> tuple[QLabel, QLabel]:
    """좌측 목표 이미지·우측 매칭 이미지(캡션+썸네일) 가로 배치. 반환 (매칭 캡션, 매칭 썸네일)."""
    row = QHBoxLayout()
    row.setSpacing(scale_px_h(12))
    left_col = QVBoxLayout()
    left_col.setSpacing(scale_px_v(4))
    right_col = QVBoxLayout()
    right_col.setSpacing(scale_px_v(4))
    target_cap = QLabel(TARGET_TEMPLATE_CAPTION)
    target_cap.setWordWrap(True)
    target_cap.setStyleSheet(settings_template_thumb_target_caption_style())
    typo.add(
        lambda w=target_cap: w.setStyleSheet(settings_template_thumb_target_caption_style()),
    )
    settings_label_align_center_h(target_cap)
    left_col.addWidget(target_cap, 0, Qt.AlignmentFlag.AlignHCenter)
    left_col.addWidget(target_thumb, 0, Qt.AlignmentFlag.AlignHCenter)
    match_cap, match_thumb = create_last_match_thumb_row(typo)
    typo.add(lambda w=match_cap: w.setStyleSheet(settings_template_thumb_match_caption_style()))
    right_col.addWidget(match_cap, 0, Qt.AlignmentFlag.AlignHCenter)
    right_col.addWidget(match_thumb, 0, Qt.AlignmentFlag.AlignHCenter)
    if pipela_mod is not None and hit_kind:

        def _get_bgr():
            fn = getattr(pipela_mod, "get_template_last_match_patch_bgr", None)
            return fn(str(hit_kind)) if callable(fn) else None

        from pipela_qt.panels.thumbnail_preview_dialog import attach_match_patch_click_preview

        attach_match_patch_click_preview(match_thumb, _get_bgr)
    lw = QWidget()
    lw.setLayout(left_col)
    rw = QWidget()
    rw.setLayout(right_col)
    row.addWidget(lw, 1)
    row.addWidget(rw, 1)
    parent_lay.addLayout(row)
    return match_cap, match_thumb


def append_template_matched_image_preview(
    parent_lay: QVBoxLayout,
    typo: TypographyStyleBundle,
    *,
    pipela_mod: Any | None = None,
    hit_kind: str | None = None,
) -> tuple[QLabel, QLabel]:
    """캡션(점수 포함)·썸네일 슬롯 세로 추가. 반환 (캡션 라벨, 썸네일 라벨)."""
    cap, thumb = create_last_match_thumb_row(typo)
    typo.add(lambda w=cap: w.setStyleSheet(settings_template_thumb_match_caption_style()))
    parent_lay.addWidget(cap, 0, Qt.AlignmentFlag.AlignHCenter)
    parent_lay.addWidget(thumb, 0, Qt.AlignmentFlag.AlignHCenter)
    if pipela_mod is not None and hit_kind:

        def _get_bgr():
            fn = getattr(pipela_mod, "get_template_last_match_patch_bgr", None)
            return fn(str(hit_kind)) if callable(fn) else None

        from pipela_qt.panels.thumbnail_preview_dialog import attach_match_patch_click_preview

        attach_match_patch_click_preview(thumb, _get_bgr)
    return cap, thumb


def update_last_match_thumbnail(
    thumb: QLabel,
    pipela_mod,
    hit_kind: str,
    *,
    match_caption_lbl: QLabel | None = None,
    orig_thumb: QLabel | None = None,
) -> None:
    """`orig_thumb`가 있으면 매칭 없음(—)일 때 그 라벨과 동일 크기로 맞춤."""
    owh = thumb_empty_size_from_orig_template_label(orig_thumb)

    def _empty() -> None:
        fit_template_thumb_label_to_pixmap(
            thumb,
            None,
            empty_text="—",
            empty_fixed_wh=owh,
        )
        if match_caption_lbl is not None:
            match_caption_lbl.setText(f"{LAST_MATCH_CAPTION} · —")

    getr = getattr(pipela_mod, "get_template_last_match_patch_bgr", None)
    if not callable(getr):
        _empty()
        return
    bgr = getr(str(hit_kind))
    if bgr is None or (isinstance(bgr, np.ndarray) and bgr.size == 0):
        _empty()
        return
    tw, th = thumb_preview_max_wh()
    pm = pixmap_from_bgr(bgr, tw, th)
    if pm:
        fit_template_thumb_label_to_pixmap(thumb, pm, empty_text="—")
        if match_caption_lbl is not None:
            match_caption_lbl.setText(_format_last_match_caption(pipela_mod, hit_kind))
    else:
        _empty()
