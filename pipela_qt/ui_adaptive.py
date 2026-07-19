"""Pipela UI 가변 스케일 — 가로(제어 폭)·세로(앵커 클라 높이)·루트 pt.

위젯·QSS·레이아웃은 가능하면 여기서 re-export 되는 API만 사용한다.
실제 계산은 `ui_typography` — 본 모듈이 공통 진입점이다.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtGui import QFont, QFontMetricsF

from pipela_core.ui_fonts import FONT_QT_FAMILY_STACK
from pipela_qt.ui_typography import (
    control_action_label_pt_factor,
    fit_qpushbutton_text_width_qss,
    letter_spacing_qss,
    qss_pad_all,
    qss_pad_trbl,
    qss_pad_vh,
    root_font_pt,
    scale_px,
    scale_px_h,
    scale_px_v,
    scaled_design_pt,
    set_root_font_pt,
    set_typography_layout_height_px,
    set_typography_layout_width_px,
    spt,
    typography_height_scale,
    typography_layout_height_px,
    typography_layout_width_px,
    typography_width_scale,
)

__all__ = (
    "action_button_qss_padding",
    "action_icon_label_gap",
    "action_icon_label_gap_px",
    "control_action_label_pt_factor",
    "control_icon_side_px",
    "dock_panel_icon_width_boost",
    "letter_spacing_qss",
    "main_shell_margins_lr_tb",
    "qss_pad_all",
    "qss_pad_trbl",
    "qss_pad_vh",
    "root_font_pt",
    "scale_px",
    "scale_px_h",
    "scale_px_v",
    "scaled_design_pt",
    "set_root_font_pt",
    "set_typography_layout_height_px",
    "set_typography_layout_width_px",
    "spt",
    "typography_height_scale",
    "typography_layout_height_px",
    "typography_layout_width_px",
    "typography_width_scale",
    "fit_qpushbutton_text_width_qss",
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


def action_icon_label_gap_px() -> int:
    """기능 그리드 `action_icon_label_gap()` 과 같은 폭 단계의 아이콘↔라벨 간격(px).

    QPushButton 은 유니코드 공백 문자로 간격을 두고, 픽셀 레이아웃(예: 메인 탭)은 여기 값을 쓴다."""
    w = typography_layout_width_px()
    if w is None or int(w) >= 420:
        return max(3, scale_px_h(6))
    if int(w) >= 340:
        return max(2, scale_px_h(5))
    if int(w) >= 280:
        return max(2, scale_px_h(4))
    return 0


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


_DOCK_ICON_W_REF = 400.0
# typography_width_scale 상한 때문에 폭만 넓혀도 아이콘이 많이 안 커지므로 패널 논리 폭 전용 배율을 둔다.
_DOCK_ICON_SLOPE = 500.0


def dock_panel_icon_width_boost() -> float:
    """제어창 논리 폭이 넓을수록 큼 (~400px 기준). 좁게 리사이즈 시 약간만 축소."""

    w = typography_layout_width_px()
    if w is None:
        return 1.0
    t = (float(w) - _DOCK_ICON_W_REF) / _DOCK_ICON_SLOPE
    t = max(-0.28, min(1.0, t))
    return float(1.0 + 0.32 * t)


def control_icon_side_px(pipela_mod: Any) -> int:
    """기능 그리드 아이콘 한 변 — 라벨과 같은 DemiBold 10×factor pt 줄높이(×0.94)에 맞춤 + 폭 부스트."""

    _ = pipela_mod
    boost = dock_panel_icon_width_boost()
    pt = float(scaled_design_pt(10.0 * control_action_label_pt_factor()))
    pt_f = max(7.5, min(22.0, pt))
    f = QFont()
    f.setFamilies(list(FONT_QT_FAMILY_STACK))
    f.setWeight(QFont.Weight.DemiBold)
    f.setPointSizeF(pt_f)
    fm = QFontMetricsF(f)
    raw = round(float(fm.height()) * 0.94 * boost)
    return max(10, min(54, int(raw)))
