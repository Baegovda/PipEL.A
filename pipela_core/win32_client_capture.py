"""Win32: HWND **클라이언트**만 BGR (mss 는 화면 겹침·다른 창 합성 포함)."""

from __future__ import annotations

import sys
from typing import Any

# pywin32


def _win32_capture_client_bgr_bitblt(hwnd: int) -> Any:
    """
    GDI BitBlt: 클라이언트 DC → DIB. **모니터 합성**이 아니라 해당 창 뒤면(가능한 범위).
    Direct3D 전용 창은 검은 이미지가 될 수 있음 → `vision_capture`에서 mss 폴백.
    """
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        import numpy as np
        import win32con
        import win32gui
        import win32ui
    except Exception:
        return None

    who = int(hwnd)
    if not win32gui.IsWindow(who):
        return None
    r = win32gui.GetClientRect(who)
    w, hgt = r[2] - r[0], r[3] - r[1]
    if w < 2 or hgt < 2:
        return None
    hwnd_dc = None
    src_dc = None
    mem_dc = None
    bitmap = None
    bits = b""
    try:
        hwnd_dc = win32gui.GetDC(who)
        if not hwnd_dc:
            return None
        src_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        mem_dc = src_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(src_dc, w, hgt)
        mem_dc.SelectObject(bitmap)
        ok = mem_dc.BitBlt(
            (0, 0),
            (w, hgt),
            src_dc,
            (0, 0),
            win32con.SRCCOPY,
        )
        if not ok:
            return None
        bits = bitmap.GetBitmapBits(True)
    except Exception:
        return None
    finally:
        try:
            if bitmap is not None:
                try:
                    win32gui.DeleteObject(bitmap.GetHandle())
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if mem_dc is not None:
                mem_dc.DeleteDC()
        except Exception:
            pass
        try:
            if src_dc is not None:
                src_dc.DeleteDC()
        except Exception:
            pass
        try:
            if hwnd_dc and who:
                win32gui.ReleaseDC(who, hwnd_dc)
        except Exception:
            pass

    if not bits or len(bits) < w * hgt * 4:
        return None
    arr = np.frombuffer(bits, dtype=np.uint8)
    need = w * hgt * 4
    if int(arr.size) < need:
        return None
    bgra = arr[:need].reshape((hgt, w, 4))
    bgr = np.ascontiguousarray(bgra[:, :, :3][::-1, :, :])  # BGR, bottom-up DIB → top-down
    return bgr
