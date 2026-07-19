import sys
import builtins

# AGENT: kernprof/line_profiler expects ``@profile`` on builtins; identity when not under kernprof.
if not hasattr(builtins, "profile"):
    builtins.profile = lambda f: f

import ctypes
import threading
import time
import random
import math
import atexit
import types

from pipela_core.display_timing import (
    display_aligned_wall_ms,
    display_refresh_hz,
    display_tick_ms,
)
from pipela_core.console_log_constants import (
    CONSOLE_LOG_RETENTION_MAX_MIN,
    CONSOLE_LOG_RETENTION_MIN_MIN,
    CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    CONSOLE_LOG_TIME_MODE_RELATIVE,
)
from pipela_core.kill_counter_layout import (
    KILL_COUNTER_STAT_ROW_KEYS_DEFAULT,
    kill_counter_stat_row_order_normalize as _kill_counter_stat_row_order_normalize,
)
from pipela_core.kill_counter_tier_data import get_kill_counter_rank_table_rows
from pipela_core.primary_monitor import primary_monitor_dict, scale_ratio_from_monitor_height
from pipela_core.region_dispatch import (
    CAPTURE_KIND_TO_REGION_TYPE as _CAPTURE_KIND_TO_REGION_TYPE,
    REGION_PREVIEW_PERSIST_VALID as _REGION_PREVIEW_PERSIST_VALID,
    REGION_TYPES_CLEAR_MATCH_ROI as _REGION_TYPES_CLEAR_MATCH_ROI,
    REGION_TYPE_TO_GLOBAL_NAME as _REGION_TYPE_TO_GLOBAL_NAME,
    REGION_TYPE_UI_LABEL_PAIR as _REGION_TYPE_UI_LABEL_PAIR,
)
from pipela_core.scale_geometry import BASE_HEIGHT, get_region_pixels, get_scale_ratio
from pipela_core.telemetry_metrics import (
    telemetry_kc_frame,
    telemetry_record_ocr_sec,
    telemetry_start_periodic_emitter,
)
from pipela_core.app_state import AppState, InputState, KillCounterState, WorkerRuntimeState
from pipela_core.input_keymap import pynput_key_to_vk as _pynput_key_to_vk
from pipela_qt.dev_ui_mode import pipela_dev_ui_enabled
from pipela_core.profile_bootstrap import (
    pipela_profile_agent_cli_or_env_enabled as _pipela_profile_agent_cli_or_env_enabled,
    pipela_strip_profile_agent_argv as _pipela_strip_profile_agent_argv,
    pipela_subprocess_pyspy_or_exit as _pipela_subprocess_pyspy_or_exit,
    pipela_subprocess_scalene_or_exit as _pipela_subprocess_scalene_or_exit,
    pipela_tracemalloc_start_maybe as _pipela_tracemalloc_start_maybe,
    pipela_tracemalloc_dump_maybe as _pipela_tracemalloc_dump_maybe,
    pipela_write_agent_cprofile_handoff as _pipela_write_agent_cprofile_handoff,
)
from pipela_core.ui_fonts import FONT_UI, FONT_UI_KO, FONT_UI_MONO
from pipela_core.win32_input_constants import (
    KEYEVENTF_EXTENDEDKEY,
    KEYEVENTF_KEYUP,
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
    VK_0,
    VK_1,
    VK_2,
    VK_3,
    VK_4,
    VK_5,
    VK_6,
    VK_7,
    VK_8,
    VK_9,
    VK_CAPITAL,
    VK_RETURN,
    VK_Z,
    VK_TO_KEY_NAME,
    vk_to_display_name,
)

# AGENT: defer daemon threads + global hooks until after first UI paint (startup feel).
PIPELA_BACKGROUND_START_DELAY_MS = 50
# AGENT: extra delay before pystray import/thread (reduces startup spike).
PIPELA_TRAY_ICON_DELAY_MS = 1200
try:
    import pystray  # noqa: F401
    PIPELA_TRAY_AVAILABLE = True
except ImportError:
    PIPELA_TRAY_AVAILABLE = False

import ssl
import subprocess
import tempfile
import urllib.error
import urllib.request
import webbrowser
import os
import shutil
import json
import base64
import io
import re
import queue
import collections
import datetime
from contextlib import contextmanager
import win32gui
import winreg
from pynput import mouse, keyboard
from PIL import Image, ImageDraw, ImageFont

# AGENT: session-relative console timestamps; see pipela_core.console_log_prefix + Qt control.
pipela_app_start_monotonic = time.monotonic()

# AGENT: lazy-load cv2/numpy/mss after first GUI frame (import cost).
cv2 = None
np = None
mss = None


def _ensure_cv2_numpy_mss():
    """AGENT: sync lazy cv2/np/mss into main globals via `pipela_core.vision_lazy`."""
    global cv2, np, mss
    if cv2 is not None:
        return
    from pipela_core.vision_lazy import ensure_cv2_numpy_mss as _vl_ensure

    cv2, np, mss = _vl_ensure()


# AGENT: state globals
left_click_feature_enabled = True  # AGENT: master switch LeftClick; OFF blocks hold-to-arm
left_click_active = False
# AGENT: control window + overlay layout tick; same cadence as display_tick_ms().
# AGENT: z-order sync throttle — too many SetWindowPos = cost; too few = visible jank.
CONTROL_Z_SYNC_MIN_INTERVAL_SEC = 0.05
# AGENT: layout tick multiplier vs refresh hz when tracking game (2 => ~2x; interval base//2 ms).
CONTROL_GUI_LAYOUT_FOLLOW_TICK_DIVISOR = 2
# AGENT: reapply taskbar-hide Win32 style on interval only (per-layout = main-thread jank).
CONTROL_TASKBAR_EXSTYLE_REAPPLY_SEC = 1.25


def control_gui_update_ms() -> int:
    return display_tick_ms()


def control_gui_widgets_update_ms() -> int:
    return display_tick_ms()
# AGENT: P1: DPI query TTL (sec) for resolution label.
NATIVE_DPI_CACHE_TTL_SEC = 5.0
# AGENT: P2: skip canvas redraw if set_colors/set_rest unchanged; kill panel scroll: one update_idletasks.
# AGENT: power-save: after game was seen, if client missing for this many sec -> low-duty sleep.
GAME_CLIENT_EXIT_GRACE_SEC = 1.0
_game_client_power_save_active = False
GAME_CLIENT_POWER_SAVE_LAYOUT_MS = 2500
GAME_CLIENT_POWER_SAVE_WIDGET_MS = 2000
GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC = 2.5
GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC = 0.3


def pipela_overlay_tick_ms() -> int:
    """오버레이 geometry 폴링 — 절전 시 간격 확대."""
    if _game_client_power_save_active:
        return int(GAME_CLIENT_POWER_SAVE_LAYOUT_MS)
    return int(control_gui_update_ms())


def pipela_kill_counter_overlay_poll_ms() -> int:
    if _game_client_power_save_active:
        return int(GAME_CLIENT_POWER_SAVE_WIDGET_MS)
    return int(display_tick_ms())


# AGENT: auto-click inter-click wait (ms); synthetic-ignore window inside mouse_click: MOUSE_CLICK_IGNORE_SEC.
left_click_interval_ms = 100.0
# AGENT: LeftClick ON: min left-hold duration (sec); shorter = faster but more false triggers.
left_click_hold_sec = 0.15
# AGENT: when user OFF overlaps auto-click (ignore_left), delay before reading physical button after synth.
LEFT_CLICK_OFF_ARM_DELAY_SEC = 0.025
# AGENT: pynput ignore window for synthetic clicks during mouse_click (sec); shorter = snappier OFF.
MOUSE_CLICK_IGNORE_SEC = 0.004
# AGENT: same window for synthetic RMB — else pynput delivers RIGHTDOWN after ignore clears and toggles RightHold.
MOUSE_RIGHT_IGNORE_SEC = MOUSE_CLICK_IGNORE_SEC
left_click_random_enabled = False  # AGENT: if True uniform random interval min..max ms
left_click_random_min_ms = 100.0
left_click_random_max_ms = 100.0
right_hold_feature_enabled = True  # AGENT: master switch RightHold
right_hold_active = False
flame_trigger_feature_enabled = True  # AGENT: master switch Flame Trigger
flame_trigger_active = False
flame_trigger_start_time = 0  # AGENT: FT start time.time() anchor
merc_fire_enabled = True  # AGENT: Merc Fire key-spam sub-feature default ON
merc_fire_key_code = VK_1
merc_fire_random_min_ms = 500.0
merc_fire_random_max_ms = 1500.0
merc_fire_interval_use_seconds = True  # UI는 초만 사용; 스냅샷·호환용
flame_trigger_press_text_until = 0.0  # AGENT: HUD "Press N" hide after monotonic/ts
flame_trigger_press_key_name = "1"    # AGENT: last key label for HUD
flame_trigger_press_count = 0         # AGENT: press counter for HUD
flame_trigger_last_press_interval_sec = 0.0  # AGENT: delta between presses (sec)
flame_trigger_prev_press_timestamp = None    # AGENT: internal last key ts
# AGENT: Flame HUD — reload successes this FT session; nobullet→리로드 발동 시각(HUD 경과); 완료 시각(보조)
flame_trigger_hud_session_start_time = 0.0
flame_trigger_session_reload_count = 0
flame_trigger_last_reload_trigger_time = 0.0
flame_trigger_last_reload_complete_time = 0.0
# AGENT: 리로드로 FT 잠깐 OFF 될 때 teardown 이 HUD 리셋하지 않게
flame_trigger_reload_teardown_preserve_hud = False


def _format_flame_trigger_runtime_hms(elapsed: float) -> str:
    """Flame Trigger 경과 시간 — `pipela_qt.cursor_hud` HUD 표시용."""
    t = int(max(0.0, float(elapsed)))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_flame_overlay_sec(sec: float) -> str:
    """초 값 짧은 문자열 — FT HUD의 Merc Fire 간격 표시(`cursor_hud`)."""
    v = max(0.0, float(sec))
    if v >= 100.0:
        return f"{v:.0f}"
    if v >= 10.0:
        return f"{v:.1f}"
    t = f"{v:.2f}"
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t


reload_active = True  # AGENT: default ON
ammo_restock_active = False
ammo_restock_threshold = 0.6  # AGENT: legacy; keep in sync with buybutton
ammo_restock_buybutton_threshold = 0.6
ammo_restock_inven_threshold = 0.6
ammo_restock_bank_threshold = 0.6
ammo_restock_buybutton_score = 0.0
ammo_restock_inven_score = 0.0
ammo_restock_bank_score = 0.0
ammo_restock_sequence_busy = False  # AGENT: buy→inven→bank in flight; FT input paused
call_merc_active = False  # AGENT: like Reload L-click toggle; ON watches;① drops FT until cycle end
call_merc_sequence_busy = False  # AGENT: steps ②~④ in flight (GUI busy like reload)
call_merc_restore_ft_after_cycle = False  # AGENT: restore FT after cycle only if was ON before①
# AGENT: slot① score — same gate as reload nobullet; if >= threshold start ②③④ sequence.
call_merc_1_threshold = 0.6
call_merc_2_threshold = 0.6
call_merc_3_threshold = 0.6
call_merc_4_threshold = 0.6
call_merc_1_score = 0.0
call_merc_2_score = 0.0
call_merc_3_score = 0.0
call_merc_4_score = 0.0
running = True
# AGENT: Qt dock phase: "standby"|"launcher"|"client" (pipela_qt.dock_ui_phase); runtime only, not registry.
pipela_ui_dock_phase = "standby"
mouse_listener = None
keyboard_listener = None
_pipela_background_loops_started = False
_start_game_launcher_loop_thread_started = False
# AGENT: terminal log line retention (min); older lines pruned periodically.
pipela_ui_font_pt = 11  # AGENT: Qt root font pt clamp 8..24
# AGENT: 킬 카운터 floater 폭(논리 px); 0 = 미설정 → `get_dock_panel_wh` 폴백.
kill_counter_panel_w = 0
# AGENT: 제어 창 폭(논리 px); 0 = 미설정 → `get_dock_panel_wh` 폴백.
control_panel_w = 0
console_log_retention_minutes = 30
console_log_retention_seconds = 0  # 분에 더해지는 초(0~59); 합산 보존 시간
# AGENT: console time mode: absolute vs relative (updated every 1s for relative).
# AGENT: CONSOLE_LOG_* lives in pipela_core.console_log_constants
console_log_time_display_mode = CONSOLE_LOG_TIME_MODE_ABSOLUTE
target_hwnd = None
# AGENT: if True, center Eternal City window in monitor rcWork periodically (not during region select).
game_window_center_on_detect_enabled = True
_GAME_CENTER_THROTTLE_SEC = 0.72
_game_center_throttle_next_mono = 0.0
_last_centered_target_game_hwnd: int | None = None
_smart_updater_hwnd_cache = None  # AGENT: launcher HWND cache for START template
# AGENT: skip launcher Enum when game HWND known (avoids Enum storm at ~25Hz refresh).
_smart_updater_poll_skip_until = 0.0
_game_client_was_ever_connected = False
_game_client_disconnect_since = None  # AGENT: ts when client lost (after ever connected)
ignore_left = False
ignore_right = False
image_detected = False
image_score = 0.0  # AGENT: Ride match score GUI
ride_threshold = 0.6  # AGENT: Ride threshold
reload_threshold = 0.6  # AGENT: legacy alias reload_nobullet_threshold
reload_nobullet_threshold = 0.6  # AGENT: nobullet threshold
reload_bullet_threshold = 0.6  # AGENT: bullet threshold
reload_vault_threshold = 0.6  # AGENT: vault threshold when bullet miss
reload_ammo_count = 45  # AGENT: ammo digits sent during reload seq default 45
hp_refill_threshold = 0.6  # AGENT: hp refill threshold
ride_feature_enabled = True  # AGENT: Ride+CapsLock feature
hp_refill_feature_enabled = True  # AGENT: HP refill feature
capslock_state = False
select_mode = False
ride_detect_region = None   # AGENT: Ride ROI
hp_refill_detect_region = None  # AGENT: HP ROI
kill_counter_detect_region = None  # AGENT: KC OCR ROI; None disables
# AGENT: template ROI normalized [x,y,w,h] in client; None = full client.
reload_nobullet_match_region = None
reload_bullet_match_region = None
reload_vault_match_region = None  # AGENT: vault ROI; None skips vault step
ammo_buybutton_match_region = None
ammo_inven_match_region = None
ammo_bank_match_region = None
call_merc_1_match_region = None  # AGENT: call merc① ROI same role as nobullet
call_merc_2_match_region = None
call_merc_3_match_region = None
call_merc_4_match_region = None
left_pressed = False  # AGENT: LMB down state
left_click_id = 0     # AGENT: click generation id
user_left_pending = False  # AGENT: user arming OFF
_left_off_arm_gen = 0  # AGENT: OFF-delay thread generation

# AGENT: reload state
nobullet_detected = False  # AGENT: nobullet latched / job active
last_nobullet_time = -1  # AGENT: last nobullet ts; -1 unset
# AGENT: nobullet 감지 후 ① 재폴링까지 monotonic 쿨다운 — Qt 리로드 버튼 게이지와 동일
RELOAD_NOBULLET_REARM_COOLDOWN_SEC = 10.0
# AGENT: 중간 단계에서 진전 없이 초과 시 시퀀스 취소(워커 monotonic 기준)
RELOAD_SEQUENCE_STUCK_SEC = 3.0
CALL_MERC_SEQUENCE_STUCK_SEC = 5.0
reload_nobullet_arm_until_mono = 0.0
nobullet_detection_score = 0.0  # AGENT: nobullet score GUI
bullet_detection_score = 0.0  # AGENT: bullet score GUI
vault_detection_score = 0.0  # AGENT: vault score GUI
reload_success_count = 0  # AGENT: reload success counter
reload_intermediate_started_mono = 0.0  # AGENT: reload step 1–3·nobullet 래치 stuck 타이머
# AGENT: 설정 패널 시퀀스 자동 스크롤 단계 — 키는 pipela_qt.settings_sequence_autoscroll.FEAT_*
settings_sequence_autoscroll_steps: dict[str, int] = {}

# AGENT: settings "live" probe map: (feature,sub) -> last match-attempt monotonic.
_template_probe_last_mono = {}
_SETTINGS_PROBE_STALE_SEC = 1.5  # AGENT: settings probe TTL for "live" indicator
# AGENT: last successful match patch BGR by kind (Qt panels may read).
_template_last_hit_bgr = {}
_template_last_hit_score: dict[str, float] = {}

# AGENT: ammo restock state
ammo_restock_loop_count = 0  # AGENT: ammo loop counter
# AGENT: hotkey VK toggles ammo-restock detection.
ammo_restock_toggle_key_code = 0x75  # F6

# AGENT: call merc ON: poll① like reload nobullet; restore FT at end only if disabled during①.
call_merc_loop_count = 0
CALL_MERC_ARM_COOLDOWN_SEC = 10.0  # AGENT: cooldown after④ before① re-arm
# AGENT: monotonic deadline for ① re-arm; GUI 쿨 게이지. 0 = 쿨 없음
call_merc_arm_until_mono = 0.0
# AGENT: settings phase arrows sync with call_merc_loop (read on GUI thread).
call_merc_phase_ui = 0  # AGENT: UI phase 0..3 maps steps①..④
call_merc_arrow_pulse_idx = -1  # AGENT: arrow pulse idx; 3=done anim
call_merc_arrow_pulse_mono = 0.0
call_merc_intermediate_started_mono = 0.0  # AGENT: step 1–3 stuck 취소용

# AGENT: hp refill state
hp_refill_detection_score = 0.0  # AGENT: hp score GUI
hp_refill_key_code = VK_Z  # AGENT: key on hit default Z
hp_refill_trigger_total = 0  # AGENT: session hit count

# AGENT: kill counter OCR digits/slash in ROI; run OCR only on pixel change.
kill_counter_enabled = True
# AGENT: capture sample interval (fixed); OCR only when ROI changed vs previous.
_KILL_COUNTER_CHANGE_PROBE_SLEEP_SEC = 0.07
# AGENT: skip OCR if downscaled gray mean abs delta between captures < threshold.
# AGENT: NOTE: old logic compared only last OCR frame + coarse downscale → missed digit-only changes.
_KILL_COUNTER_CHANGE_MEAN_ABS_THRESH = 1.15
_kill_counter_last_change_probe_bgr = None
# AGENT: last good Tesseract config tried first next call (fewer subprocess/PIL writes).
_kill_counter_tesseract_cfg_first: str | None = None
# AGENT: kill stats row order (drag reorder, JSON in registry); keys: pipela_core.kill_counter_layout.
kill_counter_stats_row_order = list(KILL_COUNTER_STAT_ROW_KEYS_DEFAULT)
# AGENT: lap — permanent kill events after lap start ts (None = not started).
kill_counter_lap_start_ts = None
# AGENT: pause intervals [[start,end],...]; end None => still paused.
kill_counter_lap_pause_segments = []
_KILL_COUNTER_LAP_PAUSE_BTN_BG = "#b45309"
_KILL_COUNTER_LAP_PAUSE_BTN_ACTIVE_BG = "#c2410c"
_KILL_COUNTER_LAP_PAUSE_BTN_FG = "#ffffff"
_KILL_COUNTER_LAP_SW_FG_RUNNING = "#e2e8f0"
_KILL_COUNTER_LAP_SW_FG_PAUSED = "#fbbf24"
_KILL_COUNTER_LAP_CELL_OUTLINE = "#3f4a5c"
# AGENT: kill counter tier rows from pipela_core.kill_counter_tier_data (cached).
_kill_counter_rank_table_rows = None
# AGENT: OCR pair n1/n2 — n1 drives session/stats/tiers; n2 compat only.
kill_counter_last_progress = ""  # AGENT: raw OCR string e.g. 3/10
kill_counter_last_poll_ts = 0.0  # AGENT: last capture+OCR ts
# AGENT: last OCR status ok|empty|no_pair|unstable|error; None before first poll.
kill_counter_last_poll_phase = None
kill_counter_last_poll_detail = None  # AGENT: extra status line
# AGENT: tesseract (ok, reason, ts) — reason: None|pytesseract|engine
_kill_counter_tesseract_av_cache = None
# AGENT: panel kill text color matches KC pulse border tone (_kc_pulse_draw_num_red).
KILL_COUNTER_DETECTED_NUM_FG = "#52E6DA"  # AGENT: KC num accent BGR-ish hex
KILL_COUNTER_PANEL_CURRENT_TITLE_FG = "#9fe8ff"  # AGENT: KC section title cyan
# AGENT: session kills = delta of n1 from first detection (sum segments on tier reset).
kill_counter_session_baseline_n1 = None
kill_counter_session_last_n1 = None
kill_counter_session_carried_kills = 0
kill_counter_session_start_ts = None  # AGENT: session display anchor ts
# AGENT: after spike reject, accept if similar n1 repeats this many consecutive ticks.
KILL_COUNTER_SPIKE_CONFIRM_POLLS = 3
kill_counter_spike_confirm_streak = 0
kill_counter_spike_confirm_last_n = None
# AGENT: persistent stats append (ts, count) under %LOCALAPPDATA%\Pipela\kill_counter_stats.json
_kill_counter_stats_lock = threading.RLock()
_kill_counter_stats_loaded = False
_kill_counter_stats_events = []  # [{"t": unix_float, "d": int}, ...]
_kill_counter_stats_reload_marks: list[float] = []  # reload 시퀀스 완료 시각(그래프 봉 표시용)
_kill_counter_stats_daily = {}  # AGENT: local-day -> kill sum
_kill_counter_stats_save_timer = None
# AGENT: ``_kill_counter_graph_bucket_series`` — avoid repeated O(events) work on panel refresh ticks.
_graph_bucket_series_cache_key: object | None = None
_graph_bucket_series_cache_value: list[dict] | None = None
# AGENT: reconcile daily baseline n1 vs persistent events so sum(events) <= n1-start.
kill_counter_reconcile_local_date = None
kill_counter_n1_at_local_day_start = None
# AGENT: KC debug pulse on detect; rect in capture coords (l,t,r,b).
_kill_counter_overlay_queue = queue.Queue()
# AGENT: template debug overlay queue items: (rect, "0.00" score) same coord space.
_template_debug_overlay_queue = queue.Queue()
# AGENT: template pulse fill stipple ~40.6%; rest black for colorkey transparency.
_TEMPLATE_DETECT_OVERLAY_FILL_STIPPLE_XBM = """
#define echtdet40_width 8
#define echtdet40_height 8
static unsigned char echtdet40_bits[] = {
   0xaa, 0x55, 0xaa, 0x55, 0x88, 0x22, 0x88, 0x33
};
"""
# AGENT: flame start banner on real trigger (center RMB hold); worker -> main thread.
_flame_start_banner_queue = queue.Queue(maxsize=8)
_kill_counter_tesseract_cmd_checked = False

# AGENT: phase-3 map — globals grouped for state migration and worker read/write boundaries.
_STATE_DOMAIN_FIELDS = {
    "input_toggle": (
        "left_click_feature_enabled",
        "left_click_active",
        "left_pressed",
        "left_click_id",
        "flame_trigger_active",
        "reload_active",
        "ammo_restock_active",
        "reload_nobullet_arm_until_mono",
        "ammo_restock_toggle_key_code",
        "flame_trigger_start_time",
        "flame_trigger_press_text_until",
        "flame_trigger_press_key_name",
        "flame_trigger_press_count",
        "flame_trigger_last_press_interval_sec",
        "flame_trigger_prev_press_timestamp",
        "flame_trigger_hud_session_start_time",
        "flame_trigger_session_reload_count",
        "flame_trigger_last_reload_complete_time",
        "flame_trigger_last_reload_trigger_time",
        "flame_trigger_reload_teardown_preserve_hud",
    ),
    "worker_runtime": (
        "running",
        "target_hwnd",
        "select_mode",
        "nobullet_detected",
        "last_nobullet_time",
        "nobullet_detection_score",
        "bullet_detection_score",
        "vault_detection_score",
        "reload_success_count",
        "reload_ammo_count",
        "ammo_restock_loop_count",
        "ammo_restock_buybutton_score",
        "ammo_restock_inven_score",
        "ammo_restock_bank_score",
    ),
    "kill_counter": (
        "kill_counter_enabled",
        "kill_counter_detect_region",
        "kill_counter_last_progress",
        "kill_counter_last_poll_ts",
        "kill_counter_last_poll_phase",
        "kill_counter_last_poll_detail",
        "kill_counter_session_baseline_n1",
        "kill_counter_session_last_n1",
        "kill_counter_session_carried_kills",
        "_kill_counter_last_change_probe_bgr",
    ),
}

_STATE_WORKER_RW_MAP = {
    "kill_counter_loop": {
        "reads": (
            "running", "target_hwnd", "kill_counter_enabled", "select_mode", "kill_counter_detect_region",
            "kill_counter_last_poll_phase", "kill_counter_last_progress",
            "kill_counter_session_baseline_n1", "kill_counter_session_last_n1",
        ),
        "writes": (
            "_kill_counter_last_change_probe_bgr", "kill_counter_last_poll_ts",
            "kill_counter_last_progress", "kill_counter_last_poll_phase", "kill_counter_last_poll_detail",
        ),
    },
    "reload_loop": {
        "reads": (
            "running", "target_hwnd", "reload_active", "select_mode",
            "reload_nobullet_arm_until_mono", "reload_ammo_count", "nobullet_detected",
        ),
        "writes": (
            "nobullet_detected", "last_nobullet_time", "reload_nobullet_arm_until_mono",
            "nobullet_detection_score", "bullet_detection_score", "vault_detection_score",
            "reload_success_count",
        ),
    },
    "ammo_restock_loop": {
        "reads": ("running", "target_hwnd", "ammo_restock_active", "select_mode"),
        "writes": (
            "ammo_restock_buybutton_score", "ammo_restock_inven_score",
            "ammo_restock_bank_score", "ammo_restock_loop_count",
        ),
    },
}


def _build_app_state_from_globals() -> AppState:
    g = globals()
    return AppState(
        input=InputState(
            left_click_feature_enabled=bool(g["left_click_feature_enabled"]),
            left_click_active=bool(g["left_click_active"]),
            left_pressed=bool(g["left_pressed"]),
            left_click_id=int(g["left_click_id"]),
            flame_trigger_active=bool(g["flame_trigger_active"]),
            reload_active=bool(g["reload_active"]),
            ammo_restock_active=bool(g["ammo_restock_active"]),
            reload_nobullet_arm_until_mono=float(g["reload_nobullet_arm_until_mono"]),
            ammo_restock_toggle_key_code=int(g["ammo_restock_toggle_key_code"]),
            flame_trigger_start_time=float(g["flame_trigger_start_time"]),
            flame_trigger_press_text_until=float(g["flame_trigger_press_text_until"]),
            flame_trigger_press_key_name=str(g["flame_trigger_press_key_name"]),
            flame_trigger_press_count=int(g["flame_trigger_press_count"]),
            flame_trigger_last_press_interval_sec=float(g["flame_trigger_last_press_interval_sec"]),
            flame_trigger_prev_press_timestamp=g["flame_trigger_prev_press_timestamp"],
            flame_trigger_hud_session_start_time=float(g["flame_trigger_hud_session_start_time"]),
            flame_trigger_session_reload_count=int(g["flame_trigger_session_reload_count"]),
            flame_trigger_last_reload_complete_time=float(g["flame_trigger_last_reload_complete_time"]),
            flame_trigger_last_reload_trigger_time=float(g["flame_trigger_last_reload_trigger_time"]),
            flame_trigger_reload_teardown_preserve_hud=bool(g["flame_trigger_reload_teardown_preserve_hud"]),
        ),
        worker=WorkerRuntimeState(
            running=bool(g["running"]),
            target_hwnd=g["target_hwnd"],
            select_mode=bool(g["select_mode"]),
            nobullet_detected=bool(g["nobullet_detected"]),
            last_nobullet_time=float(g["last_nobullet_time"]),
            nobullet_detection_score=float(g["nobullet_detection_score"]),
            bullet_detection_score=float(g["bullet_detection_score"]),
            vault_detection_score=float(g["vault_detection_score"]),
            reload_success_count=int(g["reload_success_count"]),
            reload_ammo_count=int(g["reload_ammo_count"]),
            ammo_restock_loop_count=int(g["ammo_restock_loop_count"]),
            ammo_restock_buybutton_score=float(g["ammo_restock_buybutton_score"]),
            ammo_restock_inven_score=float(g["ammo_restock_inven_score"]),
            ammo_restock_bank_score=float(g["ammo_restock_bank_score"]),
        ),
        kill_counter=KillCounterState(
            kill_counter_enabled=bool(g["kill_counter_enabled"]),
            kill_counter_detect_region=g["kill_counter_detect_region"],
            kill_counter_last_progress=str(g["kill_counter_last_progress"]),
            kill_counter_last_poll_ts=float(g["kill_counter_last_poll_ts"]),
            kill_counter_last_poll_phase=g["kill_counter_last_poll_phase"],
            kill_counter_last_poll_detail=g["kill_counter_last_poll_detail"],
            kill_counter_session_baseline_n1=g["kill_counter_session_baseline_n1"],
            kill_counter_session_last_n1=g["kill_counter_session_last_n1"],
            kill_counter_session_carried_kills=int(g["kill_counter_session_carried_kills"]),
            _kill_counter_last_change_probe_bgr=g["_kill_counter_last_change_probe_bgr"],
        ),
    )


_APP_STATE = _build_app_state_from_globals()


def _state_gets(key: str, default=None):
    """AGENT: strict AppState getter for migrated keys (no globals fallback)."""
    if _APP_STATE.has(key):
        return _APP_STATE.get(key, default)
    return default


def _state_set(key: str, value):
    g = globals()
    g[key] = value
    if _APP_STATE.has(key):
        _APP_STATE.set(key, value)
    return value


def _state_inc_int(key: str, delta: int = 1) -> int:
    """AGENT: typed int increment helper for migrated state counters."""
    next_value = int(_state_gets(key)) + int(delta)
    _state_set(key, next_value)
    return next_value


def _sync_migrated_state_from_globals() -> None:
    """레지스트리 로드 등으로 globals만 바뀐 뒤 AppState 미러 정렬 (_state_gets 일치)."""
    g = globals()
    for obj in (_APP_STATE.input, _APP_STATE.worker, _APP_STATE.kill_counter):
        for name in obj.__dataclass_fields__:
            if name not in g:
                continue
            _state_set(name, g[name])


# AGENT: paths single source pipela_core.paths (frozen vs dev).
from pipela_core.paths import (
    SCRIPT_DIR,
    PIPELA_TEMPLATES_DIR,
    migrate_legacy_bundle_template_path,
    RIDE_TARGET_IMAGE_PATH,
    RELOAD_NOBULLET_IMAGE_PATH,
    RELOAD_BULLET_IMAGE_PATH,
    RELOAD_VAULT_IMAGE_PATH,
    AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH,
    AMMO_RESTOCK_INVEN_IMAGE_PATH,
    AMMO_RESTOCK_BANK_IMAGE_PATH,
    CALL_MERC_1_IMAGE_PATH,
    CALL_MERC_2_IMAGE_PATH,
    CALL_MERC_3_IMAGE_PATH,
    CALL_MERC_4_IMAGE_PATH,
    START_GAME_IMAGE_PATH,
    START_GAME_INTRO_SKIP_IMAGE_PATH,
    START_GAME_ACCEPT_IMAGE_PATH,
    RIDE_ICON_PATH,
    CURSOR_RIDE_ICON_PATH,
    MOVE_ICON_PATH,
    FIRE_ICON_PATH,
    HP_REFILL_ZKEY_IMAGE_PATH,
    PIPELA_APP_ICON_PATH,
    PIPELA_ICO_PATH,
)
from pipela_core.version_info import (
    PIPELA_APP_DISPLAY_NAME,
    PIPELA_APP_VERSION,
    PIPELA_REINSTALL_DOWNLOAD_URL,
    PIPELA_REINSTALL_EXE_URL,
    PIPELA_STRIP_DISPLAY_VERSION,
    PIPELA_UPDATE_MANIFEST_URL,
)
from pipela_core.config_registry_extended import (
    apply_optional_float_pairs,
    apply_try_set_int,
    load_ammo_restock_thresholds,
    load_ammo_toggle_key_masked,
    load_call_merc_thresholds,
    load_console_ui_region_preview,
    load_float_legacy,
    load_int_legacy,
    load_left_click_timing,
    load_merc_fire_enabled,
    load_reload_ammo_count_clamped,
    load_reload_threshold_pack,
    load_settings_sequence_autoscroll_json,
    registry_load_bool,
    save_call_merc_thresholds,
    save_console_ui_region_preview,
    save_ammo_restock_thresholds,
    save_settings_sequence_autoscroll_json,
)
from pipela_core.config_registry_kill_counter import (
    load_kill_counter_state,
    save_kill_counter_state,
)
from pipela_core.config_registry_load import (
    load_image_data_presence_from_registry,
    load_json_regions_from_registry,
    load_template_image_paths_from_registry,
    migrate_reload_vault_image_data_flag,
    migrate_reload_vault_image_path,
    migrate_reload_vault_match_region,
)
from pipela_core.config_registry_save import (
    delete_registry_values_if_present,
    save_json_region_optional,
    save_merc_fire_fields,
    save_reg_global_pairs,
    save_sz_same_key,
)
from pipela_core.config_registry_tables import (
    CONFIG_LOAD_BOOLS_PRE_KC as _CONFIG_LOAD_BOOLS_PRE_KC,
    CONFIG_LOAD_IMAGE_DATA_PRESENCE as _CONFIG_LOAD_IMAGE_DATA_PRESENCE,
    CONFIG_LOAD_JSON_REGIONS as _CONFIG_LOAD_JSON_REGIONS,
    CONFIG_LOAD_OPTIONAL_FLOATS as _CONFIG_LOAD_OPTIONAL_FLOATS,
    CONFIG_LOAD_TEMPLATE_IMAGE_PATHS as _CONFIG_LOAD_TEMPLATE_IMAGE_PATHS,
    CONFIG_SAVE_BOOLS_FLAME as _CONFIG_SAVE_BOOLS_FLAME,
    CONFIG_SAVE_BOOLS_PRE_KC as _CONFIG_SAVE_BOOLS_PRE_KC,
    CONFIG_SAVE_JSON_REGION_NAMES as _CONFIG_SAVE_JSON_REGION_NAMES,
    CONFIG_SAVE_LEFTCLICK_FIELDS as _CONFIG_SAVE_LEFTCLICK_FIELDS,
    CONFIG_SAVE_SZ_FIELDS as _CONFIG_SAVE_SZ_FIELDS,
    SETTINGS_SEQUENCE_AUTOSCROLL_FEAT_KEYS as _SETTINGS_SEQUENCE_AUTOSCROLL_FEAT_KEYS,
)
from pipela_core.registry_constants import REGISTRY_PATH
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    refresh_registry_config_snapshot,
)
from pipela_core.registry_snapshot_read import snapshot_bool, snapshot_float, snapshot_int
from pipela_core.template_capture_catalog import (
    AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND as _AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND,
    TEMPLATE_CAPTURE_KIND_PATH_BINDING as _TEMPLATE_CAPTURE_KIND_PATH_BINDING,
    get_template_capture_kind_meta as _template_capture_kind_meta,
)
from pipela_core.ammo_restock_catalog import (
    AMMO_BUNDLE_FILENAME_BY_KIND as _AMMO_BUNDLE_FILENAME_BY_KIND,
    AMMO_FILE_DIALOG_TITLE_BY_KIND as _AMMO_FILE_DIALOG_TITLE_BY_KIND,
    AMMO_LOOP_LOG_TAG as _AMMO_LOOP_LOG_TAG,
    AMMO_MATCH_ROI_GLOBAL as _AMMO_MATCH_ROI_GLOBAL,
    AMMO_PATH_GLOBAL_BY_KIND as _AMMO_PATH_GLOBAL_BY_KIND,
    AMMO_PREVIEW_LABEL_ATTR as _AMMO_PREVIEW_LABEL_ATTR,
    AMMO_REGISTRY_DATA_KEY_BY_KIND as _AMMO_REGISTRY_DATA_KEY_BY_KIND,
    AMMO_RESTOCK_KINDS as _AMMO_RESTOCK_KINDS,
    AMMO_SCORE_GLOBAL_BY_KIND as _AMMO_SCORE_GLOBAL_BY_KIND,
    AMMO_SCORE_ROW_BINDINGS as _AMMO_SCORE_ROW_BINDINGS,
    AMMO_SUFFIX_VAR_ATTR as _AMMO_SUFFIX_VAR_ATTR,
    AMMO_THR_GLOBAL_BY_KIND as _AMMO_THR_GLOBAL_BY_KIND,
)
from pipela_core.ammo_restock_templates import ammo_restock_sync_templates
from pipela_core.call_merc_catalog import (
    CALL_MERC_BUNDLE_FN as _CALL_MERC_BUNDLE_FN,
    CALL_MERC_FILE_DLG as _CALL_MERC_FILE_DLG,
    CALL_MERC_KINDS as _CALL_MERC_KINDS,
    CALL_MERC_LOOP_LOG_TAG as _CALL_MERC_LOOP_LOG_TAG,
    CALL_MERC_PATH_KEY as _CALL_MERC_PATH_KEY,
    CALL_MERC_PREVIEW_ATTR_BY_KIND as _CALL_MERC_PREVIEW_BY_KIND,
    CALL_MERC_REG_DATA_KEY as _CALL_MERC_REG_DATA_KEY,
    CALL_MERC_ROI_KEY as _CALL_MERC_ROI_KEY,
    CALL_MERC_SCORE_BINDINGS as _CALL_MERC_SCORE_BINDINGS,
    CALL_MERC_SCORE_KEY as _CALL_MERC_SCORE_KEY,
    CALL_MERC_SUFFIX_ATTR_BY_KIND as _CALL_MERC_SUFFIX_BY_KIND,
    CALL_MERC_THR_KEY as _CALL_MERC_THR_KEY,
)
from pipela_core.call_merc_match import (
    call_merc_match_one_kind as _call_merc_match_one_kind_core,
)
from pipela_core.call_merc_templates import call_merc_try_reload_templates
from pipela_core.flame_trigger_automation import (
    automation_disable_flame_trigger_if_active,
    automation_reenable_flame_trigger_after_success,
)
from pipela_core.client_idle_teardown import apply_no_game_client_session_teardown
from pipela_core.image_registry import (
    load_image_data,
    load_image_data_if_path_changed,
    load_image_from_registry,
    save_image_to_registry,
)
from pipela_core.reload_sequence import (
    reload_clamp_ammo_count,
    reload_match_bullet_on_screen,
    reload_match_vault_on_screen,
    reload_move_sleep_double_click,
    reload_send_digit_keys_and_return,
)
from pipela_core.reload_nobullet_bullet import (
    reload_rescale_nobullet_bullet_if_needed,
    reload_try_reload_nobullet_bullet_templates,
)
from pipela_core.template_capture_region import (
    capture_drag_rect_to_pil_rgb,
    drag_rect_exceeds_min_size,
    normalized_roi_xywh_from_drag_rect,
)
from pipela_core.template_apply import (
    apply_template_capture_png,
    template_capture_load_existing_pil,
    template_capture_output_path_for_kind,
    write_pil_rgb_to_png_cv2,
)
from pipela_core.template_debug_match import (
    debug_sample_template_match as _debug_sample_template_match_core,
)
from pipela_core.template_match_config import template_match_threshold_for_globals
from pipela_core.template_matching import (
    extract_match_patch as _template_extract_match_patch,
    find_image,
    find_image_location,
    match_patch_if_ok as _template_match_patch_if_ok,
    match_template_ccoeff_normed_max as _match_template_ccoeff_normed_max,
    match_template_max_score,
    refresh_scaled_map_if_ratio_changed,
    rescale_if_ratio_changed,
    scale_template,
)
from pipela_core.template_roi import (
    match_center_to_screen_xy as _match_center_to_screen_xy,
    region_roi_from_globals,
    region_roi_set_in_globals,
    template_roi_for_kind as _template_roi_for_kind_impl,
)
from pipela_core.vision_capture import (
    capture_region,
    capture_region_primary_monitor,
    capture_window,
    get_region_pixels_primary_monitor,
)
from pipela_core.win32_game_windows import (
    SMART_UPDATER_TITLE_KO_SUBSTR as START_GAME_SMART_UPDATER_TITLE_SUBSTR,
    find_eternalcity_window,
    find_smart_updater_window,
    get_window_outer_rect_screen,
    get_window_rect,
    get_window_size,
    refresh_eternalcity_hwnd_cached,
    refresh_smart_updater_hwnd_cached,
    smart_updater_title_matches,
)
from pipela_core.win32_window_ops import (
    center_outer_window_on_monitor_work_area as _center_outer_window_on_monitor_work_area,
    ensure_process_dpi_awareness as _ensure_process_dpi_awareness,
    get_dpi_for_monitor_containing_window,
    get_native_window_dpi,
    is_window_minimized,
    set_window_z_order_directly_above,
    win32_clip_cursor_release,
    win32_clip_cursor_to_screen_rect,
)
from pipela_qt.settings_sequence_autoscroll import (
    FEAT_AMMO_RESTOCK,
    FEAT_CALL_MERC,
    FEAT_RELOAD,
    FEAT_START_GAME,
    seq_scroll_set,
)


def _seq_scroll(feat: str, step: int) -> None:
    seq_scroll_set(_pipela_mod_for_qt(), feat, int(step))
    try:
        schedule_save_config()
    except Exception:
        pass


def _reload_set_seq_step(step: int) -> None:
    """Reload 설정 패널 단계 + 중간 단계 stuck 타이머 앵커."""
    g = globals()
    s = int(step)
    seq_scroll_set(_pipela_mod_for_qt(), FEAT_RELOAD, s)
    if s in (1, 2, 3):
        g["reload_intermediate_started_mono"] = time.monotonic()
    else:
        g["reload_intermediate_started_mono"] = 0.0
    try:
        schedule_save_config()
    except Exception:
        pass


# AGENT: in-memory image blobs loaded from registry.
RELOAD_NOBULLET_IMAGE_DATA = None
RELOAD_BULLET_IMAGE_DATA = None
RELOAD_VAULT_IMAGE_DATA = None
HP_REFILL_ZKEY_IMAGE_DATA = False  # AGENT: registry blob present flag
# AGENT: launcher: template match only on client of windows matching title rules.
# AGENT: KO title substr constant: pipela_core.win32_game_windows.SMART_UPDATER_TITLE_KO_SUBSTR
start_game_launcher_active = False
start_game_launcher_threshold = 0.65
start_game_launcher_match_region = None
start_game_launcher_score = 0.0
START_GAME_LAUNCHER_IMAGE_DATA = False
# AGENT: slot② after launcher START: one Intro Skip template click in game client.
start_game_intro_skip_threshold = 0.65
start_game_intro_skip_match_region = None
start_game_intro_skip_score = 0.0
START_GAME_INTRO_SKIP_IMAGE_DATA = False
START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC = 180.0
# AGENT: slot③ after intro skip: one Accept template click.
start_game_accept_threshold = 0.65
start_game_accept_match_region = None
start_game_accept_score = 0.0
START_GAME_ACCEPT_IMAGE_DATA = False
START_GAME_ACCEPT_ARM_TIMEOUT_SEC = 180.0
# AGENT: launcher START: 1 click; if launcher still up after N sec -> one retry; if window dies first arm intro skip.
START_GAME_LAUNCHER_POST_CLICK_DISAPPEAR_WAIT_SEC = 5.0
# AGENT: min gap before retrying same launcher click sequence.
START_GAME_LAUNCHER_RETRY_COOLDOWN_SEC = 1.0
_start_game_intro_skip_armed = False
_start_game_intro_skip_arm_until_mono = 0.0
_start_game_accept_armed = False
_start_game_accept_arm_until_mono = 0.0

# AGENT: flame HUD reads these constants from pipela_qt.cursor_hud
CURSOR_FLAME_OVERLAY_ALPHA = 0.8
CURSOR_FLAME_PANEL_OFFSET_X = 48

# 커서 HUD — Left click / Right hold / Ride 아이콘 **중심**이 커서 핫스팟에서 떨어진 거리 (Qt 논리 px).
# None = 아래 CURSOR_HUD_ICON_GAP 으로 자동(왼·오·아래 대칭). 정수면 그 픽셀만큼 직접 지정.
# dx: 음수=커서보다 왼쪽, 양수=오른쪽 / dy: 음수=위, 양수=아래
CURSOR_HUD_ICON_GAP = None  # None → pipela_qt.cursor_hud 가 scale_px(30) 근처 자동; 정수면 그 값을 gap으로
CURSOR_HUD_LEFTCLICK_ICON_DX = None
CURSOR_HUD_LEFTCLICK_ICON_DY = None
CURSOR_HUD_RIGHTHOLD_ICON_DX = None
CURSOR_HUD_RIGHTHOLD_ICON_DY = None
CURSOR_HUD_RIDE_ICON_DX = None
CURSOR_HUD_RIDE_ICON_DY = 50
# 커서 HUD 전체(아이콘 3종 + Flame 패널)를 한꺼번에 옮김 (Qt 논리 px).
CURSOR_HUD_GLOBAL_OFFSET_X = 25
CURSOR_HUD_GLOBAL_OFFSET_Y = 25
# (레거시) FLAME 오버레이: 예전 “커서 오른쪽·아래” 배치 — 현 구현은 **아이콘 중심=커서**라 미사용.
CURSOR_FLAME_HUD_CURSOR_MARGIN = None
# FT HUD만: 화면 커서 기준 가산(논리 px). 0,0 = 아이콘 정중앙=핫스팟.
# 양수 = 오른쪽·아래, 음수 = 왼쪽·위
CURSOR_FLAME_HUD_NUDGE_X = 25
CURSOR_FLAME_HUD_NUDGE_Y = 5
# 정보 패널 배경·테두리 알파 (0–255). 낮을수록 더 투명.
FLAME_TRIGGER_HUD_PANEL_BG_ALPHA = 170
FLAME_TRIGGER_HUD_PANEL_BORDER_ALPHA = 255
FLAME_START_BANNER_TEXT = "Flame Trigger가 시작되었습니다!"
# 표시(펄스) 구간. 이어서 FLAME_START_BANNER_OUTRO_SEC 만큼 깜빡이며 흐려짐(잘림 방지) 후 숨김.
FLAME_START_BANNER_DURATION_SEC = 3.0
# 홀드 종료 후 창 투명도: 여러 번 깜빡(repeat sin) + 전체 엔벨롭(자연스럽게 사라짐).
FLAME_START_BANNER_OUTRO_SEC = 0.9
FLAME_START_BANNER_OUTRO_FLICKERS = 4
# 예전 세로 비율 배치용(현재 배너는 클라 중앙 — `pipela_qt.cursor_hud.QtFlameStartBanner`).
FLAME_START_BANNER_CLIENT_Y_FRACTION = 0.15  # 클라이언트 상단→하단 0~1, 배너 세로 중심 위치
FLAME_START_BANNER_FONT_PT = 22
# 배너 펄스(창 투명도) — 사인 파형, BLINK_ON/OFF 가 진폭. 강렬: OFF 낮추고 PEAK_GAMMA < 1.
FLAME_START_BANNER_BLINK_ON_ALPHA = 0.98
FLAME_START_BANNER_BLINK_OFF_ALPHA = 0.04
FLAME_START_BANNER_PULSE_PERIOD_SEC = 0.72
FLAME_START_BANNER_PULSE_PEAK_GAMMA = 0.40
FLAME_START_BANNER_RAINBOW_DEG_PER_SEC = 68.0
FLAME_START_BANNER_BLINK_MS = 320  # 레거시(펄스 도입 전); 미사용
FLAME_START_BANNER_ANIM_MS = 50


def _load_tray_icon_image():
    """시스템 트레이용 PIL 이미지 (pystray). 실패 시 단색 플레이스홀더."""
    for path in (PIPELA_APP_ICON_PATH, PIPELA_ICO_PATH):
        if os.path.isfile(path):
            try:
                im = Image.open(path).convert("RGBA")
                im.thumbnail((64, 64), Image.Resampling.LANCZOS)
                return im
            except Exception:
                continue
    return Image.new("RGBA", (64, 64), (40, 40, 40, 255))


# AGENT: GUI font stack pipela_core.ui_fonts; policy in AGENTS.md §19


def ui_px(base_px):
    return max(1, int(round(float(base_px))))


def ui_font(pt, *extra):
    """기본 UI 글꼴 — 맑은 고딕 기준(FONT_UI_KO). 버튼·라벨·한글 본문."""
    sz = max(5, int(round(float(pt))))
    if extra:
        return (FONT_UI, sz) + extra
    return (FONT_UI, sz)


def ui_font_mono(pt, *extra):
    sz = max(5, int(round(float(pt))))
    if extra:
        return (FONT_UI_MONO, sz) + extra
    return (FONT_UI_MONO, sz)


def ui_text_ko_font(pt, *extra):
    """한글 본문용 Text·안내 블록 — 맑은 고딕(FONT_UI_KO). mono가 아닌 `ui_font`와 동일, 이름으로 용도만 구분."""
    return ui_font(pt, *extra)


def ui_icon_side(base=20):
    return max(8, int(round(float(base))))


# AGENT: align with Qt font helpers; title pady=12; section gap CONTROL_PANEL_GAP_Y
SETTINGS_WINDOW_WIDTH = 320
CONTROL_WINDOW_DISCONNECTED_HEIGHT = 1440  # AGENT: control height when no game
CONTROL_WINDOW_FALLBACK_HEIGHT = 640  # AGENT: fallback control height
CONTROL_WINDOW_LAUNCHER_DOCK_HEIGHT = 920  # AGENT: launcher-only dock height px
# AGENT: control main buttons — unified font/padding/icon height per row.
CONTROL_PANEL_BTN_FONT_SIZE = 12
CONTROL_PANEL_ICON_SIDE = 24  # AGENT: icon px scales with ui
CONTROL_PANEL_BTN_PADX = 12
CONTROL_PANEL_BTN_PADY = 11
CONTROL_PANEL_GAP_Y = 18  # AGENT: vertical gap control panel
SETTINGS_WRAPLENGTH = 280      # AGENT: wrap width minus pad
SETTINGS_SLIDER_LENGTH = 210   # AGENT: slider track design px
SETTINGS_SLIDER_LENGTH_RELOAD = 154  # AGENT: reload panel slider width
SETTINGS_PAD_X = 20  # AGENT: design pad; scaled via settings_pad_x()
SETTINGS_TITLE_PADY = (10, 4)  # AGENT: title card pady tight to hint
SETTINGS_GAP_Y = 6             # AGENT: section vertical gap
SETTINGS_BLOCK_PADY = 8        # AGENT: inner block pady
# AGENT: hint block vertical rhythm — avoid gap between title card and divider.
SETTINGS_HINT_FR_PADY = (4, 4)
# AGENT: one spacer line (px) between hint and first section rule.
SETTINGS_HINT_TO_SECTION_LINE = 3
SETTINGS_FOOTER_PAD = (4, 12)
SETTINGS_FOOTER_PAD_TOP_EXTRA = 12  # AGENT: footer top extra pad
SETTINGS_FOOTER_PAD_OUTER = (
    SETTINGS_FOOTER_PAD[0] + SETTINGS_FOOTER_PAD_TOP_EXTRA,
    SETTINGS_FOOTER_PAD[1],
)
SETTINGS_BTN_PADX_FLAT = 10
SETTINGS_BTN_PADY_FLAT = 8
SETTINGS_MAIN_BTN_PAD = (15, 8)  # AGENT: main action btn pad
SETTINGS_MAIN_ROW_BTN_PAD = (25, 10)  # AGENT: wide row btn pad
SETTINGS_CARD_INNER_PAD = (16, 14)     # AGENT: settings card inner pad

# AGENT: dark palette — must match pipela_qt/theme.py + Qt layout constants
SETTINGS_WINDOW_BG = "#1e1e1e"
CONTROL_MAIN_FG = "#d4d4d4"
SETTINGS_BTN_BG = "#2d2d2d"
CONTROL_BTN_ACTIVE_BG = "#3d3d3d"
SETTINGS_ENTRY_BG = "#3c3c3c"
SETTINGS_TROUGH_BG = "#252526"
SETTINGS_ENTRY_DISABLED_FG = "#888888"
SETTINGS_ACCENT_BG = "#0a6b63"
SETTINGS_PANEL_BG = "#252526"
SETTINGS_SECTION_HEADING_FG = "#e2e8f0"
SETTINGS_SECTION_SUB_HEADING_FG = "#9eb0c8"
CONTROL_SEPARATOR_BG = "#444444"
_SETTINGS_TEMPLATE_HIT_ACCENT_DEFAULT = "#2a9d96"
_SETTINGS_TEMPLATE_HIT_ACCENT_BY_KIND = {
    "ride_target": "#66bb6a",
    "reload_nobullet": "#29b6f6",
    "reload_bullet": "#42a5f5",
    "reload_vault": "#ab47bc",
    "hp_zkey": "#ef5350",
    "ammo_buybutton": "#ffa726",
    "ammo_inven": "#ffca28",
    "ammo_bank": "#ffd54f",
    "call_merc_1": "#7e57c2",
    "call_merc_2": "#5c6bc0",
    "call_merc_3": "#42a5f5",
    "call_merc_4": "#78909c",
    "start_game_launcher": "#26c6da",
    "start_game_intro_skip": "#26a69a",
    "start_game_accept": "#2e7d32",
}


def settings_pad_x():
    """좌우 패딩(디자인 px)."""
    return ui_px(SETTINGS_PAD_X)


def _control_panel_body_label_wraplength(window_width_px=None):
    """
    메인 제어창과 동일: panel_body 가로 padx(10) + 터미널 Text padx(8) 기준 본문 라벨 wraplength.
    window_width_px: 실제 창 너비(px). None이면 SETTINGS_WINDOW_WIDTH 기준(디자인 px).
    좁은 창에서도 inner를 넘지 않도록 상한만 둠(과거 min(inner,·) 뒤 max(160,·)로 역으로 넘치던 문제 제거).
    """
    if window_width_px is None:
        w = max(1, int(ui_px(SETTINGS_WINDOW_WIDTH)))
    else:
        w = max(1, int(window_width_px))
    inner = max(1, w - 2 * ui_px(10) - 2 * ui_px(8))
    cap = max(1, int(ui_px(SETTINGS_WRAPLENGTH)))
    return max(1, min(inner, cap))


# AGENT: settings title hierarchy — option blocks: small bold + color (Qt + pipela_mod helpers).
def SETTINGS_SECTION_TITLE_FONT():
    """템플릿/옵션 구역 메인 제목(네임카드 왼쪽 강조 줄)."""
    return ui_font(11, "bold")


def SETTINGS_SUBSECTION_TITLE_FONT():
    """하위 단계·부제목."""
    return ui_font(10, "bold")


def KILL_COUNTER_STATS_HEADING_FONT():
    """Kill Counter — 「현재 킬」「그래프」「킬 통계」 섹션 제목."""
    return ui_font(10, "bold")


def KILL_COUNTER_PANEL_PROGRESS_NUM_FONT():
    """Kill Counter 정보 탭 — 현재 킬 숫자(강조)."""
    return ui_font_mono(18, "bold")


def KILL_COUNTER_STAT_GROUP_TITLE_FONT():
    """Kill Counter 킬 통계 — 최근·집계·동시간대 비교·랩 그룹명."""
    return ui_font(11, "bold")


def KILL_COUNTER_STAT_GROUP_META_FONT():
    """그룹 머리글 오른쪽 보조(랩 시작/경과 등)."""
    return ui_font(8)


def KILL_COUNTER_LAP_STOPWATCH_FONT():
    """랩 섹션 머리글 오른쪽 경과 — 큰 스톱워치(모노)."""
    return ui_font_mono(12, "bold")


def _kill_counter_lap_stopwatch_tick_ms():
    """랩 스톱워치 갱신 간격 — `display_tick_ms()`와 동일."""
    return display_tick_ms()


def SETTINGS_ACCENT_ROW_FONT():
    return ui_font(13, "bold")


def settings_gap_y():
    return ui_px(SETTINGS_GAP_Y)


def settings_block_pady():
    return ui_px(SETTINGS_BLOCK_PADY)


def settings_title_pady():
    return (ui_px(SETTINGS_TITLE_PADY[0]), ui_px(SETTINGS_TITLE_PADY[1]))


def settings_footer_pad_outer():
    return (
        ui_px(SETTINGS_FOOTER_PAD[0] + SETTINGS_FOOTER_PAD_TOP_EXTRA),
        ui_px(SETTINGS_FOOTER_PAD[1]),
    )


def settings_hint_fr_pady():
    return (
        ui_px(SETTINGS_HINT_FR_PADY[0]),
        ui_px(SETTINGS_HINT_FR_PADY[1]),
    )


def settings_hint_to_section_sep_pre_line_pady():
    """힌트(또는 상단 안내) 다음, 첫 #444 구분선 직전 상단 공백."""
    return (ui_px(SETTINGS_HINT_TO_SECTION_LINE), 0)


def settings_main_btn_pad():
    return (ui_px(SETTINGS_MAIN_BTN_PAD[0]), ui_px(SETTINGS_MAIN_BTN_PAD[1]))


def settings_main_row_btn_pad():
    return (ui_px(SETTINGS_MAIN_ROW_BTN_PAD[0]), ui_px(SETTINGS_MAIN_ROW_BTN_PAD[1]))


def settings_card_inner_pad():
    return (ui_px(SETTINGS_CARD_INNER_PAD[0]), ui_px(SETTINGS_CARD_INNER_PAD[1]))


def _left_click_approx_cps():
    """mouse_click 내장 0.01초(10ms) 포함한 대략 초당 클릭 수 (표시용). 랜덤이면 평균 간격 기준."""
    global left_click_interval_ms, left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    if left_click_random_enabled:
        lo = min(left_click_random_min_ms, left_click_random_max_ms)
        hi = max(left_click_random_min_ms, left_click_random_max_ms)
        ms = max(0.0, (lo + hi) / 2.0)
    else:
        ms = max(0.0, float(left_click_interval_ms))
    return 1000.0 / (10.0 + ms)


def _left_click_approx_cps_range():
    """랜덤일 때 (낮은 CPS, 높은 CPS) 표시용. 고정이면 (단일, 단일)."""
    global left_click_interval_ms, left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    if not left_click_random_enabled:
        c = _left_click_approx_cps()
        return (c, c)
    lo_ms = min(left_click_random_min_ms, left_click_random_max_ms)
    hi_ms = max(left_click_random_min_ms, left_click_random_max_ms)
    c_short = 1000.0 / (10.0 + lo_ms)
    c_long = 1000.0 / (10.0 + hi_ms)
    return (min(c_short, c_long), max(c_short, c_long))

def _win_font_path(*filenames):
    fdir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for name in filenames:
        p = os.path.join(fdir, name)
        if os.path.isfile(p):
            return p
    return None


def _segment_runs_mono_ko(s):
    """ASCII(단일 바이트)만 True(모노), 나머지는 맑은 고딕·Gulim 등 한글 스택."""
    if not s:
        return []
    out, buf, cur = [], None, None
    for ch in s:
        use_mono = ord(ch) < 128
        if cur is None:
            cur, buf = use_mono, [ch]
        elif use_mono == cur:
            buf.append(ch)
        else:
            out.append(("".join(buf), cur))
            cur, buf = use_mono, [ch]
    if buf:
        out.append(("".join(buf), cur))
    return out


def _pil_font_pair(size_px):
    """ASCII: 모노스페이스(볼드 우선); 한글: 맑은 고딕(우선)·Noto/Pretendard PIL 폰트 폴백."""
    sz = max(8, int(size_px))
    p_m = _win_font_path(
        "consolab.ttf",
        "consola.ttf",
        "CascadiaMono-Bold.ttf",
        "CascadiaMono.ttf",
        "JetBrainsMono-Bold.ttf",
        "JetBrainsMono-Regular.ttf",
    )
    p_k = _win_font_path(
        "malgunbd.ttf",
        "malgun.ttf",
        "NotoSansKR-Bold.otf",
        "NotoSansKR-SemiBold.otf",
        "NotoSansKR-Medium.otf",
        "NotoSansKR-Regular.otf",
        "NotoSansKR-Bold.ttf",
        "NotoSansKR-SemiBold.ttf",
        "NotoSansKR-Medium.ttf",
        "NotoSansKR-Regular.ttf",
        "NotoSansKR-VariableFont_wght.ttf",
        "Pretendard-Bold.otf",
        "Pretendard-SemiBold.otf",
        "Pretendard-Medium.otf",
        "Pretendard-Regular.otf",
        "PretendardVariable.ttf",
        "gulim.ttc",
        "gulim.ttf",
    )
    try:
        fm = ImageFont.truetype(p_m, sz) if p_m else None
    except OSError:
        fm = None
    fk = None
    if p_k:
        try:
            if p_k.lower().endswith(".ttc"):
                fk = ImageFont.truetype(p_k, sz, index=0)
            else:
                fk = ImageFont.truetype(p_k, sz)
        except OSError:
            fk = None
    if fk is None:
        fk = fm
    if fm is None:
        fm = fk
    return fm, fk


def _pil_text_run_length(draw, txt, font):
    if not txt:
        return 0
    if hasattr(draw, "textlength"):
        try:
            return int(draw.textlength(txt, font=font))
        except Exception:
            pass
    bb = draw.textbbox((0, 0), txt, font=font)
    return max(1, bb[2] - bb[0])



def _template_probe_mark(feature: str, sub: str) -> None:
    """해당 템플릿에 대해 매칭을 시도하는 코드 경로에서 호출 (루프 스레드)."""
    _template_probe_last_mono[(feature, sub)] = time.monotonic()


def load_config():
    """설정 로드 (레지스트리)"""
    global ride_detect_region, hp_refill_detect_region, kill_counter_detect_region
    global reload_nobullet_match_region, reload_bullet_match_region, reload_vault_match_region
    global ammo_buybutton_match_region, ammo_inven_match_region, ammo_bank_match_region
    global call_merc_1_match_region, call_merc_2_match_region, call_merc_3_match_region, call_merc_4_match_region
    global start_game_launcher_match_region, start_game_launcher_active, start_game_launcher_threshold
    global start_game_intro_skip_match_region, start_game_intro_skip_threshold, start_game_intro_skip_score
    global start_game_accept_match_region, start_game_accept_threshold, start_game_accept_score
    global ride_threshold, reload_threshold, reload_nobullet_threshold, reload_bullet_threshold, reload_vault_threshold, reload_ammo_count, hp_refill_threshold, hp_refill_key_code, ammo_restock_threshold
    global ammo_restock_buybutton_threshold, ammo_restock_inven_threshold, ammo_restock_bank_threshold
    global call_merc_1_threshold, call_merc_2_threshold, call_merc_3_threshold, call_merc_4_threshold
    global ammo_restock_toggle_key_code
    global reload_active, ammo_restock_active
    global left_click_feature_enabled, right_hold_feature_enabled, ride_feature_enabled, hp_refill_feature_enabled, flame_trigger_feature_enabled, kill_counter_enabled
    global left_click_interval_ms, left_click_hold_sec
    global left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    global RELOAD_NOBULLET_IMAGE_PATH, RELOAD_BULLET_IMAGE_PATH, RELOAD_VAULT_IMAGE_PATH, RELOAD_NOBULLET_IMAGE_DATA, RELOAD_BULLET_IMAGE_DATA, RELOAD_VAULT_IMAGE_DATA, HP_REFILL_ZKEY_IMAGE_DATA
    global RIDE_TARGET_IMAGE_PATH, HP_REFILL_ZKEY_IMAGE_PATH, AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH, AMMO_RESTOCK_INVEN_IMAGE_PATH, AMMO_RESTOCK_BANK_IMAGE_PATH
    global CALL_MERC_1_IMAGE_PATH, CALL_MERC_2_IMAGE_PATH, CALL_MERC_3_IMAGE_PATH, CALL_MERC_4_IMAGE_PATH
    global START_GAME_IMAGE_PATH, START_GAME_LAUNCHER_IMAGE_DATA
    global START_GAME_INTRO_SKIP_IMAGE_PATH, START_GAME_INTRO_SKIP_IMAGE_DATA
    global START_GAME_ACCEPT_IMAGE_PATH, START_GAME_ACCEPT_IMAGE_DATA
    global merc_fire_enabled, merc_fire_key_code
    global merc_fire_random_min_ms, merc_fire_random_max_ms, merc_fire_interval_use_seconds
    global console_log_retention_minutes, console_log_retention_seconds, console_log_time_display_mode
    global pipela_ui_font_pt
    global kill_counter_panel_w
    global control_panel_w
    global kill_counter_stats_row_order
    global kill_counter_lap_start_ts
    global kill_counter_lap_pause_segments
    global region_preview_overlay_saved_kind
    global game_window_center_on_detect_enabled
    global settings_sequence_autoscroll_steps
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        g = globals()
        for _rk, _ga, _dflt in _CONFIG_LOAD_BOOLS_PRE_KC:
            registry_load_bool(key, g, _rk, _ga, _dflt)
        load_kill_counter_state(key, g)
        registry_load_bool(key, g, "flame_trigger_feature_enabled", "flame_trigger_feature_enabled", True)
        load_left_click_timing(key, g)

        load_json_regions_from_registry(key, g, _CONFIG_LOAD_JSON_REGIONS)
        migrate_reload_vault_match_region(key, g)

        apply_optional_float_pairs(key, g, _CONFIG_LOAD_OPTIONAL_FLOATS)
        apply_try_set_int(key, g, "hp_refill_key_code", "hp_refill_key_code")
        load_int_legacy(
            key, g, "pipela_ui_font_pt", "pipela_ui_font_pt", 11,
            legacy="echnew_ui_font_pt",
        )
        load_int_legacy(
            key, g, "kill_counter_panel_w", "kill_counter_panel_w", 0,
        )
        load_int_legacy(
            key, g, "control_panel_w", "control_panel_w", 0,
        )
        load_reload_threshold_pack(key, g)
        load_reload_ammo_count_clamped(key, g)
        load_ammo_restock_thresholds(key, g)
        load_call_merc_thresholds(key, g)

        load_ammo_toggle_key_masked(key, g)

        load_template_image_paths_from_registry(
            key, g, _CONFIG_LOAD_TEMPLATE_IMAGE_PATHS, migrate_legacy_bundle_template_path,
        )
        migrate_reload_vault_image_path(key, g, migrate_legacy_bundle_template_path)

        load_image_data_presence_from_registry(key, g, _CONFIG_LOAD_IMAGE_DATA_PRESENCE)
        migrate_reload_vault_image_data_flag(key, g)

        # AGENT: Merc Fire keys merc_fire_*; fallback once from legacy flame_trigger_key_* then migrate.
        load_merc_fire_enabled(key, g)
        load_int_legacy(
            key, g, "merc_fire_key_code", "merc_fire_key_code", VK_1,
            legacy="flame_trigger_key_code",
        )
        load_float_legacy(
            key, g, "merc_fire_random_min_ms", "merc_fire_random_min_ms", 500.0,
            legacy="flame_trigger_key_random_min_ms",
        )
        load_float_legacy(
            key, g, "merc_fire_random_max_ms", "merc_fire_random_max_ms", 1500.0,
            legacy="flame_trigger_key_random_max_ms",
        )
        registry_load_bool(
            key, g, "merc_fire_interval_use_seconds", "merc_fire_interval_use_seconds", True,
        )

        load_console_ui_region_preview(
            key,
            g,
            CONSOLE_LOG_RETENTION_MIN_MIN,
            CONSOLE_LOG_RETENTION_MAX_MIN,
            CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            CONSOLE_LOG_TIME_MODE_RELATIVE,
            _REGION_PREVIEW_PERSIST_VALID,
        )
        load_settings_sequence_autoscroll_json(key, g, _SETTINGS_SEQUENCE_AUTOSCROLL_FEAT_KEYS)

        winreg.CloseKey(key)
    except FileNotFoundError:
        # AGENT: missing registry key -> defaults (first run).
        pass
    except Exception as e:
        print(f"[{PIPELA_APP_DISPLAY_NAME}] 설정 로드 FAIL: {e}")
    finally:
        _g = globals()
        try:
            _v = int(_g.get("pipela_ui_font_pt", 11))
        except (TypeError, ValueError):
            _v = 11
        _g["pipela_ui_font_pt"] = max(8, min(24, _v))
        try:
            _kw = int(_g.get("kill_counter_panel_w", 0))
        except (TypeError, ValueError):
            _kw = 0
        if _kw != 0:
            _g["kill_counter_panel_w"] = max(260, min(900, _kw))
        else:
            _g["kill_counter_panel_w"] = 0
        try:
            _cw = int(_g.get("control_panel_w", 0))
        except (TypeError, ValueError):
            _cw = 0
        if _cw != 0:
            _g["control_panel_w"] = max(260, min(900, _cw))
        else:
            _g["control_panel_w"] = 0
        _sync_migrated_state_from_globals()
        refresh_registry_config_snapshot(globals())

def save_config():
    """설정 저장 (레지스트리)"""
    global ride_detect_region, hp_refill_detect_region, kill_counter_detect_region
    global reload_nobullet_match_region, reload_bullet_match_region, reload_vault_match_region
    global ammo_buybutton_match_region, ammo_inven_match_region, ammo_bank_match_region
    global call_merc_1_match_region, call_merc_2_match_region, call_merc_3_match_region, call_merc_4_match_region
    global start_game_launcher_match_region, start_game_launcher_active, start_game_launcher_threshold
    global start_game_intro_skip_match_region, start_game_intro_skip_threshold, start_game_intro_skip_score
    global start_game_accept_match_region, start_game_accept_threshold, start_game_accept_score
    global ride_threshold, reload_threshold, reload_nobullet_threshold, reload_bullet_threshold, reload_vault_threshold, reload_ammo_count, hp_refill_threshold, hp_refill_key_code, ammo_restock_threshold
    global ammo_restock_buybutton_threshold, ammo_restock_inven_threshold, ammo_restock_bank_threshold
    global call_merc_1_threshold, call_merc_2_threshold, call_merc_3_threshold, call_merc_4_threshold
    global ammo_restock_toggle_key_code
    global reload_active, ammo_restock_active
    global left_click_feature_enabled, right_hold_feature_enabled, ride_feature_enabled, hp_refill_feature_enabled, flame_trigger_feature_enabled, kill_counter_enabled
    global left_click_interval_ms, left_click_hold_sec
    global left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    global RELOAD_NOBULLET_IMAGE_PATH, RELOAD_BULLET_IMAGE_PATH, RELOAD_VAULT_IMAGE_PATH, RELOAD_NOBULLET_IMAGE_DATA, RELOAD_BULLET_IMAGE_DATA, RELOAD_VAULT_IMAGE_DATA, HP_REFILL_ZKEY_IMAGE_DATA
    global RIDE_TARGET_IMAGE_PATH, HP_REFILL_ZKEY_IMAGE_PATH, AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH, AMMO_RESTOCK_INVEN_IMAGE_PATH, AMMO_RESTOCK_BANK_IMAGE_PATH
    global CALL_MERC_1_IMAGE_PATH, CALL_MERC_2_IMAGE_PATH, CALL_MERC_3_IMAGE_PATH, CALL_MERC_4_IMAGE_PATH
    global START_GAME_IMAGE_PATH, START_GAME_INTRO_SKIP_IMAGE_PATH, START_GAME_ACCEPT_IMAGE_PATH
    global merc_fire_enabled, merc_fire_key_code
    global merc_fire_random_min_ms, merc_fire_random_max_ms, merc_fire_interval_use_seconds
    global console_log_retention_minutes, console_log_retention_seconds, console_log_time_display_mode
    global pipela_ui_font_pt
    global kill_counter_panel_w
    global control_panel_w
    global kill_counter_stats_row_order
    global kill_counter_lap_start_ts
    global kill_counter_lap_pause_segments
    global region_preview_overlay_saved_kind
    global game_window_center_on_detect_enabled
    global settings_sequence_autoscroll_steps
    try:
        # AGENT: create or open registry key.
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.CloseKey(key)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_WRITE)
        gsave = globals()
        
        save_sz_same_key(key, gsave, _CONFIG_SAVE_BOOLS_PRE_KC)
        save_sz_same_key(key, gsave, _CONFIG_SAVE_BOOLS_FLAME)
        save_merc_fire_fields(key, gsave)
        save_kill_counter_state(key, gsave)

        save_sz_same_key(key, gsave, _CONFIG_SAVE_LEFTCLICK_FIELDS)

        for _rn in _CONFIG_SAVE_JSON_REGION_NAMES:
            save_json_region_optional(key, _rn, gsave[_rn])

        save_reg_global_pairs(key, gsave, _CONFIG_SAVE_SZ_FIELDS)
        save_reg_global_pairs(key, gsave, _CONFIG_LOAD_TEMPLATE_IMAGE_PATHS)

        save_ammo_restock_thresholds(key, gsave)
        save_call_merc_thresholds(key, gsave)
        winreg.SetValueEx(key, "ammo_restock_toggle_key_code", 0, winreg.REG_SZ, str(ammo_restock_toggle_key_code))

        save_console_ui_region_preview(
            key,
            gsave,
            CONSOLE_LOG_RETENTION_MIN_MIN,
            CONSOLE_LOG_RETENTION_MAX_MIN,
            CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            CONSOLE_LOG_TIME_MODE_RELATIVE,
            _REGION_PREVIEW_PERSIST_VALID,
        )
        save_settings_sequence_autoscroll_json(key, gsave, _SETTINGS_SEQUENCE_AUTOSCROLL_FEAT_KEYS)

        delete_registry_values_if_present(
            key,
            (
                "flame_trigger_key_enabled",
                "flame_trigger_key_code",
                "flame_trigger_key_random_min_ms",
                "flame_trigger_key_random_max_ms",
            ),
        )

        winreg.CloseKey(key)
    except Exception as e:
        print(f"[{PIPELA_APP_DISPLAY_NAME}] 설정 저장 FAIL: {e}")
    finally:
        refresh_registry_config_snapshot(globals())


_save_config_qt_timer = None
SAVE_CONFIG_DEBOUNCE_MS = 400


def _schedule_save_config_qt_on_main():
    """Qt 메인 스레드에서만 호출: QTimer 단발 디바운스 후 save_config."""
    global _save_config_qt_timer
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
    except Exception:
        try:
            save_config()
        except Exception:
            pass
        return
    app = QApplication.instance()
    if app is None:
        try:
            save_config()
        except Exception:
            pass
        return
    if _save_config_qt_timer is None:

        def _on_qt_save_timeout():
            try:
                save_config()
            except Exception:
                pass

        _save_config_qt_timer = QTimer(app)
        _save_config_qt_timer.setSingleShot(True)
        _save_config_qt_timer.timeout.connect(_on_qt_save_timeout)
    _save_config_qt_timer.stop()
    _save_config_qt_timer.start(SAVE_CONFIG_DEBOUNCE_MS)


def schedule_save_config():
    """UI에서 연속 변경 시 레지스트리 쓰기를 한 번으로 묶음. Qt 이벤트 루프에서 디바운스."""
    try:
        refresh_registry_config_snapshot(globals())
    except Exception:
        pass
    try:
        from PyQt6.QtCore import QTimer as _QTimer
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            if threading.current_thread() is threading.main_thread():
                _schedule_save_config_qt_on_main()
            else:
                _QTimer.singleShot(0, _schedule_save_config_qt_on_main)
            return
    except Exception:
        pass
    try:
        save_config()
    except Exception:
        pass


def _flush_save_config_impl():
    global _save_config_qt_timer
    if _save_config_qt_timer is not None:
        try:
            _save_config_qt_timer.stop()
        except Exception:
            pass
    try:
        save_config()
    except Exception:
        pass


def flush_save_config_debounced():
    """대기 중인 디바운스 저장을 취소한 뒤 즉시 1회 저장(종료·동기화 시)."""
    if threading.current_thread() is threading.main_thread():
        _flush_save_config_impl()
        return
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            done = threading.Event()

            def _do():
                try:
                    _flush_save_config_impl()
                finally:
                    done.set()

            QTimer.singleShot(0, _do)
            done.wait(timeout=15.0)
            return
    except Exception:
        pass
    _flush_save_config_impl()


def _atexit_save_registry_config():
    try:
        save_config()
    except Exception:
        pass


def _macro_loop_chatter_enabled():
    """환경변수 PIPELA_QUIET_MACRO=1 이면 백그라운드 루프·핫키 토글 등 성공/상태 로그 억제(FAIL·오류는 항상 출력)."""
    try:
        return os.environ.get("PIPELA_QUIET_MACRO", "").strip().lower() not in ("1", "true", "yes")
    except Exception:
        return True


def _loop_print(msg, **kwargs):
    if _macro_loop_chatter_enabled():
        print(msg, **kwargs)


# 터미널 시퀀스 로그 (워커 루프) — 한글 접두 + 단계
_LOG_RELOAD = "[리로드]"
_LOG_CALL_MERC = "[용병호출]"
_LOG_AMMO_RESTOCK = "[탄약보급]"
_LOG_START_GAME = "[게임시작]"
_LOG_HP_REFILL = "[HP회복]"
_LOG_FLAME = "[플레임트리거]"
_LOG_LEFT_CLICK = "[좌클릭자동]"
_LOG_RIGHT_HOLD = "[우클릭홀드]"
_AMMO_STAGE_KO = {"buybutton": "①구매버튼", "inven": "②인벤토리", "bank": "③은행"}
_CALL_MERC_STAGE_KO = {
    "trigger": "①트리거",
    "contract": "②계약서",
    "call": "③호출",
    "close": "④닫기",
}


def _region_preview_persist_set(kind):
    """선택 영역 미리보기 ON 종류를 저장(끔=None). 값이 같으면 save 생략."""
    global region_preview_overlay_saved_kind
    if kind is not None and kind not in _REGION_PREVIEW_PERSIST_VALID:
        kind = None
    if region_preview_overlay_saved_kind == kind:
        return
    region_preview_overlay_saved_kind = kind
    try:
        schedule_save_config()
    except Exception:
        pass


def _region_preview_sync_persist_from_live():
    """실제 오버레이가 떠 있으면 저장 종류를 그에 맞춤. 끔(None)은 `toggle`·`_close_region_preview_*` 가 이미 persist 처리.

    Qt 종료 시 위젯이 먼저 파괴되면 live 를 잃으므로, live 가 None 일 때는 저장값을 지우지 않는다(재실행 복원 유지).
    """
    global region_preview_overlay_saved_kind
    live = None
    try:
        from pipela_qt.region_preview_overlay import qt_region_preview_current_kind

        qk = qt_region_preview_current_kind()
        if qk in _REGION_PREVIEW_PERSIST_VALID:
            live = qk
    except Exception:
        pass
    if live is None:
        return
    if region_preview_overlay_saved_kind == live:
        return
    region_preview_overlay_saved_kind = live
    try:
        schedule_save_config()
    except Exception:
        pass


def refresh_smart_updater_hwnd_if_needed():
    """캐시된 스마트업데이터 HWND가 유효하면 재사용, 아니면 Enum."""
    from pipela_qt.client_transition_debug import span as _ctd_span

    global _smart_updater_hwnd_cache, _smart_updater_poll_skip_until
    now = time.monotonic()
    try:
        th = target_hwnd
        if (
            th
            and win32gui.IsWindow(int(th))
            and now < _smart_updater_poll_skip_until
        ):
            return _smart_updater_hwnd_cache
    except Exception:
        pass
    with _ctd_span("main.refresh_smart_updater_hwnd_cached"):
        _smart_updater_hwnd_cache = refresh_smart_updater_hwnd_cached(
            _smart_updater_hwnd_cache,
            START_GAME_SMART_UPDATER_TITLE_SUBSTR,
        )
    try:
        th = target_hwnd
        if th and win32gui.IsWindow(int(th)):
            _smart_updater_poll_skip_until = now + 0.52
        else:
            _smart_updater_poll_skip_until = 0.0
    except Exception:
        _smart_updater_poll_skip_until = 0.0
    return _smart_updater_hwnd_cache


def refresh_target_hwnd_if_needed():
    """
    전역 target_hwnd 갱신. 기존 HWND가 여전히 게임 창이면 EnumWindows 생략
    (오버레이/위치 추적은 매 프레임 수준으로 호출되므로 부하·버벅임 완화).
    """
    global _game_client_power_save_active, _game_client_was_ever_connected, _game_client_disconnect_since
    from pipela_qt.client_transition_debug import log as _ctd_log
    from pipela_qt.client_transition_debug import span as _ctd_span

    current = _state_gets("target_hwnd")
    with _ctd_span("main.refresh_eternalcity_hwnd_cached"):
        next_hwnd = refresh_eternalcity_hwnd_cached(current)
    prev_power = bool(_game_client_power_save_active)

    if next_hwnd:
        _game_client_was_ever_connected = True
        _game_client_disconnect_since = None
        _game_client_power_save_active = False
    else:
        if _game_client_was_ever_connected:
            now_m = time.monotonic()
            if _game_client_disconnect_since is None:
                _game_client_disconnect_since = now_m
            elif (now_m - float(_game_client_disconnect_since)) >= float(GAME_CLIENT_EXIT_GRACE_SEC):
                _game_client_power_save_active = True

    need_teardown = False
    if not next_hwnd:
        need_teardown = True
    if (not prev_power) and bool(_game_client_power_save_active):
        need_teardown = True
    if need_teardown:
        _apply_no_game_client_session_teardown_main()

    _state_set("target_hwnd", next_hwnd)
    try:
        _ctd_log(f"refresh_target_hwnd_if_needed prev={current!r} → next={next_hwnd!r}")
    except Exception:
        pass
    return next_hwnd


def apply_game_window_screen_center() -> bool:
    """
    이터널시티(상단) 창을 담는 모니터의 작업 영역 정중앙에 맞춤.
    `game_window_center_on_detect_enabled`가 꺼져 있거나 `select_mode`(감지 영역 선택)이면 생략.
    HWND가 바뀌면 즉시 1회, 이후엔 throttled로 `SetWindowPos` 부하·깜빡임을 줄임.
    """
    global _game_center_throttle_next_mono, _last_centered_target_game_hwnd
    global target_hwnd, game_window_center_on_detect_enabled, select_mode
    if not game_window_center_on_detect_enabled or select_mode:
        return False
    refresh_target_hwnd_if_needed()
    h = target_hwnd
    if not h or is_window_minimized(h):
        return False
    now = time.monotonic()
    hi = int(h)
    if _last_centered_target_game_hwnd != hi:
        _last_centered_target_game_hwnd = hi
    elif now < _game_center_throttle_next_mono:
        return False
    _game_center_throttle_next_mono = now + _GAME_CENTER_THROTTLE_SEC
    return bool(_center_outer_window_on_monitor_work_area(hi))


class _ScreenCursorPOINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def try_screen_cursor_pos_for_macros() -> tuple[int, int] | None:
    """``GetCursorPos`` — API 실패 시 None. 일부 독점 전체화면·드라이버에서 (0,0) 유령값이 잦아 무시.

    HUD·게임 오버레이와 무관하게 동일 증상이 나올 수 있어, 매크로 판별·Flame 스냅은 이 경로만 쓴다.
    """
    pt = _ScreenCursorPOINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return None
    x, y = int(pt.x), int(pt.y)
    if x == 0 and y == 0:
        return None
    return (x, y)


def is_mouse_in_window():
    """마우스가 창 안에 있고, 게임 창이 활성화 상태인지 확인"""
    global target_hwnd
    if not target_hwnd:
        return False
    # AGENT: check if game window is foreground/active.
    if win32gui.GetForegroundWindow() != target_hwnd:
        return False
    rect = get_window_rect(target_hwnd)
    if not rect:
        return False
    pos = try_screen_cursor_pos_for_macros()
    if pos is None:
        return False
    px, py = pos
    return rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]

def mouse_click():
    """저수준 마우스 클릭"""
    global ignore_left
    ignore_left = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(MOUSE_CLICK_IGNORE_SEC)
    ignore_left = False

def mouse_move(x, y):
    """마우스 이동 (절대 좌표) — (0,0)·최소화 좌표(-32000) 등 비정상 목적지는 무시한다.

    화면이 다른 모니터에 걸쳐 있어도 (0,0) 으로의 SetCursorPos 가 매 틱 반복되면 마우스 커서가
    좌상단·원위치 사이에서 점멸하는 것처럼 보이는 현상이 자주 보고된다 — 매크로 좌표는 거의 항상
    클라이언트 중심·매칭 좌표라 (0,0)에 도달할 수 없으므로, 안전하게 거른다.
    """
    try:
        ix, iy = int(x), int(y)
    except Exception:
        return
    if ix == 0 and iy == 0:
        return
    # AGENT: block bogus coords (e.g. minimized GetWindowRect -32000) before SetCursorPos.
    if ix <= -32000 or iy <= -32000:
        return
    ctypes.windll.user32.SetCursorPos(ix, iy)

def mouse_double_click():
    """마우스 더블클릭"""
    global ignore_left
    ignore_left = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.01)
    ignore_left = False

def send_key(key_code, hwnd=None):
    """키보드 입력 (hwnd 지정 시 해당 창에 포커스 후 전송)"""
    if hwnd:
        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.02)
        except Exception:
            pass
    try:
        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        time.sleep(0.03)
        ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.03)
    except Exception:
        pass

def mouse_right_down():
    """저수준 오른쪽 마우스 누름 — ``mouse_click`` 과 같이 짧은 ignore 유지(pynput 비동기 RIGHT 토글 방지)."""
    global ignore_right
    ignore_right = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    time.sleep(MOUSE_RIGHT_IGNORE_SEC)
    ignore_right = False

def mouse_right_up():
    """저수준 오른쪽 마우스 떼기 — 합성 RIGHTUP 이 콜백에 늦게 도착해도 토글에 걸리지 않게 유지."""
    global ignore_right
    ignore_right = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    time.sleep(MOUSE_RIGHT_IGNORE_SEC)
    ignore_right = False

def set_capslock(state):
    """Caps Lock 켜기/끄기"""
    global capslock_state
    current = ctypes.windll.user32.GetKeyState(VK_CAPITAL) & 1
    if state and not current:
        ctypes.windll.user32.keybd_event(VK_CAPITAL, 0x45, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(VK_CAPITAL, 0x45, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        capslock_state = True
    elif not state and current:
        ctypes.windll.user32.keybd_event(VK_CAPITAL, 0x45, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(VK_CAPITAL, 0x45, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        capslock_state = False

def _scale_ratio_primary_monitor(sct):
    """1440p 기준 — 주 모니터 높이 비율."""
    m = primary_monitor_dict(sct)
    if not m:
        return 1.0
    return scale_ratio_from_monitor_height(int(m["height"]), float(BASE_HEIGHT))


# AGENT: region_type dispatch -> pipela_core.region_dispatch (_REGION_* aliases from import).


def _region_type_ui_label(region_type: str, *, preview_log: bool = False) -> str:
    t = _REGION_TYPE_UI_LABEL_PAIR.get(region_type)
    if t is None:
        return str(region_type)
    return t[1] if preview_log else t[0]


def _region_roi_global_get(region_type: str):
    return region_roi_from_globals(region_type, globals())


def _region_roi_global_set(region_type: str, value):
    region_roi_set_in_globals(region_type, globals(), value)


def _template_roi_for_kind(kind: str):
    """템플릿 capture kind → 매칭 ROI(None이면 전체 클라이언트)."""
    return _template_roi_for_kind_impl(kind, globals())


def clear_template_match_region(region_type: str):
    """매칭/OCR ROI 제거 → 다음 처리부터 전체 클라이언트(또는 Kill Counter 기본 동작)."""
    if region_type not in _REGION_TYPES_CLEAR_MATCH_ROI:
        return
    lab = _region_type_ui_label(region_type)
    _region_roi_global_set(region_type, None)
    schedule_save_config()
    if region_type == "kill_counter":
        print(f"[{lab}] OCR 영역 해제", flush=True)
    else:
        print(f"[{lab}] 매칭 영역 해제 → 전체 화면", flush=True)
    _close_region_preview_if_active(region_type)


def _template_last_hit_store(kind: str, patch_bgr, score: float | None = None) -> None:
    """워커 스레드에서 호출 — 성공 매칭 패치(BGR)·당시 점수 보관."""
    if patch_bgr is None or getattr(patch_bgr, "size", 0) == 0:
        return
    k = str(kind)
    _template_last_hit_bgr[k] = patch_bgr
    if score is not None:
        _template_last_hit_score[k] = float(score)


def get_template_last_match_patch_bgr(kind: str):
    """설정 UI — kind별 직전에 잡힌 인게임 매칭 패치(BGR). 없으면 None. Qt 스레드에서 안전히 쓰려 복사본."""
    p = _template_last_hit_bgr.get(str(kind))
    if p is None or getattr(p, "size", 0) == 0:
        return None
    try:
        return p.copy()
    except Exception:
        return None


def get_template_last_match_score(kind: str) -> float | None:
    """설정 UI — kind별 직전 성공 매칭의 TM_CCOEFF_NORMED 점수. 없으면 None."""
    try:
        v = _template_last_hit_score.get(str(kind))
    except Exception:
        return None
    if v is None:
        return None
    return float(v)


def _kill_counter_enhance_bgr_for_ocr(bgr_img):
    """어두운 UI·작은 글자용 대비 강화(전체 창 OCR 안정화)."""
    if bgr_img is None or bgr_img.size == 0:
        return bgr_img
    try:
        lab = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l2 = clahe.apply(l_ch)
        merged = cv2.merge([l2, a_ch, b_ch])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    except Exception:
        return bgr_img


def _kill_counter_upscale_bgr(bgr_img):
    """숫자 전용 OCR용 — 과도한 업스케일 생략(속도)."""
    h, w = bgr_img.shape[:2]
    long_edge = max(w, h)
    if long_edge < 640:
        sc = max(2, int(math.ceil(640.0 / float(long_edge))))
        sc = min(sc, 3)
    else:
        sc = 2 if long_edge < 1200 else 1
    if sc <= 1:
        return bgr_img
    return cv2.resize(
        bgr_img,
        (max(1, w * sc), max(1, h * sc)),
        interpolation=cv2.INTER_LINEAR,
    )


def _kill_counter_boxes_from_tesseract_dict(d):
    """pytesseract `image_to_data` dict → 동일 box 리스트."""
    out = []
    n = len(d.get("text", []))
    for i in range(n):
        t = (d["text"][i] or "").strip()
        if not t:
            continue
        try:
            cf = float(d["conf"][i])
        except (TypeError, ValueError, KeyError):
            cf = -1.0
        out.append({
            "text": t,
            "left": float(d["left"][i]),
            "right": float(d["left"][i]) + float(d["width"][i]),
            "top": float(d["top"][i]),
            "bottom": float(d["top"][i]) + float(d["height"][i]),
            "conf": cf,
        })
    return out


def _kill_counter_box_union(box_list):
    if not box_list:
        return None
    return {
        "left": min(float(b["left"]) for b in box_list),
        "top": min(float(b["top"]) for b in box_list),
        "right": max(float(b["right"]) for b in box_list),
        "bottom": max(float(b["bottom"]) for b in box_list),
    }



_SLASH_PAIR_RE = re.compile(r"\d[\d,\s]*\s*/\s*\d[\d,\s]*")
_SLASH_TIGHT_RE = re.compile(r"\d[\d,]*/\d[\d,]*")


def _kill_counter_slash_pair_parts(prog_txt):
    """
    `숫자1/숫자2` 형태에서 (숫자1, 숫자2). **숫자1 = 현재 킬**만 카운트·표시에 사용.
    숫자2는 UI에 `a/b`가 있을 때 패턴 매칭용(로직상 미사용).
    Returns: (str_or_None, str_or_None) 정규화된 숫자 문자열(쉼표·공백 제거).
    """
    if not (prog_txt or "").strip():
        return None, None
    s = prog_txt.strip()
    m = _SLASH_PAIR_RE.search(s) or _SLASH_TIGHT_RE.search(_kill_counter_norm_join(s))
    if not m:
        return None, None
    raw = m.group(0)
    parts = re.split(r"\s*/\s*", _kill_counter_norm_join(raw), maxsplit=1)
    if len(parts) != 2:
        return None, None

    def _norm_num(x):
        return re.sub(r"[\s,]", "", (x or "").strip())

    return _norm_num(parts[0]), _norm_num(parts[1])


# AGENT: reject unrealistic OCR spike in one tick from session/stats/UI.
# AGENT: hard cap on n1 delta per poll (blocks e.g. 2686->50109 misread).
_KILL_COUNTER_OCR_MAX_DELTA_PER_POLL = 3500
_KILL_COUNTER_OCR_MAX_UNANCHORED_N1 = 500_000  # AGENT: cap first n1 without history
# AGENT: on load, drop persistent events with per-event delta > cap (legacy bad data).
_KILL_COUNTER_STATS_MAX_SINGLE_EVENT_DELTA = 12000
_kill_counter_ocr_reject_last_log_ts = 0.0


def _kill_counter_ocr_digit_concat_spike(prev: int, ni: int) -> bool:
    """3000→300000처럼 자리수만 크게 붙은 오인식 추정."""
    if prev < 5:
        return False
    sp, sn = str(prev), str(ni)
    return len(sn) >= len(sp) + 2 and ni >= prev * 40


def _kill_counter_ocr_maybe_log_reject(ni: int, prev):
    global _kill_counter_ocr_reject_last_log_ts
    now = time.time()
    if now - _kill_counter_ocr_reject_last_log_ts < 25.0:
        return
    _kill_counter_ocr_reject_last_log_ts = now
    try:
        _pd = f"{int(prev):,}" if isinstance(prev, int) else str(prev)
    except (TypeError, ValueError):
        _pd = str(prev)
    print(f"[Kill Counter] 튀는 값 무시 — OCR {ni:,} (직전 {_pd})", flush=True)


def _kill_counter_spike_n1_close(a: int, b: int) -> bool:
    """급증 의심 구간에서 서로 같은 ‘묶음’으로 볼 수 있는 n1인지 (OCR 흔들림 허용)."""
    try:
        a, b = int(a), int(b)
    except (TypeError, ValueError):
        return False
    tol = max(8, int(0.015 * max(abs(a), abs(b))))
    return abs(a - b) <= tol


def _kill_counter_reset_spike_confirm():
    global kill_counter_spike_confirm_streak, kill_counter_spike_confirm_last_n
    kill_counter_spike_confirm_streak = 0
    kill_counter_spike_confirm_last_n = None


def _kill_counter_ocr_n1_over_final_rank_cap(ni: int) -> bool:
    """등급표 마지막 행 누적(초인 상한)을 초과하면 True — 비정상 OCR."""
    try:
        cap, _tit = _kill_counter_rank_final_goal()
    except Exception:
        return False
    if cap is None:
        return False
    try:
        return int(ni) > int(cap)
    except (TypeError, ValueError):
        return True


def _kill_counter_ocr_n1_accept(ni: int) -> int:
    """
    단일 틱 plausible + 연속 유사 검출 인정(급증 전용).
    큰 하락은 OCR 오류 가능성이 높아 연속 인정으로 수용하지 않음.
    Returns:
      0 = 반영 안 함 (급증 의심, 연속 확인 중이면 다음 폴링까지 대기)
      1 = plausible 한 번에 통과
      2 = plausible 실패했으나 비슷한 n1이 KILL_COUNTER_SPIKE_CONFIRM_POLLS회 연속 → 정식 인정
    """
    global kill_counter_spike_confirm_streak, kill_counter_spike_confirm_last_n
    if _kill_counter_ocr_n1_over_final_rank_cap(ni):
        _kill_counter_reset_spike_confirm()
        return 0
    if _kill_counter_ocr_n1_plausible(ni):
        _kill_counter_reset_spike_confirm()
        return 1
    _prev_acc = kill_counter_session_last_n1
    if _prev_acc is None:
        _prev_acc = kill_counter_session_baseline_n1
    if (
        _prev_acc is not None
        and ni < _prev_acc
        and (_prev_acc - ni) > _KILL_COUNTER_OCR_MAX_DELTA_PER_POLL
    ):
        _kill_counter_reset_spike_confirm()
        return 0
    if kill_counter_spike_confirm_last_n is not None and _kill_counter_spike_n1_close(
        kill_counter_spike_confirm_last_n, ni,
    ):
        kill_counter_spike_confirm_streak += 1
    else:
        kill_counter_spike_confirm_streak = 1
        kill_counter_spike_confirm_last_n = ni
    need = max(2, int(KILL_COUNTER_SPIKE_CONFIRM_POLLS))
    if kill_counter_spike_confirm_streak >= need:
        print(f"[Kill Counter] 같은 수 {need}회 연속 → 반영 ({ni:,})", flush=True)
        _kill_counter_reset_spike_confirm()
        return 2
    return 0


def _kill_counter_ocr_n1_plausible(ni: int) -> bool:
    """
    이전 검출 대비 비현실적 변화면 False — 세션·영구 통계에 반영하지 않음.
    증가: Δ 상한·자리 붙음. 하락: Δ 상한(증가와 동일) 초과면 OCR 오인식으로 보고 거부 —
    실제 대량 리셋은 세션 초기화 등으로만 반영.
    """
    global kill_counter_session_last_n1, kill_counter_session_baseline_n1
    if ni < 0:
        return False
    if _kill_counter_ocr_n1_over_final_rank_cap(ni):
        return False
    prev = kill_counter_session_last_n1
    if prev is None:
        prev = kill_counter_session_baseline_n1
    if prev is None:
        return ni <= _KILL_COUNTER_OCR_MAX_UNANCHORED_N1
    if ni == prev:
        return True
    if ni < prev:
        drop = prev - ni
        if drop > _KILL_COUNTER_OCR_MAX_DELTA_PER_POLL:
            return False
        return True
    delta = ni - prev
    # AGENT: per-tick delta cap regardless of ratio (old logic required ni>prev*45 so large mid-ratio jumps passed).
    if delta > _KILL_COUNTER_OCR_MAX_DELTA_PER_POLL:
        return False
    if _kill_counter_ocr_digit_concat_spike(prev, ni):
        return False
    return True


def _kill_counter_fmt_int_str(s):
    """숫자만으로 된 문자열 → 천단위 쉼표. 파싱 실패 시 원문."""
    if s is None:
        return ""
    s = str(s).strip()
    if not s:
        return s
    try:
        return f"{int(s):,}"
    except (ValueError, TypeError, OverflowError):
        return s


def _kill_counter_fmt_int_display(n):
    """정수 표시용 천단위 쉼표."""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError, OverflowError):
        return str(n)


def _kill_counter_fmt_embedded_digits(s):
    """문자열 안의 연속 숫자 구간을 각각 천단위 정수로 포맷 (OCR 원문 등)."""
    if not s:
        return s

    def _repl(m):
        try:
            return f"{int(m.group(0)):,}"
        except ValueError:
            return m.group(0)

    return re.sub(r"\d+", _repl, s)


def _kill_counter_reset_session_kills():
    """첫 검출 기준·누적 킬 세션 초기화(토글 OFF·버튼 등)."""
    global kill_counter_session_start_ts
    _state_set("kill_counter_session_baseline_n1", None)
    _state_set("kill_counter_session_last_n1", None)
    _state_set("kill_counter_session_carried_kills", 0)
    kill_counter_session_start_ts = None
    _kill_counter_reset_spike_confirm()


def _kill_counter_session_total_kills_display():
    """세션 누적 킬(첫 검출 숫자1 대비 현재 숫자1까지의 증가 + 완료된 구간)."""
    baseline_n1 = _state_gets("kill_counter_session_baseline_n1")
    last_n1 = _state_gets("kill_counter_session_last_n1")
    carried_kills = _state_gets("kill_counter_session_carried_kills")
    if baseline_n1 is None:
        return 0
    return int(
        carried_kills
        + max(0, (last_n1 or 0) - baseline_n1)
    )


def _kill_counter_update_session_from_n1(ni: int):
    """
    숫자1(현재 킬) 갱신. 첫 검출을 기준으로 증가분을 세고,
    큰 하락(단계 리셋 추정)이면 이전 구간의 (마지막−기준)을 누적에 더한다.
    """
    global kill_counter_session_start_ts
    baseline_n1 = _state_gets("kill_counter_session_baseline_n1")
    last_n1 = _state_gets("kill_counter_session_last_n1")
    carried_kills = int(_state_gets("kill_counter_session_carried_kills"))
    if baseline_n1 is None:
        _state_set("kill_counter_session_baseline_n1", ni)
        _state_set("kill_counter_session_last_n1", ni)
        kill_counter_session_start_ts = time.time()
        return
    prev = last_n1
    if prev is None:
        _state_set("kill_counter_session_last_n1", ni)
        return
    if ni < prev and (prev - ni) >= 2:
        carried_kills += max(0, prev - baseline_n1)
        _state_set("kill_counter_session_carried_kills", carried_kills)
        _state_set("kill_counter_session_baseline_n1", ni)
        _state_set("kill_counter_session_last_n1", ni)
        return
    if ni < baseline_n1 and prev >= baseline_n1:
        carried_kills += max(0, prev - baseline_n1)
        _state_set("kill_counter_session_carried_kills", carried_kills)
        _state_set("kill_counter_session_baseline_n1", ni)
        _state_set("kill_counter_session_last_n1", ni)
        return
    if ni < prev and (prev - ni) == 1:
        return
    _state_set("kill_counter_session_last_n1", ni)


def _kill_counter_session_reanchor_after_ocr_gap(ni: int) -> None:
    """인식 실패(empty/error/no_pair) 뒤 첫 성공 시: 세션 표시 합을 유지한 채 n1에 맞춤.
    update_session만 쓰면 오인식·공백 구간 뒤 절대값이 누적 킬처럼 통계에 박힐 수 있음."""
    global kill_counter_session_start_ts
    try:
        ni = int(ni)
    except (TypeError, ValueError):
        return
    if ni < 0:
        return
    baseline_was_none = _state_gets("kill_counter_session_baseline_n1") is None
    t = _kill_counter_session_total_kills_display()
    _state_set("kill_counter_session_carried_kills", int(t))
    _state_set("kill_counter_session_baseline_n1", ni)
    _state_set("kill_counter_session_last_n1", ni)
    if baseline_was_none:
        kill_counter_session_start_ts = time.time()


def _kill_counter_panel_progress_value_text(prog_txt):
    """Kill Counter 패널 상단 — 현재 킬 숫자만(천만 단위 한 줄, 모노스페이스용)."""
    t = (prog_txt or "").strip()
    if not t:
        return "—"
    n1, n2 = _kill_counter_slash_pair_parts(t)
    if n1 and n2:
        return _kill_counter_fmt_int_str(n1)
    return _kill_counter_fmt_embedded_digits(t)


def _kill_counter_fmt_eta_hours_mins(hours_float: float) -> str:
    """예상 소요 — 일·시간·분까지 표기(0인 단위는 생략)."""
    if hours_float <= 0:
        return "—"
    total_min = int(round(hours_float * 60.0))
    total_min = max(1, total_min)
    days = total_min // (24 * 60)
    rem = total_min % (24 * 60)
    h = rem // 60
    m = rem % 60
    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if h > 0:
        parts.append(f"{h}시간")
    if m > 0:
        parts.append(f"{m}분")
    return "약 " + " ".join(parts)


def _kill_counter_load_rank_table():
    """등급·몬스터킬 구간표 — ``pipela_core.kill_counter_tier_data`` 내장 데이터."""
    global _kill_counter_rank_table_rows
    if _kill_counter_rank_table_rows is not None:
        return _kill_counter_rank_table_rows
    _kill_counter_rank_table_rows = get_kill_counter_rank_table_rows()
    return _kill_counter_rank_table_rows


def _kill_counter_progress_n1_or_none():
    """OCR 진행 문자열에서 현재 킬(n1)만. a/b가 없으면 None."""
    t = (kill_counter_last_progress or "").strip()
    n1s, _n2s = _kill_counter_slash_pair_parts(t)
    if not n1s:
        return None
    try:
        return int(n1s)
    except ValueError:
        return None


def _kill_counter_tier_state_for_n1(n1: int):
    """등급표 기준 현재 행·다음 몬스터킬 상한·구간 진행률. 표 없으면 None."""
    rows = _kill_counter_load_rank_table()
    if not rows:
        return None
    n1 = max(0, int(n1))
    cur = rows[0]
    for r in rows:
        if int(r["point"]) <= n1:
            cur = r
        else:
            break
    floor = int(cur["point"])
    next_cap = cur["next_cap"]
    title = cur["title"]
    rnum = int(cur["num"])
    next_title = None
    if next_cap is not None:
        cap = int(next_cap)
        for r in rows:
            if int(r["point"]) == cap:
                next_title = (r["title"] or "").strip() or None
                break
    if next_cap is None:
        return {
            "floor": floor,
            "next_cap": None,
            "title": title,
            "num": rnum,
            "next_title": None,
            "segment_total": None,
            "into": n1 - floor,
            "rem": None,
            "pct": 100.0,
            "at_max": True,
        }
    cap = int(next_cap)
    seg = cap - floor
    into = n1 - floor
    rem = cap - n1
    if seg <= 0:
        pct = None
    else:
        pct = 100.0 * float(into) / float(seg)
        pct = max(0.0, min(100.0, pct))
    return {
        "floor": floor,
        "next_cap": cap,
        "title": title,
        "num": rnum,
        "next_title": next_title,
        "segment_total": seg,
        "into": into,
        "rem": rem,
        "pct": pct,
        "at_max": False,
    }


def _kill_counter_rank_final_goal():
    """등급표 마지막 행 — 누적 포인트 상한·호칭(예: 초인). 표 없으면 (None, None)."""
    rows = _kill_counter_load_rank_table()
    if not rows:
        return None, None
    r = rows[-1]
    try:
        pt = int(r["point"])
    except (TypeError, ValueError):
        return None, None
    if pt <= 0:
        return None, None
    tit = (r.get("title") or "").strip() or "초인"
    return pt, tit


def _kill_counter_goal_choin_pct_float():
    """마지막 등급(초인) 누적 포인트까지 진행률 0~100. OCR·표 없으면 None."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return None
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return None
    return max(0.0, min(100.0, 100.0 * float(n1) / float(cap)))


def _kill_counter_goal_choin_eta_suffix(kills_last_hour: float, kph_roll24: float) -> str:
    """초인(표 마지막 누적)까지 남은 킬 기준 예상 소요."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "—"
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return "—"
    if n1 >= cap:
        return "달성"
    rem = int(cap) - int(n1)
    if rem <= 0:
        return "달성"
    rate = float(kills_last_hour) if kills_last_hour > 0 else 0.0
    if rate <= 0:
        rate = float(kph_roll24) if kph_roll24 > 0 else 0.0
    if rate <= 0:
        return "—"
    return _kill_counter_fmt_eta_hours_mins(float(rem) / rate)


def _kill_counter_goal_choin_caption(kills_last_hour: float, kph_roll24: float):
    """「킬작 졸업까지」아래 한 줄 — 남은 킬만(+예상 기간). 호칭(초인 등) 문구 없음."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return None
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return None
    eta = _kill_counter_goal_choin_eta_suffix(kills_last_hour, kph_roll24)
    rem = max(0, int(cap) - int(n1))
    if n1 >= cap:
        return "남은 킬 0 · 달성"
    rem_s = f"{rem:,}"
    if eta == "—":
        return f"남은 킬 {rem_s}"
    return f"남은 킬 {rem_s} · {eta}"


def _kill_counter_goal_choin_rem_line():
    """킬작 졸업(표 마지막 누적)까지 — 남은 킬만."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "남은 킬 —"
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return "남은 킬 —"
    if int(n1) >= int(cap):
        return "남은 킬 0"
    rem = max(0, int(cap) - int(n1))
    return f"남은 킬 {rem:,}"


def _kill_counter_goal_choin_eta_line(kills_last_hour: float, kph_roll24: float):
    """킬작 졸업까지 — ETA 문자열만(라벨 없음)."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "—"
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return "—"
    if int(n1) >= int(cap):
        return "달성"
    eta = _kill_counter_goal_choin_eta_suffix(kills_last_hour, kph_roll24)
    if eta == "—":
        return "—"
    return eta


def _kill_counter_goal_segment_eta_suffix(kills_last_hour: float, kph_roll24: float) -> str:
    """등급표 다음 몬스터킬까지 예상 소요 — 1h 킬 속도 우선, 없으면 24h 롤링 kph."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "—"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "—"
    if st.get("at_max"):
        return "—"
    rem = st.get("rem")
    if rem is None:
        return "—"
    if rem <= 0:
        return "달성"
    rate = float(kills_last_hour) if kills_last_hour > 0 else 0.0
    if rate <= 0:
        rate = float(kph_roll24) if kph_roll24 > 0 else 0.0
    if rate <= 0:
        return "—"
    hours = float(rem) / rate
    return _kill_counter_fmt_eta_hours_mins(hours)


def _kill_counter_goal_tier_pct_float():
    """현재 등급 구간 달성도 0~100. OCR·표 없으면 None."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return None
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return None
    return st.get("pct")


def _kill_counter_goal_tier_pct_string():
    """현재 구간 달성도(%)."""
    p = _kill_counter_goal_tier_pct_float()
    if p is None:
        return None
    return f"{p:.0f}%"


def _kill_counter_goal_transition_line():
    """「다음」열 — 현재 호칭 → 다음 구간 호칭."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "목표·현재 킬 OCR 대기"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "등급 구간 표를 불러오지 못함"
    tit = (st.get("title") or "—").strip() or "—"
    if st.get("at_max"):
        return f"{tit} → —"
    nt = (st.get("next_title") or "—").strip() or "—"
    return f"{tit} → {nt}"


def _kill_counter_goal_choin_transition_line():
    """「킬작 졸업」열 — 현재 호칭 → 표 마지막(초인 등) 호칭."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "목표·현재 킬 OCR 대기"
    cap, ftit = _kill_counter_rank_final_goal()
    st = _kill_counter_tier_state_for_n1(n1)
    if not st or cap is None:
        return "등급 구간 표를 불러오지 못함"
    tit = (st.get("title") or "—").strip() or "—"
    nt = (ftit or "—").strip() or "—"
    if int(n1) >= int(cap):
        return f"{tit} → 달성"
    return f"{tit} → {nt}"


def _kill_counter_goal_rem_line():
    """게이지 아래 — 남은 킬만."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "남은 킬 —"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "남은 킬 —"
    if st.get("at_max"):
        return "남은 킬 0"
    rem = st.get("rem")
    if rem is not None and rem <= 0:
        return "남은 킬 0"
    rem_s = f"{max(0, int(rem)):,}" if rem is not None else "—"
    return f"남은 킬 {rem_s}"


def _kill_counter_goal_eta_line(kills_last_hour: float, kph_roll24: float):
    """게이지 아래 — ETA 문자열만(라벨 없음)."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "—"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "—"
    if st.get("at_max"):
        return "—"
    eta = _kill_counter_goal_segment_eta_suffix(kills_last_hour, kph_roll24)
    if eta == "—":
        return "—"
    return eta


def _kill_counter_next_goal_line_suffix(kills_last_hour: float, kph_roll24: float) -> str:
    """다음 단계까지 한 줄 요약 — 달성도 + ETA."""
    eta = _kill_counter_goal_segment_eta_suffix(kills_last_hour, kph_roll24)
    pct = _kill_counter_goal_tier_pct_string()
    if eta == "—" and pct is None:
        return "—"
    if pct is None:
        return eta if eta != "—" else "—"
    if eta == "—":
        return pct
    return f"{pct} · {eta}"


def _kill_counter_dod_grid_values(td: int, yst: int) -> tuple:
    """동시간대 비교 2×2 셀 — (어제 동시간 합, 오늘 0시~ 누적, 킬 차이, 증감률)."""
    diff = int(td) - int(yst)
    v_yst = f"{int(yst):,}"
    v_td = f"{int(td):,}"
    v_diff = f"{diff:+,}"
    if yst > 0:
        pct = 100.0 * float(diff) / float(yst)
        v_pct = f"{pct:+.1f}%"
    else:
        v_pct = "—"
    return (v_yst, v_td, v_diff, v_pct)


def _kill_counter_stats_file_path():
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("USERPROFILE") or ""
    if not base:
        base = SCRIPT_DIR
    d = os.path.join(base, "Pipela")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    new_p = os.path.join(d, "kill_counter_stats.json")
    old_p = os.path.join(base, "ECHNew", "kill_counter_stats.json")
    if (not os.path.isfile(new_p)) and os.path.isfile(old_p):
        try:
            import shutil

            shutil.copy2(old_p, new_p)
        except OSError:
            pass
    return new_p


def _kill_counter_stats_rebuild_daily_from_events():
    """이벤트 목록으로 날짜별(로컬 0시~익일 0시) 합계 재계산."""
    global _kill_counter_stats_daily
    d = {}
    for e in _kill_counter_stats_events:
        try:
            dk = time.strftime("%Y-%m-%d", time.localtime(float(e["t"])))
            d[dk] = d.get(dk, 0) + int(e["d"])
        except (KeyError, TypeError, ValueError):
            continue
    _kill_counter_stats_daily = d


def _kill_counter_stats_prune_events(now_ts):
    """오래된 이벤트 제거(약 60일)."""
    global _kill_counter_stats_events
    cutoff = float(now_ts) - 60.0 * 86400.0
    _kill_counter_stats_events = [e for e in _kill_counter_stats_events if float(e["t"]) >= cutoff]


def _kill_counter_stats_prune_reload_marks(now_ts):
    global _kill_counter_stats_reload_marks
    cutoff = float(now_ts) - 60.0 * 86400.0
    _kill_counter_stats_reload_marks = [
        float(t) for t in _kill_counter_stats_reload_marks if float(t) >= cutoff
    ]


def _kill_counter_stats_ensure_loaded():
    global _kill_counter_stats_loaded, _kill_counter_stats_events
    global _kill_counter_stats_reload_marks
    if _kill_counter_stats_loaded:
        return
    _kill_counter_stats_loaded = True
    path = _kill_counter_stats_file_path()
    _kill_counter_stats_events = []
    _kill_counter_stats_reload_marks = []
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            evs = data.get("events") if isinstance(data, dict) else None
            if isinstance(evs, list):
                for e in evs:
                    if not isinstance(e, dict):
                        continue
                    try:
                        _kill_counter_stats_events.append(
                            {"t": float(e["t"]), "d": int(e["d"])},
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
            rmarks = data.get("reload_marks") if isinstance(data, dict) else None
            if isinstance(rmarks, list):
                for x in rmarks:
                    try:
                        _kill_counter_stats_reload_marks.append(float(x))
                    except (TypeError, ValueError):
                        continue
    except Exception as e:
        print(f"[Kill Counter] 통계 JSON 불러오기 실패: {e}", flush=True)
    try:
        _now = time.time()
        _kill_counter_stats_prune_events(_now)
        _kill_counter_stats_prune_reload_marks(_now)
        _kill_counter_stats_drop_outlier_events_on_load()
        _kill_counter_stats_rebuild_daily_from_events()
    except Exception:
        pass


def _kill_counter_stats_drop_outlier_events_on_load():
    """저장된 이벤트 중 단일 증가분이 비현실적으로 큰 항목 제거 후 파일 재저장."""
    global _kill_counter_stats_events
    max_d = int(_KILL_COUNTER_STATS_MAX_SINGLE_EVENT_DELTA)
    if max_d <= 0:
        return
    before = len(_kill_counter_stats_events)
    _kill_counter_stats_events = [
        e for e in _kill_counter_stats_events
        if int(e.get("d", 0)) <= max_d
    ]
    dropped = before - len(_kill_counter_stats_events)
    if dropped > 0:
        print(
            f"[Kill Counter] 비정상 큰 기록 {dropped}건 삭제 (건당 상한 {max_d:,})",
            flush=True,
        )
        try:
            _kill_counter_stats_save()
        except Exception:
            pass


def _kill_counter_stats_save():
    path = _kill_counter_stats_file_path()
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        payload = {
            "events": list(_kill_counter_stats_events),
            "reload_marks": list(_kill_counter_stats_reload_marks),
        }
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except Exception as e:
        print(f"[Kill Counter] 통계 JSON 저장 실패: {e}", flush=True)


def _kill_counter_stats_schedule_save():
    global _kill_counter_stats_save_timer

    def _do():
        global _kill_counter_stats_save_timer
        _kill_counter_stats_save_timer = None
        _kill_counter_stats_save()

    with _kill_counter_stats_lock:
        if _kill_counter_stats_save_timer is not None:
            try:
                _kill_counter_stats_save_timer.cancel()
            except Exception:
                pass
        _kill_counter_stats_save_timer = threading.Timer(1.5, _do)
        _kill_counter_stats_save_timer.daemon = True
        _kill_counter_stats_save_timer.start()


def _kill_counter_stats_flush_pending_save():
    """디바운스 타이머를 취소하고 즉시 디스크에 저장.
    종료 직전(1.5초 이내)에만 쌓인 기록이 사라지는 것을 막는다."""
    global _kill_counter_stats_save_timer
    with _kill_counter_stats_lock:
        t = _kill_counter_stats_save_timer
        if t is not None:
            try:
                t.cancel()
            except Exception:
                pass
            _kill_counter_stats_save_timer = None
    _kill_counter_stats_save()


def _kill_counter_stats_date_key_for_ts(ts) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(float(ts)))


def _kill_counter_stats_sum_events_for_day(today_key: str) -> int:
    s = 0
    for e in _kill_counter_stats_events:
        try:
            if _kill_counter_stats_date_key_for_ts(e["t"]) == today_key:
                s += int(e["d"])
        except (KeyError, TypeError, ValueError):
            continue
    return s


def _kill_counter_stats_sum_events_window(t_lo: float, t_hi: float) -> int:
    s = 0
    for e in _kill_counter_stats_events:
        try:
            t = float(e["t"])
            if t_lo <= t <= t_hi:
                s += int(e["d"])
        except (KeyError, TypeError, ValueError):
            continue
    return s


def _kill_counter_stats_partition_events_by_day(today_key: str):
    today_list = []
    other = []
    for e in _kill_counter_stats_events:
        try:
            if _kill_counter_stats_date_key_for_ts(e["t"]) == today_key:
                today_list.append(e)
            else:
                other.append(e)
        except (KeyError, TypeError, ValueError):
            other.append(e)
    return other, today_list


def _kill_counter_stats_trim_event_list_to_target_sum(ev_list, target_sum: int) -> bool:
    """ev_list의 d 합이 target_sum이 되도록 최신 시각부터 d를 줄임. d<=0 항목 제거."""
    if target_sum < 0:
        target_sum = 0
    cur = sum(int(e["d"]) for e in ev_list)
    if cur <= target_sum:
        return False
    excess = cur - target_sum
    ev_list.sort(key=lambda x: -float(x["t"]))
    for e in ev_list:
        if excess <= 0:
            break
        d = int(e["d"])
        if d <= 0:
            continue
        sub = min(d, excess)
        e["d"] = d - sub
        excess -= sub
    i = 0
    while i < len(ev_list):
        if int(ev_list[i].get("d", 0)) <= 0:
            ev_list.pop(i)
        else:
            i += 1
    return True


def _kill_counter_stats_merge_event_lists(*parts):
    global _kill_counter_stats_events
    m = []
    for p in parts:
        m.extend(p)
    m.sort(key=lambda x: float(x["t"]))
    _kill_counter_stats_events = m


def _kill_counter_stats_reconcile_with_n1(n1: int) -> None:
    """OCR 현재 킬 n1과 영구 이벤트 합을 맞춤: 당일 첫 n1 기준 허용 증가·n1 상한·최근24h 상한."""
    global kill_counter_reconcile_local_date, kill_counter_n1_at_local_day_start
    global _kill_counter_stats_events
    if n1 < 0:
        return
    try:
        now = time.time()
        today_key = time.strftime("%Y-%m-%d", time.localtime())
        with _kill_counter_stats_lock:
            _kill_counter_stats_ensure_loaded()
            changed = False
            if kill_counter_reconcile_local_date != today_key:
                kill_counter_reconcile_local_date = today_key
                # AGENT: after restart/midnight first OCR: subtract today's persisted event sum from n1 so
                # AGENT: daily baseline matches file; else baseline=n1 => allow=0 and
                # AGENT: today's saved events would all be clipped.
                t_prior = _kill_counter_stats_sum_events_for_day(today_key)
                try:
                    kill_counter_n1_at_local_day_start = max(0, int(n1) - int(t_prior))
                except (TypeError, ValueError):
                    kill_counter_n1_at_local_day_start = n1
            bs = kill_counter_n1_at_local_day_start
            if bs is None:
                kill_counter_n1_at_local_day_start = n1
                bs = n1
            elif n1 < bs - 2:
                kill_counter_n1_at_local_day_start = n1
                bs = n1
            allow = max(0, n1 - kill_counter_n1_at_local_day_start)
            t_today = _kill_counter_stats_sum_events_for_day(today_key)
            target_today = min(allow, n1)
            if t_today > target_today:
                others, today_ev = _kill_counter_stats_partition_events_by_day(today_key)
                if _kill_counter_stats_trim_event_list_to_target_sum(today_ev, target_today):
                    changed = True
                _kill_counter_stats_merge_event_lists(others, today_ev)
            t_hi = now
            t_lo = now - 86400.0
            r24 = _kill_counter_stats_sum_events_window(t_lo, t_hi)
            if r24 > n1:
                out_w = []
                in_w = []
                for e in _kill_counter_stats_events:
                    try:
                        ft = float(e["t"])
                        if t_lo <= ft <= t_hi:
                            in_w.append(e)
                        else:
                            out_w.append(e)
                    except (KeyError, TypeError, ValueError):
                        out_w.append(e)
                if _kill_counter_stats_trim_event_list_to_target_sum(in_w, n1):
                    changed = True
                _kill_counter_stats_merge_event_lists(out_w, in_w)
            if changed:
                _kill_counter_stats_rebuild_daily_from_events()
                print(
                    f"[Kill Counter] 저장 통계를 현재 킬 {n1:,}에 맞게 조정",
                    flush=True,
                )
                _kill_counter_stats_schedule_save()
    except Exception:
        pass


def _kill_counter_stats_record_delta(delta: int, *, allow_large_jump: bool = False):
    """세션 킬이 늘어난 만큼 영구 통계에 반영.
    allow_large_jump: 연속 유사 검출로 급증을 인정한 경우 단일 이벤트 상한을 우회."""
    if delta <= 0:
        return
    if (
        not allow_large_jump
        and delta > _KILL_COUNTER_STATS_MAX_SINGLE_EVENT_DELTA
    ):
        print(
            f"[Kill Counter] 통계 +{delta:,} 반영 안 함 (한 번에 최대 {_KILL_COUNTER_STATS_MAX_SINGLE_EVENT_DELTA:,})",
            flush=True,
        )
        return
    try:
        now = time.time()
        with _kill_counter_stats_lock:
            _kill_counter_stats_ensure_loaded()
            _kill_counter_stats_events.append({"t": now, "d": int(delta)})
            _kill_counter_stats_prune_events(now)
            _kill_counter_stats_prune_reload_marks(now)
            _kill_counter_stats_rebuild_daily_from_events()
        _kill_counter_stats_schedule_save()
    except Exception:
        pass


def _kill_counter_stats_record_reload_mark(ts: float | None = None) -> None:
    """Reload 시퀀스(탄약 입력까지) 완료 시각 — 킬 그래프 봉 마커용."""
    global _graph_bucket_series_cache_key, _graph_bucket_series_cache_value
    try:
        t = float(time.time() if ts is None else ts)
        with _kill_counter_stats_lock:
            _kill_counter_stats_ensure_loaded()
            _kill_counter_stats_reload_marks.append(t)
            _kill_counter_stats_prune_reload_marks(t)
        _graph_bucket_series_cache_key = None
        _graph_bucket_series_cache_value = None
        _kill_counter_stats_schedule_save()
    except Exception:
        pass


def _kill_counter_stats_reset_all():
    """영구 킬 통계(이벤트·일별 합·JSON 파일) 전부 비움."""
    global _kill_counter_stats_save_timer, _kill_counter_stats_events, _kill_counter_stats_daily
    global _kill_counter_stats_reload_marks
    global _graph_bucket_series_cache_key, _graph_bucket_series_cache_value
    global kill_counter_reconcile_local_date, kill_counter_n1_at_local_day_start
    global kill_counter_lap_start_ts
    global kill_counter_lap_pause_segments
    kill_counter_lap_start_ts = None
    kill_counter_lap_pause_segments = []
    try:
        save_config()
    except Exception:
        pass
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        _kill_counter_stats_events = []
        _kill_counter_stats_reload_marks = []
        _kill_counter_stats_daily = {}
        kill_counter_reconcile_local_date = None
        kill_counter_n1_at_local_day_start = None
        if _kill_counter_stats_save_timer is not None:
            try:
                _kill_counter_stats_save_timer.cancel()
            except Exception:
                pass
            _kill_counter_stats_save_timer = None
    _graph_bucket_series_cache_key = None
    _graph_bucket_series_cache_value = None
    _kill_counter_stats_save()


def _kill_counter_reset_all_counts():
    """세션 킬·마지막 OCR 문자열·영구 통계까지 전부 초기화."""
    global kill_counter_last_progress
    _kill_counter_reset_session_kills()
    kill_counter_last_progress = ""
    _kill_counter_stats_reset_all()
    print("[Kill Counter] 통계·세션 전부 초기화", flush=True)


def _kill_counter_stats_sum_last_seconds(sec: float) -> int:
    """최근 sec 초(롤링) 구간 킬 합."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        now = time.time()
        cutoff = now - float(sec)
        return sum(int(e["d"]) for e in _kill_counter_stats_events if float(e["t"]) >= cutoff)


# AGENT: kill graph bucket minutes (UI 봉 선택과 동일해야 함).
_KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED = (5, 30, 60, 360, 720)
_KILL_COUNTER_GRAPH_DAY_BUCKET_WINDOW_DAYS = 30
# AGENT: graph time bucket buttons fixed char width 6 for uniform size.
_KILL_COUNTER_GRAPH_BUCKET_BTN_CHAR_WIDTH = 6


def _kill_counter_local_bucket_key(ts: float, bucket_minutes: int):
    """로컬 시계 기준 버킷 시작 (연,월,일,시,분).

    bucket_minutes는 허용 집합(예: 5·30·60·360·720분 또는 1440=자정~익일 0시 일봉) 중 하나여야 한다.
    """
    lt = time.localtime(ts)
    bm = int(bucket_minutes)
    if bm <= 1:
        return (lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min)
    if bm < 1:
        bm = 1
    total_min = lt.tm_hour * 60 + lt.tm_min
    floored = (total_min // bm) * bm
    h, mi = divmod(floored, 60)
    return (lt.tm_year, lt.tm_mon, lt.tm_mday, h, mi)


def _kill_counter_graph_bucket_tip_caption(bucket_minutes: int) -> str:
    bm = int(bucket_minutes)
    if bm >= 1440:
        return "1일 구간"
    if bm >= 60 and bm % 60 == 0:
        h = bm // 60
        return "1시간 구간" if h == 1 else f"{h}시간 구간"
    return f"{bm}분 구간"


def _kill_counter_graph_bucket_max_axis_suffix(bucket_minutes: int) -> str:
    bm = int(bucket_minutes)
    if bm >= 1440:
        return "1일"
    if bm >= 60 and bm % 60 == 0:
        h = bm // 60
        return "1시간" if h == 1 else f"{h}시간"
    return f"{bm}분"


def _kill_counter_graph_bucket_series(bucket_minutes: int):
    """
    버킷마다 킬 합(구간에 이벤트 없으면 0). 항목: kills, hhmm(축 라벨), ymdhm, reload_mark(bool).
    분봉/시간봉: 로컬 당일 0시~현재까지 버킷. (1440 분이면 과거 일자 창은 별도 분기.)

    허용 bucket_minutes: ``_KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED`` 또는 내부용 1440.
    reload_mark: 해당 구간에 Reload 시퀀스 완료 시각이 있으면 True.
    """
    global _graph_bucket_series_cache_key, _graph_bucket_series_cache_value
    bm = int(bucket_minutes)
    if bm not in _KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED:
        bm = int(_KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED[0])
    now = time.time()
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        n_ev = len(_kill_counter_stats_events)
        le = _kill_counter_stats_events[-1] if n_ev else None
        last_t = float(le["t"]) if le is not None else 0.0
        if bm >= 1440:
            t_bucket = datetime.date.today().toordinal()
        else:
            t_bucket = int(now // 60.0)
        rmarks = list(_kill_counter_stats_reload_marks)
        n_rm = len(rmarks)
        last_rm = float(rmarks[-1]) if n_rm > 0 else 0.0
        ck: tuple[object, ...] = (bm, n_ev, last_t, t_bucket, n_rm, last_rm)
        if _graph_bucket_series_cache_key == ck and _graph_bucket_series_cache_value is not None:
            return [dict(x) for x in _graph_bucket_series_cache_value]
        evs = list(_kill_counter_stats_events)

    def _reload_keys_for_window(ml: list[float], t_lo: float, t_hi: float, bmm: int) -> set[tuple]:
        s: set[tuple] = set()
        bi = int(bmm)
        for tm in ml:
            try:
                ft = float(tm)
            except (TypeError, ValueError):
                continue
            if ft < t_lo or ft > t_hi:
                continue
            s.add(_kill_counter_local_bucket_key(ft, bi))
        return s

    def _graph_series_cache_store(out: list) -> list:
        global _graph_bucket_series_cache_key, _graph_bucket_series_cache_value
        _graph_bucket_series_cache_key = ck
        _graph_bucket_series_cache_value = [dict(x) for x in out]
        return [dict(x) for x in out]

    sums = collections.defaultdict(int)

    if bm == 1440:
        n_days = int(_KILL_COUNTER_GRAPH_DAY_BUCKET_WINDOW_DAYS)
        if n_days < 1:
            n_days = 30
        end_d = datetime.date.today()
        start_d = end_d - datetime.timedelta(days=n_days - 1)
        try:
            t0 = time.mktime(
                (start_d.year, start_d.month, start_d.day, 0, 0, 0, 0, 0, -1),
            )
        except (OverflowError, ValueError):
            return _graph_series_cache_store([])
        if now + 0.5 < t0:
            return _graph_series_cache_store([])
        for e in evs:
            try:
                te = float(e["t"])
                if te < t0 or te > now:
                    continue
                dd = int(e["d"])
                if dd <= 0:
                    continue
                sums[_kill_counter_local_bucket_key(te, bm)] += dd
            except (KeyError, TypeError, ValueError):
                continue
        rk = _reload_keys_for_window(rmarks, t0, now, bm)
        out = []
        d = start_d
        while d <= end_d:
            k = (d.year, d.month, d.day, 0, 0)
            kills = int(sums.get(k, 0))
            out.append(
                {
                    "kills": kills,
                    "hhmm": f"{d.month:d}/{d.day:d}",
                    "ymdhm": k,
                    "reload_mark": k in rk,
                },
            )
            d += datetime.timedelta(days=1)
        return _graph_series_cache_store(out)

    t0 = float(_kill_counter_local_midnight_ts())
    if now + 0.5 < t0:
        return _graph_series_cache_store([])
    for e in evs:
        try:
            te = float(e["t"])
            if te < t0 or te > now:
                continue
            dd = int(e["d"])
            if dd <= 0:
                continue
            sums[_kill_counter_local_bucket_key(te, bm)] += dd
        except (KeyError, TypeError, ValueError):
            continue
    rk = _reload_keys_for_window(rmarks, t0, now, bm)
    k_end = _kill_counter_local_bucket_key(now, bm)
    out = []
    cur_ts = t0
    while True:
        k = _kill_counter_local_bucket_key(cur_ts, bm)
        y, mo, d, h, mi = k
        kills = int(sums.get(k, 0))
        out.append(
            {
                "kills": kills,
                "hhmm": f"{h:d}:{mi:02d}",
                "ymdhm": k,
                "reload_mark": k in rk,
            }
        )
        if k == k_end:
            break
        cur_ts += float(bm) * 60.0
    return _graph_series_cache_store(out)


def _kill_counter_graph_compare_pct_suffix(cur: int, ref) -> str:
    """이웃 구간 대비 퍼센트 문자열. ref가 None이면 빈 문자열."""
    if ref is None:
        return ""
    try:
        cur = int(cur)
        ref = int(ref)
    except (TypeError, ValueError):
        return ""
    if ref == 0:
        return " (+100%)" if cur > 0 else ""
    d = cur - ref
    pct = 100.0 * d / float(ref)
    return f" ({pct:+.1f}%)"


def _kill_counter_lap_is_paused():
    segs = kill_counter_lap_pause_segments
    return bool(segs) and segs[-1][1] is None


def _kill_counter_lap_event_included(t: float) -> bool:
    """랩 집계에 포함되는 이벤트 시각인지(시작 이후·일시중지 구간 제외)."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return False
    if t < float(ts):
        return False
    for seg in kill_counter_lap_pause_segments:
        p = float(seg[0])
        r = seg[1]
        if r is None:
            if t >= p:
                return False
        else:
            rf = float(r)
            if p <= t < rf:
                return False
    return True


def _kill_counter_lap_active_elapsed_seconds(now=None):
    """랩 경과(초) — 일시중지로 멈춘 구간은 제외."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return 0
    if now is None:
        now = time.time()
    raw = max(0.0, now - float(ts))
    sub = 0.0
    for seg in kill_counter_lap_pause_segments:
        p = float(seg[0])
        r = seg[1]
        if r is None:
            sub += max(0.0, now - p)
        else:
            sub += max(0.0, float(r) - p)
    return max(0.0, raw - sub)


def _format_kill_counter_lap_stopwatch(elapsed: float) -> str:
    """경과(초) → MM:SS.cc 또는 H:MM:SS.cc (소수 둘째 자리까지 고정 폭)."""
    e = max(0.0, float(elapsed))
    total_cs = int(round(e * 100.0))
    cs = total_cs % 100
    t_whole_s = total_cs // 100
    s = t_whole_s % 60
    tm = t_whole_s // 60
    m = tm % 60
    h = tm // 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    return f"{m:02d}:{s:02d}.{cs:02d}"


def _kill_counter_stats_sum_lap_total() -> int:
    """랩 시작 시각 이후 영구 이벤트 d 합 (미시작이면 0)."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return 0
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        t0 = float(ts)
        return sum(
            int(e["d"])
            for e in _kill_counter_stats_events
            if float(e["t"]) >= t0 and _kill_counter_lap_event_included(float(e["t"]))
        )


def _kill_counter_stats_sum_lap_in_last_seconds(sec: float) -> int:
    """랩 구간 안에서 최근 sec 초(롤링) 킬 합. 미시작이면 0."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return 0
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        now = time.time()
        cutoff = now - float(sec)
        t0 = max(float(ts), cutoff)
        return sum(
            int(e["d"])
            for e in _kill_counter_stats_events
            if float(e["t"]) >= t0 and _kill_counter_lap_event_included(float(e["t"]))
        )


def _kill_counter_session_header_meta_text() -> str:
    """세션 그룹 머리글 오른쪽 — 첫 기준 잡힌 시각(로컬)."""
    ts = kill_counter_session_start_ts
    if ts is None:
        return "시작 —"
    st_str = time.strftime("%m-%d %H:%M:%S", time.localtime(float(ts)))
    return f"시작 {st_str}"


def _kill_counter_lap_header_meta_text() -> str:
    """랩 그룹 머리글 오른쪽 — 경과 스톱워치만(M:SS.cc, 일시중지 구간 제외)."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return "—"
    elapsed = _kill_counter_lap_active_elapsed_seconds()
    return _format_kill_counter_lap_stopwatch(elapsed)


def _kill_counter_lap_group_title_text() -> str:
    """랩 블록 제목 왼쪽 — 누적 킬(섹션에 「랩」이 있으므로 숫자만)."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return "—"
    return f"{_kill_counter_stats_sum_lap_total():,}"


def _kill_counter_lap_stopwatch_label_fg() -> str:
    return (
        _KILL_COUNTER_LAP_SW_FG_PAUSED
        if _kill_counter_lap_is_paused()
        else _KILL_COUNTER_LAP_SW_FG_RUNNING
    )


def _kill_counter_local_midnight_ts():
    """로컬 당일 0시 unix 시각."""
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, lt.tm_wday, lt.tm_yday, lt.tm_isdst))


def _kill_counter_stats_sum_events_in_range(t_lo: float, t_hi: float) -> int:
    """이벤트 시각이 t_lo <= t <= t_hi 인 구간의 d 합."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        s = 0
        for e in _kill_counter_stats_events:
            try:
                t = float(e["t"])
                if t_lo <= t <= t_hi:
                    s += int(e["d"])
            except (KeyError, TypeError, ValueError):
                continue
        return s


def _kill_counter_stats_calendar_today_total() -> int:
    """로컬 오늘 0시~현재 (일별 집계와 동일)."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        lt = time.localtime()
        dk = f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"
        return int(_kill_counter_stats_daily.get(dk, 0))


def _kill_counter_stats_calendar_week_to_date_total() -> int:
    """이번 주 월요일 0시~현재(로컬) 합."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        daily = _kill_counter_stats_daily
    lt = time.localtime()
    base = datetime.date(lt.tm_year, lt.tm_mon, lt.tm_mday)
    monday = base - datetime.timedelta(days=base.weekday())
    total = 0
    cur = monday
    while cur <= base:
        k = f"{cur.year:04d}-{cur.month:02d}-{cur.day:02d}"
        total += int(daily.get(k, 0))
        cur += datetime.timedelta(days=1)
    return total


def _kill_counter_stats_calendar_month_to_date_total() -> int:
    """이번 달 1일 0시~현재(로컬) 합."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        daily = _kill_counter_stats_daily
    lt = time.localtime()
    base = datetime.date(lt.tm_year, lt.tm_mon, lt.tm_mday)
    first = datetime.date(lt.tm_year, lt.tm_mon, 1)
    total = 0
    cur = first
    while cur <= base:
        k = f"{cur.year:04d}-{cur.month:02d}-{cur.day:02d}"
        total += int(daily.get(k, 0))
        cur += datetime.timedelta(days=1)
    return total


def _kill_counter_stats_yesterday_same_elapsed_total() -> int:
    """어제 0시부터, 오늘 0시~현재와 같은 경과 시간만큼의 킬 합."""
    now = time.time()
    t0 = _kill_counter_local_midnight_ts()
    elapsed = max(0.0, now - t0)
    y0 = t0 - 86400.0
    y1 = y0 + elapsed
    return _kill_counter_stats_sum_events_in_range(y0, y1)


def _kill_counter_stats_daily_snapshot():
    """날짜 키(YYYY-MM-DD) → 일일 킬 합 스냅샷."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        return dict(_kill_counter_stats_daily)


def _kill_counter_daily_calendar_delta_fmt(n: int) -> str:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return "0"
    if v > 0:
        return f"+{_kill_counter_fmt_int_display(v)}"
    if v < 0:
        return f"−{_kill_counter_fmt_int_display(abs(v))}"
    return "0"


def _kill_counter_daily_calendar_delta_fg(n: int) -> str:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return "#94a3b8"
    if v > 0:
        return "#4ade80"
    if v < 0:
        return "#f87171"
    return "#94a3b8"


def _kill_counter_capture_mean_abs_diff(prev_bgr, cur_bgr) -> float:
    """같은 크기 BGR 캡처 간 다운스케일 그레이 평균 절대차(0~255). 비교 불가면 inf."""
    if prev_bgr is None or cur_bgr is None:
        return float("inf")
    try:
        if prev_bgr.size == 0 or cur_bgr.size == 0:
            return float("inf")
        if prev_bgr.shape != cur_bgr.shape:
            return float("inf")
        ha, wa = cur_bgr.shape[:2]
        tw = max(16, int(wa // 2))
        th = max(16, int(ha // 2))
        pa = cv2.resize(prev_bgr, (tw, th), interpolation=cv2.INTER_AREA)
        pb = cv2.resize(cur_bgr, (tw, th), interpolation=cv2.INTER_AREA)
        ga = cv2.cvtColor(pa, cv2.COLOR_BGR2GRAY)
        gb = cv2.cvtColor(pb, cv2.COLOR_BGR2GRAY)
        d = np.abs(ga.astype(np.float32) - gb.astype(np.float32))
        mean_d = float(np.mean(d))
        # AGENT: digit-only changes can shift many pixels locally — mean alone misses; use stricter change detect.
        if float(np.max(d)) >= 6.0:
            return max(mean_d, _KILL_COUNTER_CHANGE_MEAN_ABS_THRESH + 0.01)
        return mean_d
    except Exception:
        return float("inf")


def _kill_counter_should_skip_ocr_same_screen(cur_bgr) -> bool:
    """직전 루프 캡처와 거의 같으면 True(OCR 생략). 급증 확인·오류 재시도 중에는 False."""
    if cur_bgr is None or getattr(cur_bgr, "size", 0) == 0:
        return False
    _phase = _state_gets("kill_counter_last_poll_phase")
    if _phase is None:
        return False
    if _phase in ("unstable", "no_pair", "empty", "error"):
        return False
    if kill_counter_spike_confirm_streak > 0:
        return False
    prev = _state_gets("_kill_counter_last_change_probe_bgr")
    if prev is None:
        return False
    return _kill_counter_capture_mean_abs_diff(prev, cur_bgr) < float(_KILL_COUNTER_CHANGE_MEAN_ABS_THRESH)


def _kill_counter_norm_join(s: str) -> str:
    return re.sub(r"[\s\u200b\u00a0]+", "", s or "")


def _kill_counter_ocr_box_to_capture(ocr_box, bgr_img, bgr_u):
    """OCR 좌표(업스케일 캡처 기준) → 원본 캡처 픽셀 좌표."""
    if ocr_box is None:
        return None
    if bgr_u is None or bgr_img is None or bgr_img.size == 0:
        return None
    uw = max(1, int(bgr_u.shape[1]))
    uh = max(1, int(bgr_u.shape[0]))
    iw = max(1, int(bgr_img.shape[1]))
    ih = max(1, int(bgr_img.shape[0]))
    sx = iw / float(uw)
    sy = ih / float(uh)
    return (
        float(ocr_box["left"]) * sx,
        float(ocr_box["top"]) * sy,
        float(ocr_box["right"]) * sx,
        float(ocr_box["bottom"]) * sy,
    )


def _kill_counter_extract_slash_text(s: str):
    if not (s or "").strip():
        return None
    m = _SLASH_PAIR_RE.search(s) or _SLASH_TIGHT_RE.search(_kill_counter_norm_join(s))
    return (m.group(0) or "").strip() if m else None


def _kill_counter_read_digits_tesseract(bgr_u):
    """
    Tesseract `eng` + 숫자·슬래시 화이트리스트만 (kor 불필요).
    Returns: (val, err, label_ocr_box, progress_ocr_box, prog_txt)
    """
    global _kill_counter_tesseract_cfg_first
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        raise
    _kill_counter_ensure_tesseract_cmd()
    rgb = cv2.cvtColor(bgr_u, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    wl = "-c tessedit_char_whitelist=0123456789/"
    # AGENT: psm11 slow sparse; kill line OCR usually ok with psm 7/6.
    ocr_cfgs = [
        f"--oem 3 --psm 7 {wl}",
        f"--oem 3 --psm 6 {wl}",
    ]
    _pref = _kill_counter_tesseract_cfg_first
    if _pref and _pref in ocr_cfgs:
        ocr_cfgs = [_pref] + [c for c in ocr_cfgs if c != _pref]
    prog_txt = None
    for cfg in ocr_cfgs:
        try:
            raw = pytesseract.image_to_string(pil, lang="eng", config=cfg) or ""
        except Exception:
            continue
        prog_txt = _kill_counter_extract_slash_text(raw)
        if prog_txt:
            _kill_counter_tesseract_cfg_first = cfg
            break
    if not prog_txt:
        try:
            d = pytesseract.image_to_data(
                pil,
                lang="eng",
                output_type=Output.DICT,
                config=f"--oem 3 --psm 6 {wl}",
            )
            boxes = _kill_counter_boxes_from_tesseract_dict(d)
            items = sorted(boxes, key=lambda b: (float(b["top"]), float(b["left"])))
            acc = "".join((b.get("text") or "").strip() for b in items)
            prog_txt = _kill_counter_extract_slash_text(acc)
        except Exception:
            prog_txt = None
    if not prog_txt:
        return None, "숫자/숫자 패턴 미검출", None, None, None
    n1, n2 = _kill_counter_slash_pair_parts(prog_txt)
    if n1 and n2:
        val = f"현재 킬 {_kill_counter_fmt_int_str(n1)}"
    else:
        val = f"현재 킬 {_kill_counter_fmt_embedded_digits(prog_txt)}"
    return val, None, None, None, prog_txt


def kill_counter_read_digits(bgr_img):
    """
    감지 영역(BGR)에서 숫자·슬래시만 OCR (Tesseract eng).
    표시 문자열은 현재 킬(숫자1)만. prog_txt는 원문 `a/b` 유지.
    Returns: (표시_문자열, err, label_rect_capture, progress_rect_capture, prog_txt)
    """
    t0 = time.perf_counter()
    try:
        if bgr_img is None or bgr_img.size == 0:
            return None, "캡처 없음", None, None, None
        bgr_u = _kill_counter_upscale_bgr(_kill_counter_enhance_bgr_for_ocr(bgr_img))

        def _finish(val, err, label_ocr_box, prog_ocr_box, prog_txt):
            cap_p = _kill_counter_ocr_box_to_capture(prog_ocr_box, bgr_img, bgr_u) if prog_ocr_box else None
            return val, err, None, cap_p, prog_txt

        try:
            return _finish(*_kill_counter_read_digits_tesseract(bgr_u))
        except ImportError:
            return None, "pytesseract 미설치 (pip install pytesseract)", None, None, None
        except Exception as ex:
            msg = str(ex).lower()
            if "not installed" in msg or "not in your path" in msg:
                return (
                    None,
                    "Tesseract 엔진 없음 — Windows용 Tesseract 설치(eng.traineddata). "
                    "https://github.com/UB-Mannheim/tesseract/wiki",
                    None,
                    None,
                    None,
                )
            return None, f"Tesseract OCR: {ex}", None, None, None
    finally:
        telemetry_record_ocr_sec(time.perf_counter() - t0)



def _kill_counter_tesseract_exe_candidates():
    """가능한 tesseract.exe 경로(중복 제거). IDE 실행 시 PATH에 없을 때 레지스트리·고정 경로로 보완."""
    out = []
    seen = set()

    def add(p):
        if not p:
            return
        p = os.path.normpath(os.path.expandvars(str(p).strip().strip('"')))
        if p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)

    add(os.environ.get("TESSERACT_CMD"))
    for name in ("tesseract", "tesseract.exe"):
        w = shutil.which(name)
        if w:
            add(w)
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LocalAppData", "")
        for p in (
            os.path.join(pf, "Tesseract-OCR", "tesseract.exe"),
            os.path.join(pfx86, "Tesseract-OCR", "tesseract.exe"),
            os.path.join(local, "Programs", "Tesseract-OCR", "tesseract.exe") if local else None,
            r"C:\Tesseract-OCR\tesseract.exe",
        ):
            add(p)
        try:
            import winreg
            for hive, sub in (
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tesseract-OCR"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tesseract-OCR"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Tesseract-OCR"),
            ):
                try:
                    k = winreg.OpenKey(hive, sub, 0, winreg.KEY_READ)
                    try:
                        base, _ = winreg.QueryValueEx(k, "InstallDir")
                        add(os.path.join(base, "tesseract.exe"))
                    finally:
                        winreg.CloseKey(k)
                except OSError:
                    pass
        except Exception:
            pass
    return out


def _kill_counter_try_bind_working_tesseract():
    """실제로 `--version`에 성공하는 실행 파일을 pytesseract에 연결."""
    import pytesseract
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        pass
    for exe in _kill_counter_tesseract_exe_candidates():
        if not exe or not os.path.isfile(exe):
            continue
        try:
            pytesseract.pytesseract.tesseract_cmd = exe
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            continue
    return False


def _kill_counter_ensure_tesseract_cmd():
    """
    pytesseract에 동작하는 Tesseract.exe 연결.
    PATH·Program Files·레지스트리·환경변수 TESSERACT_CMD 후보를 순서대로 시도.
    """
    global _kill_counter_tesseract_cmd_checked
    if _kill_counter_tesseract_cmd_checked:
        return
    _kill_counter_tesseract_cmd_checked = True
    try:
        import pytesseract
    except ImportError:
        return
    _kill_counter_try_bind_working_tesseract()


def _kill_counter_install_help_text():
    """Tesseract·pytesseract 설치 안내 (복사용 블록)."""
    return (
        "# Kill Counter — 감지 영역 화면 변화 시에만 숫자 OCR (Tesseract eng)\n"
        "# 감지 영역: `현재킬/목표` 형태 OCR (예: 3/10) — 카운트는 앞 숫자(현재 킬)만 사용\n"
        "# OCR 영역: 설정에서 선택 영역 지정 필수(미지정 시 OCR 안 함)\n"
        "\n"
        "# PATH에 tesseract 없으면 환경변수로 직접 지정 가능:\n"
        "# TESSERACT_CMD=C:\\\\Program Files\\\\Tesseract-OCR\\\\tesseract.exe\n"
        "\n"
        "# pytesseract + Windows Tesseract (eng.traineddata)\n"
        "pip install pytesseract\n"
        "https://github.com/UB-Mannheim/tesseract/wiki\n"
    )


def _kill_counter_tesseract_state():
    """(준비됨, 이유) — 이유: None=OK, pytesseract=pip 패키지 없음, engine=exe 미탐/실패."""
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract"
    _kill_counter_ensure_tesseract_cmd()
    import pytesseract
    try:
        pytesseract.get_tesseract_version()
        return True, None
    except Exception:
        return False, "engine"


def _kill_counter_tesseract_available():
    """pytesseract + Tesseract 실행 파일이 실제로 동작하는지(get_tesseract_version 성공)."""
    return _kill_counter_tesseract_state()[0]


def _kill_counter_tesseract_state_cached():
    """상태 UI — (ok, reason) 수 초마다 갱신."""
    global _kill_counter_tesseract_av_cache
    now = time.monotonic()
    if _kill_counter_tesseract_av_cache is not None:
        ok, reason, ts = _kill_counter_tesseract_av_cache
        if now - ts < 12.0:
            return ok, reason
    ok, reason = _kill_counter_tesseract_state()
    _kill_counter_tesseract_av_cache = (ok, reason, now)
    return ok, reason


def _kill_counter_tesseract_available_cached():
    """상태 UI 등에서 반복 호출용 — 수 초 단위로만 실제 검사."""
    return _kill_counter_tesseract_state_cached()[0]


def _kill_counter_ui_short_detail(s, max_len=88):
    """상태 줄 부가 텍스트 — 한 줄로 잘라 표시."""
    if not s:
        return None
    t = str(s).replace("\n", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _kill_counter_status_mode_detail():
    """Kill Counter 패널 상태: (ui_mode, 부가 설명 또는 None).
    ui_mode: off | idle | kc_waiting | kc_ok | kc_empty | kc_no_pair | kc_unstable | kc_error
    """
    if not _state_gets("kill_counter_enabled"):
        return "off", None
    if not _state_gets("target_hwnd"):
        return "idle", "게임 창 미연결"
    if _state_gets("select_mode"):
        return "idle", "영역 선택 모드"
    if not _state_gets("kill_counter_detect_region"):
        return "idle", "감지 영역 미지정"
    _t_ok, _t_reason = _kill_counter_tesseract_state_cached()
    if not _t_ok:
        if _t_reason == "pytesseract":
            return "idle", "pytesseract 미설치 (pip install pytesseract)"
        if _t_reason == "engine":
            return "idle", "Tesseract 엔진 경로 없음 (PATH·TESSERACT_CMD·설치 안내)"
        return "idle", "Tesseract 사용 불가"
    ph = _state_gets("kill_counter_last_poll_phase")
    if ph is None:
        return "kc_waiting", "첫 OCR 결과 대기"
    d = _state_gets("kill_counter_last_poll_detail")
    if ph == "ok":
        lp = (_state_gets("kill_counter_last_progress") or "").strip()
        if lp:
            n1s, n2s = _kill_counter_slash_pair_parts(lp)
            if n1s and n2s:
                lp = f"{_kill_counter_fmt_int_str(n1s)} / {_kill_counter_fmt_int_str(n2s)}"
            else:
                lp = re.sub(
                    r"\s*/\s*",
                    " / ",
                    _kill_counter_fmt_embedded_digits(lp),
                )
        return "kc_ok", (lp if lp else None)
    if ph == "empty":
        return "kc_empty", d or "인식된 문자 없음"
    if ph == "no_pair":
        return "kc_no_pair", d or "a/b 형식 아님"
    if ph == "unstable":
        return "kc_unstable", d or "급증 의심 — 직전 표시 유지"
    if ph == "error":
        return "kc_error", _kill_counter_ui_short_detail(d) or "캡처·OCR 오류"
    return "kc_waiting", None


def kill_counter_loop():
    """게임 창 캡처 → (화면 변화 시) OCR → 세션·통계 갱신.
    감지 영역 픽셀이 이전과 비슷하면 OCR 생략.
    급증 확인(unstable)·OCR 실패(empty/error/no_pair) 구간은 변화 없어도 OCR 유지."""
    sct = mss.mss()
    while _state_gets("running"):
        snap = get_registry_config_snapshot()
        kc_en = snapshot_bool(snap, "kill_counter_enabled", _state_gets("kill_counter_enabled"))
        kc_roi = snap.get("kill_counter_detect_region", _state_gets("kill_counter_detect_region"))
        hwnd = _state_gets("target_hwnd")
        _kc_active = kc_en and hwnd and (not _state_gets("select_mode")) and kc_roi
        if not _kc_active:
            _state_set("_kill_counter_last_change_probe_bgr", None)
        if _kc_active:
            img = capture_region(hwnd, sct, kc_roi)
            _skip_ocr = _kill_counter_should_skip_ocr_same_screen(img)
            _kc_has = img is not None and getattr(img, "size", 0) > 0
            if _kc_has:
                telemetry_kc_frame(
                    skipped=bool(_skip_ocr),
                    ran_ocr=(not _skip_ocr),
                )
            if not _skip_ocr:
                _state_set("kill_counter_last_poll_ts", time.time())
                val, err, label_rect_cap, num_rect_cap, prog_txt = kill_counter_read_digits(img)
                raw_prog = (prog_txt or "").strip()
                if raw_prog:
                    n1s, n2s = _kill_counter_slash_pair_parts(raw_prog)
                    if n1s and n2s:
                        try:
                            n1 = int(n1s)
                            n2 = int(n2s)
                        except ValueError:
                            n1s = None
                    if n1s and n2s:
                        _acc = _kill_counter_ocr_n1_accept(n1)
                        if _acc:
                            _state_set("kill_counter_last_progress", raw_prog)
                            _prev_ph = _state_gets("kill_counter_last_poll_phase")
                            _recover = _prev_ph in ("empty", "error", "no_pair")
                            try:
                                if _recover:
                                    _kill_counter_reset_spike_confirm()
                                    _kill_counter_session_reanchor_after_ocr_gap(n1)
                                else:
                                    _before_k = _kill_counter_session_total_kills_display()
                                    _kill_counter_update_session_from_n1(n1)
                                    _after_k = _kill_counter_session_total_kills_display()
                                    if _after_k > _before_k:
                                        _kill_counter_stats_record_delta(
                                            _after_k - _before_k,
                                            allow_large_jump=(_acc == 2),
                                        )
                            except ValueError:
                                pass
                            try:
                                _kill_counter_stats_reconcile_with_n1(n1)
                            except Exception:
                                pass
                            _state_set("kill_counter_last_poll_phase", "ok")
                            _state_set("kill_counter_last_poll_detail", None)
                        else:
                            _prev = _state_gets("kill_counter_session_last_n1")
                            if _prev is None:
                                _prev = _state_gets("kill_counter_session_baseline_n1")
                            _kill_counter_ocr_maybe_log_reject(n1, _prev)
                            _last_prog = _state_gets("kill_counter_last_progress")
                            if _last_prog:
                                n1g, n2g = _kill_counter_slash_pair_parts(_last_prog)
                                if n1g and n2g:
                                    val = f"현재 킬 {_kill_counter_fmt_int_str(n1g)}"
                                    err = None
                            else:
                                val = None
                                err = err or "OCR 급증 무시"
                            _state_set("kill_counter_last_poll_phase", "unstable")
                            _state_set("kill_counter_last_poll_detail", "급증 의심 — 직전 표시 유지")
                    else:
                        _state_set("kill_counter_last_progress", raw_prog)
                        _state_set("kill_counter_last_poll_phase", "no_pair")
                        _state_set("kill_counter_last_poll_detail", "a/b 숫자 쌍 아님")
                else:
                    _state_set("kill_counter_last_progress", "")
                    if err:
                        _state_set("kill_counter_last_poll_phase", "error")
                        _state_set("kill_counter_last_poll_detail", err)
                    else:
                        _state_set("kill_counter_last_poll_phase", "empty")
                        _state_set("kill_counter_last_poll_detail", None)
                if label_rect_cap is not None or num_rect_cap is not None:
                    try:
                        if kc_roi is not None:
                            rp = get_region_pixels(hwnd, kc_roi)
                            if rp:
                                rx, ry = rp[0], rp[1]
                                if label_rect_cap is not None:
                                    l, t, r, b = label_rect_cap
                                    label_rect_cap = (l + rx, t + ry, r + rx, b + ry)
                                if num_rect_cap is not None:
                                    ln, tn, rn, bn = num_rect_cap
                                    num_rect_cap = (ln + rx, tn + ry, rn + rx, bn + ry)
                        _kill_counter_overlay_queue.put_nowait((label_rect_cap, num_rect_cap))
                    except Exception:
                        pass
            if img is not None and getattr(img, "size", 0) > 0:
                _state_set("_kill_counter_last_change_probe_bgr", np.ascontiguousarray(img))
        if _state_gets("running"):
            if _game_client_power_save_active:
                time.sleep(max(float(GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC), 0.03))
            else:
                time.sleep(max(0.03, float(_KILL_COUNTER_CHANGE_PROBE_SLEEP_SEC)))
    try:
        sct.close()
    except Exception:
        pass


def _template_match_threshold_for_kind(kind: str) -> float:
    """디버그·썸네일용 — kind별 매칭 기준(전역 변수명)."""
    return template_match_threshold_for_globals(globals(), kind)


def _debug_sample_template_match(kind: str):
    """
    설정 「감지」: 1회 캡처·매칭. 루프와 동일한 범위·스케일.
    전역 감지 점수(image_score 등)는 갱신하지 않음 — 「현재」 라벨은 백그라운드 루프 값 유지.
    반환: (score, err, rect, patch_bgr) — rect는 창 캡처 기준 (l,t,r,b); patch_bgr는 임계값 충족 시 매칭 패치(BGR).
    """
    global target_hwnd
    return _debug_sample_template_match_core(
        kind,
        globals(),
        target_hwnd=target_hwnd,
        get_launcher_hwnd=refresh_smart_updater_hwnd_if_needed,
    )


_template_debug_busy = False
_template_debug_state = threading.Lock()


def _template_debug_detect_run(kind: str, _ui_owner=None):
    """감지 1회: 「현재」 라벨은 건드리지 않고, 게임 위 오버레이에 박스·점수 표시.

    Qt GUI 스레드에서 호출될 수 있어 캡처·매칭은 백그라운드에서 수행한다.
    캡처 직전에 디버그 펄스 오버레이를 숨겨 mss 폴백 시에도 박스가 매칭에 끼지 않게 한다.
    """
    global _template_debug_busy
    with _template_debug_state:
        if _template_debug_busy:
            return
        _template_debug_busy = True

    def _work():
        global _template_debug_busy
        try:
            score, err, rect, patch_bgr = _debug_sample_template_match(kind)
            if err:
                meta = _template_capture_kind_meta(kind)
                tag = meta[2] if meta else kind
                print(f"[템플릿 감지] {tag}: {err}", flush=True)
                return
            if patch_bgr is not None:
                _template_last_hit_store(kind, patch_bgr, float(score))
            cap = f"{score:.2f}"
            if rect is not None:
                try:
                    _template_debug_overlay_queue.put_nowait((rect, cap, kind))
                except Exception:
                    pass
        except Exception as e:
            meta = _template_capture_kind_meta(kind)
            tag = meta[2] if meta else kind
            print(f"[템플릿 감지] {tag}: {e}", flush=True)
        finally:
            with _template_debug_state:
                _template_debug_busy = False

    ovl = globals().get("_qt_debug_pulse_overlay")
    if ovl is not None:
        try:
            ovl.prepare_template_test_capture()
        except Exception:
            pass

    def _start_worker():
        threading.Thread(target=_work, daemon=True).start()

    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            QTimer.singleShot(0, _start_worker)
            return
    except Exception:
        pass
    threading.Thread(target=_work, daemon=True).start()


def ride_loop():
    """Ride 루프 (target.png 이미지 감지) - 상시 작동"""
    global image_detected, image_score, running, target_hwnd, ride_detect_region, ride_feature_enabled
    
    sct = mss.mss()
    last_ratio = None
    template_original = None
    last_ride_path = None
    scaled_template = None
    
    while _state_gets("running"):
        snap = get_registry_config_snapshot()
        path_r = snap.get("RIDE_TARGET_IMAGE_PATH", RIDE_TARGET_IMAGE_PATH)
        prev_lp = last_ride_path
        template_original, last_ride_path = load_image_data_if_path_changed(
            path_r,
            "ride_target_image_data",
            last_ride_path,
            template_original,
        )
        if last_ride_path != prev_lp:
            last_ratio = None
            scaled_template = template_original

        if template_original is None:
            time.sleep(1.0)
            continue

        if target_hwnd and not select_mode and snapshot_bool(
            snap, "ride_feature_enabled", ride_feature_enabled,
        ):
            current_ratio = get_scale_ratio(target_hwnd)
            scaled_template, last_ratio = rescale_if_ratio_changed(
                template_original, scaled_template, current_ratio, last_ratio,
            )
            thr_r = snapshot_float(snap, "ride_threshold", ride_threshold)
            roi_r = snap.get("ride_detect_region", ride_detect_region)
            screen = capture_region(target_hwnd, sct, roi_r)
            _template_probe_mark("ride", "target")
            patch_r, score = _template_match_patch_if_ok(screen, scaled_template, thr_r)
            detected = patch_r is not None
            image_score = score  # AGENT: ride score GUI
            if detected and patch_r is not None:
                _template_last_hit_store("ride_target", patch_r, float(score))
            
            if detected != image_detected:
                image_detected = detected
                set_capslock(detected)  # AGENT: caps mirrors detect

        time.sleep(
            GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.05
        )
    
    sct.close()

def hp_refill_loop():
    """HP Refill 루프 (zkey.png 이미지 감지 시 설정 키 입력)"""
    global running, target_hwnd, hp_refill_detection_score, hp_refill_detect_region, hp_refill_key_code, hp_refill_feature_enabled, hp_refill_trigger_total
    
    sct = mss.mss()
    last_ratio = None
    template_original = None
    last_hp_zkey_path = None
    scaled_template = None
    hp_refill_last_key_time = -1.0  # AGENT: post-key cooldown
    HP_REFILL_KEY_COOLDOWN = 0.5
    _hp_shown_fail = False
    _hp_ok_logged = False
    
    while running:
        snap = get_registry_config_snapshot()
        path_z = snap.get("HP_REFILL_ZKEY_IMAGE_PATH", HP_REFILL_ZKEY_IMAGE_PATH)
        prev_zp = last_hp_zkey_path
        template_original, last_hp_zkey_path = load_image_data_if_path_changed(
            path_z,
            "hp_refill_zkey_image_data",
            last_hp_zkey_path,
            template_original,
        )
        if last_hp_zkey_path != prev_zp:
            last_ratio = None
            scaled_template = template_original
            _hp_ok_logged = False

        if template_original is None:
            if not _hp_shown_fail:
                print(f"{_LOG_HP_REFILL} 오류 zkey 템플릿 없음 (재시도)", flush=True)
                _hp_shown_fail = True
            time.sleep(1.0)
            continue
        _hp_shown_fail = False
        if not _hp_ok_logged:
            _loop_print(f"{_LOG_HP_REFILL} 템플릿 로드 OK (zkey)")
            roi0 = snap.get("hp_refill_detect_region", hp_refill_detect_region)
            _loop_print(
                f"{_LOG_HP_REFILL} 감지 모드: 지정 영역"
                if roi0
                else f"{_LOG_HP_REFILL} 감지 모드: 전체 화면",
            )
            _hp_ok_logged = True

        if target_hwnd and not select_mode and snapshot_bool(
            snap, "hp_refill_feature_enabled", hp_refill_feature_enabled,
        ):
            current_ratio = get_scale_ratio(target_hwnd)
            scaled_template, last_ratio = rescale_if_ratio_changed(
                template_original, scaled_template, current_ratio, last_ratio,
            )
            thr_h = snapshot_float(snap, "hp_refill_threshold", hp_refill_threshold)
            roi_h = snap.get("hp_refill_detect_region", hp_refill_detect_region)
            hp_kc = snapshot_int(snap, "hp_refill_key_code", int(hp_refill_key_code))
            screen = capture_region(target_hwnd, sct, roi_h)
            _template_probe_mark("hp_refill", "zkey")
            patch_h, score = _template_match_patch_if_ok(screen, scaled_template, thr_h)
            detected = patch_h is not None
            hp_refill_detection_score = score  # AGENT: score for GUI
            if detected and patch_h is not None:
                _template_last_hit_store("hp_zkey", patch_h, float(score))
            
            if detected:
                now = time.time()
                if hp_refill_last_key_time < 0 or (now - hp_refill_last_key_time) >= HP_REFILL_KEY_COOLDOWN:
                    send_key(hp_kc, target_hwnd)
                    hp_refill_last_key_time = now
                    hp_refill_trigger_total += 1
                    _loop_print(
                        f"{_LOG_HP_REFILL} 템플릿 매칭 → 키 입력 "
                        f"{vk_to_display_name(hp_kc)} (누적 {hp_refill_trigger_total}회)",
                    )

        time.sleep(
            GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.05
        )
    
    sct.close()

def reload_loop():
    """Reload 루프"""
    global flame_trigger_session_reload_count, flame_trigger_last_reload_complete_time
    global flame_trigger_last_reload_trigger_time
    global flame_trigger_hud_session_start_time, flame_trigger_reload_teardown_preserve_hud
    
    sct = mss.mss()
    last_ratio = None
    scaled_nobullet = None
    scaled_bullet = None
    check_count = 0
    nobullet_template = None
    bullet_template = None
    last_nobullet_path = None
    last_bullet_path = None
    vault_template = None
    last_vault_path = None
    path_check_count = 0

    def load_templates(path_snap=None):
        """템플릿 이미지 로드 (경로 변경 시 재로드)"""
        nonlocal nobullet_template, bullet_template, last_nobullet_path, last_bullet_path, scaled_nobullet, scaled_bullet, last_ratio
        snap_lt = (
            path_snap if path_snap is not None else get_registry_config_snapshot()
        )
        path_nb = snap_lt.get("RELOAD_NOBULLET_IMAGE_PATH", RELOAD_NOBULLET_IMAGE_PATH)
        path_bu = snap_lt.get("RELOAD_BULLET_IMAGE_PATH", RELOAD_BULLET_IMAGE_PATH)
        ok, _attempted, pair = reload_try_reload_nobullet_bullet_templates(
            path_nb,
            path_bu,
            last_nobullet_path,
            last_bullet_path,
            nobullet_template,
            bullet_template,
        )
        if not ok:
            return False
        if pair is not None:
            nobullet_template, bullet_template, last_nobullet_path, last_bullet_path = pair
            scaled_nobullet = None
            scaled_bullet = None
            last_ratio = None
            _loop_print(f"{_LOG_RELOAD} 템플릿 로드 OK (탄약없음·슬롯)")
        return nobullet_template is not None and bullet_template is not None
    
    # AGENT: initial template load
    load_templates()
    
    while running:
        _snap_cached = None

        def snap_once():
            nonlocal _snap_cached
            if _snap_cached is None:
                _snap_cached = get_registry_config_snapshot()
            return _snap_cached

        # AGENT: poll path + reload template every 5s.
        path_check_count += 1
        if path_check_count >= 5:
            path_check_count = 0
            if not load_templates(snap_once()):
                time.sleep(1.0)
                continue
        
        hwnd = _state_gets("target_hwnd")
        if hwnd and _state_gets("reload_active") and not _state_gets("select_mode"):
            snap = snap_once()
            thr_nb = snapshot_float(snap, "reload_nobullet_threshold", reload_nobullet_threshold)
            thr_bu = snapshot_float(snap, "reload_bullet_threshold", reload_bullet_threshold)
            thr_v = snapshot_float(snap, "reload_vault_threshold", reload_vault_threshold)
            ammo_count_local = snapshot_int(
                snap, "reload_ammo_count", int(_state_gets("reload_ammo_count"))
            )
            roi_nb = snap.get("reload_nobullet_match_region", reload_nobullet_match_region)
            roi_bu = snap.get("reload_bullet_match_region", reload_bullet_match_region)
            roi_v = snap.get("reload_vault_match_region", reload_vault_match_region)
            # AGENT: try load template if missing.
            if nobullet_template is None or bullet_template is None:
                if not load_templates(snap_once()):
                    time.sleep(1.0)
                    continue
            
            current_ratio = get_scale_ratio(hwnd)
            if current_ratio is None or current_ratio <= 0:
                time.sleep(0.5)
                continue
            
            scaled_nobullet, scaled_bullet, last_ratio, _ = (
                reload_rescale_nobullet_bullet_if_needed(
                    nobullet_template,
                    bullet_template,
                    scaled_nobullet,
                    scaled_bullet,
                    current_ratio,
                    last_ratio,
                )
            )
            
            # AGENT: skip nobullet detect while reload job active.
            if _state_gets("nobullet_detected"):
                _g_r = globals()
                _t0r = float(_g_r.get("reload_intermediate_started_mono") or 0.0)
                if (
                    _t0r > 0.0
                    and time.monotonic() - _t0r > RELOAD_SEQUENCE_STUCK_SEC
                ):
                    _loop_print(
                        f"{_LOG_RELOAD}[중단] NoBullet 래치 {RELOAD_SEQUENCE_STUCK_SEC:.0f}초 이상 "
                        "진전 없음 — 시퀀스 취소",
                    )
                    _state_set("nobullet_detected", False)
                    _reload_set_seq_step(0)
                else:
                    time.sleep(0.1)
                continue
            
            # AGENT: nobullet ① 재무장 쿨다운 — monotonic (GUI 게이지와 동일)
            _now_m = time.monotonic()
            if (
                _state_gets("reload_nobullet_arm_until_mono") > 0.0
                and _now_m < _state_gets("reload_nobullet_arm_until_mono")
            ):
                _reload_set_seq_step(0)
                check_count += 1
                if check_count >= 10:  # AGENT: poll every 10 ticks
                    check_count = 0
                time.sleep(1.0)  # AGENT: 1s sleep in branch
                continue
            
            if scaled_nobullet is None or scaled_bullet is None:
                time.sleep(0.5)
                continue
            
            # AGENT: nobullet poll every 1s in this branch.
            screen = capture_region(hwnd, sct, roi_nb)
            if screen is None:
                time.sleep(1.0)
                continue
            
            if scaled_nobullet is None or nobullet_template is None:
                time.sleep(0.5)
                continue
            
            _template_probe_mark("reload", "nobullet")
            patch_nb, score = _template_match_patch_if_ok(screen, scaled_nobullet, thr_nb)
            detected = patch_nb is not None
            _state_set("nobullet_detection_score", score)  # AGENT: score for GUI
            if detected and patch_nb is not None:
                _template_last_hit_store("reload_nobullet", patch_nb, float(score))
            # AGENT: while① idle do not capture/match②③ (bullet,vault).
            # AGENT: NOTE: old idle score refresh looked like periodic "detect" in UI.
            _state_set("bullet_detection_score", 0.0)
            _state_set("vault_detection_score", 0.0)

            # AGENT: detection state gate.
            check_count += 1
            if check_count >= 5:  # AGENT: idle check cadence
                check_count = 0
            
            if detected:
                _loop_print(f"{_LOG_RELOAD}[①] 탄약 없음(NoBullet) 템플릿 매칭 성공 — 재장전 시퀀스 시작")
                _state_set("nobullet_detected", True)
                _reload_set_seq_step(1)
                _state_set("last_nobullet_time", time.time())  # AGENT: latch detect ts
                _state_set(
                    "reload_nobullet_arm_until_mono",
                    time.monotonic() + RELOAD_NOBULLET_REARM_COOLDOWN_SEC
                )

                # AGENT: release flame: RMB up + stop merc-fire loop.
                global flame_trigger_active, flame_trigger_start_time, flame_trigger_feature_enabled
                global flame_trigger_reload_teardown_preserve_hud
                _reload_had_ft = bool(_state_gets("flame_trigger_active"))
                if _reload_had_ft:
                    _state_set("flame_trigger_last_reload_trigger_time", time.time())
                    _state_set("flame_trigger_reload_teardown_preserve_hud", True)

                def _reload_ft_disable():
                    global flame_trigger_active
                    _state_set("flame_trigger_active", False)
                    mouse_right_up()
                    win32_clip_cursor_release()

                automation_disable_flame_trigger_if_active(
                    flame_trigger_active=_reload_had_ft,
                    disable=_reload_ft_disable,
                )
                _loop_print(
                    f"{_LOG_RELOAD}[①] 플레임 트리거 일시 정지 (우클릭 해제)"
                    if _reload_had_ft
                    else f"{_LOG_RELOAD}[①] 플레임 트리거 비활성 — 대기 상태 유지",
                )
                try:
                
                    time.sleep(1.0)
                
                    _loop_print(f"{_LOG_RELOAD}[②] 1초 대기 후 탄약 슬롯 캡처·매칭")
                    screen = capture_region(hwnd, sct, roi_bu)
                    if screen is None:
                        print(f"{_LOG_RELOAD}[②][실패] 탄 슬롯 영역 캡처 실패", flush=True)
                        _state_set("nobullet_detected", False)
                        _reload_set_seq_step(0)
                        time.sleep(0.5)
                        continue
                
                    if scaled_bullet is None:
                        print(f"{_LOG_RELOAD}[②][실패] 탄 슬롯 템플릿 없음", flush=True)
                        _state_set("nobullet_detected", False)
                        _reload_set_seq_step(0)
                        time.sleep(0.5)
                        continue
                
                    b_score, b_tl, bullet_pos = reload_match_bullet_on_screen(
                        screen,
                        scaled_bullet,
                        thr_bu,
                        on_patch=lambda p, sc: _template_last_hit_store(
                            "reload_bullet", p, float(sc),
                        ),
                        probe=lambda: _template_probe_mark("reload", "bullet"),
                    )
                    _state_set("bullet_detection_score", b_score)

                    if bullet_pos is None and roi_v is not None:
                        _reload_set_seq_step(2)
                        _loop_print(f"{_LOG_RELOAD}[②-보조] 금고(Vault) 템플릿 경로 — 슬롯이 안 보일 때 처리")
                        mp = snap.get("RELOAD_VAULT_IMAGE_PATH", RELOAD_VAULT_IMAGE_PATH)
                        vault_template, last_vault_path = load_image_data_if_path_changed(
                            mp,
                            "reload_vault_image_data",
                            last_vault_path,
                            vault_template,
                        )
                        if vault_template is not None:
                            sm = scale_template(vault_template, current_ratio)
                            scr_m = capture_region(hwnd, sct, roi_v)
                            if scr_m is not None and sm is not None:
                                _vault_score, m_tl = reload_match_vault_on_screen(
                                    scr_m,
                                    sm,
                                    thr_v,
                                    on_patch=lambda p, sc: _template_last_hit_store(
                                        "reload_vault", p, float(sc),
                                    ),
                                    probe=lambda: _template_probe_mark("reload", "vault"),
                                )
                                _state_set("vault_detection_score", _vault_score)
                                mh, mw = int(sm.shape[0]), int(sm.shape[1])
                                abs_v = _match_center_to_screen_xy(
                                    hwnd,
                                    roi_v,
                                    m_tl,
                                    mw,
                                    mh,
                                )
                                if (
                                    m_tl is not None
                                    and _vault_score >= thr_v
                                    and abs_v is not None
                                ):
                                    abs_x, abs_y = abs_v
                                    _loop_print(
                                        f"{_LOG_RELOAD}[②-보조] 금고 더블클릭 좌표 ({abs_x},{abs_y})",
                                    )
                                    reload_move_sleep_double_click(
                                        abs_x,
                                        abs_y,
                                        mouse_move_fn=mouse_move,
                                        mouse_double_click_fn=mouse_double_click,
                                    )
                                    _loop_print(f"{_LOG_RELOAD}[②-보조] 금고 입력 완료 → 탄약 슬롯 다시 확인")
                                    time.sleep(0.35)
                                    screen = capture_region(hwnd, sct, roi_bu)
                                    if screen is not None and scaled_bullet is not None:
                                        _reload_set_seq_step(1)
                                        b_score, b_tl, bullet_pos = (
                                            reload_match_bullet_on_screen(
                                                screen,
                                                scaled_bullet,
                                                thr_bu,
                                                on_patch=lambda p, sc: _template_last_hit_store(
                                                    "reload_bullet", p, float(sc),
                                                ),
                                                probe=lambda: _template_probe_mark(
                                                    "reload", "bullet"
                                                ),
                                            )
                                        )
                                        _state_set("bullet_detection_score", b_score)
                                    else:
                                        bullet_pos = None
                
                    if bullet_pos:
                        _loop_print(f"{_LOG_RELOAD}[②] 탄약 슬롯 매칭 성공")
                        bh, bw = scaled_bullet.shape[:2]
                        abs_pt = _match_center_to_screen_xy(
                            hwnd, roi_bu, b_tl, bw, bh,
                        )
                        if abs_pt is not None:
                            abs_x, abs_y = abs_pt
                            _loop_print(f"{_LOG_RELOAD}[③] 탄약 슬롯 더블클릭 좌표 ({abs_x},{abs_y})")
                            reload_move_sleep_double_click(
                                abs_x,
                                abs_y,
                                mouse_move_fn=mouse_move,
                                mouse_double_click_fn=mouse_double_click,
                            )
                            _loop_print(f"{_LOG_RELOAD}[③] 탄약 슬롯 더블클릭 완료")
                        
                            # AGENT: keyboard: ammo count digits + Enter.
                            ammo_n, digits = reload_clamp_ammo_count(ammo_count_local)
                            _loop_print(f"{_LOG_RELOAD}[④] 입력할 탄약 수: {ammo_n}")
                            _reload_set_seq_step(3)
                            reload_send_digit_keys_and_return(digits, hwnd, send_key)
                            _loop_print(
                                f"{_LOG_RELOAD}[④] 숫자 키·Enter 전송 ({digits} + Enter)",
                            )

                            def _reload_ft_enable():
                                global flame_trigger_active, flame_trigger_start_time
                                _pause_left_click_and_right_hold_for_flame_trigger()
                                _state_set("flame_trigger_active", True)
                                _state_set("flame_trigger_start_time", time.time())

                            if automation_reenable_flame_trigger_after_success(
                                feature_enabled=snapshot_bool(
                                    snap,
                                    "flame_trigger_feature_enabled",
                                    flame_trigger_feature_enabled,
                                ),
                                restore_flag=_reload_had_ft,
                                enable=_reload_ft_enable,
                            ):
                                _loop_print(f"{_LOG_RELOAD}[⑤] 플레임 트리거 재개")
                            else:
                                _loop_print(f"{_LOG_RELOAD}[⑤] 플레임 트리거 재개 생략 (설정 또는 이전 상태)")
                        
                            _next_reload_ok = _state_inc_int("reload_success_count")
                            _kill_counter_stats_record_reload_mark(time.time())
                            _loop_print(f"{_LOG_RELOAD}[완료] 재장전 성공 (누적 {_next_reload_ok}회)")
                            if _reload_had_ft:
                                _state_inc_int("flame_trigger_session_reload_count")
                                _state_set("flame_trigger_last_reload_complete_time", time.time())
                            _state_set("nobullet_detected", False)  # AGENT: job done reset
                            _reload_set_seq_step(0)
                        else:
                            print(f"{_LOG_RELOAD}[③][실패] 더블클릭 좌표 계산 실패 (창 사각형)", flush=True)
                            _state_set("nobullet_detected", False)
                            _reload_set_seq_step(0)
                    else:
                        print(f"{_LOG_RELOAD}[②][실패] 탄약 슬롯 매칭 실패 — 시퀀스 중단", flush=True)
                        _state_set("nobullet_detected", False)
                        _reload_set_seq_step(0)
                finally:
                    _state_set("flame_trigger_reload_teardown_preserve_hud", False)
                    if _reload_had_ft and not _state_gets("flame_trigger_active"):
                        _state_set("flame_trigger_hud_session_start_time", 0.0)
                        _state_set("flame_trigger_session_reload_count", 0)
                        _state_set("flame_trigger_last_reload_complete_time", 0.0)
                        _state_set("flame_trigger_last_reload_trigger_time", 0.0)

            else:
                _reload_set_seq_step(0)

        # AGENT: default 1s poll (busy path continues earlier).
        time.sleep(GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 1.0)
    
    sct.close()

# AGENT: ammo restock catalog pipela_core.ammo_restock_catalog; main-only UI tuples.
_AMMO_SETTINGS_SECTIONS = (
    (
        "1. 구매 버튼",
        "buybutton",
        "buybutton_preview_label",
        SETTINGS_SECTION_TITLE_FONT,
        None,
        "_ar_suffix_buy",
        "ammo_restock_buybutton_threshold",
    ),
    (
        "2. 인벤토리",
        "inven",
        "inven_preview_label",
        SETTINGS_SUBSECTION_TITLE_FONT,
        SETTINGS_SECTION_SUB_HEADING_FG,
        "_ar_suffix_inven",
        "ammo_restock_inven_threshold",
    ),
    (
        "3. 은행",
        "bank",
        "bank_preview_label",
        SETTINGS_SUBSECTION_TITLE_FONT,
        SETTINGS_SECTION_SUB_HEADING_FG,
        "_ar_suffix_bank",
        "ammo_restock_bank_threshold",
    ),
)

# AGENT: call merc catalog pipela_core.call_merc_catalog; main-only UI tuples.
_CALL_MERC_SETTINGS_SECTIONS = (
    (
        "1. 트리거 · 용병 없음 안내",
        "call_merc_1",
        "cm_pr_1",
        SETTINGS_SECTION_TITLE_FONT,
        None,
        "_cm_sfx_1",
        "call_merc_1_threshold",
    ),
    (
        "2. 고용계약서 · 더블클릭",
        "call_merc_2",
        "cm_pr_2",
        SETTINGS_SUBSECTION_TITLE_FONT,
        SETTINGS_SECTION_SUB_HEADING_FG,
        "_cm_sfx_2",
        "call_merc_2_threshold",
    ),
    (
        "3. 호출 · 클릭",
        "call_merc_3",
        "cm_pr_3",
        SETTINGS_SUBSECTION_TITLE_FONT,
        SETTINGS_SECTION_SUB_HEADING_FG,
        "_cm_sfx_3",
        "call_merc_3_threshold",
    ),
    (
        "4. 창 닫기 · 클릭",
        "call_merc_4",
        "cm_pr_4",
        SETTINGS_SUBSECTION_TITLE_FONT,
        SETTINGS_SECTION_SUB_HEADING_FG,
        "_cm_sfx_4",
        "call_merc_4_threshold",
    ),
)


def _ammo_roi_val(kind: str):
    return globals()[_AMMO_MATCH_ROI_GLOBAL[kind]]


def _ammo_restock_click_at_match(hwnd, roi, tl, scaled_template, log_tag: str):
    bh, bw = scaled_template.shape[:2]
    abs_pt = _match_center_to_screen_xy(hwnd, roi, tl, bw, bh)
    if abs_pt is None:
        return
    abs_x, abs_y = abs_pt
    _st = _AMMO_STAGE_KO.get(log_tag, log_tag)
    _loop_print(f"{_LOG_AMMO_RESTOCK} {_st} — 클릭 좌표 ({abs_x},{abs_y})")
    mouse_move(abs_x, abs_y)
    time.sleep(0.05)
    mouse_click()
    _loop_print(f"{_LOG_AMMO_RESTOCK} {_st} — 클릭 완료")


def _ammo_restock_thr_global_set(kind, v):
    g = globals()
    g[_AMMO_THR_GLOBAL_BY_KIND[kind]] = v
    if kind == "buybutton":
        g["ammo_restock_threshold"] = v


def _ammo_restock_thr_global_get(kind):
    return globals()[_AMMO_THR_GLOBAL_BY_KIND[kind]]


def _call_merc_thr_global_set(kind, v):
    globals()[_CALL_MERC_THR_KEY[kind]] = v


def _call_merc_thr_global_get(kind):
    return globals()[_CALL_MERC_THR_KEY[kind]]


def _call_merc_ui_sync_phase(prev: int, new: int) -> None:
    """call_merc_loop 단계 변경 시 설정창 화살표 애니메이션과 동기(워커 스레드에서 호출)."""
    g = globals()
    g["call_merc_phase_ui"] = new
    _seq_scroll(FEAT_CALL_MERC, int(new))
    nin = int(new)
    if nin in (1, 2, 3):
        g["call_merc_intermediate_started_mono"] = time.monotonic()
    else:
        g["call_merc_intermediate_started_mono"] = 0.0
    g["call_merc_arrow_pulse_mono"] = time.monotonic()
    if prev == 0 and new == 1:
        g["call_merc_arrow_pulse_idx"] = 0
    elif prev == 1 and new == 2:
        g["call_merc_arrow_pulse_idx"] = 1
    elif prev == 2 and new == 3:
        g["call_merc_arrow_pulse_idx"] = 2
    elif prev == 3 and new == 0:
        g["call_merc_arrow_pulse_idx"] = 3
    else:
        g["call_merc_arrow_pulse_idx"] = -1


def _call_merc_abort_stuck_mid_sequence(
    *,
    phase_was: int,
    ft_en: bool,
) -> None:
    """Steps 1–3: 템플릿 진전 없이 CALL_MERC_SEQUENCE_STUCK_SEC 초과 시 idle로."""
    g = globals()
    _loop_print(
        f"{_LOG_CALL_MERC}[중단] 중간 단계 {int(phase_was)}에서 "
        f"{CALL_MERC_SEQUENCE_STUCK_SEC:.0f}초 이상 진전 없음 — 대기(①)로 복귀",
    )

    def _merc_ft_enable():
        global flame_trigger_active, flame_trigger_start_time
        _pause_left_click_and_right_hold_for_flame_trigger()
        _state_set("flame_trigger_active", True)
        _state_set("flame_trigger_start_time", time.time())

    if automation_reenable_flame_trigger_after_success(
        feature_enabled=ft_en,
        restore_flag=bool(g.get("call_merc_restore_ft_after_cycle")),
        enable=_merc_ft_enable,
    ):
        _loop_print(f"{_LOG_CALL_MERC}[복구] 플레임 트리거 재개")
    else:
        _loop_print(f"{_LOG_CALL_MERC}[복구] 플레임 트리거 재개 생략")
    g["call_merc_restore_ft_after_cycle"] = False
    _prev = int(phase_was)
    _call_merc_ui_sync_phase(_prev, 0)
    g["call_merc_sequence_busy"] = False


def _call_merc_match_one_kind(
    g,
    kind,
    target_hwnd,
    sct,
    scaled,
    *,
    match_threshold: float | None = None,
    roi_override=None,
):
    """Call Merc — 현재 단계만 캡처·매칭(②는 ②만 확인한 뒤 더블클릭 등)."""
    _template_probe_mark("call_merc", kind)
    return _call_merc_match_one_kind_core(
        g,
        kind,
        target_hwnd,
        sct,
        scaled,
        on_patch_hit=_template_last_hit_store,
        match_threshold=match_threshold,
        roi_override=roi_override,
    )


def _call_merc_click_at_match(hwnd, roi, tl, scaled_template, *, double: bool, log_tag: str):
    bh, bw = scaled_template.shape[:2]
    abs_pt = _match_center_to_screen_xy(hwnd, roi, tl, bw, bh)
    if abs_pt is None:
        return
    abs_x, abs_y = abs_pt
    # AGENT: double-click token matches [Reload] dbc.
    _st = _CALL_MERC_STAGE_KO.get(log_tag, log_tag)
    if double:
        _loop_print(f"{_LOG_CALL_MERC} {_st} — 더블클릭 좌표 ({abs_x},{abs_y})")
    else:
        _loop_print(f"{_LOG_CALL_MERC} {_st} — 클릭 좌표 ({abs_x},{abs_y})")
    mouse_move(abs_x, abs_y)
    time.sleep(0.08)
    if double:
        mouse_double_click()
        _loop_print(f"{_LOG_CALL_MERC} {_st} — 더블클릭 완료")
    else:
        mouse_click()
        _loop_print(f"{_LOG_CALL_MERC} {_st} — 클릭 완료")


def ammo_restock_loop():
    """Ammo Restock 루프"""

    g = globals()
    templates: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    last_ammo_paths: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    sct = mss.mss()
    last_ratio = None
    scaled: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    _ammo_ok_logged = False
    _ammo_fail_shown = False
    
    while _state_gets("running"):
        hwnd = _state_gets("target_hwnd")
        if hwnd and _state_gets("ammo_restock_active") and not _state_gets("select_mode"):
            snap = get_registry_config_snapshot()
            ok, path_changed = ammo_restock_sync_templates(
                g, templates, last_ammo_paths, path_snap=snap,
            )
            if path_changed:
                last_ratio = None
            if not ok:
                _ammo_ok_logged = False
                if not _ammo_fail_shown:
                    print(f"{_LOG_AMMO_RESTOCK} 오류 템플릿 없음 (재시도)", flush=True)
                    _ammo_fail_shown = True
                time.sleep(1.0)
                continue
            _ammo_fail_shown = False
            if not _ammo_ok_logged:
                _loop_print(f"{_LOG_AMMO_RESTOCK} 템플릿 로드 OK (구매·인벤·은행)")
                _ammo_ok_logged = True
            thr_bb = snapshot_float(
                snap, "ammo_restock_buybutton_threshold", g["ammo_restock_buybutton_threshold"],
            )
            thr_in = snapshot_float(
                snap, "ammo_restock_inven_threshold", g["ammo_restock_inven_threshold"],
            )
            thr_bk = snapshot_float(
                snap, "ammo_restock_bank_threshold", g["ammo_restock_bank_threshold"],
            )
            roi_bb = snap.get("ammo_buybutton_match_region", g["ammo_buybutton_match_region"])
            roi_in = snap.get("ammo_inven_match_region", g["ammo_inven_match_region"])
            roi_bk = snap.get("ammo_bank_match_region", g["ammo_bank_match_region"])
            current_ratio = get_scale_ratio(hwnd)
            last_ratio, ratio_changed = refresh_scaled_map_if_ratio_changed(
                templates, scaled, _AMMO_RESTOCK_KINDS, current_ratio, last_ratio,
            )
            if ratio_changed:
                size = get_window_size(target_hwnd)
                if size:
                    _loop_print(
                        f"{_LOG_AMMO_RESTOCK} 해상도 스케일 {size[0]}×{size[1]} "
                        f"(배율 {current_ratio:.2f})",
                    )
            
            screen = capture_region(hwnd, sct, roi_bb)
            if screen is None:
                time.sleep(0.5)
                continue
            
            st_buy = scaled["buybutton"]
            _template_probe_mark("ammo_restock", "buybutton")
            _bb_score, buy_tl = _match_template_ccoeff_normed_max(screen, st_buy)
            _state_set("ammo_restock_buybutton_score", _bb_score)
            # Idle: 1단계(구매 버튼)만 감지 — 이전에 inven/bank를 같이 돌리면 UI·점수가 동시에 올라옴.
            _state_set("ammo_restock_inven_score", 0.0)
            _state_set("ammo_restock_bank_score", 0.0)

            if buy_tl is not None and _state_gets("ammo_restock_buybutton_score") >= thr_bb:
                buybutton_pos = True
                pb = _template_extract_match_patch(screen, st_buy, buy_tl)
                if pb is not None:
                    _template_last_hit_store(
                        "ammo_buybutton",
                        pb,
                        float(_state_gets("ammo_restock_buybutton_score")),
                    )
            else:
                buybutton_pos = None
            
            if buybutton_pos:
                if get_window_rect(hwnd):
                    with _ammo_restock_sequence_guard():
                        _ammo_restock_click_at_match(
                            hwnd, roi_bb, buy_tl, st_buy, _AMMO_LOOP_LOG_TAG["buybutton"],
                        )
                        time.sleep(0.1)
                        send_key(VK_4)
                        time.sleep(0.05)
                        send_key(VK_5)
                        time.sleep(0.05)
                        send_key(VK_RETURN)
                        _loop_print(f"{_LOG_AMMO_RESTOCK}[①] 구매 버튼 클릭 후 단축키 4, 5, Enter 전송")
                        _seq_scroll(FEAT_AMMO_RESTOCK, 1)
                        _state_set("ammo_restock_buybutton_score", 0.0)

                        time.sleep(0.15)
                        screen = capture_region(hwnd, sct, roi_in)
                        if screen is None:
                            _state_set("ammo_restock_inven_score", 0.0)
                            print(f"{_LOG_AMMO_RESTOCK}[②][실패] 인벤 영역 캡처 실패", flush=True)
                            time.sleep(0.2)
                            continue
                        
                        st_inv = scaled["inven"]
                        _template_probe_mark("ammo_restock", "inven")
                        _in_score, inv_tl = _match_template_ccoeff_normed_max(screen, st_inv)
                        _state_set("ammo_restock_inven_score", _in_score)
                        if inv_tl is not None and _state_gets("ammo_restock_inven_score") >= thr_in:
                            inven_pos = True
                            pi = _template_extract_match_patch(screen, st_inv, inv_tl)
                            if pi is not None:
                                _template_last_hit_store(
                                    "ammo_inven",
                                    pi,
                                    float(_state_gets("ammo_restock_inven_score")),
                                )
                        else:
                            inven_pos = None
                        
                        if inven_pos:
                            _seq_scroll(FEAT_AMMO_RESTOCK, 2)
                            _ammo_restock_click_at_match(
                                hwnd, roi_in, inv_tl, st_inv, _AMMO_LOOP_LOG_TAG["inven"],
                            )
                            time.sleep(0.15)
                            screen = capture_region(hwnd, sct, roi_bk)
                            if screen is None:
                                _state_set("ammo_restock_bank_score", 0.0)
                                print(f"{_LOG_AMMO_RESTOCK}[③][실패] 은행 영역 캡처 실패", flush=True)
                                time.sleep(0.2)
                                continue

                            st_bnk = scaled["bank"]
                            _template_probe_mark("ammo_restock", "bank")
                            _bk_score, bank_tl = _match_template_ccoeff_normed_max(screen, st_bnk)
                            _state_set("ammo_restock_bank_score", _bk_score)
                            if bank_tl is not None and _state_gets("ammo_restock_bank_score") >= thr_bk:
                                bank_pos = True
                                pbnk = _template_extract_match_patch(screen, st_bnk, bank_tl)
                                if pbnk is not None:
                                    _template_last_hit_store(
                                        "ammo_bank",
                                        pbnk,
                                        float(_state_gets("ammo_restock_bank_score")),
                                    )
                            else:
                                bank_pos = None
                            
                            if bank_pos:
                                _seq_scroll(FEAT_AMMO_RESTOCK, 3)
                                _ammo_restock_click_at_match(
                                    hwnd, roi_bk, bank_tl, st_bnk, _AMMO_LOOP_LOG_TAG["bank"],
                                )
                                _next_cycle = _state_inc_int("ammo_restock_loop_count")
                                _loop_print(
                                    f"{_LOG_AMMO_RESTOCK}[완료] 한 사이클 성공 (누적 {_next_cycle}회)",
                                )
                                time.sleep(0.1)
                                _seq_scroll(FEAT_AMMO_RESTOCK, 0)
                                continue
                            else:
                                print(f"{_LOG_AMMO_RESTOCK}[③][실패] 은행 매칭·클릭 실패", flush=True)
                                time.sleep(0.2)
                                continue
                        else:
                            print(f"{_LOG_AMMO_RESTOCK}[②][실패] 인벤 매칭·클릭 실패", flush=True)
                            time.sleep(0.2)
                            continue
                else:
                    print(f"{_LOG_AMMO_RESTOCK}[실패] 게임 창 사각형 없음", flush=True)
                    time.sleep(0.2)
                    continue
            else:
                _seq_scroll(FEAT_AMMO_RESTOCK, 0)
                time.sleep(0.2)
                continue
        else:
            _seq_scroll(FEAT_AMMO_RESTOCK, 0)
            time.sleep(
                GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.1
            )
    
    sct.close()
    _loop_print(f"{_LOG_AMMO_RESTOCK} 워커 루프 종료")


def call_merc_loop():
    """용병 호출 — ①은 트리거만; ②③④는 단계마다 ROI만 확인 후 클릭. ① 직전 FT가 켜져 있었을 때만 끝에 FT 재켜기."""
    global call_merc_active, call_merc_sequence_busy, running, target_hwnd, call_merc_loop_count
    global call_merc_restore_ft_after_cycle, call_merc_arm_until_mono
    global call_merc_1_threshold, call_merc_2_threshold, call_merc_3_threshold, call_merc_4_threshold
    global call_merc_1_score, call_merc_2_score, call_merc_3_score, call_merc_4_score
    global flame_trigger_active, flame_trigger_start_time, flame_trigger_feature_enabled

    g = globals()
    templates = {k: None for k in _CALL_MERC_KINDS}
    last_paths = {k: None for k in _CALL_MERC_KINDS}
    sct = mss.mss()
    last_ratio = None
    scaled = {}
    phase = 0  # AGENT: 0 watch① like nobullet; 1-3 do②④
    _arm_until = 0.0
    _merc_template_reload_next_mono = 0.0

    def load_templates(path_snap=None):
        """경로 변경 또는 미로드 시에만 디스크/레지스트리 로드 — Reload 와 동일 패턴."""
        nonlocal templates, last_ratio, scaled, last_paths, _merc_template_reload_next_mono
        r = call_merc_try_reload_templates(
            g,
            templates,
            last_paths,
            now_mono=time.monotonic(),
            cooldown_until_mono=_merc_template_reload_next_mono,
            path_snap=path_snap,
        )
        _merc_template_reload_next_mono = r.cooldown_until_mono
        if r.sync_last_paths is not None:
            for k in _CALL_MERC_KINDS:
                last_paths[k] = r.sync_last_paths[k]
        if not r.ok:
            return False
        if r.templates is not None:
            templates = r.templates
            scaled = {k: templates[k] for k in _CALL_MERC_KINDS}
            last_ratio = None
            _loop_print(
                f"{_LOG_CALL_MERC} 템플릿 로드 OK (①트리거·②계약·③호출·④닫기)",
            )
        return True

    load_templates(get_registry_config_snapshot())

    while running:
        snap = get_registry_config_snapshot()
        merc_on = snapshot_bool(snap, "call_merc_active", call_merc_active)
        if not merc_on:
            if phase != 0:
                phase = 0
            g["call_merc_phase_ui"] = 0
            g["call_merc_arrow_pulse_idx"] = -1
            g["call_merc_intermediate_started_mono"] = 0.0
            call_merc_sequence_busy = False
            call_merc_restore_ft_after_cycle = False
            call_merc_arm_until_mono = 0.0
            _seq_scroll(FEAT_CALL_MERC, 0)

        if not load_templates(snap):
            time.sleep(1.0)
            continue

        # AGENT: always sync phase with loop state (stale yellow "busy" if load/target/select diverge).
        if merc_on:
            call_merc_sequence_busy = phase != 0

        if target_hwnd and merc_on and not select_mode:
            merc_thr = {
                k: snapshot_float(snap, _CALL_MERC_THR_KEY[k], float(g[_CALL_MERC_THR_KEY[k]]))
                for k in _CALL_MERC_KINDS
            }
            merc_roi = {
                k: snap.get(_CALL_MERC_ROI_KEY[k], g[_CALL_MERC_ROI_KEY[k]])
                for k in _CALL_MERC_KINDS
            }
            ft_en = snapshot_bool(snap, "flame_trigger_feature_enabled", flame_trigger_feature_enabled)
            current_ratio = get_scale_ratio(target_hwnd)
            if current_ratio is None or current_ratio <= 0:
                time.sleep(0.5)
                continue

            last_ratio, ratio_changed = refresh_scaled_map_if_ratio_changed(
                templates, scaled, _CALL_MERC_KINDS, current_ratio, last_ratio,
            )
            if ratio_changed:
                size = get_window_size(target_hwnd)
                if size:
                    _loop_print(
                        f"{_LOG_CALL_MERC} 해상도 스케일 {size[0]}×{size[1]} "
                        f"(배율 {current_ratio:.2f})",
                    )

            if phase == 0:
                if time.monotonic() < _arm_until:
                    time.sleep(0.06)
                    continue
                call_merc_arm_until_mono = 0.0
                k = "call_merc_1"
                tl1 = _call_merc_match_one_kind(
                    g,
                    k,
                    target_hwnd,
                    sct,
                    scaled,
                    match_threshold=merc_thr[k],
                    roi_override=merc_roi[k],
                )
                if tl1 is not None and g[_CALL_MERC_SCORE_KEY[k]] >= merc_thr[k]:
                    _prev = phase
                    phase = 1
                    _call_merc_ui_sync_phase(_prev, phase)
                    _loop_print(f"{_LOG_CALL_MERC}[①] 트리거 템플릿 매칭 — ②계약서 단계로 진행")
                    # AGENT: remember FT on-state before disable; restore only if was on.
                    had_flame_trigger = bool(flame_trigger_active)
                    call_merc_restore_ft_after_cycle = had_flame_trigger

                    def _merc_ft_disable():
                        _state_set("flame_trigger_active", False)
                        mouse_right_up()
                        win32_clip_cursor_release()

                    automation_disable_flame_trigger_if_active(
                        flame_trigger_active=had_flame_trigger,
                        disable=_merc_ft_disable,
                    )
                    _loop_print(
                        f"{_LOG_CALL_MERC}[①] 플레임 트리거 일시 정지 (우클릭 해제)"
                        if had_flame_trigger
                        else f"{_LOG_CALL_MERC}[①] 플레임 트리거 비활성 — 대기",
                    )
                time.sleep(0.12)
                continue

            if not get_window_rect(target_hwnd):
                time.sleep(0.2)
                continue

            if phase == 1:
                _tm = float(g.get("call_merc_intermediate_started_mono") or 0.0)
                if _tm > 0.0 and time.monotonic() - _tm > CALL_MERC_SEQUENCE_STUCK_SEC:
                    _call_merc_abort_stuck_mid_sequence(phase_was=phase, ft_en=ft_en)
                    phase = 0
                    continue
                k = "call_merc_2"
                roi = merc_roi[k]
                tl2 = _call_merc_match_one_kind(
                    g,
                    k,
                    target_hwnd,
                    sct,
                    scaled,
                    match_threshold=merc_thr[k],
                    roi_override=roi,
                )
                if tl2 is not None and g[_CALL_MERC_SCORE_KEY[k]] >= merc_thr[k]:
                    _call_merc_click_at_match(
                        target_hwnd,
                        roi,
                        tl2,
                        scaled[k],
                        double=True,
                        log_tag=_CALL_MERC_LOOP_LOG_TAG["call_merc_2"],
                    )
                    _prev = phase
                    phase = 2
                    _call_merc_ui_sync_phase(_prev, phase)
                    time.sleep(0.12)
                else:
                    time.sleep(0.08)
                continue

            if phase == 2:
                _tm = float(g.get("call_merc_intermediate_started_mono") or 0.0)
                if _tm > 0.0 and time.monotonic() - _tm > CALL_MERC_SEQUENCE_STUCK_SEC:
                    _call_merc_abort_stuck_mid_sequence(phase_was=phase, ft_en=ft_en)
                    phase = 0
                    continue
                k = "call_merc_3"
                roi = merc_roi[k]
                tl3 = _call_merc_match_one_kind(
                    g,
                    k,
                    target_hwnd,
                    sct,
                    scaled,
                    match_threshold=merc_thr[k],
                    roi_override=roi,
                )
                if tl3 is not None and g[_CALL_MERC_SCORE_KEY[k]] >= merc_thr[k]:
                    _call_merc_click_at_match(
                        target_hwnd,
                        roi,
                        tl3,
                        scaled[k],
                        double=False,
                        log_tag=_CALL_MERC_LOOP_LOG_TAG["call_merc_3"],
                    )
                    _prev = phase
                    phase = 3
                    _call_merc_ui_sync_phase(_prev, phase)
                    time.sleep(0.12)
                else:
                    time.sleep(0.08)
                continue

            if phase == 3:
                _tm = float(g.get("call_merc_intermediate_started_mono") or 0.0)
                if _tm > 0.0 and time.monotonic() - _tm > CALL_MERC_SEQUENCE_STUCK_SEC:
                    _call_merc_abort_stuck_mid_sequence(phase_was=phase, ft_en=ft_en)
                    phase = 0
                    continue
                k = "call_merc_4"
                roi = merc_roi[k]
                tl4 = _call_merc_match_one_kind(
                    g,
                    k,
                    target_hwnd,
                    sct,
                    scaled,
                    match_threshold=merc_thr[k],
                    roi_override=roi,
                )
                if tl4 is not None and g[_CALL_MERC_SCORE_KEY[k]] >= merc_thr[k]:
                    _call_merc_click_at_match(
                        target_hwnd,
                        roi,
                        tl4,
                        scaled[k],
                        double=False,
                        log_tag=_CALL_MERC_LOOP_LOG_TAG["call_merc_4"],
                    )
                    call_merc_loop_count += 1
                    _loop_print(
                        f"{_LOG_CALL_MERC}[완료] 사이클 성공 (누적 {call_merc_loop_count}회) — ①대기로 복귀",
                    )

                    def _merc_ft_enable():
                        global flame_trigger_active, flame_trigger_start_time
                        _pause_left_click_and_right_hold_for_flame_trigger()
                        _state_set("flame_trigger_active", True)
                        _state_set("flame_trigger_start_time", time.time())

                    if automation_reenable_flame_trigger_after_success(
                        feature_enabled=ft_en,
                        restore_flag=call_merc_restore_ft_after_cycle,
                        enable=_merc_ft_enable,
                    ):
                        _loop_print(f"{_LOG_CALL_MERC}[복구] 플레임 트리거 재개")
                    else:
                        _loop_print(f"{_LOG_CALL_MERC}[복구] 플레임 트리거 재개 생략")
                    call_merc_restore_ft_after_cycle = False
                    _arm_until = time.monotonic() + CALL_MERC_ARM_COOLDOWN_SEC
                    call_merc_arm_until_mono = float(_arm_until)
                    _prev = phase
                    phase = 0
                    _call_merc_ui_sync_phase(_prev, phase)
                    call_merc_sequence_busy = False  # AGENT: clear busy sticky
                    time.sleep(0.15)
                else:
                    time.sleep(0.08)
                continue

        else:
            time.sleep(
                GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.1
            )

    sct.close()
    _loop_print(f"{_LOG_CALL_MERC} 워커 루프 종료")


def start_game_launcher_loop():
    """① 런처에서 START GAME 매칭 시 1회 클릭; 런처 창이 N초 안에 사라지면 Intro Skip 무장(끝).
    사라지지 않으면 1회만 재클릭한 뒤 다시 N초 대기; 여전히 남으면 쿨다운(Intro Skip 무장 없음).
    ② 런처 종료 조건 후 게임 창에서 Intro Skip 1회 클릭(무장 구간).
    ③ Intro Skip 성공 직후 Accept 템플릿 1회 클릭(별도 무장 구간)."""
    global running, select_mode, target_hwnd
    global _smart_updater_hwnd_cache, _smart_updater_poll_skip_until
    global start_game_launcher_active, start_game_launcher_score, start_game_launcher_threshold
    global start_game_launcher_match_region, START_GAME_IMAGE_PATH
    global start_game_intro_skip_score, start_game_intro_skip_threshold, start_game_intro_skip_match_region
    global START_GAME_INTRO_SKIP_IMAGE_PATH
    global _start_game_intro_skip_armed, _start_game_intro_skip_arm_until_mono
    global start_game_accept_score, start_game_accept_threshold, start_game_accept_match_region
    global START_GAME_ACCEPT_IMAGE_PATH
    global _start_game_accept_armed, _start_game_accept_arm_until_mono
    _ensure_cv2_numpy_mss()
    sct = mss.mss()
    last_launcher_click_mono = 0.0
    launcher_click_cooldown_sec = float(START_GAME_LAUNCHER_RETRY_COOLDOWN_SEC)
    last_sg_launcher_path = None
    tpl_launcher_cache = None
    last_sg_intro_path = None
    tpl_intro_cache = None
    last_sg_accept_path = None
    tpl_accept_cache = None
    _disappear_w = float(START_GAME_LAUNCHER_POST_CLICK_DISAPPEAR_WAIT_SEC)

    from pipela_qt.dock_ui_phase import is_start_game_launcher_template1_effective_on

    # `sys.modules[__name__]` 는 스크립트와 `import main`·번들/프록시마다
    # `refresh_target_hwnd_if_needed` 가 없는 «다른 __main__»이 될 수 있음.
    _pipela_mod = _pipela_mod_for_qt()

    def _wait_launcher_window_gone(deadline_mono: float) -> str:
        """스마트업데이트 런처 창이 사라질 때까지 대기.
        'gone' 사라짐, 'timeout' deadline 도달, 'aborted' 기능 끄김/선택 모드/종료."""
        while running and not select_mode:
            if time.monotonic() >= deadline_mono:
                return "timeout"
            time.sleep(0.08)
            snap_w = get_registry_config_snapshot()
            if not is_start_game_launcher_template1_effective_on(_pipela_mod, snap_w):
                return "aborted"
            if not refresh_smart_updater_hwnd_if_needed():
                return "gone"
        return "aborted"

    try:
        while running:
            time.sleep(0.06)
            snap = get_registry_config_snapshot()
            if not is_start_game_launcher_template1_effective_on(_pipela_mod, snap):
                _start_game_intro_skip_armed = False
                _start_game_intro_skip_arm_until_mono = 0.0
                _start_game_accept_armed = False
                _start_game_accept_arm_until_mono = 0.0
                start_game_launcher_score = 0.0
                start_game_intro_skip_score = 0.0
                start_game_accept_score = 0.0
                _seq_scroll(FEAT_START_GAME, 0)
                time.sleep(0.22)
                continue
            if select_mode:
                time.sleep(0.12)
                continue

            path_launcher = snap.get("START_GAME_IMAGE_PATH", START_GAME_IMAGE_PATH)
            tpl_launcher_cache, last_sg_launcher_path = load_image_data_if_path_changed(
                path_launcher,
                "start_game_launcher_image_data",
                last_sg_launcher_path,
                tpl_launcher_cache,
            )
            path_intro = snap.get(
                "START_GAME_INTRO_SKIP_IMAGE_PATH", START_GAME_INTRO_SKIP_IMAGE_PATH,
            )
            tpl_intro_cache, last_sg_intro_path = load_image_data_if_path_changed(
                path_intro,
                "start_game_intro_skip_image_data",
                last_sg_intro_path,
                tpl_intro_cache,
            )
            path_accept = snap.get("START_GAME_ACCEPT_IMAGE_PATH", START_GAME_ACCEPT_IMAGE_PATH)
            tpl_accept_cache, last_sg_accept_path = load_image_data_if_path_changed(
                path_accept,
                "start_game_accept_image_data",
                last_sg_accept_path,
                tpl_accept_cache,
            )

            mono_now = time.monotonic()
            if _start_game_accept_armed:
                _seq_scroll(FEAT_START_GAME, 2)
            elif _start_game_intro_skip_armed:
                _seq_scroll(FEAT_START_GAME, 1)
            else:
                _seq_scroll(FEAT_START_GAME, 0)

            if _start_game_accept_armed:
                if mono_now > _start_game_accept_arm_until_mono:
                    _start_game_accept_armed = False
                    _start_game_accept_arm_until_mono = 0.0
                    start_game_accept_score = 0.0
                    time.sleep(0.12)
                    continue
                refresh_target_hwnd_if_needed()
                gh_ac = target_hwnd
                if not gh_ac:
                    start_game_accept_score = 0.0
                    time.sleep(0.25)
                    continue
                tpl_ac = tpl_accept_cache
                if tpl_ac is None:
                    start_game_accept_score = 0.0
                    time.sleep(0.55)
                    continue
                ratio_ac = get_scale_ratio(gh_ac)
                if ratio_ac is None or ratio_ac <= 0:
                    start_game_accept_score = 0.0
                    time.sleep(0.25)
                    continue
                scaled_ac = scale_template(tpl_ac, ratio_ac)
                if scaled_ac is None:
                    start_game_accept_score = 0.0
                    time.sleep(0.35)
                    continue
                cap_ac = snap.get("start_game_accept_match_region", start_game_accept_match_region)
                screen_ac = capture_region(gh_ac, sct, cap_ac)
                _template_probe_mark("start_game", "accept")
                if screen_ac is None:
                    start_game_accept_score = 0.0
                    time.sleep(0.2)
                    continue
                if (
                    screen_ac.shape[0] < scaled_ac.shape[0]
                    or screen_ac.shape[1] < scaled_ac.shape[1]
                ):
                    start_game_accept_score = 0.0
                    time.sleep(0.15)
                    continue
                max_ac, loc_ac = _match_template_ccoeff_normed_max(screen_ac, scaled_ac)
                if loc_ac is None:
                    start_game_accept_score = 0.0
                    time.sleep(0.1)
                    continue
                start_game_accept_score = float(max_ac)
                thr_ac = snapshot_float(
                    snap, "start_game_accept_threshold", float(start_game_accept_threshold),
                )
                if max_ac < thr_ac:
                    time.sleep(0.07)
                    continue
                th, tw = scaled_ac.shape[0], scaled_ac.shape[1]
                abs_pt_ac = _match_center_to_screen_xy(gh_ac, cap_ac, loc_ac, tw, th)
                if abs_pt_ac is None:
                    time.sleep(0.2)
                    continue
                cx, cy = abs_pt_ac
                pb_ac = _template_extract_match_patch(screen_ac, scaled_ac, loc_ac)
                if pb_ac is not None:
                    _template_last_hit_store(
                        "start_game_accept",
                        pb_ac,
                        float(max_ac),
                    )
                _loop_print(
                    f"{_LOG_START_GAME}[③수락] 매칭 점수 {max_ac:.2f} → 클릭 ({cx},{cy})",
                )
                mouse_move(cx, cy)
                time.sleep(0.045)
                mouse_click()
                _start_game_accept_armed = False
                _start_game_accept_arm_until_mono = 0.0
                start_game_accept_score = 0.0
                time.sleep(0.35)
                continue

            if _start_game_intro_skip_armed:
                if mono_now > _start_game_intro_skip_arm_until_mono:
                    _start_game_intro_skip_armed = False
                    _start_game_intro_skip_arm_until_mono = 0.0
                    start_game_intro_skip_score = 0.0
                    _loop_print(
                        f"{_LOG_START_GAME}[②서버선택] 무장 시간 초과 — ①런처 대기로",
                    )
                    time.sleep(0.12)
                    continue
                refresh_target_hwnd_if_needed()
                gh = target_hwnd
                if not gh:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.25)
                    continue
                tpl_is = tpl_intro_cache
                if tpl_is is None:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.55)
                    continue
                ratio_g = get_scale_ratio(gh)
                if ratio_g is None or ratio_g <= 0:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.25)
                    continue
                scaled_is = scale_template(tpl_is, ratio_g)
                if scaled_is is None:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.35)
                    continue
                cap_is = snap.get("start_game_intro_skip_match_region", start_game_intro_skip_match_region)
                screen_g = capture_region(gh, sct, cap_is)
                _template_probe_mark("start_game", "intro_skip")
                if screen_g is None:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.2)
                    continue
                if (
                    screen_g.shape[0] < scaled_is.shape[0]
                    or screen_g.shape[1] < scaled_is.shape[1]
                ):
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.15)
                    continue
                max_is, loc_is = _match_template_ccoeff_normed_max(screen_g, scaled_is)
                if loc_is is None:
                    start_game_intro_skip_score = 0.0
                    time.sleep(0.1)
                    continue
                start_game_intro_skip_score = float(max_is)
                thr_is = snapshot_float(
                    snap, "start_game_intro_skip_threshold", float(start_game_intro_skip_threshold),
                )
                if max_is < thr_is:
                    time.sleep(0.07)
                    continue
                th, tw = scaled_is.shape[0], scaled_is.shape[1]
                abs_pt_is = _match_center_to_screen_xy(gh, cap_is, loc_is, tw, th)
                if abs_pt_is is None:
                    time.sleep(0.2)
                    continue
                cx, cy = abs_pt_is
                pb_is = _template_extract_match_patch(screen_g, scaled_is, loc_is)
                if pb_is is not None:
                    _template_last_hit_store(
                        "start_game_intro_skip",
                        pb_is,
                        float(max_is),
                    )
                _loop_print(
                    f"{_LOG_START_GAME}[②서버선택] 매칭 점수 {max_is:.2f} → 클릭 ({cx},{cy})",
                )
                mouse_move(cx, cy)
                time.sleep(0.045)
                mouse_click()
                _start_game_intro_skip_armed = False
                _start_game_intro_skip_arm_until_mono = 0.0
                start_game_intro_skip_score = 0.0
                _start_game_accept_armed = True
                _start_game_accept_arm_until_mono = (
                    mono_now + float(START_GAME_ACCEPT_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue

            start_game_intro_skip_score = 0.0
            start_game_accept_score = 0.0
            uh = refresh_smart_updater_hwnd_if_needed()
            if not uh:
                start_game_launcher_score = 0.0
                time.sleep(0.35)
                continue
            tpl = tpl_launcher_cache
            if tpl is None:
                start_game_launcher_score = 0.0
                time.sleep(0.85)
                continue
            cap_reg = snap.get("start_game_launcher_match_region", start_game_launcher_match_region)
            screen = capture_region(uh, sct, cap_reg)
            _template_probe_mark("start_game", "launcher")
            if screen is None:
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            ratio = get_scale_ratio(uh)
            candidates = []
            candidates.append(tpl)
            scaled_by_ratio = scale_template(tpl, ratio)
            if scaled_by_ratio is not None:
                candidates.append(scaled_by_ratio)
            best_score = -1.0
            best_loc = None
            best_scaled = None
            for cand in candidates:
                if cand is None:
                    continue
                if screen.shape[0] < cand.shape[0] or screen.shape[1] < cand.shape[1]:
                    continue
                sc, loc = _match_template_ccoeff_normed_max(screen, cand)
                if loc is None:
                    continue
                if float(sc) > best_score:
                    best_score = float(sc)
                    best_loc = loc
                    best_scaled = cand
            if best_loc is None or best_scaled is None:
                start_game_launcher_score = 0.0
                time.sleep(0.12)
                continue
            max_val = float(best_score)
            max_loc = best_loc
            scaled = best_scaled
            start_game_launcher_score = max_val
            thr = snapshot_float(
                snap, "start_game_launcher_threshold", float(start_game_launcher_threshold),
            )
            if max_val < thr:
                time.sleep(0.07)
                continue
            now = time.monotonic()
            if now - last_launcher_click_mono < launcher_click_cooldown_sec:
                time.sleep(0.1)
                continue

            th, tw = scaled.shape[0], scaled.shape[1]
            abs_pt = _match_center_to_screen_xy(uh, cap_reg, max_loc, tw, th)
            if abs_pt is None:
                time.sleep(0.2)
                continue
            cx, cy = abs_pt
            pb = _template_extract_match_patch(screen, scaled, max_loc)
            if pb is not None:
                _template_last_hit_store(
                    "start_game_launcher",
                    pb,
                    float(max_val),
                )
            _loop_print(
                f"{_LOG_START_GAME}[①런처] 1회 클릭 매칭 {max_val:.2f} → 좌표 ({cx},{cy})",
            )
            mouse_move(cx, cy)
            time.sleep(0.045)
            mouse_click()
            t_after_first = time.monotonic()
            last_launcher_click_mono = t_after_first
            _smart_updater_hwnd_cache = None
            _smart_updater_poll_skip_until = 0.0
            w0 = _wait_launcher_window_gone(t_after_first + _disappear_w)
            if w0 == "gone":
                _arm_t0 = time.monotonic()
                _loop_print(
                    f"{_LOG_START_GAME}[①런처] 창 닫힘 확인(1클릭) → ②서버 선택 단계 무장",
                )
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t0 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            if w0 == "aborted":
                time.sleep(0.12)
                continue

            # AGENT: if launcher still up within 5s -> one extra click only.
            uh3 = refresh_smart_updater_hwnd_if_needed()
            if not uh3:
                _arm_t0 = time.monotonic()
                _loop_print(
                    f"{_LOG_START_GAME}[①런처] 5초 대기 전후 창 없음 → ②서버 선택 단계 무장",
                )
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t0 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            snap2 = get_registry_config_snapshot()
            if not is_start_game_launcher_template1_effective_on(_pipela_mod, snap2):
                time.sleep(0.12)
                continue
            thr2 = snapshot_float(
                snap2, "start_game_launcher_threshold", float(start_game_launcher_threshold),
            )
            cap2 = snap2.get("start_game_launcher_match_region", start_game_launcher_match_region)
            screen_b = capture_region(uh3, sct, cap2)
            _template_probe_mark("start_game", "launcher")
            if screen_b is None:
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            ratio_b = get_scale_ratio(uh3)
            candidates_b = []
            candidates_b.append(tpl)
            scaled_b_ratio = scale_template(tpl, ratio_b)
            if scaled_b_ratio is not None:
                candidates_b.append(scaled_b_ratio)
            best_score_b = -1.0
            best_loc_b = None
            best_scaled_b = None
            for cand_b in candidates_b:
                if cand_b is None:
                    continue
                if (
                    screen_b.shape[0] < cand_b.shape[0]
                    or screen_b.shape[1] < cand_b.shape[1]
                ):
                    continue
                sc_b, loc_tmp_b = _match_template_ccoeff_normed_max(screen_b, cand_b)
                if loc_tmp_b is None:
                    continue
                if float(sc_b) > best_score_b:
                    best_score_b = float(sc_b)
                    best_loc_b = loc_tmp_b
                    best_scaled_b = cand_b
            if best_loc_b is None or best_scaled_b is None:
                start_game_launcher_score = 0.0
                time.sleep(0.12)
                continue
            max_b = float(best_score_b)
            loc_b = best_loc_b
            scaled_b = best_scaled_b
            start_game_launcher_score = max_b
            if max_b < thr2:
                _arm_t0 = time.monotonic()
                _loop_print(
                    f"{_LOG_START_GAME}[①런처] 2차 템플릿 미매칭 → ②서버 선택 단계 무장",
                )
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t0 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            th2, tw2 = scaled_b.shape[0], scaled_b.shape[1]
            abs_pt_b = _match_center_to_screen_xy(uh3, cap2, loc_b, tw2, th2)
            if abs_pt_b is None:
                time.sleep(0.2)
                continue
            cx2, cy2 = abs_pt_b
            pb2 = _template_extract_match_patch(screen_b, scaled_b, loc_b)
            if pb2 is not None:
                _template_last_hit_store(
                    "start_game_launcher",
                    pb2,
                    float(max_b),
                )
            _loop_print(
                f"{_LOG_START_GAME}[①런처] 2회 클릭(재시도) 매칭 {max_b:.2f} → ({cx2},{cy2})",
            )
            mouse_move(cx2, cy2)
            time.sleep(0.045)
            mouse_click()
            t_after_second = time.monotonic()
            last_launcher_click_mono = t_after_second
            _smart_updater_hwnd_cache = None
            _smart_updater_poll_skip_until = 0.0
            w1 = _wait_launcher_window_gone(t_after_second + _disappear_w)
            if w1 == "gone":
                _arm_t1 = time.monotonic()
                _loop_print(
                    f"{_LOG_START_GAME}[①런처] 창 닫힘 확인(2클릭) → ②서버 선택 단계 무장",
                )
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t1 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            if w1 == "aborted":
                time.sleep(0.12)
                continue
            _loop_print(
                f"{_LOG_START_GAME}[①런처] 2회 클릭 후에도 런처 유지 — "
                f"{launcher_click_cooldown_sec:.1f}초 쿨다운",
            )
            time.sleep(0.35)
    finally:
        try:
            sct.close()
        except Exception:
            pass


def left_click_loop():
    """왼쪽 클릭 반복 루프"""
    while _state_gets("running"):
        snap = get_registry_config_snapshot()
        lc_en = snapshot_bool(snap, "left_click_feature_enabled", left_click_feature_enabled)
        if not lc_en and _state_gets("left_click_active"):
            _state_set("left_click_active", False)
        lc_rand = snapshot_bool(snap, "left_click_random_enabled", left_click_random_enabled)
        lc_iv = snapshot_float(snap, "left_click_interval_ms", float(left_click_interval_ms))
        lc_rmin = snapshot_float(snap, "left_click_random_min_ms", float(left_click_random_min_ms))
        lc_rmax = snapshot_float(snap, "left_click_random_max_ms", float(left_click_random_max_ms))
        if (
            lc_en
            and _state_gets("left_click_active")
            and is_mouse_in_window()
            and not _state_gets("select_mode")
            and not _state_gets("flame_trigger_active")
        ):
            mouse_click()
            if lc_rand:
                lo = min(lc_rmin, lc_rmax)
                hi = max(lc_rmin, lc_rmax)
                interval_ms = random.uniform(lo, hi)
            else:
                interval_ms = float(lc_iv)
            time.sleep(max(0.001, interval_ms / 1000.0))
        else:
            time.sleep(GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC if _game_client_power_save_active else 0.01)

@contextmanager
def _ammo_restock_sequence_guard():
    """탄약 보충 시퀀스 구간 — FT 루프가 Merc Fire/클립/우홀드를 쉬게 함."""
    global ammo_restock_sequence_busy
    ammo_restock_sequence_busy = True
    try:
        yield
    finally:
        ammo_restock_sequence_busy = False


def _other_automation_suppresses_flame_trigger():
    """Reload/Call Merc/탄약 시퀀스 중 — FT 루프가 Merc Fire·ClipCursor·우클릭 유지를 하지 않음."""
    return bool(_state_gets("nobullet_detected")) or bool(call_merc_sequence_busy) or bool(ammo_restock_sequence_busy)


def right_hold_loop():
    """오른쪽 마우스 유지 루프"""
    while _state_gets("running"):
        snap = get_registry_config_snapshot()
        rh_en = snapshot_bool(snap, "right_hold_feature_enabled", right_hold_feature_enabled)
        if (
            right_hold_active
            and rh_en
            and is_mouse_in_window()
            and not _state_gets("select_mode")
            and not _state_gets("flame_trigger_active")
        ):
            mouse_right_down()
            time.sleep(0.05)
        else:
            time.sleep(GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC if _game_client_power_save_active else 0.01)


def _flame_trigger_release_inputs_and_reset_hud_counters() -> None:
    """게임 창 상실 등 — RMB/Clip 해제 + HUD 카운터 초기화(flame_trigger_active 끄기는 호출부)."""
    mouse_right_up()
    win32_clip_cursor_release()
    _state_set("flame_trigger_prev_press_timestamp", None)
    _state_set("flame_trigger_last_press_interval_sec", 0.0)
    _state_set("flame_trigger_hud_session_start_time", 0.0)
    _state_set("flame_trigger_session_reload_count", 0)
    _state_set("flame_trigger_last_reload_complete_time", 0.0)
    _state_set("flame_trigger_last_reload_trigger_time", 0.0)


def _set_right_hold_active_main(v: bool) -> None:
    global right_hold_active
    right_hold_active = bool(v)


def _clear_user_left_pending_main() -> None:
    global user_left_pending
    user_left_pending = False
    _state_set("left_pressed", False)


def _apply_no_game_client_session_teardown_main() -> None:
    apply_no_game_client_session_teardown(
        state_get=_state_gets,
        state_set=_state_set,
        get_right_hold_active=lambda: bool(right_hold_active),
        set_right_hold_active=_set_right_hold_active_main,
        mouse_right_up=mouse_right_up,
        release_flame_hardware=_flame_trigger_release_inputs_and_reset_hud_counters,
        clear_user_left_pending=_clear_user_left_pending_main,
    )


def flame_trigger_loop():
    """화면 중앙 우클릭 홀드 + 마우스 고정 + Merc Fire(설정 키를 간격으로 연속 입력)"""
    flame_trigger_executed = False  # AGENT: one-shot executed
    last_key_time = 0  # AGENT: last merc key ts
    next_key_interval = 0  # AGENT: next key delay sec
    key_loop_active = True  # AGENT: merc fire loop running
    # AGENT: ClipCursor box half (0=1×1 …). PIPELA_FT_CLIP_HALF 느슨하게 올릴 수 있음.
    try:
        _ft_clip_half = max(0, int(os.environ.get("PIPELA_FT_CLIP_HALF", "0") or 0))
    except (TypeError, ValueError):
        _ft_clip_half = 0

    while _state_gets("running"):
        snap = get_registry_config_snapshot()
        ft_feat = snapshot_bool(snap, "flame_trigger_feature_enabled", flame_trigger_feature_enabled)
        mf_en = snapshot_bool(snap, "merc_fire_enabled", merc_fire_enabled)
        mf_kc = snapshot_int(snap, "merc_fire_key_code", int(merc_fire_key_code))
        mf_lo = snapshot_float(snap, "merc_fire_random_min_ms", float(merc_fire_random_min_ms))
        mf_hi = snapshot_float(snap, "merc_fire_random_max_ms", float(merc_fire_random_max_ms))
        _ft_active = bool(_state_gets("flame_trigger_active"))
        if not ft_feat and _ft_active:
            _state_set("flame_trigger_active", False)
            _ft_active = False
        # AGENT: on flame_trigger_active False -> immediate teardown.
        if not _ft_active:
            if flame_trigger_executed:
                # AGENT: immediate RMB up + stop key loop.
                mouse_right_up()
                win32_clip_cursor_release()
                flame_trigger_executed = False
                key_loop_active = False
                next_key_interval = 0
                _state_set("flame_trigger_prev_press_timestamp", None)
                _state_set("flame_trigger_last_press_interval_sec", 0.0)
                if not _state_gets("flame_trigger_reload_teardown_preserve_hud"):
                    _state_set("flame_trigger_hud_session_start_time", 0.0)
                    _state_set("flame_trigger_session_reload_count", 0)
                    _state_set("flame_trigger_last_reload_complete_time", 0.0)
                    _state_set("flame_trigger_last_reload_trigger_time", 0.0)
            time.sleep(
                GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC if _game_client_power_save_active else 0.01
            )
            continue
        
        hwnd = _state_gets("target_hwnd")
        if hwnd and not _state_gets("select_mode"):
            if _other_automation_suppresses_flame_trigger():
                if flame_trigger_executed:
                    mouse_right_up()
                    win32_clip_cursor_release()
                    flame_trigger_executed = False
                time.sleep(
                    GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC
                    if _game_client_power_save_active
                    else 0.02,
                )
                continue
            if not flame_trigger_executed:
                # AGENT: once: move to center then RMB down hold.
                rect = get_window_rect(hwnd)
                # AGENT: skip one-shot if client rect invalid (minimized) to avoid bad snap.
                if (
                    rect
                    and rect[2] > rect[0]
                    and rect[3] > rect[1]
                    and not is_window_minimized(hwnd)
                ):
                    wx, wy, wx2, wy2 = rect
                    center_x = wx + (wx2 - wx) // 2
                    center_y = wy + (wy2 - wy) // 2
                    mouse_move(center_x, center_y)
                    time.sleep(0.1)
                    # AGENT: Reload/Call Merc may clear active during sleep — do not arm RMB/clip.
                    if not _state_gets("flame_trigger_active"):
                        continue
                    mouse_right_down()
                    flame_trigger_executed = True
                    _state_set("flame_trigger_start_time", time.time())  # AGENT: store start ts
                    _reload_hud_carry = (
                        _state_gets("flame_trigger_session_reload_count") > 0
                        or _state_gets("flame_trigger_last_reload_trigger_time")
                        > 0.0
                    )
                    if not _reload_hud_carry:
                        _state_set("flame_trigger_hud_session_start_time", time.time())
                        _state_set("flame_trigger_session_reload_count", 0)
                        _state_set("flame_trigger_last_reload_complete_time", 0.0)
                        _state_set("flame_trigger_last_reload_trigger_time", 0.0)
                    _state_set("flame_trigger_press_count", 0)  # AGENT: reset press count
                    _state_set("flame_trigger_prev_press_timestamp", None)
                    _state_set("flame_trigger_last_press_interval_sec", 0.0)
                    # AGENT: key loop on/off per settings.
                    key_loop_active = mf_en
                    _ft_merc_t0 = time.time()
                    last_key_time = _ft_merc_t0
                    # AGENT: random key interval ms->sec; first key sent immediately then spaced.
                    next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0
                    if key_loop_active and mf_en:
                        send_key(mf_kc, hwnd)
                        _state_set("flame_trigger_press_count", 1)
                        _state_set(
                            "flame_trigger_last_press_interval_sec",
                            _ft_merc_t0
                            - float(_state_gets("flame_trigger_start_time")),
                        )
                        _state_set("flame_trigger_prev_press_timestamp", _ft_merc_t0)
                        last_key_time = _ft_merc_t0
                        _state_set("flame_trigger_press_text_until", _ft_merc_t0 + 0.5)
                        _state_set("flame_trigger_press_key_name", vk_to_display_name(mf_kc))
                        next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0
                    if not _reload_hud_carry:
                        try:
                            _flame_start_banner_queue.put_nowait(1)
                        except queue.Full:
                            pass
            
            # AGENT: while active snap cursor to window center until wheel-click OFF.
            if flame_trigger_executed:
                # AGENT: Reload/Call Merc clears active between while-head and here; skip re-clip this tick.
                if not _state_gets("flame_trigger_active"):
                    time.sleep(0.016)
                    continue
                current_time = time.time()

                rect = get_window_rect(hwnd)
                # AGENT: if client rect bogus skip snap+keys — bad coords (-32000) +
                # AGENT: SetCursorPos clamp near (0,0) reads as cursor flicker.
                rect_ok = bool(
                    rect
                    and rect[2] > rect[0]
                    and rect[3] > rect[1]
                    and not is_window_minimized(hwnd)
                )
                if rect_ok:
                    wx, wy, wx2, wy2 = rect
                    center_x = wx + (wx2 - wx) // 2
                    center_y = wy + (wy2 - wy) // 2

                    h = _ft_clip_half
                    _l = center_x - h
                    _t = center_y - h
                    _r = center_x + h + 1
                    _b = center_y + h + 1
                    _ft_clip_ok = win32_clip_cursor_to_screen_rect(_l, _t, _r, _b)

                    # AGENT: periodic keydown when loop+setting enabled.
                    if key_loop_active and mf_en:
                        time_since_last_key = current_time - last_key_time
                        if time_since_last_key >= next_key_interval:
                            send_key(mf_kc, hwnd)
                            _state_inc_int("flame_trigger_press_count")
                            _prev_press_ts = _state_gets("flame_trigger_prev_press_timestamp")
                            if _prev_press_ts is not None:
                                _state_set(
                                    "flame_trigger_last_press_interval_sec",
                                    current_time - float(_prev_press_ts),
                                )
                            else:
                                _state_set(
                                    "flame_trigger_last_press_interval_sec",
                                    current_time
                                    - float(_state_gets("flame_trigger_start_time")),
                                )
                            _state_set("flame_trigger_prev_press_timestamp", current_time)
                            last_key_time = current_time
                            # AGENT: show under-cursor "Flame Trigger Press N" 0.5s.
                            _state_set("flame_trigger_press_text_until", current_time + 0.5)
                            _state_set("flame_trigger_press_key_name", vk_to_display_name(mf_kc))
                            next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0

                    # AGENT: ClipCursor(최대 1×1~)+매 틱 SetCursorPos로 드리프트 제거.
                    mouse_move(center_x, center_y)
                    cur = try_screen_cursor_pos_for_macros()
                    if cur is None:
                        current_x, current_y = center_x, center_y
                    else:
                        current_x, current_y = cur
                    dist = ((current_x - center_x) ** 2 + (current_y - center_y) ** 2) ** 0.5
                    if (not _ft_clip_ok and dist > 5) or (_ft_clip_ok and dist > 0.5):
                        mouse_right_down()

                    time.sleep(0.016)
                else:
                    # AGENT: no window / bogus rect -> 세션·입력 공통 정리.
                    _apply_no_game_client_session_teardown_main()
                    flame_trigger_executed = False
                    key_loop_active = False
                    _loop_print(f"{_LOG_FLAME} 끔 (게임 창 없음)")
        else:
            if _ft_active and (not hwnd or _state_gets("select_mode")):
                _apply_no_game_client_session_teardown_main()
                _ft_active = False
                flame_trigger_executed = False
                key_loop_active = False
                next_key_interval = 0
                if not hwnd:
                    _loop_print(f"{_LOG_FLAME} 끔 (게임 클라 없음)")
            time.sleep(
                GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.05
            )

def _physical_left_button_down():
    """Windows 물리 왼쪽 버튼 눌림(합성 클릭과 겹칠 때 OFF 판별용)."""
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
    except Exception:
        return False


def _delayed_arm_left_off_pending(arm_gen):
    """ignore_left로 press 이벤트가 버려졌을 때, 직후 물리 버튼이 눌려 있으면 OFF 예약."""
    global user_left_pending, left_click_active, _left_off_arm_gen
    time.sleep(LEFT_CLICK_OFF_ARM_DELAY_SEC)
    if arm_gen != _left_off_arm_gen:
        return
    if (
        not _state_gets("running")
        or not _state_gets("left_click_active")
        or not _state_gets("left_click_feature_enabled")
    ):
        return
    if _state_gets("select_mode") or not is_mouse_in_window():
        return
    if _physical_left_button_down():
        user_left_pending = True


def _pause_left_click_and_right_hold_for_flame_trigger() -> None:
    """Flame Trigger가 켜질 때 LeftClick / RightHold 자동 기동만 중지(기능 토글은 유지)."""
    global left_click_active, right_hold_active, user_left_pending
    if _state_gets("left_click_active"):
        _state_set("left_click_active", False)
        user_left_pending = False
        _loop_print(f"{_LOG_LEFT_CLICK} 끔 (플레임 트리거 우선)")
    if right_hold_active:
        right_hold_active = False
        mouse_right_up()
        _loop_print(f"{_LOG_RIGHT_HOLD} 끔 (플레임 트리거 우선)")


def on_click(x, y, button, pressed):
    """마우스 클릭 감지"""
    global left_click_active, right_hold_active, right_hold_feature_enabled, flame_trigger_active, flame_trigger_feature_enabled, ignore_left, ignore_right, left_pressed, left_click_id, user_left_pending
    global _left_off_arm_gen
    
    if select_mode or not is_mouse_in_window():
        return
    
    # AGENT: left button branch
    if button == mouse.Button.left:
        if pressed:
            if _state_gets("left_click_active") and _state_gets("left_click_feature_enabled"):
                # AGENT: OFF from ON: usually user_left_pending; synth overlap may drop press -> delayed fix.
                if ignore_left:
                    _left_off_arm_gen += 1
                    threading.Thread(
                        target=_delayed_arm_left_off_pending,
                        args=(_left_off_arm_gen,),
                        daemon=True,
                    ).start()
                    return
                user_left_pending = True
                return
            if ignore_left:
                return  # AGENT: ignore path when auto-click arming ON
            if _state_gets("left_click_feature_enabled"):
                if _state_gets("flame_trigger_active"):
                    return
                # AGENT: feature ON and logical OFF -> hold timing check.
                _state_set("left_pressed", True)
                _state_inc_int("left_click_id")
                current_id = int(_state_gets("left_click_id"))
                threading.Thread(target=check_left_hold, args=(current_id,), daemon=True).start()
        else:
            _state_set("left_pressed", False)
            if user_left_pending:
                user_left_pending = False
                _state_set("left_click_active", False)
                _loop_print(f"{_LOG_LEFT_CLICK} 끔 (사용자 해제)")
    
    # AGENT: right down toggles when feature enabled. Flame Trigger 중엔 켤 수 없음(OFF 는 허용).
    elif button == mouse.Button.right and not ignore_right and pressed:
        if right_hold_feature_enabled:
            if _state_gets("flame_trigger_active") and not right_hold_active:
                return
            right_hold_active = not right_hold_active
            _loop_print(
                f"{_LOG_RIGHT_HOLD} {'켜짐' if right_hold_active else '꺼짐'}",
            )
    
    # AGENT: wheel click toggles flame trigger when feature enabled.
    elif button == mouse.Button.middle and pressed:
        if flame_trigger_feature_enabled:
            _next_ft = not bool(_state_gets("flame_trigger_active"))
            _state_set("flame_trigger_active", _next_ft)
            if _next_ft:
                _pause_left_click_and_right_hold_for_flame_trigger()
            _loop_print(
                f"{_LOG_FLAME} {'켜짐' if _next_ft else '꺼짐'}",
            )

def check_left_hold(click_id):
    """왼쪽 버튼 홀드 체크 (ON용) - left_click_feature_enabled일 때만 발동"""
    time.sleep(left_click_hold_sec)
    # AGENT: same button still down + feature enabled check. FT 중엔 켤 수 없다.
    if (
        _state_gets("left_click_feature_enabled")
        and _state_gets("left_pressed")
        and click_id == _state_gets("left_click_id")
        and not _state_gets("left_click_active")
        and not _state_gets("flame_trigger_active")
    ):
        _state_set("left_click_active", True)
        _state_set("left_pressed", False)
        _loop_print(f"{_LOG_LEFT_CLICK} 켜짐 (홀드 인식)")

def on_key(key):
    """키보드 감지"""
    if key == keyboard.Key.f8:
        _loop_print(f"[{PIPELA_APP_DISPLAY_NAME}] 종료")
        set_capslock(False)
        _state_set("running", False)
        return False
    elif key == keyboard.Key.f5:
        _next_reload = not bool(_state_gets("reload_active"))
        _state_set("reload_active", _next_reload)
        if not _next_reload:
            _state_set("reload_nobullet_arm_until_mono", 0.0)
        _loop_print(f"{_LOG_RELOAD} 기능 {'켜짐' if _next_reload else '꺼짐'} (F5)")
        try:
            schedule_save_config()
        except Exception:
            pass
    else:
        vk = _pynput_key_to_vk(key, keyboard)
        if vk is not None and vk == (_state_gets("ammo_restock_toggle_key_code") & 0xFF):
            _next_ammo = not bool(_state_gets("ammo_restock_active"))
            _state_set("ammo_restock_active", _next_ammo)
            _loop_print(
                f"{_LOG_AMMO_RESTOCK} 기능 {'켜짐' if _next_ammo else '꺼짐'}",
            )
            try:
                schedule_save_config()
            except Exception:
                pass

# AGENT: ROI preview -> pipela_qt.region_preview_overlay only.
# _REGION_PREVIEW_PERSIST_VALID — pipela_core.region_dispatch
# AGENT: last preview kind None=off; restore on relaunch.
region_preview_overlay_saved_kind = None
# AGENT: region/template capture via pipela_qt.*_drag_overlay + pipela_mod.
_region_select_active_type = None
_template_capture_active_kind = None


def _force_close_template_capture_overlay():
    """템플릿 캡처 드래그 오버레이만 닫음."""
    global select_mode, _template_capture_active_kind
    try:
        from pipela_qt.template_drag_overlay import close_qt_template_capture_overlay

        close_qt_template_capture_overlay()
    except Exception:
        pass
    _template_capture_active_kind = None
    _state_set("select_mode", False)


def _force_close_region_select_overlay_only():
    """감지 영역 선택 오버레이만 닫음 (select_mode·active_type 정리)."""
    global _region_select_active_type, select_mode
    try:
        from pipela_qt.region_drag_overlay import close_qt_region_select_overlay

        close_qt_region_select_overlay()
    except Exception:
        pass
    _region_select_active_type = None
    _state_set("select_mode", False)


def _region_preview_client_rect_pixels(region_type):
    """
    저장된 감지 영역을 클라이언트 좌표 (rx, ry, rw, rh)로 반환.
    미지정(None)이면 전체 클라이언트(게임 창 본문 전체) — 캡처와 동일.
    """
    global target_hwnd
    if region_type == "start_game_launcher":
        uh = refresh_smart_updater_hwnd_if_needed()
        if not uh:
            return None
        rect = get_window_rect(uh)
        if not rect:
            return None
        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]
        region = _region_roi_global_get(region_type)
        if region:
            rp = get_region_pixels(uh, region)
            return rp if rp else None
        return (0, 0, int(win_w), int(win_h))
    if not target_hwnd:
        return None
    rect = get_window_rect(target_hwnd)
    if not rect:
        return None
    win_w = rect[2] - rect[0]
    win_h = rect[3] - rect[1]
    region = _region_roi_global_get(region_type)
    if region:
        rp = get_region_pixels(target_hwnd, region)
        return rp if rp else None
    return (0, 0, int(win_w), int(win_h))


def _region_preview_any_active():
    try:
        from pipela_qt.region_preview_overlay import qt_region_preview_overlay_active

        return qt_region_preview_overlay_active()
    except Exception:
        return False


def toggle_region_preview_overlay(region_type):
    """저장된 감지 ROI 미리보기 — Qt `QtRegionPreviewOverlay` 전용."""
    label = _region_type_ui_label(region_type, preview_log=True)
    try:
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is None:
            print(f"[{label}] preview FAIL (Qt 앱 필요)", flush=True)
            return
        from pipela_qt.region_preview_overlay import qt_region_preview_toggle

        qt_region_preview_toggle(_pipela_mod_for_qt(), region_type, label)
    except Exception as e:
        print(f"[{label}] preview FAIL: {e}", flush=True)


def _close_region_preview_if_active(kind):
    """감지 영역 미리보기가 해당 종류면 닫기(영역 해제 후 낡은 박스 방지)."""
    try:
        from pipela_qt.region_preview_overlay import close_qt_region_preview_if_active

        if close_qt_region_preview_if_active(kind):
            _region_preview_persist_set(None)
    except Exception:
        pass


def region_preview_try_restore_saved():
    """재실행 후 저장된 종류가 있으면 미리보기 다시 띄움."""
    global target_hwnd
    k = region_preview_overlay_saved_kind
    if k not in _REGION_PREVIEW_PERSIST_VALID:
        return
    if _region_preview_any_active():
        return
    refresh_target_hwnd_if_needed()
    if k == "start_game_launcher":
        if not refresh_smart_updater_hwnd_if_needed():
            return
    elif not target_hwnd:
        return
    try:
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is None:
            return
    except Exception:
        return
    toggle_region_preview_overlay(k)


def start_region_select(region_type="ride"):
    """영역 선택 — Qt `QtClientRegionSelectOverlay` 전용."""
    global target_hwnd

    label = _region_type_ui_label(region_type)
    if region_type == "start_game_launcher":
        if not refresh_smart_updater_hwnd_if_needed():
            print(f"[{label}] 스마트업데이터 창 없음")
            return
    elif not target_hwnd:
        print(f"[{label}] window?")
        return

    _force_close_template_capture_overlay()

    try:
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is None:
            print(f"[{label}] Qt 앱이 필요합니다.", flush=True)
            return
        from pipela_qt.region_drag_overlay import qt_region_select_start

        qt_region_select_start(_pipela_mod_for_qt(), region_type, label)
    except Exception as e:
        print(f"[{label}] 영역 선택 실패: {e}", flush=True)


# AGENT: --- template matching inventory (cv2.matchTemplate) ---
# AGENT: bundled PNG defaults: SCRIPT_DIR/assets/ (templates + UI icons)
# AGENT: col: loop | global path / registry *_image_data | settings UI capture
#  ride_loop         RIDE_TARGET / ride_target_image_data        RideSettingsWindow
#  reload_loop       RELOAD_NOBULLET / reload_nobullet_image_data  ThresholdSettingsWindow (NoBullet)
#  reload_loop       RELOAD_BULLET / reload_bullet_image_data       ThresholdSettingsWindow (Bullet)
#  reload_loop       RELOAD_VAULT / reload_vault_image_data  ThresholdSettingsWindow (Vault)
#  hp_refill_loop    HP_REFILL_ZKEY / hp_refill_zkey_image_data    ThresholdSettingsWindow (HP Bar)
# AGENT: ammo_restock_loop slots buybutton,inven,bank -> AmmoRestockSettingsWindow
# AGENT: call_merc_loop ①=nobullet gate ②③④ follow clicks -> CallMercSettingsWindow
# AGENT: kill_counter_loop OCR pytesseract — no user PNG template.
# AGENT: slots map 1:1 to pipela_core.template_capture_catalog + start_template_image_capture.
# AGENT: ROI: ride/hp share target-row region globals; reload/ammo use *_match_region else full window.


def _apply_template_capture_png(kind, abs_png_path):
    """PNG 경로를 해당 기능의 매칭 템플릿으로 등록(레지스트리 이미지 데이터 + 경로 저장)."""
    if not apply_template_capture_png(kind, abs_png_path, globals()):
        return False
    schedule_save_config()
    return True


def _template_capture_load_existing_pil(kind):
    """현재 지정된 매칭 템플릿을 PIL RGB로. 없으면 None."""
    return template_capture_load_existing_pil(kind, globals())


def start_template_image_capture(kind, parent_win, on_applied=None):
    """
    템플릿 PNG 드래그 캡처 — Qt `QtTemplateCaptureOverlay` + 확인 다이얼로그.
    parent_win: 레거시 인자(무시).
    """
    global target_hwnd, _template_capture_active_kind
    _ = parent_win
    meta = _template_capture_kind_meta(kind)
    if meta is None:
        print("[캡처] 알 수 없는 종류")
        return
    _fname, _reg_key, label = meta
    if kind != "start_game_launcher" and not target_hwnd:
        print(f"[{label}] 게임 창 없음")
        return

    _qt_tc_open = False
    try:
        from pipela_qt.template_drag_overlay import qt_template_capture_overlay_active

        _qt_tc_open = qt_template_capture_overlay_active()
    except Exception:
        pass

    if _template_capture_active_kind == kind and _qt_tc_open:
        print(f"[{label}] 지정 취소")
        _force_close_template_capture_overlay()
        return

    _force_close_region_select_overlay_only()
    _force_close_template_capture_overlay()

    try:
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is None:
            print(f"[{label}] Qt 앱이 필요합니다.", flush=True)
            return
        from pipela_qt.template_drag_overlay import qt_template_capture_start

        qt_template_capture_start(_pipela_mod_for_qt(), kind, label, on_applied)
    except Exception as e:
        print(f"[{label}] 캡처 시작 실패: {e}", flush=True)


def _pipela_version_tuple(ver_str):
    """버전 문자열 → 비교용 튜플 (예: 1.2.3 / 1.2.3-beta → 앞부분 숫자만)."""
    if not ver_str or not str(ver_str).strip():
        return (0, 0, 0)
    out = []
    for part in str(ver_str).strip().split("."):
        part = part.strip()
        if not part:
            continue
        n = ""
        for ch in part:
            if ch.isdigit():
                n += ch
            else:
                break
        out.append(int(n) if n else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def _pipela_update_manifest_download_url(obj):
    if not isinstance(obj, dict):
        return None
    u = obj.get("download_url") or obj.get("url")
    if not u:
        return None
    s = str(u).strip()
    return s if s else None


def _pipela_update_manifest_browser_url(obj):
    """브라우저로 열 URL — 릴리스 태그·노트 페이지 우선, 없으면 download_url."""
    if not isinstance(obj, dict):
        return None
    for key in ("release_url", "release_page_url"):
        u = obj.get(key)
        if u:
            s = str(u).strip()
            if s:
                return s
    return _pipela_update_manifest_download_url(obj)


def _pipela_fetch_update_manifest():
    """HTTP(S) JSON manifest. 반환: (dict|None, 오류코드·문자열|None)."""
    url = (PIPELA_UPDATE_MANIFEST_URL or "").strip()
    if not url:
        return None, "no_manifest_url"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"{PIPELA_APP_DISPLAY_NAME}/{PIPELA_APP_VERSION} (update-check)",
            },
            method="GET",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None, "invalid_json_object"
        return data, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except json.JSONDecodeError as e:
        return None, f"JSON 오류: {e}"
    except Exception as e:
        return None, str(e)


def _pipela_resolve_reinstall_download_url():
    """Re-download current build without version check. PIPELA_REINSTALL_DOWNLOAD_URL, else manifest download_url (zip)."""
    forced = (PIPELA_REINSTALL_DOWNLOAD_URL or "").strip()
    if forced:
        return forced, None
    data, err = _pipela_fetch_update_manifest()
    if err:
        return None, f"manifest: {err}"
    dl = _pipela_update_manifest_download_url(data)
    if not dl:
        return (
            None,
            "download_url 없음. 환경변수 PIPELA_REINSTALL_DOWNLOAD_URL 에 zip 주소를 넣거나 manifest JSON을 채우세요.",
        )
    return dl, None


def _pipela_resolve_reinstall_exe_url():
    # AGENT: legacy alias for pipela_mod callers.
    return _pipela_resolve_reinstall_download_url()


def _pipela_is_frozen_exe():
    return bool(getattr(sys, "frozen", False))


def _ensure_start_game_launcher_loop_thread():
    """런처 START(템플릿①) 루프 — Qt 이벤트 루프·다른 매크로보다 먼저 돌려 기동 직후부터 감지."""
    global _start_game_launcher_loop_thread_started
    if _start_game_launcher_loop_thread_started:
        return
    _start_game_launcher_loop_thread_started = True
    threading.Thread(target=start_game_launcher_loop, daemon=True).start()


def _start_pipela_background_threads_and_listeners():
    """UI 표시 후 기동 — 8개 매크로 루프 + pynput 마우스/키보드."""
    global mouse_listener, keyboard_listener, _pipela_background_loops_started
    if _pipela_background_loops_started:
        return
    _ensure_cv2_numpy_mss()
    _pipela_background_loops_started = True
    threading.Thread(target=left_click_loop, daemon=True).start()
    threading.Thread(target=right_hold_loop, daemon=True).start()
    threading.Thread(target=flame_trigger_loop, daemon=True).start()
    threading.Thread(target=ride_loop, daemon=True).start()
    threading.Thread(target=hp_refill_loop, daemon=True).start()
    threading.Thread(target=reload_loop, daemon=True).start()
    threading.Thread(target=ammo_restock_loop, daemon=True).start()
    threading.Thread(target=call_merc_loop, daemon=True).start()
    threading.Thread(target=kill_counter_loop, daemon=True).start()
    _ensure_start_game_launcher_loop_thread()
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    keyboard_listener = keyboard.Listener(on_press=on_key)
    keyboard_listener.start()
    telemetry_start_periodic_emitter()


def _pipela_bootstrap_pre_ui():
    """UI 기동 전 공통 — DPI·설정·창 탐색·배너 출력 후 `start_tray_only` 반환."""
    global start_game_launcher_active
    atexit.register(_kill_counter_stats_flush_pending_save)
    atexit.register(_atexit_save_registry_config)
    _ensure_process_dpi_awareness()
    print("=" * 40)
    print(PIPELA_APP_DISPLAY_NAME)
    print("=" * 40)
    print(f"[{PIPELA_APP_DISPLAY_NAME}] LeftClick — 홀드 시 자동 클릭")
    print(f"[{PIPELA_APP_DISPLAY_NAME}] RightHold — 우클릭 토글")
    print(f"[{PIPELA_APP_DISPLAY_NAME}] Flame — GUI 좌클릭: 기능 / 휠클릭: ON (기능 ON일 때)")
    print(f"[{PIPELA_APP_DISPLAY_NAME}] F5 Reload · F6 Ammo · F8 종료 · 트레이 우클릭(종료)")
    print("=" * 40)
    print(f"[{PIPELA_APP_DISPLAY_NAME}] scale BASE_HEIGHT={BASE_HEIGHT}px")
    load_config()
    game_hwnd = find_eternalcity_window()
    if game_hwnd:
        try:
            apply_game_window_screen_center()
        except Exception:
            pass
    launcher_hwnd = find_smart_updater_window()
    if game_hwnd:
        print(f"[{PIPELA_APP_DISPLAY_NAME}] game window OK")
    else:
        print(f"[{PIPELA_APP_DISPLAY_NAME}] game window — (대기)")
    if launcher_hwnd and not game_hwnd:
        print(
            f"[{PIPELA_APP_DISPLAY_NAME}] 스마트업데이터 런처 OK — 게임 미연결 시 런처에 UI 도킹",
            flush=True,
        )
        # AGENT: even if registry intro-skip off, launcher-only boot forces START template① detect+click on.
        try:
            if not is_window_minimized(int(launcher_hwnd)):
                start_game_launcher_active = True
                refresh_registry_config_snapshot(globals())
        except Exception:
            pass
    start_tray_only = (game_hwnd is None and launcher_hwnd is None) and PIPELA_TRAY_AVAILABLE
    if pipela_dev_ui_enabled():
        start_tray_only = False
        if game_hwnd is None and launcher_hwnd is None:
            print(
                f"[{PIPELA_APP_DISPLAY_NAME}] DEV UI — 게임·런처 없이 제어창·킬·스트립 표시 "
                "(소스 실행 기본 / PIPELA_DEV_UI=1 / --dev-ui, 끄기: PIPELA_DEV_UI=0)",
                flush=True,
            )
    if game_hwnd is None and launcher_hwnd is None and not PIPELA_TRAY_AVAILABLE:
        print(
            f"[{PIPELA_APP_DISPLAY_NAME}] pystray 미설치 — 제어창을 표시합니다. "
            "(게임·런처 없을 때 트레이 전용 시작: pip install pystray)",
            flush=True,
        )
    elif start_tray_only:
        print(
            f"[{PIPELA_APP_DISPLAY_NAME}] 게임·런처 미감지 — 시스템 트레이만 사용합니다. "
            "종료: 트레이 우클릭 → «종료». 게임 또는 스마트업데이터 런처가 보이면 제어창이 자동 도킹됩니다.",
            flush=True,
        )
    return start_tray_only


def shutdown_after_ui_mainloop():
    """`QApplication.exec()` 종료 직전 정리(저장·훅·리스너)."""
    global running, mouse_listener, keyboard_listener
    try:
        from pipela_core.ai_debug_session_log import log_ai_json_event

        log_ai_json_event("qt_mainloop_end", {"running": False})
    except Exception:
        pass
    _region_preview_sync_persist_from_live()
    try:
        flush_save_config_debounced()
    except Exception:
        pass
    try:
        _kill_counter_stats_flush_pending_save()
    except Exception:
        pass
    _state_set("running", False)
    set_capslock(False)
    if mouse_listener is not None:
        try:
            mouse_listener.stop()
        except Exception:
            pass
    if keyboard_listener is not None:
        try:
            keyboard_listener.stop()
        except Exception:
            pass


class _PipelaExecGlobalsProxy:
    """`python -m cProfile … main.py` 는 스크립트를 ``exec(code, globs)`` 로 돌려
    ``pipela_overlay_tick_ms`` 등이 ``globs`` 에만 있고 ``sys.modules['__main__']`` 와 어긋날 수 있다.
    ``main_qt.__globals__`` 와 동일한 dict 에 속성 접근을 맞춘다.
    """

    __slots__ = ("_g",)

    def __init__(self, g: dict) -> None:
        object.__setattr__(self, "_g", g)

    def __getattribute__(self, name: str):
        if name == "_g":
            return object.__getattribute__(self, "_g")
        g = object.__getattribute__(self, "_g")
        try:
            return g[name]
        except KeyError:
            return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value) -> None:
        if name == "_g":
            object.__setattr__(self, name, value)
        else:
            self._g[name] = value


def _pipela_mod_for_qt():
    """Qt에 넘기는 `pipela_mod` — 실제 로드된 main 모듈을 우선(프록시 `__getattribute__` 호출 방지)."""
    for _k in (__name__, "__main__", "main"):
        m = sys.modules.get(_k)
        if m is None:
            continue
        if getattr(m, "pipela_overlay_tick_ms", None) is None:
            continue
        if not hasattr(m, "target_hwnd") or not hasattr(m, "refresh_target_hwnd_if_needed"):
            continue
        return m
    return _PipelaExecGlobalsProxy(main_qt.__globals__)


def main_qt():
    """PyQt6 기본 진입 — 소스·PyInstaller 공통(`if __name__ == "__main__"` 기본 분기)."""
    global running
    try:
        from pipela_core.ai_debug_session_log import install_stdio_tee

        install_stdio_tee()
    except Exception:
        pass
    start_tray_only = _pipela_bootstrap_pre_ui()
    import pipela_qt.shell as _pipela_qt_shell

    pipela_mod = _pipela_mod_for_qt()
    _state_set("running", True)
    _ensure_start_game_launcher_loop_thread()
    try:
        _pipela_qt_shell.run_qt_application(pipela_mod=pipela_mod, start_tray_only=start_tray_only)
    finally:
        shutdown_after_ui_mainloop()


def pipela_cli_main() -> None:
    """Entry for ``python main.py`` — applies ``--profile-agent`` shell-wide."""
    while "--qt" in sys.argv:
        sys.argv.remove("--qt")
    while "--tk" in sys.argv:
        sys.argv.remove("--tk")
    while "--dev-ui" in sys.argv:
        sys.argv.remove("--dev-ui")
    while "--no-dev-ui" in sys.argv:
        sys.argv.remove("--no-dev-ui")
    _pipela_subprocess_pyspy_or_exit(main_file=__file__)
    _pipela_subprocess_scalene_or_exit(main_file=__file__)
    _tm_on = _pipela_tracemalloc_start_maybe()
    _pipela_cprof_agent = None
    if _pipela_profile_agent_cli_or_env_enabled():
        _pipela_strip_profile_agent_argv()
        import cProfile

        print(
            "Pipela: cProfile on - on exit -> profiling/agent_profile/ (PIPELA_PROFILE_AGENT=1 or --profile-agent)",
            flush=True,
        )
        _pipela_cprof_agent = cProfile.Profile()
        _pipela_cprof_agent.enable()
    try:
        main_qt()
    finally:
        _pipela_tracemalloc_dump_maybe(_tm_on, main_file=__file__)
        if _pipela_cprof_agent is not None:
            _pipela_cprof_agent.disable()
            try:
                _pipela_write_agent_cprofile_handoff(_pipela_cprof_agent, main_file=__file__)
            except Exception:
                repo = os.path.dirname(os.path.abspath(__file__))
                err_txt = os.path.join(repo, "profiling", "agent_profile", "cprofile_handoff_fatal.txt")
                try:
                    os.makedirs(os.path.dirname(err_txt), exist_ok=True)
                    import traceback as _tb

                    with open(err_txt, "w", encoding="utf-8", errors="replace") as ef:
                        ef.write(_tb.format_exc())
                except Exception:
                    pass
            print("Pipela: profiling handoff folder -> profiling\\agent_profile\\", flush=True)


if __name__ == "__main__":
    pipela_cli_main()
