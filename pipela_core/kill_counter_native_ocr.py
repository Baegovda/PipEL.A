"""AGENT: Kill counter OCR bridge for C++ kill_counter_worker."""

from __future__ import annotations

from typing import Any, Mapping


def process_bgr_for_native(module_globals: Mapping[str, Any], bgr_bytes: bytes, w: int, h: int) -> dict[str, Any]:
    """Run Python OCR + session path; mirrors kill_counter_loop when C++ captures ROI."""
    import numpy as np

    tick_fn = module_globals.get("kill_counter_native_ocr_tick")
    skip_fn = module_globals.get("_kill_counter_should_skip_ocr_same_screen")
    if not tick_fn:
        return {"poll_phase": "error", "poll_detail": "OCR unavailable", "ok": False}

    img = np.frombuffer(bgr_bytes, dtype=np.uint8).reshape((int(h), int(w), 3))
    if skip_fn and skip_fn(img):
        return {"skip": True, "ok": True}

    result = tick_fn(img)
    if not isinstance(result, dict):
        return {"ok": False, "poll_phase": "error", "poll_detail": "bad tick result"}
    return result
