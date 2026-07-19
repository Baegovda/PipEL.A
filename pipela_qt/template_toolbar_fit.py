"""설정·킬 카운터 템플릿 툴바 — `fit_qpushbutton_text_width_qss` + `panel_template_toolbar_button_qss` 공통."""

from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtWidgets import QPushButton

from pipela_qt.panels.settings_chrome import TemplateToolbarRole, panel_template_toolbar_button_qss
from pipela_qt.ui_adaptive import fit_qpushbutton_text_width_qss, scale_px_h, scale_px_v
from pipela_qt.ui_typography import typography_layout_width_px


def settings_template_toolbar_min_measure_px() -> int:
    """제어창 논리 폭 기준 — `max(96, width // 3)` 하한(킬 패널 세션·영구 줄 버튼 근사와 동일)."""
    w = typography_layout_width_px()
    if w is None or int(w) <= 0:
        return 96
    return max(96, int(w) // 3)


def apply_panel_template_toolbar_row_fit(
    pairs: Sequence[tuple[QPushButton, TemplateToolbarRole]],
    *,
    horizontal_padding_px: int | None = None,
    vertical_padding_px: int | None = None,
    min_measure_width_px: int | None = None,
    base_design_pt: float = 9.0,
    min_design_pt: float = 3.8,
) -> None:
    """각 버튼에 폭 피팅 후 역할색 템플릿 툴바 QSS 적용."""
    ph = (
        int(horizontal_padding_px)
        if horizontal_padding_px is not None
        else int(scale_px_h(9, lo=4, hi=160))
    )
    pv = (
        int(vertical_padding_px)
        if vertical_padding_px is not None
        else int(scale_px_v(6, lo=3, hi=112))
    )
    budget = (
        min_measure_width_px
        if min_measure_width_px is not None
        else settings_template_toolbar_min_measure_px()
    )
    for btn, role in pairs:
        f_sz, l_sp = fit_qpushbutton_text_width_qss(
            btn,
            btn.text() or "",
            horizontal_padding_px=ph,
            base_design_pt=base_design_pt,
            min_design_pt=min_design_pt,
            min_measure_width_px=budget,
        )
        btn.setStyleSheet(
            panel_template_toolbar_button_qss(
                role,
                font_size=f_sz,
                letter_spacing=l_sp,
                vertical_padding_px=pv,
                horizontal_padding_px=ph,
            ),
        )
