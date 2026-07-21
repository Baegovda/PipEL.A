"""레지스트리 키 ↔ 전역 이름 매핑 테이블 — load/save 루프에서 재사용."""

from __future__ import annotations

# JSON 영역: (reg_key, globals 키, 로드 성공 시 print 문구 또는 None)
CONFIG_LOAD_JSON_REGIONS: tuple[tuple[str, str, str | None], ...] = (
    ("ride_detect_region", "ride_detect_region", None),
    ("hp_refill_detect_region", "hp_refill_detect_region", "[HP Refill] 영역 로드 OK"),
    ("kill_counter_detect_region", "kill_counter_detect_region", None),
    ("reload_nobullet_match_region", "reload_nobullet_match_region", None),
    ("reload_bullet_match_region", "reload_bullet_match_region", None),
    ("reload_vault_match_region", "reload_vault_match_region", None),
    ("ammo_buybutton_match_region", "ammo_buybutton_match_region", None),
    ("ammo_inven_match_region", "ammo_inven_match_region", None),
    ("ammo_bank_match_region", "ammo_bank_match_region", None),
    ("call_merc_1_match_region", "call_merc_1_match_region", None),
    ("call_merc_2_match_region", "call_merc_2_match_region", None),
    ("call_merc_3_match_region", "call_merc_3_match_region", None),
    ("call_merc_4_match_region", "call_merc_4_match_region", None),
    ("start_game_launcher_match_region", "start_game_launcher_match_region", None),
    ("start_game_intro_skip_match_region", "start_game_intro_skip_match_region", None),
    ("start_game_accept_match_region", "start_game_accept_match_region", None),
)

CONFIG_SAVE_JSON_REGION_NAMES: tuple[str, ...] = tuple(
    _rk for _rk, _ga, _ in CONFIG_LOAD_JSON_REGIONS
)

CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS: tuple[str, ...] = (
    "ammo_restock_buybutton_threshold",
    "ammo_restock_inven_threshold",
    "ammo_restock_bank_threshold",
)

CONFIG_CALL_MERC_THRESHOLD_KEYS: tuple[str, ...] = (
    "call_merc_1_threshold",
    "call_merc_2_threshold",
    "call_merc_3_threshold",
    "call_merc_4_threshold",
)

CONFIG_LOAD_TEMPLATE_IMAGE_PATHS: tuple[tuple[str, str], ...] = (
    ("reload_nobullet_image_path", "RELOAD_NOBULLET_IMAGE_PATH"),
    ("reload_bullet_image_path", "RELOAD_BULLET_IMAGE_PATH"),
    ("reload_vault_image_path", "RELOAD_VAULT_IMAGE_PATH"),
    ("ride_target_image_path", "RIDE_TARGET_IMAGE_PATH"),
    ("hp_refill_zkey_image_path", "HP_REFILL_ZKEY_IMAGE_PATH"),
    ("ammo_restock_buybutton_image_path", "AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH"),
    ("ammo_restock_inven_image_path", "AMMO_RESTOCK_INVEN_IMAGE_PATH"),
    ("ammo_restock_bank_image_path", "AMMO_RESTOCK_BANK_IMAGE_PATH"),
    ("call_merc_1_image_path", "CALL_MERC_1_IMAGE_PATH"),
    ("call_merc_2_image_path", "CALL_MERC_2_IMAGE_PATH"),
    ("call_merc_3_image_path", "CALL_MERC_3_IMAGE_PATH"),
    ("call_merc_4_image_path", "CALL_MERC_4_IMAGE_PATH"),
    ("start_game_launcher_image_path", "START_GAME_IMAGE_PATH"),
    ("start_game_intro_skip_image_path", "START_GAME_INTRO_SKIP_IMAGE_PATH"),
    ("start_game_accept_image_path", "START_GAME_ACCEPT_IMAGE_PATH"),
)

CONFIG_LOAD_IMAGE_DATA_PRESENCE: tuple[tuple[str, str], ...] = (
    ("reload_nobullet_image_data", "RELOAD_NOBULLET_IMAGE_DATA"),
    ("reload_bullet_image_data", "RELOAD_BULLET_IMAGE_DATA"),
    ("reload_vault_image_data", "RELOAD_VAULT_IMAGE_DATA"),
    ("hp_refill_zkey_image_data", "HP_REFILL_ZKEY_IMAGE_DATA"),
    ("start_game_launcher_image_data", "START_GAME_LAUNCHER_IMAGE_DATA"),
    ("start_game_intro_skip_image_data", "START_GAME_INTRO_SKIP_IMAGE_DATA"),
    ("start_game_accept_image_data", "START_GAME_ACCEPT_IMAGE_DATA"),
)

# (reg_key, globals 이름, 기본값)
CONFIG_LOAD_BOOLS_PRE_KC: tuple[tuple[str, str, bool], ...] = (
    ("left_click_feature_enabled", "left_click_feature_enabled", True),
    ("right_hold_feature_enabled", "right_hold_feature_enabled", True),
    ("ride_feature_enabled", "ride_feature_enabled", True),
    ("hp_refill_feature_enabled", "hp_refill_feature_enabled", True),
    ("kill_counter_enabled", "kill_counter_enabled", True),
    ("reload_active", "reload_active", True),
    ("ammo_restock_active", "ammo_restock_active", False),
    ("call_merc_active", "call_merc_active", False),
    ("start_game_launcher_active", "start_game_launcher_active", False),
    ("game_window_center_on_detect_enabled", "game_window_center_on_detect_enabled", True),
)

CONFIG_SAVE_BOOLS_PRE_KC: tuple[str, ...] = (
    "left_click_feature_enabled",
    "right_hold_feature_enabled",
    "ride_feature_enabled",
    "hp_refill_feature_enabled",
    "kill_counter_enabled",
    "reload_active",
    "ammo_restock_active",
    "call_merc_active",
    "start_game_launcher_active",
    "game_window_center_on_detect_enabled",
)

# ``main.settings_sequence_autoscroll_steps`` 키 — ``pipela_qt.settings_sequence_autoscroll.FEAT_*`` 와 동일
SETTINGS_SEQUENCE_AUTOSCROLL_FEAT_KEYS: frozenset[str] = frozenset(
    ("reload", "call_merc", "ammo_restock", "start_game"),
)

CONFIG_SAVE_BOOLS_FLAME: tuple[str, ...] = ("flame_trigger_feature_enabled",)

CONFIG_SAVE_LEFTCLICK_FIELDS: tuple[str, ...] = (
    "left_click_interval_ms",
    "left_click_random_enabled",
    "left_click_random_min_ms",
    "left_click_random_max_ms",
    "left_click_hold_sec",
)

CONFIG_SAVE_MERC_FIRE_FIELDS: tuple[str, ...] = (
    "merc_fire_enabled",
    "merc_fire_key_code",
    "merc_fire_random_min_ms",
    "merc_fire_random_max_ms",
    "merc_fire_interval_use_seconds",
)

# 레지 키 → gsave[global_attr]
CONFIG_SAVE_SZ_FIELDS: tuple[tuple[str, str], ...] = (
    ("hp_refill_threshold", "hp_refill_threshold"),
    ("hp_refill_key_code", "hp_refill_key_code"),
    ("ride_threshold", "ride_threshold"),
    ("reload_nobullet_threshold", "reload_nobullet_threshold"),
    ("reload_bullet_threshold", "reload_bullet_threshold"),
    ("reload_vault_threshold", "reload_vault_threshold"),
    ("reload_threshold", "reload_nobullet_threshold"),
    ("reload_ammo_count", "reload_ammo_count"),
    ("start_game_launcher_threshold", "start_game_launcher_threshold"),
    ("start_game_intro_skip_threshold", "start_game_intro_skip_threshold"),
    ("start_game_accept_threshold", "start_game_accept_threshold"),
    ("pipela_ui_font_pt", "pipela_ui_font_pt"),
    ("kill_counter_panel_w", "kill_counter_panel_w"),
    ("control_panel_w", "control_panel_w"),
)

CONFIG_LOAD_OPTIONAL_FLOATS: tuple[tuple[str, str], ...] = (
    ("hp_refill_threshold", "hp_refill_threshold"),
    ("ride_threshold", "ride_threshold"),
    ("start_game_launcher_threshold", "start_game_launcher_threshold"),
    ("start_game_intro_skip_threshold", "start_game_intro_skip_threshold"),
    ("start_game_accept_threshold", "start_game_accept_threshold"),
)


def _build_registry_config_snapshot_keys() -> tuple[str, ...]:
    """레지 load/save 가 건드리는 main 전역 이름 — 읽기 전용 스냅샷용(중복 제거·선언 순서)."""
    out: list[str] = []
    seen: set[str] = set()

    def push(name: str) -> None:
        if name not in seen:
            seen.add(name)
            out.append(name)

    for _, ga, _ in CONFIG_LOAD_BOOLS_PRE_KC:
        push(ga)
    push("flame_trigger_feature_enabled")
    for kn in (
        "kill_counter_stats_row_order",
        "kill_counter_lap_start_ts",
        "kill_counter_lap_pause_segments",
    ):
        push(kn)
    for _, ga, _ in CONFIG_LOAD_JSON_REGIONS:
        push(ga)
    for _, ga in CONFIG_LOAD_OPTIONAL_FLOATS:
        push(ga)
    push("hp_refill_key_code")
    for kn in (
        "reload_nobullet_threshold",
        "reload_threshold",
        "reload_bullet_threshold",
        "reload_vault_threshold",
        "reload_ammo_count",
    ):
        push(kn)
    for kn in CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS:
        push(kn)
    push("ammo_restock_threshold")
    for kn in CONFIG_CALL_MERC_THRESHOLD_KEYS:
        push(kn)
    push("ammo_restock_toggle_key_code")
    for _, gv in CONFIG_LOAD_TEMPLATE_IMAGE_PATHS:
        push(gv)
    for _, gv in CONFIG_LOAD_IMAGE_DATA_PRESENCE:
        push(gv)
    for kn in (
        "merc_fire_enabled",
        "merc_fire_key_code",
        "merc_fire_random_min_ms",
        "merc_fire_random_max_ms",
        "merc_fire_interval_use_seconds",
    ):
        push(kn)
    for kn in CONFIG_SAVE_LEFTCLICK_FIELDS:
        push(kn)
    for kn in (
        "console_log_retention_minutes",
        "console_log_retention_seconds",
        "console_log_time_display_mode",
        "console_log_max_lines",
        "region_preview_overlay_saved_kind",
        "pipela_ui_font_pt",
        "kill_counter_panel_w",
        "control_panel_w",
        "settings_sequence_autoscroll_steps",
    ):
        push(kn)
    return tuple(out)


REGISTRY_CONFIG_SNAPSHOT_KEYS: tuple[str, ...] = _build_registry_config_snapshot_keys()
