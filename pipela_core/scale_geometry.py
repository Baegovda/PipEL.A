"""1440p 기준 스케일·정규화 ROI → 클라이언트 픽셀 — 템플릿·캡처 공통."""

from __future__ import annotations

from pipela_core.win32_game_windows import get_window_rect, get_window_size

# 기준 해상도 (1440p 고정 - 높이 기준)
BASE_HEIGHT = 1440


def get_scale_ratio(hwnd) -> float:
    """BASE_HEIGHT 대비 현재 창 클라이언트 높이 비율."""
    size = get_window_size(hwnd)
    if not size:
        return 1.0
    return size[1] / float(BASE_HEIGHT)


def get_region_pixels(hwnd, region):
    """비율 region [x,y,w,h]를 클라이언트 픽셀 (rx, ry, rw, rh)로. region/실패 시 None."""
    if not region:
        return None
    rect = get_window_rect(hwnd)
    if not rect:
        return None
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]
    x_ratio, y_ratio, w_ratio, h_ratio = region
    return (
        int(x_ratio * win_w),
        int(y_ratio * win_h),
        int(w_ratio * win_w),
        int(h_ratio * win_h),
    )
