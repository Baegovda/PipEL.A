"""OpenCV TM_CCOEFF_NORMED 템플릿 매칭 — 루프·디버그 공통."""

from __future__ import annotations

import time
from typing import Any, Mapping, MutableMapping, Sequence, Tuple

from pipela_core.telemetry_metrics import telemetry_record_match_sec
from pipela_core.vision_lazy import ensure_cv2_numpy_mss


def scale_template(template: Any, ratio: float) -> Any:
    """템플릿을 해상도 비율에 맞게 스케일."""
    cv2, _, _ = ensure_cv2_numpy_mss()
    if template is None:
        return None
    if abs(ratio - 1.0) < 0.01:
        return template
    new_w = max(int(template.shape[1] * ratio), 1)
    new_h = max(int(template.shape[0] * ratio), 1)
    return cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)


def match_template_ccoeff_normed_max(
    screen: Any,
    template: Any,
) -> Tuple[float, Any]:
    """TM_CCOEFF_NORMED 1회 → (max_val, max_loc_tl). 불가 시 (0.0, None)."""
    from pipela_core.native_bridge import match_template_ccoeff_normed_max as _native_match

    native_hit = _native_match(screen, template)
    if native_hit is not None:
        return native_hit
    cv2, _, _ = ensure_cv2_numpy_mss()
    if screen is None or template is None:
        return 0.0, None
    if screen.shape[0] < template.shape[0] or screen.shape[1] < template.shape[1]:
        return 0.0, None
    t0 = time.perf_counter()
    try:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return float(max_val), max_loc
    finally:
        telemetry_record_match_sec(time.perf_counter() - t0)


def find_image(screen: Any, template: Any, threshold: float = 0.6) -> Tuple[bool, float]:
    max_val, _ = match_template_ccoeff_normed_max(screen, template)
    return max_val >= threshold, max_val


def find_image_location(
    screen: Any,
    template: Any,
    threshold: float = 0.6,
) -> Tuple[int, int] | None:
    max_val, max_loc = match_template_ccoeff_normed_max(screen, template)
    if max_loc is None or max_val < threshold:
        return None
    h, w = template.shape[:2]
    x, y = max_loc
    return (x + w // 2, y + h // 2)


def match_template_max_score(screen: Any, template: Any) -> float:
    max_val, _ = match_template_ccoeff_normed_max(screen, template)
    return max_val


def extract_match_patch(screen: Any, template: Any, max_loc_tl: Any) -> Any:
    """matchTemplate 좌상단 기준 ROI 내 템플릿 크기 패치(BGR)."""
    if screen is None or template is None or max_loc_tl is None:
        return None
    mx, my = int(max_loc_tl[0]), int(max_loc_tl[1])
    th, tw = int(template.shape[0]), int(template.shape[1])
    sh, sw = screen.shape[:2]
    if my < 0 or mx < 0 or my + th > sh or mx + tw > sw:
        return None
    return screen[my : my + th, mx : mx + tw].copy()


def match_patch_if_ok(
    screen: Any,
    template: Any,
    threshold: float,
) -> Tuple[Any | None, float]:
    """임계값 충족 시 매칭 패치와 점수, 아니면 (None, score)."""
    max_val, max_loc = match_template_ccoeff_normed_max(screen, template)
    if max_loc is None or max_val < threshold:
        return None, float(max_val)
    p = extract_match_patch(screen, template, max_loc)
    return p, float(max_val)


def rescale_if_ratio_changed(
    template_original: Any,
    scaled_current: Any,
    current_ratio: float,
    last_ratio: float | None,
) -> tuple[Any, float | None]:
    """해상도 비율이 바뀐 경우에만 scale_template. (scaled, new_last_ratio)."""
    if last_ratio == current_ratio:
        return scaled_current, last_ratio
    return scale_template(template_original, current_ratio), current_ratio


def refresh_scaled_map_if_ratio_changed(
    templates: Mapping[str, Any],
    scaled: MutableMapping[str, Any],
    kinds: Sequence[str],
    current_ratio: float,
    last_ratio: float | None,
) -> tuple[float | None, bool]:
    """여러 종류 템플릿을 동일 비율로 스케일. (new_last_ratio, did_rescale)."""
    if last_ratio == current_ratio:
        return last_ratio, False
    for k in kinds:
        scaled[k] = scale_template(templates[k], current_ratio)
    return current_ratio, True


def match_tl_to_center_xy(tl_xy: Any, tw: int, th: int) -> tuple[int, int]:
    """matchTemplate 좌상단 + 템플릿 크기 → 템플릿 좌표계 중심(정수)."""
    return int(tl_xy[0]) + tw // 2, int(tl_xy[1]) + th // 2
