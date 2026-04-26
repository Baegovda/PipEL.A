"""드래그 캡처 — 정규화 ROI·BGR 캡처 → PIL RGB (UI와 분리)."""

from __future__ import annotations

from typing import Any, List

from PIL import Image

from pipela_core.vision_capture import capture_region
from pipela_core.vision_lazy import ensure_cv2_numpy_mss


def normalized_roi_xywh_from_drag_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    win_w: float,
    win_h: float,
) -> List[float]:
    """클라이언트 픽셀 직사각형 → 정규화 [x,y,w,h]."""
    return [x / win_w, y / win_h, w / win_w, h / win_h]


def drag_rect_exceeds_min_size(
    w: float,
    h: float,
    *,
    min_edge_px: float = 10.0,
) -> bool:
    """드래그 박스가 사용 가능한 최소 크기인지(양변 > min_edge_px, 오버레이와 동일 기준)."""
    return w > min_edge_px and h > min_edge_px


def capture_drag_rect_to_pil_rgb(
    hwnd: Any,
    sct: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    win_w: float,
    win_h: float,
    *,
    client_dc_only: bool = True,
) -> Image.Image | None:
    """클라이언트 픽셀 드래그 직사각형 → 정규화 ROI 캡처 → PIL RGB."""
    region_xywh_norm = normalized_roi_xywh_from_drag_rect(x, y, w, h, win_w, win_h)
    return capture_normalized_roi_to_pil_rgb(
        hwnd, sct, region_xywh_norm, client_dc_only=client_dc_only,
    )


def capture_normalized_roi_to_pil_rgb(
    hwnd: Any,
    sct: Any,
    region_xywh_norm: List[float],
    *,
    client_dc_only: bool = True,
) -> Image.Image | None:
    """정규화 ROI만 캡처해 PIL RGB. 실패 시 None."""
    bgr = capture_region(hwnd, sct, region_xywh_norm, client_dc_only=client_dc_only)
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    cv2, _, _ = ensure_cv2_numpy_mss()
    try:
        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    except Exception:
        return None
