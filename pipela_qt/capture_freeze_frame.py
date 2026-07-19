"""캡처·영역 선택 시 게임 클라 1프레임 스냅샷 — 드래그 중 화면이 멈춘 것처럼 보이게."""

from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtGui import QImage, QPixmap

from pipela_core.vision_capture import capture_window
from pipela_core.vision_lazy import ensure_cv2_numpy_mss


def snapshot_client_bgr(hwnd: int | Any) -> np.ndarray | None:
    """클라이언트 전체 BGR(물리 픽셀). 최소화·실패 시 None."""
    if not hwnd:
        return None
    _, _, mss_mod = ensure_cv2_numpy_mss()
    sct = mss_mod.mss()
    try:
        return capture_window(int(hwnd), sct)
    except Exception:
        return None
    finally:
        try:
            sct.close()
        except Exception:
            pass


def bgr_to_qpixmap(bgr: np.ndarray | None) -> QPixmap | None:
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    if bgr.ndim != 3 or int(bgr.shape[2]) != 3:
        return None
    cv2, np, _ = ensure_cv2_numpy_mss()
    h, w = int(bgr.shape[0]), int(bgr.shape[1])
    try:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        qimg = QImage(
            rgb.data,
            w,
            h,
            3 * w,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(qimg.copy())
    except Exception:
        return None


def build_capture_freeze_assets(hwnd: int | Any) -> tuple[np.ndarray | None, QPixmap | None]:
    bgr = snapshot_client_bgr(hwnd)
    return bgr, bgr_to_qpixmap(bgr)
