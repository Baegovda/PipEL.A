"""킬카운터 전용 레지스트리 로드/저장 — 정규화 기본값은 kill_counter_layout."""

from __future__ import annotations

import json
import winreg
from collections.abc import Callable, MutableMapping
from typing import Any

from pipela_core.kill_counter_layout import (
    kill_counter_lap_pause_segments_normalize as _default_pause_segments,
    kill_counter_stat_row_order_normalize as _default_row_order,
)

KILL_COUNTER_OBSOLETE_REGISTRY_KEYS: tuple[str, ...] = (
    "kill_counter_poll_sec",
    "kill_counter_ocr_on_change_only",
)


def load_kill_counter_state(
    key: Any,
    target: MutableMapping[str, Any],
    normalize_row_order: Callable[[Any], list] | None = None,
    normalize_pause_segments: Callable[[Any], list] | None = None,
) -> None:
    row_fn = normalize_row_order or _default_row_order
    pause_fn = normalize_pause_segments or _default_pause_segments
    try:
        _kc_row_raw = winreg.QueryValueEx(key, "kill_counter_stats_row_order")[0]
        if _kc_row_raw:
            target["kill_counter_stats_row_order"] = row_fn(
                json.loads(_kc_row_raw),
            )
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        pass
    try:
        _mts = winreg.QueryValueEx(key, "kill_counter_lap_start_ts")[0]
        _mts = (_mts or "").strip()
        if _mts:
            target["kill_counter_lap_start_ts"] = float(_mts)
        else:
            target["kill_counter_lap_start_ts"] = None
    except (FileNotFoundError, ValueError, TypeError):
        pass
    if target.get("kill_counter_lap_start_ts") is None:
        try:
            _mts = winreg.QueryValueEx(key, "kill_counter_manual_track_start_ts")[0]
            _mts = (_mts or "").strip()
            if _mts:
                target["kill_counter_lap_start_ts"] = float(_mts)
        except (FileNotFoundError, ValueError, TypeError):
            pass
    target["kill_counter_lap_pause_segments"] = []
    try:
        _raw_seg = winreg.QueryValueEx(key, "kill_counter_lap_pause_segments")[0]
        _raw_seg = (_raw_seg or "").strip()
        if _raw_seg:
            target["kill_counter_lap_pause_segments"] = pause_fn(
                json.loads(_raw_seg),
            )
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        pass
    if target.get("kill_counter_lap_start_ts") is None:
        target["kill_counter_lap_pause_segments"] = []


def save_kill_counter_state(
    key: Any,
    gsave: MutableMapping[str, Any],
    normalize_row_order: Callable[[Any], list] | None = None,
) -> None:
    row_fn = normalize_row_order or _default_row_order
    for _kc_obsolete in KILL_COUNTER_OBSOLETE_REGISTRY_KEYS:
        try:
            winreg.DeleteValue(key, _kc_obsolete)
        except FileNotFoundError:
            pass
        except OSError:
            pass
    _kc_ord = row_fn(gsave["kill_counter_stats_row_order"])
    gsave["kill_counter_stats_row_order"] = _kc_ord
    winreg.SetValueEx(
        key,
        "kill_counter_stats_row_order",
        0,
        winreg.REG_SZ,
        json.dumps(_kc_ord, ensure_ascii=False),
    )
    if gsave["kill_counter_lap_start_ts"] is not None:
        winreg.SetValueEx(
            key,
            "kill_counter_lap_start_ts",
            0,
            winreg.REG_SZ,
            str(float(gsave["kill_counter_lap_start_ts"])),
        )
        winreg.SetValueEx(
            key,
            "kill_counter_lap_pause_segments",
            0,
            winreg.REG_SZ,
            json.dumps(gsave["kill_counter_lap_pause_segments"], ensure_ascii=False),
        )
    else:
        try:
            winreg.DeleteValue(key, "kill_counter_lap_start_ts")
        except FileNotFoundError:
            pass
        except OSError:
            pass
        gsave["kill_counter_lap_pause_segments"] = []
        try:
            winreg.DeleteValue(key, "kill_counter_lap_pause_segments")
        except FileNotFoundError:
            pass
        except OSError:
            pass
    try:
        winreg.DeleteValue(key, "kill_counter_manual_track_start_ts")
    except FileNotFoundError:
        pass
    except OSError:
        pass
