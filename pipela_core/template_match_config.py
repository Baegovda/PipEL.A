"""캡처 kind별 매칭 임계값이 들어 있는 main 전역 이름."""

from __future__ import annotations

from typing import Any, Mapping

TEMPLATE_MATCH_THRESHOLD_GLOBAL_BY_KIND: dict[str, str] = {
    "ride_target": "ride_threshold",
    "hp_zkey": "hp_refill_threshold",
    "reload_nobullet": "reload_nobullet_threshold",
    "reload_bullet": "reload_bullet_threshold",
    "reload_vault": "reload_vault_threshold",
    "ammo_buybutton": "ammo_restock_buybutton_threshold",
    "ammo_inven": "ammo_restock_inven_threshold",
    "ammo_bank": "ammo_restock_bank_threshold",
    "call_merc_1": "call_merc_1_threshold",
    "call_merc_2": "call_merc_2_threshold",
    "call_merc_3": "call_merc_3_threshold",
    "call_merc_4": "call_merc_4_threshold",
    "start_game_launcher": "start_game_launcher_threshold",
    "start_game_intro_skip": "start_game_intro_skip_threshold",
    "start_game_accept": "start_game_accept_threshold",
}


def template_match_threshold_for_globals(
    g: Mapping[str, Any],
    kind: str,
    default: float = 0.6,
) -> float:
    name = TEMPLATE_MATCH_THRESHOLD_GLOBAL_BY_KIND.get(kind)
    if name is None:
        return default
    try:
        return float(g.get(name, default))
    except (TypeError, ValueError):
        return default
