"""Kill counter floater — viewport iso bands for fonts + KC-aware pushbutton width fit."""

from __future__ import annotations

from typing import Any

from pipela_qt.kill_counter_viewport_metrics import (
    KC_VIEWPORT_MIN_PT,
    kc_viewport_design_pt_eff_v,
)
from pipela_qt.ui_typography import fit_qpushbutton_text_width_qss

LAP_ELAPSED_BENCHMARK_TIME_PART = "999:59:59.99"


def hero_prog_pts(vscale: float) -> tuple[float, float]:
    """헤더 히어로 숫자 밴드(배수는 패널에서만 적용)."""
    hi = kc_viewport_design_pt_eff_v(vscale, 14.0)
    lo = max(7.0, kc_viewport_design_pt_eff_v(vscale, 6.25))
    return hi, lo


def recent_roll_value_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 11.0)
    lo = max(6.0, kc_viewport_design_pt_eff_v(vscale, 7.0))
    return hi, lo


def mini_column_value_pts(vscale: float) -> tuple[float, float]:
    return recent_roll_value_pts(vscale)


def dod_grid_value_pts(vscale: float) -> tuple[float, float]:
    return mini_column_value_pts(vscale)


def lap_tile_value_pts(vscale: float) -> tuple[float, float]:
    return recent_roll_value_pts(vscale)


def lap_sheet_kills_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 16.25)
    lo = max(7.0, kc_viewport_design_pt_eff_v(vscale, 8.0))
    return hi, lo


def lap_sheet_caption_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 7.65)
    lo = max(6.0, kc_viewport_design_pt_eff_v(vscale, 6.0))
    return hi, lo


def lap_sheet_elapsed_label_pts(vscale: float) -> tuple[float, float]:
    """Elapsed caption band — same as lap cumulative caption."""
    return lap_sheet_caption_pts(vscale)


def lap_sheet_elapsed_time_pts(vscale: float) -> tuple[float, float]:
    """Elapsed time numerals — same hi/lo band as lap kills line."""
    return lap_sheet_kills_pts(vscale)


def elapsed_eff_pt_clip(pt: float) -> float:
    return max(float(KC_VIEWPORT_MIN_PT), float(pt))


def elapsed_eff_pt_css(pt: float) -> str:
    v = elapsed_eff_pt_clip(pt)
    return f"{v:.4g}pt"


def gauge_overlay_pct_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 9.5)
    lo = max(6.0, kc_viewport_design_pt_eff_v(vscale, 6.5))
    return hi, lo


def status_banner_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 9.5)
    lo = max(6.5, kc_viewport_design_pt_eff_v(vscale, 6.5))
    return hi, lo


def goal_plain_subval_pts(vscale: float) -> tuple[float, float]:
    hi = kc_viewport_design_pt_eff_v(vscale, 9.5)
    lo = max(6.5, kc_viewport_design_pt_eff_v(vscale, 6.5))
    return hi, lo


def kc_fit_qpushbutton_text_width_qss(
    button: Any,
    text: str,
    *,
    vscale: float,
    horizontal_padding_px: int,
    base_design_pt: float = 9.5,
    min_design_pt: float = 6.5,
    min_measure_width_px: int | None = None,
) -> tuple[str, str]:
    """Width-fit QSS pair using KC viewport-effective pt bounds."""
    be = kc_viewport_design_pt_eff_v(vscale, float(base_design_pt))
    me = max(6.25, float(kc_viewport_design_pt_eff_v(vscale, float(min_design_pt))))
    return fit_qpushbutton_text_width_qss(
        button,
        text,
        horizontal_padding_px=int(horizontal_padding_px),
        base_design_pt=float(base_design_pt),
        min_design_pt=float(min_design_pt),
        min_measure_width_px=min_measure_width_px,
        base_pt_eff=be,
        min_pt_eff=me,
    )
