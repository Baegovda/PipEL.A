"""Ammo Restock 루프·설정 — 전역 이름·레지 키 등 순수 데이터(폰트/섹션 튜플은 `main`)."""

from __future__ import annotations

AMMO_RESTOCK_KINDS: tuple[str, ...] = ("buybutton", "inven", "bank")

AMMO_THR_GLOBAL_BY_KIND: dict[str, str] = {
    "buybutton": "ammo_restock_buybutton_threshold",
    "inven": "ammo_restock_inven_threshold",
    "bank": "ammo_restock_bank_threshold",
}
AMMO_PATH_GLOBAL_BY_KIND: dict[str, str] = {
    "buybutton": "AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH",
    "inven": "AMMO_RESTOCK_INVEN_IMAGE_PATH",
    "bank": "AMMO_RESTOCK_BANK_IMAGE_PATH",
}
AMMO_REGISTRY_DATA_KEY_BY_KIND: dict[str, str] = {
    "buybutton": "ammo_restock_buybutton_image_data",
    "inven": "ammo_restock_inven_image_data",
    "bank": "ammo_restock_bank_image_data",
}
AMMO_FILE_DIALOG_TITLE_BY_KIND: dict[str, str] = {
    "buybutton": "구매 버튼 이미지 (buybutton) 선택",
    "inven": "인벤 이미지 (inven) 선택",
    "bank": "은행 이미지 (bank) 선택",
}
AMMO_BUNDLE_FILENAME_BY_KIND: dict[str, str] = {
    "buybutton": "buybutton.png",
    "inven": "inven.png",
    "bank": "bank.png",
}
AMMO_SCORE_ROW_BINDINGS: tuple[tuple[str, str, str], ...] = (
    ("buybutton", "ammo_restock_buybutton_score", "ammo_restock_buybutton_threshold"),
    ("inven", "ammo_restock_inven_score", "ammo_restock_inven_threshold"),
    ("bank", "ammo_restock_bank_score", "ammo_restock_bank_threshold"),
)
AMMO_SCORE_GLOBAL_BY_KIND: dict[str, str] = {k: sg for k, sg, _tg in AMMO_SCORE_ROW_BINDINGS}
AMMO_MATCH_ROI_GLOBAL: dict[str, str] = {
    "buybutton": "ammo_buybutton_match_region",
    "inven": "ammo_inven_match_region",
    "bank": "ammo_bank_match_region",
}
AMMO_LOOP_LOG_TAG: dict[str, str] = {"buybutton": "buy", "inven": "inven", "bank": "bank"}
AMMO_PREVIEW_LABEL_ATTR: dict[str, str] = {
    "buybutton": "buybutton_preview_label",
    "inven": "inven_preview_label",
    "bank": "bank_preview_label",
}
AMMO_SUFFIX_VAR_ATTR: dict[str, str] = {
    "buybutton": "_ar_suffix_buy",
    "inven": "_ar_suffix_inven",
    "bank": "_ar_suffix_bank",
}
