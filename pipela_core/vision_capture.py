"""AGENT: BGR capture for game client — BitBlt-first, mss fallback. Reusable from core.

`client_dc_only=True` (default): full client is read with **Win32 BitBlt from the HWND
client DC** when possible so **monitor-composite grabs (mss) do not include Pipela overlays**
or other windows stacked on screen — same idea as preferring true client pixels for OCR.
If BitBlt is all-black / wrong size (common with some D3D exclusive windows), falls back to mss.

Shared full-client BGR cache keyed by hwnd+client_rect reduces concurrent grabs across ROIs
(thread-safe TTL `_CLIENT_BGR_CACHE_TTL_SEC`).
"""

from __future__ import annotations

import threading
import time

from pipela_core.primary_monitor import normalized_roi_to_pixels, primary_monitor_dict
from pipela_core.telemetry_metrics import telemetry_record_capture_grab_sec
from pipela_core.scale_geometry import get_region_pixels
from pipela_core.vision_lazy import ensure_cv2_numpy_mss
from pipela_core.win32_game_windows import get_window_outer_rect_screen, get_window_rect
from pipela_core.win32_window_ops import is_window_minimized

# AGENT: TTL for full-client BGR cache (hwnd+rect) — lowers mss.grab rate across ROI calls.
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


def _grab_full_client_bgr_prefer_bitblt(
    hwnd_i: int,
    cv2,
    np,
    sct,
    wx: int,
    wy: int,
    w: int,
    h: int,
):
    """BitBlt 클라이언트 DC → 합성 없음. 실패·전부 검음·크기 불일치 시 mss."""
    t0 = time.perf_counter()
    bit = None
    try:
        from pipela_core.win32_client_capture import _win32_capture_client_bgr_bitblt

        bit = _win32_capture_client_bgr_bitblt(hwnd_i)
    except Exception:
        bit = None
    if (
        bit is not None
        and getattr(bit, "size", 0) > 0
        and int(bit.shape[0]) == h
        and int(bit.shape[1]) == w
        and int(np.max(bit)) > 0
    ):
        telemetry_record_capture_grab_sec(time.perf_counter() - t0)
        return bit
    try:
        return _grab_full_client_bgr(cv2, np, sct, wx, wy, w, h)
    except Exception:
        return None


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
    """AGENT: readonly ref to cached full-client BGR; on miss grab+store in `_CLIENT_BGR_CACHE`."""
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
            full_new = _grab_full_client_bgr_prefer_bitblt(
                hwnd_i, cv2, np, sct, wx, wy, w, h
            )
        except Exception:
            return None
        if full_new is None:
            return None
        _CLIENT_BGR_CACHE[hwnd_i] = (now, sig, full_new)
        return full_new


def capture_window(hwnd, sct):
    """AGENT: full client BGR copy; None if minimized / fail."""
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
    """AGENT: BGR for normalized ROI; `region=None` → full client (or outer in outer mode).

    `client_dc_only=True`: full client from **BitBlt(client DC) when valid**, else mss — avoids
    Pipela/다른 창이 게임 위에 겹쳐도 매칭·OCR에 섞이는 합성 픽셀(공유 캐시).
    `client_dc_only=False`: outer 창 mss 한 번; ROI는 클라 기준 `get_region_pixels` 슬라이스 —
    디버그 폴백.
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
    """AGENT: normalized ROI → pixel rect on primary monitor; opens temp `mss()`."""
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
    """AGENT: BGR for primary monitor (full or ROI); `sct` = open mss instance."""
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
