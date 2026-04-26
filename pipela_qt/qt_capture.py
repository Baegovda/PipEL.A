"""캡처·ROI·미리보기 — Qt 패널에서 main(`pipela_mod`) API 호출."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout

from pipela_core.region_dispatch import (
    CAPTURE_KIND_TO_REGION_TYPE,
    REGION_TYPES_CLEAR_MATCH_ROI,
)
from pipela_qt.panels.settings_chrome import panel_toolbar_button_qss
from pipela_qt.ui_adaptive import scale_px


def _style_toolbar_button(b: QPushButton) -> None:
    b.setStyleSheet(panel_toolbar_button_qss())
    b.setCursor(Qt.CursorShape.PointingHandCursor)


def attach_template_toolbar(
    lay,
    pipela_mod,
    capture_kind: str,
    on_applied: Callable[[], None] | None,
) -> None:
    if CAPTURE_KIND_TO_REGION_TYPE.get(capture_kind) is None:
        return

    def _cap() -> None:
        def _done() -> None:
            if on_applied is not None:
                on_applied()

        pipela_mod.start_template_image_capture(capture_kind, None, on_applied=_done)

    rt = CAPTURE_KIND_TO_REGION_TYPE[capture_kind]

    def _reg() -> None:
        pipela_mod.start_region_select(rt)

    def _prev() -> None:
        pipela_mod.toggle_region_preview_overlay(rt)

    def _det() -> None:
        pipela_mod._template_debug_detect_run(capture_kind, None)

    row1 = QHBoxLayout()
    row2 = QHBoxLayout()
    bc = QPushButton("캡처")
    bc.clicked.connect(_cap)
    bt = QPushButton("테스트")
    bt.clicked.connect(_det)
    _style_toolbar_button(bc)
    _style_toolbar_button(bt)
    row1.addWidget(bc)
    row1.addWidget(bt)

    bp = QPushButton("미리보기")
    bp.clicked.connect(_prev)
    br = QPushButton("영역 선택")
    br.clicked.connect(_reg)
    _style_toolbar_button(bp)
    _style_toolbar_button(br)
    row2.addWidget(bp)
    row2.addWidget(br)
    if rt in REGION_TYPES_CLEAR_MATCH_ROI:

        def _clr() -> None:
            pipela_mod.clear_template_match_region(rt)
            if on_applied is not None:
                on_applied()

        bx = QPushButton("해제")
        bx.clicked.connect(_clr)
        _style_toolbar_button(bx)
        row2.addWidget(bx)

    col = QVBoxLayout()
    col.setSpacing(scale_px(6))
    col.addLayout(row1)
    col.addLayout(row2)
    lay.addLayout(col)


def attach_kill_counter_region_toolbar(
    lay,
    pipela_mod,
) -> tuple[QPushButton, QPushButton, QPushButton]:
    row = QHBoxLayout()

    def _reg() -> None:
        pipela_mod.start_region_select("kill_counter")

    def _prev() -> None:
        pipela_mod.toggle_region_preview_overlay("kill_counter")

    def _clr() -> None:
        pipela_mod.clear_template_match_region("kill_counter")

    bp = QPushButton("미리보기")
    bp.clicked.connect(_prev)
    br = QPushButton("영역 선택")
    br.clicked.connect(_reg)
    bx = QPushButton("해제")
    bx.clicked.connect(_clr)
    _style_toolbar_button(bp)
    _style_toolbar_button(br)
    _style_toolbar_button(bx)
    row.addWidget(bp)
    row.addWidget(br)
    row.addWidget(bx)
    lay.addLayout(row)
    return (bp, br, bx)
