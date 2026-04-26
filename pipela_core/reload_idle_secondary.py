"""Reload — (선택) nobullet 미감지 시 bullet·vault 점수 갱신. `main.reload_loop` 는 ① 감지 전 ②/③을 폴링하지 않음."""

from __future__ import annotations

from typing import Any, Callable, Optional

from pipela_core.image_registry import load_image_data_if_path_changed
from pipela_core.template_matching import (
    match_patch_if_ok,
    match_template_max_score,
    scale_template,
)
from pipela_core.vision_capture import capture_region


def reload_idle_update_bullet_vault_scores(
    target_hwnd: Any,
    sct: Any,
    *,
    scaled_bullet: Any,
    reload_bullet_match_region: Any,
    reload_bullet_threshold: float,
    reload_vault_match_region: Any | None,
    vault_image_path: str | None,
    vault_template: Any,
    last_vault_path: str | None,
    current_ratio: float,
    reload_vault_threshold: float,
    on_bullet_patch: Optional[Callable[[Any], None]] = None,
    on_vault_patch: Optional[Callable[[Any], None]] = None,
    probe: Optional[Callable[[str, str], None]] = None,
) -> tuple[float, float, Any, str | None]:
    """
    반환: bullet_detection_score, vault_detection_score, vault_template, last_vault_path.
    scr_b 가 없어도 vault ROI 가 있으면 vault 만 갱신(기존 main 과 동일).
    """
    scr_b = capture_region(
        target_hwnd, sct, reload_bullet_match_region, client_dc_only=True,
    )
    bullet_detection_score = 0.0
    if scr_b is not None:
        if probe is not None:
            probe("reload", "bullet")
        bullet_detection_score = match_template_max_score(scr_b, scaled_bullet)
        pb, _ = match_patch_if_ok(scr_b, scaled_bullet, reload_bullet_threshold)
        if pb is not None and on_bullet_patch is not None:
            on_bullet_patch(pb)

    if reload_vault_match_region is None:
        return bullet_detection_score, 0.0, vault_template, last_vault_path

    v_tpl, v_last = load_image_data_if_path_changed(
        vault_image_path,
        "reload_vault_image_data",
        last_vault_path,
        vault_template,
    )
    vault_template = v_tpl
    last_vault_path = v_last

    if vault_template is None:
        return bullet_detection_score, 0.0, vault_template, last_vault_path

    s_bm = scale_template(vault_template, current_ratio)
    if s_bm is None:
        return bullet_detection_score, 0.0, vault_template, last_vault_path

    scr_bm = capture_region(
        target_hwnd, sct, reload_vault_match_region, client_dc_only=True,
    )
    if scr_bm is None:
        return bullet_detection_score, 0.0, vault_template, last_vault_path

    if probe is not None:
        probe("reload", "vault")

    vault_detection_score = match_template_max_score(scr_bm, s_bm)
    pv, _ = match_patch_if_ok(scr_bm, s_bm, reload_vault_threshold)
    if pv is not None and on_vault_patch is not None:
        on_vault_patch(pv)

    return bullet_detection_score, vault_detection_score, vault_template, last_vault_path
