"""AGENT: Kill counter OCR bridge for C++ kill_counter_worker."""

from __future__ import annotations

from typing import Any, Mapping


def process_bgr_for_native(module_globals: Mapping[str, Any], bgr_bytes: bytes, w: int, h: int) -> dict[str, Any]:
    """Run Python OCR path and return state fields for C++ AppState."""
    import numpy as np

    read_digits = module_globals.get("kill_counter_read_digits")
    slash_pair = module_globals.get("_kill_counter_slash_pair_parts")
    if not read_digits:
        return {"poll_phase": "error", "poll_detail": "OCR unavailable", "ok": False}

    img = np.frombuffer(bgr_bytes, dtype=np.uint8).reshape((int(h), int(w), 3))
    _val, err, _label_rect, _num_rect, prog_txt = read_digits(img)
    raw_prog = (prog_txt or "").strip()
    out: dict[str, Any] = {"prog_txt": raw_prog, "ok": True}

    if raw_prog and slash_pair:
        n1s, n2s = slash_pair(raw_prog)
        if n1s and n2s:
            out["last_progress"] = raw_prog
            out["poll_phase"] = "ok"
            out["poll_detail"] = ""
            return out
        out["last_progress"] = raw_prog
        out["poll_phase"] = "no_pair"
        out["poll_detail"] = "a/b 숫자 쌍 아님"
        return out

    if err:
        out["poll_phase"] = "error"
        out["poll_detail"] = str(err)
    else:
        out["poll_phase"] = "empty"
        out["poll_detail"] = ""
    out["last_progress"] = ""
    return out
