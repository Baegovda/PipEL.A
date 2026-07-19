"""설정 창 이미지 템플릿 「테스트」1회 — 캡처·스케일·matchTemplate (백그라운드 루프 점수는 변경하지 않음).

`pipela_qt.qt_capture.attach_template_toolbar` 의 **테스트** 는 모두
``main._template_debug_detect_run`` → ``debug_sample_template_match`` 만 탄다(게임/런처 분기만 이 파일).
"""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping

import mss

from pipela_core.image_registry import load_image_data
from pipela_core.scale_geometry import get_region_pixels, get_scale_ratio
from pipela_core.template_capture_catalog import (
    TEMPLATE_CAPTURE_KIND_PATH_BINDING,
    get_template_capture_kind_meta,
)
from pipela_core.template_match_config import template_match_threshold_for_globals
from pipela_core.template_matching import match_template_ccoeff_normed_max, scale_template
from pipela_core.template_roi import template_roi_for_kind
from pipela_core.vision_capture import capture_region


# 「감지」테스트: 기본은 GDI만(`call_merc_match`·기타 루프와 동일). mss(화면 합성)는
# 게임 Rect 위에 겹친 ECH 템플릿 디버그 오버레이(탑모스트)까지 합쳐져, 연속 클릭 시 점수가 떨어질 수 있음.
def _env_template_debug_mss_fallback() -> bool:
    v = (os.environ.get("PIPELA_TEMPLATE_DEBUG_MSS_FALLBACK", "") or "").strip().lower()
    return v in ("1", "true", "yes", "on", "y")


def debug_sample_template_match(
    kind: str,
    g: Mapping[str, Any],
    *,
    target_hwnd: int | None,
    get_launcher_hwnd: Callable[[], int | None] | None = None,
) -> tuple[float, str, tuple[int, int, int, int] | None, Any]:
    """
    반환: (score, err, rect, patch_bgr) — rect는 창 캡처 기준 (l,t,r,b);
    patch_bgr는 임계값 충족 시 매칭 패치(BGR).
    """
    meta = get_template_capture_kind_meta(kind)
    bind = TEMPLATE_CAPTURE_KIND_PATH_BINDING.get(kind)
    if meta is None or bind is None:
        return 0.0, "알 수 없는 종류", None, None
    _, reg_key, _ = meta

    if kind == "start_game_launcher":
        cap_reg = template_roi_for_kind(kind, g)
        path = g.get(bind[0])
        template = load_image_data(path, reg_key)
        if template is None:
            return 0.0, "템플릿 로드 실패", None, None
        uh = get_launcher_hwnd() if get_launcher_hwnd else None
        if not uh:
            return 0.0, "스마트업데이터 창 없음", None, None
        sct = mss.mss()
        try:
            # 게임 창과 동일: 기본 GDI(클라만). mss 합성은 ECH·타 창이 섞이므로 `PIPELA_TEMPLATE_DEBUG_MSS_FALLBACK` 때만
            screen = capture_region(
                uh, sct, cap_reg, client_dc_only=True,
            )
            if screen is None and _env_template_debug_mss_fallback():
                screen = capture_region(
                    uh, sct, cap_reg, client_dc_only=False,
                )
        finally:
            try:
                sct.close()
            except Exception:
                pass
        if screen is None:
            return 0.0, "스마트업데이터 창 캡처 실패", None, None
        ratio = get_scale_ratio(uh)
        scaled = scale_template(template, ratio)
        if scaled is None or screen.shape[0] < scaled.shape[0] or screen.shape[1] < scaled.shape[1]:
            return 0.0, "화면이 템플릿보다 작음", None, None
        max_val, max_loc = match_template_ccoeff_normed_max(screen, scaled)
        if max_loc is None:
            return 0.0, "화면이 템플릿보다 작음", None, None
        mx, my = int(max_loc[0]), int(max_loc[1])
        th, tw = int(scaled.shape[0]), int(scaled.shape[1])
        thr_dbg = template_match_threshold_for_globals(g, kind)
        patch_bgr = None
        if (
            float(max_val) >= thr_dbg
            and my + th <= screen.shape[0]
            and mx + tw <= screen.shape[1]
        ):
            patch_bgr = screen[my : my + th, mx : mx + tw].copy()
        rp = get_region_pixels(uh, cap_reg) if cap_reg else None
        ox, oy = (int(rp[0]), int(rp[1])) if rp else (0, 0)
        l = ox + mx
        t = oy + my
        r, b = l + tw, t + th
        return float(max_val), "", (l, t, r, b), patch_bgr

    if not target_hwnd:
        return 0.0, "게임 창 없음", None, None

    path = g.get(bind[0])
    cap_reg = template_roi_for_kind(kind, g)
    template = load_image_data(path, reg_key)
    if template is None:
        return 0.0, "템플릿 로드 실패", None, None
    sct = mss.mss()
    try:
        screen = capture_region(
            target_hwnd, sct, cap_reg, client_dc_only=True,
        )
        if screen is None and _env_template_debug_mss_fallback():
            screen = capture_region(
                target_hwnd, sct, cap_reg, client_dc_only=False,
            )
    finally:
        try:
            sct.close()
        except Exception:
            pass
    if screen is None:
        return 0.0, "화면 캡처 실패(최소화·좌표 오류 등)", None, None
    ratio = get_scale_ratio(target_hwnd)
    if ratio is None or ratio <= 0:
        return 0.0, "창 스케일 측정 실패", None, None
    scaled = scale_template(template, ratio)
    if scaled is None or screen.shape[0] < scaled.shape[0] or screen.shape[1] < scaled.shape[1]:
        return 0.0, "화면이 템플릿보다 작음", None, None
    max_val, max_loc = match_template_ccoeff_normed_max(screen, scaled)
    if max_loc is None:
        return 0.0, "화면이 템플릿보다 작음", None, None
    mx, my = int(max_loc[0]), int(max_loc[1])
    th, tw = int(scaled.shape[0]), int(scaled.shape[1])
    thr_dbg = template_match_threshold_for_globals(g, kind)
    patch_bgr = None
    if (
        float(max_val) >= thr_dbg
        and my + th <= screen.shape[0]
        and mx + tw <= screen.shape[1]
    ):
        patch_bgr = screen[my : my + th, mx : mx + tw].copy()
    region_px = get_region_pixels(target_hwnd, cap_reg) if cap_reg else None
    if region_px:
        rx, ry = int(region_px[0]), int(region_px[1])
        l, t = rx + mx, ry + my
    else:
        l, t = mx, my
    r, b = l + tw, t + th
    return float(max_val), "", (l, t, r, b), patch_bgr
