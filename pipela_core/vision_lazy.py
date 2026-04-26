"""cv2 / numpy / mss 지연 로드 — GUI 첫 프레임 부담 완화."""

from __future__ import annotations

from typing import Any, Tuple

_cv2: Any = None
_np: Any = None
_mss: Any = None


def ensure_cv2_numpy_mss() -> Tuple[Any, Any, Any]:
    """첫 호출 시 로드 후 (cv2, numpy, mss) 반환. 이후 동일 참조."""
    global _cv2, _np, _mss
    if _cv2 is not None:
        return _cv2, _np, _mss
    import cv2 as _cv2_mod
    import numpy as _np_mod
    import mss as _mss_mod
    _cv2, _np, _mss = _cv2_mod, _np_mod, _mss_mod
    return _cv2, _np, _mss
