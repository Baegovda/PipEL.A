"""Reload 루프 — nobullet/bullet 경로 쌍에서 템플릿 로드(경로 변경·캐시 무효 시만)."""

from __future__ import annotations

import os
from typing import Any

from pipela_core.image_registry import load_image_data
from pipela_core.template_matching import scale_template


def reload_try_reload_nobullet_bullet_templates(
    current_nobullet_path: str | None,
    current_bullet_path: str | None,
    last_nobullet_path: str | None,
    last_bullet_path: str | None,
    nobullet_template: Any,
    bullet_template: Any,
) -> tuple[bool, bool, tuple[Any, Any, str | None, str | None] | None]:
    """
    Returns (success, did_attempt_reload, pair_or_none).
    - success: 템플릿 쌍 사용 가능
    - did_attempt_reload: 경로/캐시 때문에 load_image_data 를 호출했는지
    - pair_or_none: 갱신된 (nobullet, bullet, cur_nb_path, cur_bu_path); 갱신 없으면 None
    """
    need = (
        current_nobullet_path != last_nobullet_path
        or current_bullet_path != last_bullet_path
        or nobullet_template is None
        or bullet_template is None
    )
    if not need:
        return True, False, None
    new_nobullet = load_image_data(
        current_nobullet_path or "",
        "reload_nobullet_image_data",
    )
    new_bullet = load_image_data(
        current_bullet_path or "",
        "reload_bullet_image_data",
    )
    if new_nobullet is None:
        print(
            f"[Reload] FAIL nobullet ({os.path.basename(str(current_nobullet_path or ''))})",
        )
        return False, True, None
    if new_bullet is None:
        print(
            f"[Reload] FAIL bullet ({os.path.basename(str(current_bullet_path or ''))})",
        )
        return False, True, None
    return (
        True,
        True,
        (
            new_nobullet,
            new_bullet,
            current_nobullet_path,
            current_bullet_path,
        ),
    )


def reload_rescale_nobullet_bullet_if_needed(
    nobullet_orig: Any,
    bullet_orig: Any,
    scaled_nobullet: Any,
    scaled_bullet: Any,
    current_ratio: float,
    last_ratio: float | None,
) -> tuple[Any, Any, float | None, bool]:
    """
    비율 변경 또는 스케일 캐시 없을 때 nobullet/bullet 동시 스케일.
    반환: (scaled_nobullet, scaled_bullet, new_last_ratio, did_rescale)
    """
    if (
        scaled_nobullet is not None
        and scaled_bullet is not None
        and last_ratio == current_ratio
    ):
        return scaled_nobullet, scaled_bullet, last_ratio, False
    if nobullet_orig is None or bullet_orig is None:
        return scaled_nobullet, scaled_bullet, last_ratio, False
    return (
        scale_template(nobullet_orig, current_ratio),
        scale_template(bullet_orig, current_ratio),
        current_ratio,
        True,
    )
