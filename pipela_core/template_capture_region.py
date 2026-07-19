"""드래그 캡처 — 정규화 ROI·BGR 캡처 → PIL RGB (UI와 분리)."""

from __future__ import annotations

from typing import Any, List

from PIL import Image

from pipela_core.scale_geometry import get_region_pixels
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


def crop_drag_rect_from_full_bgr_to_pil_rgb(
    full_bgr: Any,
    hwnd: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    win_w: float,
    win_h: float,
) -> Image.Image | None:
    """캡처 시작 시 찍은 풀클라 BGR에서 드래그 영역만 잘라 PIL RGB (라이브 화면과 어긋남 방지)."""
    region_xywh_norm = normalized_roi_xywh_from_drag_rect(x, y, w, h, win_w, win_h)
    rp = get_region_pixels(hwnd, region_xywh_norm)
    if rp is None or full_bgr is None:
        return None
    rx, ry, rw, rh = int(rp[0]), int(rp[1]), int(rp[2]), int(rp[3])
    fb = full_bgr
    try:
        h_max, w_max = int(fb.shape[0]), int(fb.shape[1])
    except Exception:
        return None
    if rw <= 0 or rh <= 0:
        return None
    rx = max(0, rx)
    ry = max(0, ry)
    rx2 = min(w_max, rx + rw)
    ry2 = min(h_max, ry + rh)
    if rx2 <= rx or ry2 <= ry:
        return None
    slice_bgr = fb[ry:ry2, rx:rx2]
    if slice_bgr is None or getattr(slice_bgr, "size", 0) == 0:
        return None
    cv2, _, _ = ensure_cv2_numpy_mss()
    try:
        return Image.fromarray(cv2.cvtColor(slice_bgr, cv2.COLOR_BGR2RGB))
    except Exception:
        return None


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
