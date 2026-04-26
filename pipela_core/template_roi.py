"""템플릿 capture kind·region_type → ROI 전역 조회·설정, ROI 내 매칭 중심 좌표."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from pipela_core.region_dispatch import CAPTURE_KIND_TO_REGION_TYPE, REGION_TYPE_TO_GLOBAL_NAME
from pipela_core.scale_geometry import get_region_pixels
from pipela_core.win32_game_windows import get_window_rect


def region_roi_from_globals(region_type: str, g: Mapping[str, Any]) -> Any:
    name = REGION_TYPE_TO_GLOBAL_NAME.get(region_type)
    if name is None:
        return g.get("kill_counter_detect_region")
    return g.get(name)


def region_roi_set_in_globals(
    region_type: str,
    g: MutableMapping[str, Any],
    value,
) -> None:
    name = REGION_TYPE_TO_GLOBAL_NAME.get(region_type)
    if name is None:
        g["kill_counter_detect_region"] = value
    else:
        g[name] = value


def template_roi_for_kind(kind: str, g: Mapping[str, Any]) -> Any:
    """템플릿 capture kind → 매칭 ROI(None이면 전체 클라이언트)."""
    rt = CAPTURE_KIND_TO_REGION_TYPE.get(kind)
    if rt is None:
        return None
    return region_roi_from_globals(rt, g)


def match_center_in_client(hwnd, roi, tl_xy, tw: int, th: int) -> tuple[int, int]:
    """ROI 캡처에서의 matchTemplate 좌상단 tl → 클라이언트 좌표계 중심."""
    ox, oy = 0, 0
    rp = get_region_pixels(hwnd, roi) if roi else None
    if rp:
        ox, oy = int(rp[0]), int(rp[1])
    mx, my = int(tl_xy[0]), int(tl_xy[1])
    return ox + mx + tw // 2, oy + my + th // 2


def match_center_to_screen_xy(
    hwnd,
    roi,
    tl_xy,
    tw: int,
    th: int,
) -> tuple[int, int] | None:
    """클라이언트 기준 매칭 중심 → 화면 절대 픽셀. 창 좌표 실패 시 None."""
    rect = get_window_rect(hwnd)
    if not rect:
        return None
    wx, wy = int(rect[0]), int(rect[1])
    cx, cy = match_center_in_client(hwnd, roi, tl_xy, tw, th)
    return wx + cx, wy + cy
