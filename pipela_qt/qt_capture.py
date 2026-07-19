"""캡처·ROI·미리보기 — Qt 패널에서 main(`pipela_mod`) API 호출."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout

from pipela_core.region_dispatch import (
    CAPTURE_KIND_TO_REGION_TYPE,
    REGION_TYPES_CLEAR_MATCH_ROI,
)
from pipela_qt.panels.settings_chrome import TemplateToolbarRole, panel_template_toolbar_button_qss
from pipela_qt.template_toolbar_fit import apply_panel_template_toolbar_row_fit
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v


def attach_template_toolbar(
    lay,
    pipela_mod,
    capture_kind: str,
    on_applied: Callable[[], None] | None,
    *,
    typography_bundle: TypographyStyleBundle | None = None,
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
    row1.setSpacing(scale_px_h(8))
    row2 = QHBoxLayout()
    row2.setSpacing(scale_px_h(8))

    bc = QPushButton("캡처")
    bc.setStyleSheet(panel_template_toolbar_button_qss("capture"))
    bc.setCursor(Qt.CursorShape.PointingHandCursor)
    bc.clicked.connect(_cap)
    bt = QPushButton("테스트")
    bt.setStyleSheet(panel_template_toolbar_button_qss("test"))
    bt.setCursor(Qt.CursorShape.PointingHandCursor)
    bt.clicked.connect(_det)
    row1.addWidget(bc)
    row1.addWidget(bt)

    bp = QPushButton("미리보기")
    bp.setStyleSheet(panel_template_toolbar_button_qss("preview"))
    bp.setCursor(Qt.CursorShape.PointingHandCursor)
    bp.clicked.connect(_prev)
    br = QPushButton("영역 선택")
    br.setStyleSheet(panel_template_toolbar_button_qss("region"))
    br.setCursor(Qt.CursorShape.PointingHandCursor)
    br.clicked.connect(_reg)
    row2.addWidget(bp)
    row2.addWidget(br)

    toolbar_pairs: list[tuple[QPushButton, TemplateToolbarRole]] = [
        (bc, "capture"),
        (bt, "test"),
        (bp, "preview"),
        (br, "region"),
    ]
    if rt in REGION_TYPES_CLEAR_MATCH_ROI:

        def _clr() -> None:
            pipela_mod.clear_template_match_region(rt)
            if on_applied is not None:
                on_applied()

        bx = QPushButton("해제")
        bx.setStyleSheet(panel_template_toolbar_button_qss("clear"))
        bx.setCursor(Qt.CursorShape.PointingHandCursor)
        bx.clicked.connect(_clr)
        row2.addWidget(bx)
        toolbar_pairs.append((bx, "clear"))

    if typography_bundle is not None:
        typography_bundle.add(
            lambda pairs=list(toolbar_pairs): apply_panel_template_toolbar_row_fit(pairs),
        )

    col = QVBoxLayout()
    col.setSpacing(scale_px_v(8))
    col.addLayout(row1)
    col.addLayout(row2)
    lay.addLayout(col)


def attach_kill_counter_region_toolbar(
    lay,
    pipela_mod,
    *,
    merge_hbox: QHBoxLayout | None = None,
) -> tuple[QPushButton, QPushButton, QPushButton]:
    """``merge_hbox`` 가 있으면 그 줄에 버튼만 붙이고, 없으면 단독 ``QHBoxLayout`` 을 ``lay`` 에 추가."""

    def _reg() -> None:
        pipela_mod.start_region_select("kill_counter")

    def _prev() -> None:
        pipela_mod.toggle_region_preview_overlay("kill_counter")

    def _clr() -> None:
        pipela_mod.clear_template_match_region("kill_counter")

    bp = QPushButton("미리보기")
    bp.setStyleSheet(panel_template_toolbar_button_qss("preview"))
    bp.setCursor(Qt.CursorShape.PointingHandCursor)
    bp.clicked.connect(_prev)
    br = QPushButton("영역 선택")
    br.setStyleSheet(panel_template_toolbar_button_qss("region"))
    br.setCursor(Qt.CursorShape.PointingHandCursor)
    br.clicked.connect(_reg)
    bx = QPushButton("해제")
    bx.setStyleSheet(panel_template_toolbar_button_qss("clear"))
    bx.setCursor(Qt.CursorShape.PointingHandCursor)
    bx.clicked.connect(_clr)

    row = merge_hbox if merge_hbox is not None else QHBoxLayout()
    row.addWidget(bp)
    row.addWidget(br)
    row.addWidget(bx)
    if merge_hbox is None:
        lay.addLayout(row)
    return (bp, br, bx)
