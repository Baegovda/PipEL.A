"""Reload — nobullet 감지 후 bullet/vault 매칭·장전 발수 클램프(입력 I/O 제외)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple

from pipela_core.template_matching import (
    extract_match_patch,
    match_template_ccoeff_normed_max,
    match_tl_to_center_xy,
)
from pipela_core.win32_input_constants import VK_RETURN


def reload_move_sleep_double_click(
    abs_x: int,
    abs_y: int,
    *,
    mouse_move_fn: Callable[[int, int], None],
    mouse_double_click_fn: Callable[[], None],
    pre_click_sleep_sec: float = 0.1,
) -> None:
    """Reload DBC: 이동 → 짧은 대기 → 더블클릭(타이밍은 기존과 동일)."""
    mouse_move_fn(abs_x, abs_y)
    time.sleep(pre_click_sleep_sec)
    mouse_double_click_fn()


def reload_send_digit_keys_and_return(
    digits: str,
    target_hwnd: Any,
    send_key_fn: Callable[[int, Any], None],
) -> None:
    """숫자 키 순서 입력 후 Enter(기존 Reload 타이밍 유지)."""
    time.sleep(0.2)
    for ch in digits:
        if ch.isdigit():
            send_key_fn(ord(ch), target_hwnd)
            time.sleep(0.1)
    time.sleep(0.05)
    send_key_fn(VK_RETURN, target_hwnd)


def reload_clamp_ammo_count(raw: Any) -> Tuple[int, str]:
    """장전 숫자 1~99999 및 문자열(키 입력용)."""
    try:
        ammo_n = int(raw)
    except (TypeError, ValueError):
        ammo_n = 45
    ammo_n = max(1, min(99999, ammo_n))
    return ammo_n, str(ammo_n)


def reload_match_bullet_on_screen(
    screen: Any,
    scaled_bullet: Any,
    threshold: float,
    *,
    on_patch: Optional[Callable[[Any], None]] = None,
    probe: Optional[Callable[[], None]] = None,
) -> tuple[float, Any | None, tuple[int, int] | None]:
    """
    bullet ROI 캡처 화면에 대한 1회 매칭.
    반환: (score, tl, center_xy) — 임계 미달 시 center_xy None.
    """
    if probe is not None:
        probe()
    sc, tl = match_template_ccoeff_normed_max(screen, scaled_bullet)
    if tl is None or float(sc) < float(threshold):
        return float(sc), tl, None
    patch = extract_match_patch(screen, scaled_bullet, tl)
    if patch is not None and on_patch is not None:
        on_patch(patch)
    bh, bw = int(scaled_bullet.shape[0]), int(scaled_bullet.shape[1])
    return float(sc), tl, match_tl_to_center_xy(tl, bw, bh)


def reload_match_vault_on_screen(
    scr_m: Any,
    scaled_vault: Any,
    vault_threshold: float,
    *,
    on_patch: Optional[Callable[[Any], None]] = None,
    probe: Optional[Callable[[], None]] = None,
) -> tuple[float, Any | None]:
    if probe is not None:
        probe()
    m_score, m_tl = match_template_ccoeff_normed_max(scr_m, scaled_vault)
    if m_tl is not None and float(m_score) >= float(vault_threshold):
        pm = extract_match_patch(scr_m, scaled_vault, m_tl)
        if pm is not None and on_patch is not None:
            on_patch(pm)
    return float(m_score), m_tl
