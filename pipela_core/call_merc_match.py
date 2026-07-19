"""Call Merc — 한 kind에 대해 ROI 캡처·matchTemplate·점수 전역 반영."""

from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping, Optional

from pipela_core.call_merc_catalog import (
    CALL_MERC_ROI_KEY,
    CALL_MERC_SCORE_KEY,
    CALL_MERC_THR_KEY,
)
from pipela_core.template_matching import extract_match_patch, match_template_ccoeff_normed_max
from pipela_core.vision_capture import capture_region


def call_merc_match_one_kind(
    g: MutableMapping[str, Any],
    kind: str,
    target_hwnd: Any,
    sct: Any,
    scaled: Mapping[str, Any],
    *,
    on_patch_hit: Optional[Callable[[str, Any, float], None]] = None,
    match_threshold: float | None = None,
    roi_override: Any | None = None,
) -> Any:
    """매칭 상단 좌표 tl 또는 None. 실패 시 해당 kind 점수 0."""
    roi = roi_override if roi_override is not None else g[CALL_MERC_ROI_KEY[kind]]
    screen = capture_region(target_hwnd, sct, roi, client_dc_only=True)
    if screen is None:
        g[CALL_MERC_SCORE_KEY[kind]] = 0.0
        return None
    sc, tl = match_template_ccoeff_normed_max(screen, scaled[kind])
    g[CALL_MERC_SCORE_KEY[kind]] = sc
    thr = (
        float(match_threshold)
        if match_threshold is not None
        else float(g[CALL_MERC_THR_KEY[kind]])
    )
    if tl is not None and sc >= thr:
        pm = extract_match_patch(screen, scaled[kind], tl)
        if pm is not None and on_patch_hit is not None:
            on_patch_hit(kind, pm, float(sc))
    return tl
