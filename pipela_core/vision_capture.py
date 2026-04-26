"""mss 기반 창/영역 BGR 캡처 — main 과 동일 동작, 코어에서 재사용 가능."""

from __future__ import annotations

import threading
import time

from pipela_core.primary_monitor import normalized_roi_to_pixels, primary_monitor_dict
from pipela_core.telemetry_metrics import telemetry_record_capture_grab_sec
from pipela_core.scale_geometry import get_region_pixels
from pipela_core.vision_lazy import ensure_cv2_numpy_mss
from pipela_core.win32_game_windows import get_window_outer_rect_screen, get_window_rect
from pipela_core.win32_window_ops import is_window_minimized

# 동일 HWND·클라이언트 크기에서 여러 ROI가 연달아 필요할 때 mss.grab 횟수 완화(스레드 안전).
_CLIENT_BGR_CACHE_TTL_SEC = 0.02
_CLIENT_BGR_CACHE_LOCK = threading.Lock()
# hwnd_int -> (monotonic_ts, client_rect_tuple, bgr_full)
_CLIENT_BGR_CACHE: dict[int, tuple[float, tuple[int, int, int, int], object]] = {}


def _grab_full_client_bgr(cv2, np, sct, wx: int, wy: int, w: int, h: int):
    t0 = time.perf_counter()
    try:
        monitor = {"left": wx, "top": wy, "width": w, "height": h}
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    finally:
        telemetry_record_capture_grab_sec(time.perf_counter() - t0)


def _slice_from_full(np, full_bgr, rx: int, ry: int, rw: int, rh: int):
    H, W = int(full_bgr.shape[0]), int(full_bgr.shape[1])
    rx = max(0, min(int(rx), max(0, W - 1)))
    ry = max(0, min(int(ry), max(0, H - 1)))
    rw = max(10, min(int(rw), max(10, W - rx)))
    rh = max(10, min(int(rh), max(10, H - ry)))
    return np.ascontiguousarray(full_bgr[ry : ry + rh, rx : rx + rw])


def _get_cached_full_bgr_ref(
    hwnd_i: int,
    cv2,
    np,
    sct,
    rect: tuple[int, int, int, int],
):
    """캐시된 전체 클라이언트 BGR 배열 참조(읽기 전용). 미스면 grab 후 캐시에 넣고 그 참조."""
    wx, wy, wx2, wy2 = rect
    w, h = int(wx2 - wx), int(wy2 - wy)
    if w < 10 or h < 10:
        return None
    now = time.monotonic()
    sig = (int(wx), int(wy), int(wx2), int(wy2))
    with _CLIENT_BGR_CACHE_LOCK:
        ent = _CLIENT_BGR_CACHE.get(hwnd_i)
        if ent is not None:
            ts, sig0, full = ent
            if (
                (now - ts) < _CLIENT_BGR_CACHE_TTL_SEC
                and sig0 == sig
                and full is not None
                and getattr(full, "shape", None) is not None
                and int(full.shape[0]) == h
                and int(full.shape[1]) == w
            ):
                return full
        try:
            full_new = _grab_full_client_bgr(cv2, np, sct, wx, wy, w, h)
        except Exception:
            return None
        if full_new is None:
            return None
        _CLIENT_BGR_CACHE[hwnd_i] = (now, sig, full_new)
        return full_new


def capture_window(hwnd, sct):
    """전체 클라이언트 영역 BGR. 실패·최소화 시 None."""
    cv2, np, _mss = ensure_cv2_numpy_mss()
    hi = int(hwnd)
    if is_window_minimized(hwnd):
        with _CLIENT_BGR_CACHE_LOCK:
            _CLIENT_BGR_CACHE.pop(hi, None)
        return None
    rect = get_window_rect(hwnd)
    if not rect:
        return None
    try:
        full = _get_cached_full_bgr_ref(hi, cv2, np, sct, rect)
        return None if full is None else full.copy()
    except Exception:
        return None


def capture_region(hwnd, sct, region=None, client_dc_only: bool = True):
    """지정 정규화 ROI만 BGR 캡처. region=None 이면 전체 클라(또는 outer).

    client_dc_only=True(기본): 클라이언트 DC와 동일한 mss 잘라(캐시·스케일 geometry와 맞음).
    client_dc_only=False: 바깥창(타이틀·테두리 포함) 전체를 한 번 grab한 뒤, ROI는 여전히
    클라이언트 기준 정규화 → 클라이언트 픽셀을 outer 이미지 좌표로 옮겨 slice(폴백·디버그용).
    """
    cv2, np, _mss = ensure_cv2_numpy_mss()
    hi = int(hwnd)
    if is_window_minimized(hwnd):
        with _CLIENT_BGR_CACHE_LOCK:
            _CLIENT_BGR_CACHE.pop(hi, None)
        return None
    if client_dc_only:
        rect = get_window_rect(hwnd)
        if not rect:
            return None
        region_px = get_region_pixels(hwnd, region) if region else None
        try:
            full = _get_cached_full_bgr_ref(hi, cv2, np, sct, rect)
            if full is None:
                return None
            if not region_px:
                return full.copy()
            rx, ry, rw, rh = region_px
            return _slice_from_full(np, full, rx, ry, rw, rh)
        except Exception:
            return None
    # Outer-window grab (mss) — no client cache; ROI is still client-normalized from get_region_pixels
    out = get_window_outer_rect_screen(hwnd)
    cl_rect = get_window_rect(hwnd)
    if not out or not cl_rect:
        return None
    ol, ot, o_r, o_b = (int(x) for x in out)
    cl, ct, c_r, c_b = (int(x) for x in cl_rect)
    ow, oh = o_r - ol, o_b - ot
    if ow < 10 or oh < 10:
        return None
    try:
        t0 = time.perf_counter()
        try:
            monitor = {"left": ol, "top": ot, "width": int(ow), "height": int(oh)}
            screenshot = sct.grab(monitor)
            full = np.array(screenshot)
            full = cv2.cvtColor(full, cv2.COLOR_BGRA2BGR)
        finally:
            telemetry_record_capture_grab_sec(time.perf_counter() - t0)
        if not region:
            return full
        region_px = get_region_pixels(hwnd, region) if region else None
        if not region_px:
            return None
        rx, ry, rw, rh = region_px
        ox = (cl - ol) + int(rx)
        oy = (ct - ot) + int(ry)
        return _slice_from_full(np, full, int(ox), int(oy), int(rw), int(rh))
    except Exception:
        return None


def get_region_pixels_primary_monitor(region):
    """주 모니터 기준 정규화 ROI → 픽셀. 내부에서 임시 mss 인스턴스 사용(기존과 동일)."""
    if not region:
        return None
    _, _, mss_mod = ensure_cv2_numpy_mss()
    sct = mss_mod.mss()
    try:
        m = primary_monitor_dict(sct)
        if not m:
            return None
        return normalized_roi_to_pixels(region, int(m["width"]), int(m["height"]))
    finally:
        try:
            sct.close()
        except Exception:
            pass


def capture_region_primary_monitor(sct, region_normalized):
    """주 모니터(또는 그 안 정규화 ROI) BGR. sct는 열린 mss()."""
    cv2, np, _mss = ensure_cv2_numpy_mss()
    m = primary_monitor_dict(sct)
    if not m:
        return None
    ml, mt = int(m["left"]), int(m["top"])
    mw, mh = int(m["width"]), int(m["height"])
    if region_normalized:
        rp = get_region_pixels_primary_monitor(region_normalized)
        if not rp:
            return None
        rx, ry, rw, rh = rp
        x, y = ml + rx, mt + ry
        w, h = rw, rh
    else:
        x, y, w, h = ml, mt, mw, mh
    w, h = max(10, w), max(10, h)
    try:
        monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    except Exception:
        return None
