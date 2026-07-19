"""제어 창·킬 카운터 floater 도킹 폭 — **동일 폭** 클램프 및 저장값 통합 (순수 타입, Qt 비의존)."""

from __future__ import annotations

from typing import Any

DOCK_PAIR_PANEL_W_MIN = 260
DOCK_PAIR_PANEL_W_MAX = 900


def clamp_dock_pair_panel_w(w: int) -> int:
    return max(DOCK_PAIR_PANEL_W_MIN, min(DOCK_PAIR_PANEL_W_MAX, int(w)))


def resolve_unified_saved_dock_panel_w(m: Any, preset_w: int) -> int:
    """저장폭 우선순위: ``control_panel_w`` > ``kill_counter_panel_w`` > ``preset_w`` (clamp)."""
    try:
        cp = int(getattr(m, "control_panel_w", 0) or 0)
    except (TypeError, ValueError):
        cp = 0
    if cp > 0:
        return clamp_dock_pair_panel_w(cp)
    try:
        kcw = int(getattr(m, "kill_counter_panel_w", 0) or 0)
    except (TypeError, ValueError):
        kcw = 0
    if kcw > 0:
        return clamp_dock_pair_panel_w(kcw)
    return max(8, int(preset_w))
