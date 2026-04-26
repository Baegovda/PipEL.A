"""Pipela UI 가변 스케일 — 폭·루트 pt 단일 기준(중앙 참조).

위젯·QSS·레이아웃은 가능하면 여기서 re-export 되는 API만 사용한다.
실제 계산은 `ui_typography` — 본 모듈이 공통 진입점이다.
"""

from __future__ import annotations

from typing import Any

from pipela_qt.ui_typography import (
    control_action_label_pt_factor,
    letter_spacing_qss,
    qss_pad_all,
    qss_pad_trbl,
    qss_pad_vh,
    root_font_pt,
    scale_px,
    scaled_design_pt,
    set_root_font_pt,
    set_typography_layout_width_px,
    spt,
    typography_layout_width_px,
    typography_width_scale,
)

__all__ = (
    "action_button_qss_padding",
    "action_icon_label_gap",
    "control_action_label_pt_factor",
    "control_icon_side_px",
    "letter_spacing_qss",
    "main_shell_margins_lr_tb",
    "qss_pad_all",
    "qss_pad_trbl",
    "qss_pad_vh",
    "root_font_pt",
    "scale_px",
    "scaled_design_pt",
    "set_root_font_pt",
    "set_typography_layout_width_px",
    "spt",
    "typography_layout_width_px",
    "typography_width_scale",
)


def main_shell_margins_lr_tb() -> tuple[int, int, int, int]:
    """제어창·킬 독 등 본문 `QVBoxLayout` — `app_shell` 과 메인 허브(12)와 동일."""
    from pipela_qt import app_shell

    return app_shell.shell_root_outer_margins_lr_tb()


def action_icon_label_gap() -> str:
    """아이콘과 라벨 사이 — 좁은 창에서 EN SPACE 대신 더 얇은 공백."""
    w = typography_layout_width_px()
    if w is None or int(w) >= 420:
        return "\u2002"
    if int(w) >= 340:
        return "\u2009"
    if int(w) >= 280:
        return "\u200a"
    return ""


def action_button_qss_padding() -> str:
    """기능 그리드 QPushButton padding — 가로가 좁을수록 좌우 패딩 축소."""
    w = typography_layout_width_px()
    if w is None:
        return qss_pad_vh(9, 10)
    wi = int(w)
    if wi >= 420:
        return qss_pad_vh(9, 10)
    if wi >= 340:
        return qss_pad_vh(8, 8)
    if wi >= 280:
        return qss_pad_vh(7, 7)
    return qss_pad_vh(6, 5)


def control_icon_side_px(pipela_mod: Any) -> int:
    """기능 그리드 아이콘 한 변(픽셀)."""
    try:
        base = float(getattr(pipela_mod, "CONTROL_PANEL_ICON_SIDE", 24) or 24)
    except (TypeError, ValueError):
        base = 24.0
    raw = int(
        round(
            float(scale_px(base, lo=10, hi=40)) * control_action_label_pt_factor(),
        ),
    )
    return max(10, min(40, raw))
