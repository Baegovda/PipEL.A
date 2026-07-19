"""load_config / save_config 잔여 레지스트리 입출력 — target Mapping 기준."""

from __future__ import annotations

import json
import winreg
from collections.abc import MutableMapping
from typing import Any

from pipela_core.config_parse import clamp_match_threshold_01, reg_parse_bool
from pipela_core.console_log_constants import (
    console_log_retention_split_total,
    console_log_retention_total_sec,
)
from pipela_core.config_registry_query import try_query_float, try_query_int
from pipela_core.config_registry_tables import (
    CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS,
    CONFIG_CALL_MERC_THRESHOLD_KEYS,
)


def registry_load_bool(
    key: Any,
    target: MutableMapping[str, Any],
    reg_key: str,
    global_name: str,
    default: bool,
) -> None:
    try:
        target[global_name] = reg_parse_bool(winreg.QueryValueEx(key, reg_key)[0])
    except (FileNotFoundError, ValueError, TypeError):
        target[global_name] = default


def apply_optional_float_pairs(
    key: Any,
    target: MutableMapping[str, Any],
    pairs: tuple[tuple[str, str], ...],
) -> None:
    for reg_key, global_name in pairs:
        v = try_query_float(key, reg_key)
        if v is not None:
            target[global_name] = v


def apply_try_set_int(
    key: Any,
    target: MutableMapping[str, Any],
    reg_key: str,
    global_name: str,
) -> None:
    v = try_query_int(key, reg_key)
    if v is not None:
        target[global_name] = v


def load_float_legacy(
    key: Any,
    target: MutableMapping[str, Any],
    primary: str,
    global_name: str,
    default: float,
    legacy: str | None = None,
) -> None:
    try:
        target[global_name] = float(winreg.QueryValueEx(key, primary)[0])
    except (FileNotFoundError, ValueError, TypeError):
        if legacy:
            try:
                target[global_name] = float(winreg.QueryValueEx(key, legacy)[0])
            except (FileNotFoundError, ValueError, TypeError):
                target[global_name] = default
        else:
            target[global_name] = default


def load_int_legacy(
    key: Any,
    target: MutableMapping[str, Any],
    primary: str,
    global_name: str,
    default: int,
    legacy: str | None = None,
) -> None:
    try:
        target[global_name] = int(winreg.QueryValueEx(key, primary)[0])
    except (FileNotFoundError, ValueError, TypeError):
        if legacy:
            try:
                target[global_name] = int(winreg.QueryValueEx(key, legacy)[0])
            except (FileNotFoundError, ValueError, TypeError):
                target[global_name] = default
        else:
            target[global_name] = default


def load_merc_fire_enabled(key: Any, target: MutableMapping[str, Any]) -> None:
    try:
        target["merc_fire_enabled"] = reg_parse_bool(winreg.QueryValueEx(key, "merc_fire_enabled")[0])
    except (FileNotFoundError, ValueError, TypeError):
        try:
            target["merc_fire_enabled"] = reg_parse_bool(
                winreg.QueryValueEx(key, "flame_trigger_key_enabled")[0],
            )
        except (FileNotFoundError, ValueError, TypeError):
            target["merc_fire_enabled"] = True


def load_reload_threshold_pack(key: Any, target: MutableMapping[str, Any]) -> None:
    try:
        target["reload_nobullet_threshold"] = float(winreg.QueryValueEx(key, "reload_nobullet_threshold")[0])
    except (FileNotFoundError, ValueError):
        try:
            target["reload_nobullet_threshold"] = float(winreg.QueryValueEx(key, "reload_threshold")[0])
        except (FileNotFoundError, ValueError):
            target["reload_nobullet_threshold"] = 0.6
    target["reload_threshold"] = target["reload_nobullet_threshold"]
    try:
        target["reload_bullet_threshold"] = float(winreg.QueryValueEx(key, "reload_bullet_threshold")[0])
    except (FileNotFoundError, ValueError):
        target["reload_bullet_threshold"] = target["reload_nobullet_threshold"]
    try:
        target["reload_vault_threshold"] = float(winreg.QueryValueEx(key, "reload_vault_threshold")[0])
    except (FileNotFoundError, ValueError):
        try:
            target["reload_vault_threshold"] = float(winreg.QueryValueEx(key, "reload_bullet_miss_threshold")[0])
        except (FileNotFoundError, ValueError):
            target["reload_vault_threshold"] = target["reload_nobullet_threshold"]


def load_reload_ammo_count_clamped(key: Any, target: MutableMapping[str, Any]) -> None:
    try:
        n = int(winreg.QueryValueEx(key, "reload_ammo_count")[0])
        if n < 1:
            n = 1
        elif n > 99999:
            n = 99999
        target["reload_ammo_count"] = n
    except (FileNotFoundError, ValueError):
        pass


def load_ammo_toggle_key_masked(key: Any, target: MutableMapping[str, Any]) -> None:
    try:
        target["ammo_restock_toggle_key_code"] = int(winreg.QueryValueEx(key, "ammo_restock_toggle_key_code")[0]) & 0xFF
    except (FileNotFoundError, ValueError):
        try:
            target["ammo_restock_toggle_key_code"] = int(
                winreg.QueryValueEx(key, "ammo_restock_start_key_code")[0],
            ) & 0xFF
        except (FileNotFoundError, ValueError):
            pass


def load_left_click_timing(key: Any, target: MutableMapping[str, Any]) -> None:
    """left_click_interval_ms(레거시 sec), hold_sec, random min/max — 기존 순서·클램프 유지."""
    try:
        target["left_click_interval_ms"] = float(winreg.QueryValueEx(key, "left_click_interval_ms")[0])
    except (FileNotFoundError, ValueError):
        try:
            sec = float(winreg.QueryValueEx(key, "left_click_interval_sec")[0])
            target["left_click_interval_ms"] = sec * 1000.0
        except (FileNotFoundError, ValueError):
            target["left_click_interval_ms"] = 100.0
    target["left_click_interval_ms"] = max(10.0, min(5000.0, float(target["left_click_interval_ms"])))
    try:
        target["left_click_hold_sec"] = float(winreg.QueryValueEx(key, "left_click_hold_sec")[0])
    except (FileNotFoundError, ValueError):
        pass
    target["left_click_hold_sec"] = max(0.02, min(2.0, float(target["left_click_hold_sec"])))
    registry_load_bool(
        key, target, "left_click_random_enabled", "left_click_random_enabled", False,
    )
    lim = float(target["left_click_interval_ms"])
    try:
        target["left_click_random_min_ms"] = float(winreg.QueryValueEx(key, "left_click_random_min_ms")[0])
    except (FileNotFoundError, ValueError):
        target["left_click_random_min_ms"] = lim
    try:
        target["left_click_random_max_ms"] = float(winreg.QueryValueEx(key, "left_click_random_max_ms")[0])
    except (FileNotFoundError, ValueError):
        target["left_click_random_max_ms"] = lim
    target["left_click_random_min_ms"] = max(10.0, min(5000.0, float(target["left_click_random_min_ms"])))
    target["left_click_random_max_ms"] = max(10.0, min(5000.0, float(target["left_click_random_max_ms"])))


def load_ammo_restock_thresholds(key: Any, target: MutableMapping[str, Any]) -> None:
    """이미지별 ammo 매칭 임계값; 누락 시 레거시 ammo_restock_threshold(0.1~1)."""
    _ar_legacy = 0.6
    try:
        _ar_legacy = clamp_match_threshold_01(
            float(winreg.QueryValueEx(key, "ammo_restock_threshold")[0]),
        )
    except (FileNotFoundError, ValueError):
        pass
    target["ammo_restock_threshold"] = _ar_legacy
    for _k in CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS:
        try:
            _v = clamp_match_threshold_01(float(winreg.QueryValueEx(key, _k)[0]))
        except (FileNotFoundError, ValueError):
            _v = _ar_legacy
        target[_k] = _v
    target["ammo_restock_threshold"] = target["ammo_restock_buybutton_threshold"]


def save_ammo_restock_thresholds(key: Any, gsave: MutableMapping[str, Any]) -> None:
    for _tn in CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS:
        winreg.SetValueEx(key, _tn, 0, winreg.REG_SZ, str(gsave[_tn]))
    winreg.SetValueEx(
        key,
        "ammo_restock_threshold",
        0,
        winreg.REG_SZ,
        str(gsave["ammo_restock_buybutton_threshold"]),
    )


def load_call_merc_thresholds(key: Any, target: MutableMapping[str, Any]) -> None:
    _def = 0.6
    for _k in CONFIG_CALL_MERC_THRESHOLD_KEYS:
        try:
            target[_k] = clamp_match_threshold_01(float(winreg.QueryValueEx(key, _k)[0]))
        except (FileNotFoundError, ValueError):
            target[_k] = _def


def save_call_merc_thresholds(key: Any, gsave: MutableMapping[str, Any]) -> None:
    for _tn in CONFIG_CALL_MERC_THRESHOLD_KEYS:
        winreg.SetValueEx(key, _tn, 0, winreg.REG_SZ, str(gsave[_tn]))


def load_console_ui_region_preview(
    key: Any,
    target: MutableMapping[str, Any],
    retention_min_min: int,
    retention_max_min: int,
    time_mode_absolute: str,
    time_mode_relative: str,
    region_preview_persist_valid: frozenset,
) -> None:
    try:
        _cr_log = int(float(winreg.QueryValueEx(key, "console_log_retention_minutes")[0]))
    except (FileNotFoundError, ValueError):
        _cr_log = target["console_log_retention_minutes"]
    target["console_log_retention_minutes"] = max(
        retention_min_min,
        min(retention_max_min, _cr_log),
    )
    try:
        _cr_sec = int(float(winreg.QueryValueEx(key, "console_log_retention_seconds")[0]))
    except (FileNotFoundError, ValueError):
        _cr_sec = int(target.get("console_log_retention_seconds", 0))
    _cr_sec = max(0, min(59, _cr_sec))
    target["console_log_retention_seconds"] = _cr_sec
    _total = console_log_retention_total_sec(
        int(target["console_log_retention_minutes"]),
        int(target["console_log_retention_seconds"]),
    )
    _m, _s = console_log_retention_split_total(_total)
    target["console_log_retention_minutes"] = _m
    target["console_log_retention_seconds"] = _s
    try:
        _tm = winreg.QueryValueEx(key, "console_log_time_display_mode")[0].strip().lower()
        if _tm in (time_mode_absolute, time_mode_relative):
            target["console_log_time_display_mode"] = _tm
    except (FileNotFoundError, ValueError):
        pass
    try:
        _rpk = winreg.QueryValueEx(key, "region_preview_overlay_kind")[0]
        _rpk = (_rpk or "").strip().lower()
        if _rpk in region_preview_persist_valid:
            target["region_preview_overlay_saved_kind"] = _rpk
        else:
            target["region_preview_overlay_saved_kind"] = None
    except (FileNotFoundError, ValueError, TypeError):
        pass


def save_console_ui_region_preview(
    key: Any,
    gsave: MutableMapping[str, Any],
    retention_min_min: int,
    retention_max_min: int,
    time_mode_absolute: str,
    time_mode_relative: str,
    region_preview_persist_valid: frozenset,
) -> None:
    _m_raw = max(
        retention_min_min,
        min(retention_max_min, int(gsave["console_log_retention_minutes"])),
    )
    _s_raw = max(0, min(59, int(gsave.get("console_log_retention_seconds", 0))))
    _total = console_log_retention_total_sec(_m_raw, _s_raw)
    _m, _s = console_log_retention_split_total(_total)
    gsave["console_log_retention_minutes"] = _m
    gsave["console_log_retention_seconds"] = _s
    winreg.SetValueEx(key, "console_log_retention_minutes", 0, winreg.REG_SZ, str(_m))
    winreg.SetValueEx(key, "console_log_retention_seconds", 0, winreg.REG_SZ, str(_s))
    _tm = gsave["console_log_time_display_mode"]
    if _tm not in (time_mode_absolute, time_mode_relative):
        _tm = time_mode_absolute
    gsave["console_log_time_display_mode"] = _tm
    winreg.SetValueEx(key, "console_log_time_display_mode", 0, winreg.REG_SZ, _tm)
    _rpk = gsave["region_preview_overlay_saved_kind"]
    if _rpk in region_preview_persist_valid:
        winreg.SetValueEx(key, "region_preview_overlay_kind", 0, winreg.REG_SZ, str(_rpk))
    else:
        try:
            winreg.DeleteValue(key, "region_preview_overlay_kind")
        except FileNotFoundError:
            pass
        except Exception:
            pass


def load_settings_sequence_autoscroll_json(
    key: Any,
    target: MutableMapping[str, Any],
    valid_feats: frozenset[str],
) -> None:
    """백그라운드 시퀀스 단계 → 설정 패널 자동 스크롤 동기(dict)."""
    d = target.get("settings_sequence_autoscroll_steps")
    if not isinstance(d, dict):
        d = {}
        target["settings_sequence_autoscroll_steps"] = d
    try:
        raw = winreg.QueryValueEx(key, "settings_sequence_autoscroll_json")[0]
        s = (raw if isinstance(raw, str) else str(raw)).strip()
        if not s:
            return
        obj = json.loads(s)
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            sk = str(k).strip()
            if sk not in valid_feats:
                continue
            try:
                iv = int(v)
            except (TypeError, ValueError):
                continue
            d[sk] = max(0, min(32, iv))
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, TypeError, ValueError, OSError):
        pass


def save_settings_sequence_autoscroll_json(
    key: Any,
    gsave: MutableMapping[str, Any],
    valid_feats: frozenset[str],
) -> None:
    raw_d = gsave.get("settings_sequence_autoscroll_steps")
    if not isinstance(raw_d, dict):
        raw_d = {}
    out: dict[str, int] = {}
    for fk in valid_feats:
        if fk not in raw_d:
            continue
        try:
            out[fk] = max(0, min(32, int(raw_d[fk])))
        except (TypeError, ValueError):
            pass
    if out:
        winreg.SetValueEx(
            key,
            "settings_sequence_autoscroll_json",
            0,
            winreg.REG_SZ,
            json.dumps(out, ensure_ascii=False, sort_keys=True),
        )
    else:
        try:
            winreg.DeleteValue(key, "settings_sequence_autoscroll_json")
        except FileNotFoundError:
            pass
        except OSError:
            pass
