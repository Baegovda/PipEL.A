"""1440p 기준 스케일·정규화 ROI → 클라이언트 픽셀 — 템플릿·캡처 공통."""

from __future__ import annotations

import os
import sys
import time

from pipela_core.win32_game_windows import get_window_rect, get_window_size

# 기준 해상도 (1440p 고정 - 높이 기준)
BASE_HEIGHT = 1440

# 클라 실제 캡처(BitBlt) 크기 조회 결과 — 핫패스(loop)에서 과도한 GDI 호출 방지.
_CLIENT_CAPTURE_DIMS_CACHE_TTL_SEC = float(
    os.environ.get("PIPELA_CLIENT_CAPTURE_DIMS_CACHE_SEC", "0.22") or "0.22",
)
_CLIENT_CAPTURE_DIMS_CACHE: dict[tuple, tuple[float, tuple[int, int]]] = {}

# --- client capture dims (HWND, DPI, logical W×H)로 BitBlt 실측 결과를 재사용
def get_client_capture_dimensions(hwnd) -> tuple[int, int] | None:
    """
    템플릿 스케일·ROI와 같은 좌표계인 «실제 클라 픽셀» 가로·세로.

    Windows 표시 배율(125%/150% 등)이나 DPI 인식 차이로 `GetClientRect`만과
    GDI(BitBlt)·mss 캡처 버퍼 크기가 어긋나는 경우를 줄이려고,
    우선 가능하면 BitBlt 클라이언트 버퍼의 shape을 쓴다.
    """
    if not hwnd:
        return None
    hi = int(hwnd)
    size = get_window_size(hwnd)
    if not size:
        return None
    w_log, h_log = int(size[0]), int(size[1])
    dpi_sig = 96
    if sys.platform == "win32":
        try:
            from pipela_core.win32_window_ops import get_dpi_for_monitor_containing_window

            dpi_sig = int(get_dpi_for_monitor_containing_window(hi))
        except Exception:
            dpi_sig = 96

    sig = (hi, dpi_sig, w_log, h_log)
    now = time.monotonic()
    ent = _CLIENT_CAPTURE_DIMS_CACHE.get(sig)
    if (
        ent is not None
        and _CLIENT_CAPTURE_DIMS_CACHE_TTL_SEC > 0.0
        and (now - ent[0]) < _CLIENT_CAPTURE_DIMS_CACHE_TTL_SEC
    ):
        return ent[1]

    w_px, h_px = w_log, h_log
    if sys.platform == "win32":
        try:
            from pipela_core.win32_client_capture import _win32_capture_client_bgr_bitblt

            bit = _win32_capture_client_bgr_bitblt(hi)
            if bit is not None and getattr(bit, "size", 0) > 1:
                hh = int(bit.shape[0])
                ww = int(bit.shape[1])
                if hh >= 8 and ww >= 8:
                    w_px, h_px = ww, hh
        except Exception:
            pass

    tup = (w_px, h_px)
    _CLIENT_CAPTURE_DIMS_CACHE[sig] = (now, tup)
    if len(_CLIENT_CAPTURE_DIMS_CACHE) > 384:
        _CLIENT_CAPTURE_DIMS_CACHE.clear()

    return tup


def get_scale_ratio(hwnd) -> float:
    """BASE_HEIGHT 대비 현재 창 클라이언트 높이 비율."""
    dims = get_client_capture_dimensions(hwnd)
    if dims:
        return float(max(int(dims[1]), 1)) / float(BASE_HEIGHT)
    size = get_window_size(hwnd)
    if not size:
        return 1.0
    return float(max(int(size[1]), 1)) / float(BASE_HEIGHT)


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
