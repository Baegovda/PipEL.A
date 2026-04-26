"""mss 주 모니터(monitors[1]) 크기 기준 ROI·스케일 유틸."""

from __future__ import annotations


def primary_monitor_dict(sct) -> dict | None:
    """sct.monitors[1] → {left, top, width, height, …}. 실패 시 None."""
    try:
        return dict(sct.monitors[1])
    except Exception:
        return None


def normalized_roi_to_pixels(region, mw: int, mh: int):
    """정규화 ROI [x,y,w,h]를 주어진 모니터 너비·높이 기준 픽셀 튜플로."""
    if not region:
        return None
    x_ratio, y_ratio, w_ratio, h_ratio = region
    return (
        int(x_ratio * mw),
        int(y_ratio * mh),
        int(w_ratio * mw),
        int(h_ratio * mh),
    )


def scale_ratio_from_monitor_height(monitor_height: int, base_height: float) -> float:
    """BASE_HEIGHT 대비 주 모니터 논리 높이 비율."""
    return float(monitor_height) / float(base_height)
