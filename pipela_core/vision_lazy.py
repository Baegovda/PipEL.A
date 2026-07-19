"""AGENT: lazy import cv2/numpy/mss after first GUI frame. Patches mss BitBl on Windows — see `_patch_mss_windows_disable_captureblt`."""

from __future__ import annotations

import ctypes
import sys
from typing import Any, Tuple

_cv2: Any = None
_np: Any = None
_mss: Any = None
_mss_capt_blt_patched: bool = False


def _patch_mss_windows_disable_captureblt(mss_mod: Any) -> None:
    """AGENT: monkeypatch `mss.windows.MSS._grab_impl` → `BitBlt(..., SRCCOPY)` only.

    Upstream uses `SRCCOPY|CAPTUREBLT`. CAPTUREBLT forces layered children into the
    bitmap and (observed) DWM tears/restores the hardware cursor every grab. Multiple
    macro loops (Ride/HP/Ammo/CallMerc) → ~20–50 grabs/s → visible cursor flicker.

    Game template ROIs are inside the client; we do not need layered Pipela overlays
    in the capture. Removing CAPTUREBLT matches product ROI semantics and stops flicker.

    Ref: https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-bitblt
    """
    global _mss_capt_blt_patched
    if _mss_capt_blt_patched or sys.platform != "win32":
        return
    try:
        from mss import windows as _mss_win  # type: ignore
    except Exception:
        return
    SRCCOPY = 0x00CC0020

    def _patched_grab_impl(self, monitor):
        srcdc, memdc = self._handles.srcdc, self._handles.memdc
        gdi = self.gdi32
        width, height = monitor["width"], monitor["height"]
        if self._handles.region_width_height != (width, height):
            self._handles.region_width_height = (width, height)
            self._handles.bmi.bmiHeader.biWidth = width
            self._handles.bmi.bmiHeader.biHeight = -height
            self._handles.data = ctypes.create_string_buffer(width * height * 4)
            if self._handles.bmp:
                gdi.DeleteObject(self._handles.bmp)
            self._handles.bmp = gdi.CreateCompatibleBitmap(srcdc, width, height)
            gdi.SelectObject(memdc, self._handles.bmp)
        gdi.BitBlt(
            memdc, 0, 0, width, height, srcdc,
            monitor["left"], monitor["top"], SRCCOPY,
        )
        bits = gdi.GetDIBits(
            memdc,
            self._handles.bmp,
            0,
            height,
            self._handles.data,
            self._handles.bmi,
            0,
        )
        if bits != height:
            from mss.exception import ScreenShotError  # type: ignore
            raise ScreenShotError("gdi32.GetDIBits() failed.")
        return self.cls_image(bytearray(self._handles.data), monitor)

    try:
        _mss_win.MSS._grab_impl = _patched_grab_impl
        _mss_capt_blt_patched = True
    except Exception:
        pass


def ensure_cv2_numpy_mss() -> Tuple[Any, Any, Any]:
    """AGENT: first call imports cv2, numpy, mss; returns cached triple."""
    global _cv2, _np, _mss
    if _cv2 is not None:
        return _cv2, _np, _mss
    import cv2 as _cv2_mod
    import numpy as _np_mod
    import mss as _mss_mod
    _patch_mss_windows_disable_captureblt(_mss_mod)
    _cv2, _np, _mss = _cv2_mod, _np_mod, _mss_mod
    return _cv2, _np, _mss
