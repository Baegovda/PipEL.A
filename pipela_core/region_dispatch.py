"""region_type(UI)·템플릿 capture kind → ROI 글로벌 이름·라벨 — main/Qt 공통 디스패치."""

from __future__ import annotations

# region_type(UI) / capture kind → ROI 글로벌 변수 이름
REGION_TYPE_TO_GLOBAL_NAME: dict[str, str] = {
    "ride": "ride_detect_region",
    "hp_refill": "hp_refill_detect_region",
    "kill_counter": "kill_counter_detect_region",
    "reload_nobullet": "reload_nobullet_match_region",
    "reload_bullet": "reload_bullet_match_region",
    "reload_vault": "reload_vault_match_region",
    "ammo_buybutton": "ammo_buybutton_match_region",
    "ammo_inven": "ammo_inven_match_region",
    "ammo_bank": "ammo_bank_match_region",
    "call_merc_1": "call_merc_1_match_region",
    "call_merc_2": "call_merc_2_match_region",
    "call_merc_3": "call_merc_3_match_region",
    "call_merc_4": "call_merc_4_match_region",
    "start_game_launcher": "start_game_launcher_match_region",
    "start_game_intro_skip": "start_game_intro_skip_match_region",
    "start_game_accept": "start_game_accept_match_region",
}

CAPTURE_KIND_TO_REGION_TYPE: dict[str, str] = {
    "ride_target": "ride",
    "hp_zkey": "hp_refill",
    "reload_nobullet": "reload_nobullet",
    "reload_bullet": "reload_bullet",
    "reload_vault": "reload_vault",
    "ammo_buybutton": "ammo_buybutton",
    "ammo_inven": "ammo_inven",
    "ammo_bank": "ammo_bank",
    "call_merc_1": "call_merc_1",
    "call_merc_2": "call_merc_2",
    "call_merc_3": "call_merc_3",
    "call_merc_4": "call_merc_4",
    "start_game_launcher": "start_game_launcher",
    "start_game_intro_skip": "start_game_intro_skip",
    "start_game_accept": "start_game_accept",
}

REGION_TYPES_CLEAR_MATCH_ROI: frozenset[str] = frozenset(REGION_TYPE_TO_GLOBAL_NAME.keys())

REGION_TYPE_UI_LABEL_PAIR: dict[str, tuple[str, str]] = {
    "ride": ("Ride", "Ride"),
    "hp_refill": ("HP Refill", "HP Refill"),
    "kill_counter": ("Kill Counter", "Kill Counter"),
    "reload_nobullet": ("Reload NoBullet", "NoBullet"),
    "reload_bullet": ("Reload Bullet", "Bullet"),
    "reload_vault": ("Reload Vault", "Vault"),
    "ammo_buybutton": ("Ammo 구매버튼", "Ammo 구매"),
    "ammo_inven": ("Ammo 인벤", "Ammo 인벤"),
    "ammo_bank": ("Ammo 은행", "Ammo 은행"),
    "call_merc_1": ("공격을 지시할 용병이 없습니다", "용병없음"),
    "call_merc_2": ("용병 고용계약서", "고용계약"),
    "call_merc_3": ("호출", "호출"),
    "call_merc_4": ("창 닫기", "닫기"),
    "start_game_launcher": ("Intro Skip — 런처 START 버튼", "런처 START"),
    "start_game_intro_skip": ("서버 선택 (게임)", "서버 선택"),
    "start_game_accept": ("Accept (게임)", "Accept"),
}

REGION_PREVIEW_PERSIST_VALID: frozenset[str] = frozenset(REGION_TYPE_TO_GLOBAL_NAME.keys())
