"""OpenCV BGR / PIL → QPixmap 스케일 미리보기."""

from __future__ import annotations

import os
from io import BytesIO
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap


def pixmap_from_bgr(bgr, max_w: int, max_h: int) -> QPixmap | None:
    if bgr is None or not hasattr(bgr, "size") or bgr.size == 0:
        return None
    import cv2

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
    qimg = qimg.copy()
    pm = QPixmap.fromImage(qimg)
    return pm.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def pixmap_from_path(path: str, max_w: int, max_h: int) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None
    qimg = QImage(path)
    if qimg.isNull():
        return None
    pm = QPixmap.fromImage(qimg)
    return pm.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def pixmap_from_pil(pil_img, max_w: int, max_h: int) -> QPixmap | None:
    if pil_img is None:
        return None
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage.fromData(buf.getvalue())
    if qimg.isNull():
        return None
    pm = QPixmap.fromImage(qimg)
    return pm.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
