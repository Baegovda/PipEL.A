"""템플릿 캡처 kind → 메타·경로/데이터 전역 이름 — `main` 루프·UI 공통."""

from __future__ import annotations

# kind → (저장 파일명, 레지스트리 *_image_data 키, 사람이 읽는 라벨)
_TEMPLATE_CAPTURE_META: dict[str, tuple[str, str, str]] = {
    "ride_target": ("target.png", "ride_target_image_data", "Ride 타겟"),
    "reload_nobullet": ("nobullet.png", "reload_nobullet_image_data", "Reload NoBullet"),
    "reload_bullet": ("bullet.png", "reload_bullet_image_data", "Reload Bullet"),
    "reload_vault": ("vault.png", "reload_vault_image_data", "Reload Vault"),
    "hp_zkey": ("zkey.png", "hp_refill_zkey_image_data", "HP Bar (zkey)"),
    "ammo_buybutton": ("buybutton.png", "ammo_restock_buybutton_image_data", "Ammo 구매버튼"),
    "ammo_inven": ("inven.png", "ammo_restock_inven_image_data", "Ammo 인벤"),
    "ammo_bank": ("bank.png", "ammo_restock_bank_image_data", "Ammo 은행"),
    "call_merc_1": ("call_merc_1.png", "call_merc_1_image_data", "공격을 지시할 용병이 없습니다 (트리거)"),
    "call_merc_2": ("call_merc_2.png", "call_merc_2_image_data", "용병 고용계약서"),
    "call_merc_3": ("call_merc_3.png", "call_merc_3_image_data", "호출"),
    "call_merc_4": ("call_merc_4.png", "call_merc_4_image_data", "창 닫기"),
    "start_game_launcher": ("start_game.png", "start_game_launcher_image_data", "Intro Skip — 런처 START 버튼"),
    "start_game_intro_skip": ("intro_skip.png", "start_game_intro_skip_image_data", "서버 선택 (게임 창)"),
    "start_game_accept": ("accept.png", "start_game_accept_image_data", "Accept (게임 창)"),
}


def get_template_capture_kind_meta(kind: str) -> tuple[str, str, str] | None:
    """kind → (파일명, 레지 키, 라벨). 없으면 None."""
    return _TEMPLATE_CAPTURE_META.get(kind)


# kind → (경로 전역 이름, 이미지 데이터 플래그 전역 이름 또는 None)
TEMPLATE_CAPTURE_KIND_PATH_BINDING: dict[str, tuple[str, str | None]] = {
    "ride_target": ("RIDE_TARGET_IMAGE_PATH", None),
    "reload_nobullet": ("RELOAD_NOBULLET_IMAGE_PATH", "RELOAD_NOBULLET_IMAGE_DATA"),
    "reload_bullet": ("RELOAD_BULLET_IMAGE_PATH", "RELOAD_BULLET_IMAGE_DATA"),
    "reload_vault": ("RELOAD_VAULT_IMAGE_PATH", "RELOAD_VAULT_IMAGE_DATA"),
    "hp_zkey": ("HP_REFILL_ZKEY_IMAGE_PATH", "HP_REFILL_ZKEY_IMAGE_DATA"),
    "ammo_buybutton": ("AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH", None),
    "ammo_inven": ("AMMO_RESTOCK_INVEN_IMAGE_PATH", None),
    "ammo_bank": ("AMMO_RESTOCK_BANK_IMAGE_PATH", None),
    "call_merc_1": ("CALL_MERC_1_IMAGE_PATH", None),
    "call_merc_2": ("CALL_MERC_2_IMAGE_PATH", None),
    "call_merc_3": ("CALL_MERC_3_IMAGE_PATH", None),
    "call_merc_4": ("CALL_MERC_4_IMAGE_PATH", None),
    "start_game_launcher": ("START_GAME_IMAGE_PATH", None),
    "start_game_intro_skip": ("START_GAME_INTRO_SKIP_IMAGE_PATH", None),
    "start_game_accept": ("START_GAME_ACCEPT_IMAGE_PATH", None),
}

# AmmoRestockSettingsWindow UI kind ("buybutton"…) → start_template_image_capture kind
AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND: dict[str, str] = {
    "buybutton": "ammo_buybutton",
    "inven": "ammo_inven",
    "bank": "ammo_bank",
}
