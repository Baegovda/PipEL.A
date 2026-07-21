"""AGENT: lightweight app state container for phased `main.py` migration."""

from __future__ import annotations

from dataclasses import dataclass, fields
from threading import RLock
from typing import Any


@dataclass
class InputState:
    left_click_feature_enabled: bool
    left_click_active: bool
    left_pressed: bool
    right_hold_active: bool
    left_click_id: int
    flame_trigger_active: bool
    reload_active: bool
    ammo_restock_active: bool
    reload_nobullet_arm_until_mono: float
    ammo_restock_toggle_key_code: int
    flame_trigger_start_time: float
    flame_trigger_press_text_until: float
    flame_trigger_press_key_name: str
    flame_trigger_press_count: int
    flame_trigger_last_press_interval_sec: float
    flame_trigger_prev_press_timestamp: Any
    flame_trigger_hud_session_start_time: float
    flame_trigger_session_reload_count: int
    flame_trigger_last_reload_complete_time: float
    flame_trigger_last_reload_trigger_time: float
    flame_trigger_reload_teardown_preserve_hud: bool
    hp_refill_detection_score: float
    hp_refill_trigger_total: int


@dataclass
class WorkerRuntimeState:
    running: bool
    target_hwnd: Any
    select_mode: bool
    nobullet_detected: bool
    last_nobullet_time: float
    nobullet_detection_score: float
    bullet_detection_score: float
    vault_detection_score: float
    reload_success_count: int
    reload_ammo_count: int
    ammo_restock_loop_count: int
    ammo_restock_buybutton_score: float
    ammo_restock_inven_score: float
    ammo_restock_bank_score: float
    ammo_restock_sequence_busy: bool
    call_merc_sequence_busy: bool
    call_merc_1_score: float
    call_merc_2_score: float
    call_merc_3_score: float
    call_merc_4_score: float
    call_merc_loop_count: int
    start_game_launcher_score: float
    start_game_intro_skip_score: float
    start_game_accept_score: float
    start_game_launcher_loop_count: int


@dataclass
class KillCounterState:
    kill_counter_enabled: bool
    kill_counter_detect_region: Any
    kill_counter_last_progress: str
    kill_counter_last_poll_ts: float
    kill_counter_last_poll_phase: Any
    kill_counter_last_poll_detail: Any
    kill_counter_session_baseline_n1: Any
    kill_counter_session_last_n1: Any
    kill_counter_session_carried_kills: int
    kill_counter_loop_count: int
    _kill_counter_last_change_probe_bgr: Any


@dataclass
class AppState:
    input: InputState
    worker: WorkerRuntimeState
    kill_counter: KillCounterState

    def __post_init__(self) -> None:
        self._lock = RLock()
        self._index: dict[str, tuple[object, str]] = {}
        for grp in (self.input, self.worker, self.kill_counter):
            for f in fields(grp):
                self._index[f.name] = (grp, f.name)

    def has(self, key: str) -> bool:
        return key in self._index

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key not in self._index:
                return default
            obj, attr = self._index[key]
            return getattr(obj, attr)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key not in self._index:
                return
            obj, attr = self._index[key]
            setattr(obj, attr, value)

