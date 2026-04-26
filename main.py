import sys

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

# UI 첫 페인트 후 데몬 스레드·전역 입력 훅 기동(시작 체감 개선)
PIPELA_BACKGROUND_START_DELAY_MS = 50
# 시스템 트레이(pystray) — import/스레드 스파이크 완화용 추가 지연
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
import win32gui
import winreg
from pynput import mouse, keyboard
from PIL import Image, ImageDraw, ImageFont

# 터미널 «상대» 시각(세션 경과) — `pipela_core.console_log_prefix`·Qt 제어창
pipela_app_start_monotonic = time.monotonic()

# cv2 / numpy / mss — 모듈 import 비용이 커서 첫 GUI 프레임 이후·필요 시 로드
cv2 = None
np = None
mss = None


def _ensure_cv2_numpy_mss():
    """코어 `vision_lazy` 와 동기 — 기존 전역 cv2/np/mss 사용처 유지."""
    global cv2, np, mss
    if cv2 is not None:
        return
    from pipela_core.vision_lazy import ensure_cv2_numpy_mss as _vl_ensure

    cv2, np, mss = _vl_ensure()


def _pynput_key_to_vk(key):
    """pynput on_press key → Windows VK(0–255). 매핑 불가 시 None."""
    try:
        if key is not None and hasattr(key, "vk") and key.vk is not None:
            return int(key.vk) & 0xFF
    except Exception:
        pass
    try:
        _named = {
            keyboard.Key.f1: 0x70, keyboard.Key.f2: 0x71, keyboard.Key.f3: 0x72,
            keyboard.Key.f4: 0x73, keyboard.Key.f5: 0x74, keyboard.Key.f6: 0x75,
            keyboard.Key.f7: 0x76, keyboard.Key.f8: 0x77, keyboard.Key.f9: 0x78,
            keyboard.Key.f10: 0x79, keyboard.Key.f11: 0x7A, keyboard.Key.f12: 0x7B,
            keyboard.Key.space: 0x20,
            keyboard.Key.enter: 0x0D,
            keyboard.Key.tab: 0x09,
            keyboard.Key.esc: 0x1B,
            keyboard.Key.backspace: 0x08,
            keyboard.Key.insert: 0x2D,
            keyboard.Key.delete: 0x2E,
            keyboard.Key.page_up: 0x21,
            keyboard.Key.page_down: 0x22,
            keyboard.Key.end: 0x23,
            keyboard.Key.home: 0x24,
            keyboard.Key.left: 0x25,
            keyboard.Key.up: 0x26,
            keyboard.Key.right: 0x27,
            keyboard.Key.down: 0x28,
        }
        if key in _named:
            return _named[key]
    except Exception:
        pass
    try:
        if hasattr(key, "char") and key.char is not None and len(key.char) == 1:
            o = ord(key.char.upper())
            if ord("A") <= o <= ord("Z"):
                return o
            if ord("0") <= o <= ord("9"):
                return o
    except Exception:
        pass
    return None


# 상태 변수
left_click_feature_enabled = True  # LeftClick 기능 자체 ON/OFF (OFF면 홀드해도 발동 안함)
left_click_active = False
# 제어창·오버레이 레이아웃/위젯 갱신 — display_tick_ms()(주사율)와 동일 틱.
# Z-order 동기: 너무 자주 SetWindowPos 하면 부담, 너무 느리면 끊겨 보임.
CONTROL_Z_SYNC_MIN_INTERVAL_SEC = 0.05
# 게임 창 따라가기 시 레이아웃 틱을 주사율의 몇 배로 촘촘히 할지(2 ≈ 2배 빈도, 간격은 base//2 ms).
CONTROL_GUI_LAYOUT_FOLLOW_TICK_DIVISOR = 2
# 작업 표시줄 비표시 Win32 스타일 재적용 — 매 레이아웃마다 하면 메인 스레드 버벅임 유발, 주기만.
CONTROL_TASKBAR_EXSTYLE_REAPPLY_SEC = 1.25


def control_gui_update_ms() -> int:
    return display_tick_ms()


def control_gui_widgets_update_ms() -> int:
    return display_tick_ms()
# P1: 해상도 라벨용 DPI 조회 TTL (초)
NATIVE_DPI_CACHE_TTL_SEC = 5.0
# P2: 제어 패널 버튼 — set_colors/set_rest 동일값이면 캔버스 재그리기 생략; 킬 패널 스크롤은 update_idletasks 1회
# 게임을 한 번이라도 잡은 뒤 클라이언트 창이 사라진 상태가 이 시간(초) 이상이면 절전(저부하 대기)으로 전환
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


# 자동 클릭: 클릭 한 번 처리 후 다음 클릭까지 대기(ms). mouse_click() 내부 무시 창은 MOUSE_CLICK_IGNORE_SEC.
left_click_interval_ms = 100.0
# LeftClick ON: 왼쪽 홀드 최소 시간(초). 짧을수록 발동은 빨라지나 오발동 가능. 설정창·레지스트리에서 변경.
left_click_hold_sec = 0.15
# 자동 클릭과 사용자 OFF 클릭이 겹칠 때(ignore_left), 합성 입력 직후 물리 버튼 확인 지연.
LEFT_CLICK_OFF_ARM_DELAY_SEC = 0.025
# mouse_click() 동안 pynpress에 잡히는 합성 클릭 무시 창(초) — 짧을수록 OFF 반응은 좋아짐.
MOUSE_CLICK_IGNORE_SEC = 0.004
left_click_random_enabled = False  # True면 최소~최대(ms) 사이 균등 랜덤
left_click_random_min_ms = 100.0
left_click_random_max_ms = 100.0
right_hold_feature_enabled = True  # RightHold 기능 자체 ON/OFF (OFF면 우클릭으로 유지 토글 안 함)
right_hold_active = False
flame_trigger_feature_enabled = True  # Flame Trigger 기능 자체 ON/OFF (GUI·다른 기능들과 동일)
flame_trigger_active = False
flame_trigger_start_time = 0  # Flame Trigger 시작 시간 (전역 변수)
merc_fire_enabled = True  # Flame Trigger 내 Merc Fire(키 연속 입력) (기본 ON)
merc_fire_key_code = VK_1
merc_fire_random_min_ms = 500.0
merc_fire_random_max_ms = 1500.0
flame_trigger_press_text_until = 0.0  # Flame Trigger Press N 텍스트 표시 종료 시각
flame_trigger_press_key_name = "1"    # 마지막으로 누른 키 이름 (표시용)
flame_trigger_press_count = 0         # Flame Trigger Press 발동 횟수 (실시간 표시용)
flame_trigger_last_press_interval_sec = 0.0  # 직전 발동~이번 발동 간격(초), 발동마다 갱신
flame_trigger_prev_press_timestamp = None    # 내부: 마지막 키 입력 시각


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


reload_active = True  # 기본값 True
ammo_restock_active = False
ammo_restock_threshold = 0.6  # 레거시·호환 (buybutton과 동기 권장)
ammo_restock_buybutton_threshold = 0.6
ammo_restock_inven_threshold = 0.6
ammo_restock_bank_threshold = 0.6
ammo_restock_buybutton_score = 0.0
ammo_restock_inven_score = 0.0
ammo_restock_bank_score = 0.0
call_merc_active = False  # Reload와 동일 — 좌클릭 토글, ON이면 감시 (① 트리거 시 FT 해제·사이클 끝에 복귀)
call_merc_sequence_busy = False  # ②~④ 진행 중(GUI · Reload 작업중과 유사)
call_merc_restore_ft_after_cycle = False  # ① 직전 FT ON이었을 때만 사이클 완료 후 FT 재켜기
# ① 임계값·점수 — Reload의 nobullet 트리거와 동일 역할(①이 기준 이상이면 ②③④ 시퀀스 시작)
call_merc_1_threshold = 0.6
call_merc_2_threshold = 0.6
call_merc_3_threshold = 0.6
call_merc_4_threshold = 0.6
call_merc_1_score = 0.0
call_merc_2_score = 0.0
call_merc_3_score = 0.0
call_merc_4_score = 0.0
running = True
# Qt 도킹 UI 페이즈 — "standby"(대기) | "launcher" | "client" (`pipela_qt.dock_ui_phase`), 런타임만·레지 아님
pipela_ui_dock_phase = "standby"
mouse_listener = None
keyboard_listener = None
_pipela_background_loops_started = False
_start_game_launcher_loop_thread_started = False
# 터미널 로그 줄 보존 시간(분). 초과 분은 주기적으로 삭제(설정에서 변경)
pipela_ui_font_pt = 11  # Qt UI 루트 글꼴(pt), 8~24
# Qt 커서·플레임 HUD 오버레이(진단: 끄면 해당 경로만 비활성). 기동 시 PIPELA_CURSOR_HUD=0 으로 끌 수 있음
pipela_cursor_hud_enabled = True
console_log_retention_minutes = 30
# 터미널 시간 표시: absolute = 월-일 시:분:초, relative = 그 줄이 찍힌 뒤 경과(초·분·…, 1초마다 갱신)
# CONSOLE_LOG_* 상수는 pipela_core.console_log_constants
console_log_time_display_mode = CONSOLE_LOG_TIME_MODE_ABSOLUTE
target_hwnd = None
# True면 이터널시티 상단 창을 모니터 작업 영역(rcWork) 정중앙에 맞춤(주기적 재정렬, 영역 선택 중 제외)
game_window_center_on_detect_enabled = True
_GAME_CENTER_THROTTLE_SEC = 0.72
_game_center_throttle_next_mono = 0.0
_last_centered_target_game_hwnd: int | None = None
_smart_updater_hwnd_cache = None  # START GAME 템플릿 — 「스마트업데이터」창만
# 게임 HWND가 이미 있을 때 런처 Enum 생략 구간(cProfile: refresh_smart_updater ~25Hz → Enum 폭주)
_smart_updater_poll_skip_until = 0.0
_game_client_was_ever_connected = False
_game_client_disconnect_since = None  # time.time() — 미연결 시작 시각(한 번 연 뒤에만 사용)
ignore_left = False
ignore_right = False
image_detected = False
image_score = 0.0  # 현재 감지 점수 (Ride용)
ride_threshold = 0.6  # Ride 매칭 기준 점수
reload_threshold = 0.6  # 레거시·nobullet과 동기 (reload_nobullet_threshold)
reload_nobullet_threshold = 0.6  # NoBullet.png 매칭 기준
reload_bullet_threshold = 0.6  # bullet.png 매칭 기준
reload_vault_threshold = 0.6  # Vault 템플릿 매칭 기준 (Bullet 미감지 시)
reload_ammo_count = 45  # 재장전 시 입력할 총알 수 (숫자 키로 순서대로 입력됨, 기본 45)
hp_refill_threshold = 0.6  # HP Refill 매칭 기준 점수
ride_feature_enabled = True  # Ride 감지·캡스락 연동 ON/OFF
hp_refill_feature_enabled = True  # HP Refill 감지 ON/OFF
capslock_state = False
select_mode = False
ride_detect_region = None   # Ride 전용 감지 영역
hp_refill_detect_region = None  # HP Refill 전용 감지 영역
kill_counter_detect_region = None  # Kill Counter OCR — 비율 영역(미지정이면 OCR 안 함)
# 템플릿 매칭 ROI(클라이언트 비율 [x,y,w,h]). None이면 전체 클라이언트(게임 창 전체).
reload_nobullet_match_region = None
reload_bullet_match_region = None
reload_vault_match_region = None  # Vault UI — ROI 미지정이면 Vault 단계 비활성
ammo_buybutton_match_region = None
ammo_inven_match_region = None
ammo_bank_match_region = None
call_merc_1_match_region = None  # ① 매칭 ROI — Reload NoBullet 영역과 같은 개념(트리거 전용)
call_merc_2_match_region = None
call_merc_3_match_region = None
call_merc_4_match_region = None
left_pressed = False  # 왼쪽 버튼 누름 상태
left_click_id = 0     # 클릭 ID (더블클릭 구분용)
user_left_pending = False  # 사용자가 OFF하려고 클릭 중
_left_off_arm_gen = 0  # ignore_left 시 OFF 예약 지연 스레드 세대(최신만 유효)

# Reload 상태 변수
nobullet_detected = False  # nobullet 감지 및 작업 진행 중 여부
last_nobullet_time = -1  # 마지막 nobullet 감지 시간 (-1이면 초기 상태)
nobullet_detection_score = 0.0  # nobullet 감지 점수
bullet_detection_score = 0.0  # bullet 템플릿 현재 매칭 점수(표시용)
vault_detection_score = 0.0  # Vault 템플릿 점수(표시용)
reload_success_count = 0  # Reload 작업 성공 횟수

# 설정 패널 「현재」 펄스 — 템플릿별로 매칭 시도가 있었으면 True (키: (feature, sub) → time.monotonic())
_template_probe_last_mono = {}
_SETTINGS_PROBE_STALE_SEC = 1.5  # 마지막 매칭 시도 후 이 시간 안이면 펄스 유지(느린 폴링 간격 포함)
# 템플릿 매칭 성공 시 마지막 패치(BGR) — Qt 패널 등에서 필요 시 소비
_template_last_hit_bgr = {}

# Ammo Restock 상태 변수
ammo_restock_loop_count = 0  # Ammo Restock 루프 횟수
# 토글 단축키 (Windows 가상 키 코드) — 한 키로 Ammo Restock 감지 ON/OFF
ammo_restock_toggle_key_code = 0x75  # F6

# Call Merc — ON일 때 ①을 Reload nobullet처럼 폴링; ①에서 FT 끈 경우에만 끝에 FT 재켜기
call_merc_loop_count = 0
CALL_MERC_ARM_COOLDOWN_SEC = 5.0  # ④까지 끝난 뒤 ① 트리거 재감지까지(쿨타임)
# 설정창 순서 화살표 — call_merc_loop phase·단계 전환과 동기 (GUI 스레드에서 읽음)
call_merc_phase_ui = 0  # 0~3 = ①~④ 진행 상태
call_merc_arrow_pulse_idx = -1  # -1 없음, 0~2=해당 화살표 전환 펄스, 3=사이클 완료 연출
call_merc_arrow_pulse_mono = 0.0

# HP Refill 상태 변수
hp_refill_detection_score = 0.0  # HP Refill 감지 점수 (GUI 표시용)
hp_refill_key_code = VK_Z  # 감지 시 누를 키 (기본 Z)
hp_refill_trigger_total = 0  # HP Refill 키 발동 누적 횟수 (세션만, 종료 시 초기화)

# Kill Counter — 감지 영역에서 숫자·슬래시만 OCR (기본 ON). 화면 변화 시에만 OCR(픽셀 비교).
kill_counter_enabled = True
# 킬 통계 그래프 막대 가로 배율(%) — 기본 100, 50~300 레지스트리 저장
kill_counter_graph_bar_scale_percent = 100


def _kill_counter_graph_bar_scale_snap(v):
    """막대 가로 배율(%) — 50~300, 5단위 스냅."""
    v = int(round(float(v)))
    v = max(50, min(300, v))
    return 50 + round((v - 50) / 5) * 5


# 캡처 샘플링 간격(초·내부 고정). OCR은 감지 영역이 이전 대비 달라졌을 때만 수행
_KILL_COUNTER_CHANGE_PROBE_SLEEP_SEC = 0.07
# 연속 캡처 간 다운스케일 그레이 평균 절대차가 이 값(0~255) 미만이면 "변화 없음"으로 OCR 생략
# (과거: 마지막 OCR 프레임과만 비교 + 거친 축소·높은 임계값 → 숫자만 바뀌어도 갱신 누락)
_KILL_COUNTER_CHANGE_MEAN_ABS_THRESH = 1.15
_kill_counter_last_change_probe_bgr = None
# 직전 성공 OCR Tesseract config — 다음 호출에서 먼저 시도(서브프로세스·PIL 저장 횟수↓)
_kill_counter_tesseract_cfg_first: str | None = None
# 킬 통계 패널 행 순서 (드래그로 재배열, 레지스트리 JSON 저장) — 키·정규화는 pipela_core.kill_counter_layout
kill_counter_stats_row_order = list(KILL_COUNTER_STAT_ROW_KEYS_DEFAULT)
# 랩 —「랩 시작」 시각 이후 영구 킬 이벤트 (None = 미시작)
kill_counter_lap_start_ts = None
# 일시중지 구간 [[pause_start, pause_end], ...] — pause_end 가 None 이면 현재 일시중지 중
kill_counter_lap_pause_segments = []
_KILL_COUNTER_LAP_PAUSE_BTN_BG = "#b45309"
_KILL_COUNTER_LAP_PAUSE_BTN_ACTIVE_BG = "#c2410c"
_KILL_COUNTER_LAP_PAUSE_BTN_FG = "#ffffff"
_KILL_COUNTER_LAP_SW_FG_RUNNING = "#e2e8f0"
_KILL_COUNTER_LAP_SW_FG_PAUSED = "#fbbf24"
_KILL_COUNTER_LAP_CELL_OUTLINE = "#3f4a5c"
# killcount.md 등급표 (포인트~다음 단계 몬스터킬) — 최초 사용 시 로드
_kill_counter_rank_table_rows = None
# OCR `숫자1/숫자2` 패턴에서 숫자1만 세션·통계·등급표 구간에 사용. 숫자2는 인식·호환용
kill_counter_last_progress = ""  # 최근 OCR 전체 문자열(예: 3/10) — 내부 파싱·호환용
kill_counter_last_poll_ts = 0.0  # OCR 루프에서 실제 캡처·OCR 시도 직후 시각(time.time)
# 마지막 OCR 시도 결과 — ok|empty|no_pair|unstable|error, None=아직 없음(첫 폴링 전)
kill_counter_last_poll_phase = None
kill_counter_last_poll_detail = None  # 부가 한 줄(오류·형식 설명 등)
_kill_counter_tesseract_av_cache = None  # (bool, monotonic_ts) — 패널 상태 줄용 짧은 캐시
# 검출 숫자 영역 오버레이 테두리(_kc_pulse_draw_num_red)와 동일한 톤 — 패널 현재 킬 글자색
KILL_COUNTER_DETECTED_NUM_FG = "#52E6DA"  # 청록 액센트 계열 — 현재 킬 숫자(OCR·오버레이)
KILL_COUNTER_PANEL_CURRENT_TITLE_FG = "#9fe8ff"  # 「현재 킬」소제목 — 숫자 톤과 맞춘 밝은 시안
# 세션 킬: 첫 검출 숫자1을 기준으로 현재 숫자1 증가분 누적(단계 리셋 시 구간 합산)
kill_counter_session_baseline_n1 = None
kill_counter_session_last_n1 = None
kill_counter_session_carried_kills = 0
kill_counter_session_start_ts = None  # 첫 세션 기준 잡힌 시각(로컬 표시용)
# 급증 1틱 거절 후에도 비슷한 n1이 이 횟수만큼 연속 검출되면 정식 인정
KILL_COUNTER_SPIKE_CONFIRM_POLLS = 3
kill_counter_spike_confirm_streak = 0
kill_counter_spike_confirm_last_n = None
# Kill Counter 영구 통계: 세션 킬 증가분을 (시각, 개수)로 누적 — %LOCALAPPDATA%\\Pipela\\kill_counter_stats.json
_kill_counter_stats_lock = threading.RLock()
_kill_counter_stats_loaded = False
_kill_counter_stats_events = []  # [{"t": unix_float, "d": int}, ...]
_kill_counter_stats_daily = {}  # "YYYY-MM-DD" (로컬 0시 기준) -> 킬 합
_kill_counter_stats_save_timer = None
# 영구 통계 ↔ 현재 킬 n1 정합: 로컬일 첫 OCR n1을 하루 시작값으로 두고, 오늘 이벤트 합이 (n1−시작)을 넘지 않게 보정
kill_counter_reconcile_local_date = None
kill_counter_n1_at_local_day_start = None
# Kill Counter 디버그: 검출 시 오버레이 무지개 펄스 (rect는 캡처 좌표 (l,t,r,b))
_kill_counter_overlay_queue = queue.Queue()
# 템플릿 「감지」 버튼: 매칭 박스 + 점수 캡션 (rect 동일 좌표계, (rect, "0.00") 튜플)
_template_debug_overlay_queue = queue.Queue()
# 템플릿 감지 박스 내부 채움 — stipple 26/64비트 ≈ 40.6% (나머지는 검정=transparentcolor 키아웃)
_TEMPLATE_DETECT_OVERLAY_FILL_STIPPLE_XBM = """
#define echtdet40_width 8
#define echtdet40_height 8
static unsigned char echtdet40_bits[] = {
   0xaa, 0x55, 0xaa, 0x55, 0x88, 0x22, 0x88, 0x33
};
"""
# Flame Trigger 실제 시작(중앙 우클릭 홀드) 시 게임 위 배너 — 워커→메인 스레드
_flame_start_banner_queue = queue.Queue(maxsize=8)
_kill_counter_tesseract_cmd_checked = False

# 경로 — pipela_core.paths (Qt·main 공통; frozen/소스 루트 규칙은 한곳에서만 유지)
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
    registry_load_bool,
    save_call_merc_thresholds,
    save_console_ui_region_preview,
    save_ammo_restock_thresholds,
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
    CONFIG_SAVE_MERC_FIRE_FIELDS as _CONFIG_SAVE_MERC_FIRE_FIELDS,
    CONFIG_SAVE_SZ_FIELDS as _CONFIG_SAVE_SZ_FIELDS,
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
    CALL_MERC_LOG_PREFIX as _CALL_MERC_LOG_PREFIX,
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
    START_GAME_LAUNCHER_TEMPLATE_SCALE_RATIO,
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
)

# 메모리에 저장된 이미지 데이터 (레지스트리에서 로드)
RELOAD_NOBULLET_IMAGE_DATA = None
RELOAD_BULLET_IMAGE_DATA = None
RELOAD_VAULT_IMAGE_DATA = None
HP_REFILL_ZKEY_IMAGE_DATA = False  # 레지스트리 hp_refill_zkey_image_data 존재 여부 (미리보기 등)
# 런처 — 아래 타이틀 규칙에 맞는 창 클라이언트에서만 START GAME 템플릿 매칭
# (한글 부분 문자열은 pipela_core.win32_game_windows.SMART_UPDATER_TITLE_KO_SUBSTR)
start_game_launcher_active = False
start_game_launcher_threshold = 0.65
start_game_launcher_match_region = None
start_game_launcher_score = 0.0
START_GAME_LAUNCHER_IMAGE_DATA = False
# ② 런처 START GAME 클릭 후 — 이터널시티 게임 창에서 Intro Skip 템플릿 1회 클릭
start_game_intro_skip_threshold = 0.65
start_game_intro_skip_match_region = None
start_game_intro_skip_score = 0.0
START_GAME_INTRO_SKIP_IMAGE_DATA = False
START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC = 180.0
# ③ Intro Skip 클릭 후 — 게임 창에서 Accept 템플릿 1회 클릭
start_game_accept_threshold = 0.65
start_game_accept_match_region = None
start_game_accept_score = 0.0
START_GAME_ACCEPT_IMAGE_DATA = False
START_GAME_ACCEPT_ARM_TIMEOUT_SEC = 180.0
# 런처 START GAME: 1회 클릭 → 최대 N초 안에 런처 HWND 미검出면 1회 재클릭; 창이 먼저 사라지면 1클릭으로 Intro Skip 무장
START_GAME_LAUNCHER_POST_CLICK_DISAPPEAR_WAIT_SEC = 5.0
# 같은 런처에서 클릭 시퀀스를 다시 시도하기까지 최소 간격(실패·무장 직후)
START_GAME_LAUNCHER_RETRY_COOLDOWN_SEC = 1.0
_start_game_intro_skip_armed = False
_start_game_intro_skip_arm_until_mono = 0.0
_start_game_accept_armed = False
_start_game_accept_arm_until_mono = 0.0

# Flame HUD — `pipela_qt.cursor_hud` 가 아래 상수를 읽음
CURSOR_FLAME_OVERLAY_ALPHA = 0.8
CURSOR_FLAME_PANEL_OFFSET_X = 48
FLAME_START_BANNER_TEXT = "Flame Trigger가 시작되었습니다!"
FLAME_START_BANNER_DURATION_SEC = 3.0
FLAME_START_BANNER_CLIENT_Y_FRACTION = 0.15
FLAME_START_BANNER_FONT_PT = 22
FLAME_START_BANNER_BLINK_ON_ALPHA = CURSOR_FLAME_OVERLAY_ALPHA
FLAME_START_BANNER_BLINK_OFF_ALPHA = 0.10
FLAME_START_BANNER_BLINK_MS = 320
FLAME_START_BANNER_ANIM_MS = 100


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


# GUI 폰트 — pipela_core.ui_fonts (한글 맑은 고딕·영문 모노 스택, AGENTS.md)


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


# Qt 제어창·설정(`pipela_qt`·`pipela_mod` 폰트 헬퍼)과 통일 — 제목 pady=12, 섹션 간격은 CONTROL_PANEL_GAP_Y
SETTINGS_WINDOW_WIDTH = 320
CONTROL_WINDOW_DISCONNECTED_HEIGHT = 1440  # 이터널시티 미감지 시 제어창 기본 세로
CONTROL_WINDOW_FALLBACK_HEIGHT = 640  # 감지됐으나 클라이언트 크기 조회 실패 시
CONTROL_WINDOW_LAUNCHER_DOCK_HEIGHT = 920  # 게임 없이 런처만 도킹 시 세로(px) — 런처 높이와 무관
# 제어창 메인 버튼 — 폰트·패딩·아이콘 통일(행마다 높이 일치)
CONTROL_PANEL_BTN_FONT_SIZE = 12
CONTROL_PANEL_ICON_SIDE = 24  # ui_icon_side 기준 — 글자 키울 때 아이콘도 동일 배율
CONTROL_PANEL_BTN_PADX = 12
CONTROL_PANEL_BTN_PADY = 11
CONTROL_PANEL_GAP_Y = 18  # 메인 제어창 — 섹션·행 사이 세로 간격
SETTINGS_WRAPLENGTH = 280      # 좌우 SETTINGS_PAD_X 제외한 본문 폭
SETTINGS_SLIDER_LENGTH = 210   # 320px 창 기준 슬라이더 트랙 길이 (동적 폭은 ui_px(SETTINGS_SLIDER_LENGTH))
SETTINGS_SLIDER_LENGTH_RELOAD = 154  # Reload: 느슨·엄격 라벨까지 한 줄에 넣고 중앙 정렬
SETTINGS_PAD_X = 20  # 디자인 기준(px); 실제 패딩은 settings_pad_x()
SETTINGS_TITLE_PADY = (10, 4)  # 상단 네임카드 — 아래 여백을 줄여 힌트·구분선과 밀집
SETTINGS_GAP_Y = 6             # 메인 섹션 줄간격 (click_frame.pack(pady=6) 등)
SETTINGS_BLOCK_PADY = 8        # 블록 내부 (체크박스 프레임 등)
# 힌트 블록(멀티라인 본문) 위·아래 — 제목 카드와 구분선 사이가 너무 벌어지지 않게
SETTINGS_HINT_FR_PADY = (4, 4)
# 힌트 직후 ~ 첫 섹션 구분선 직전 한 줄 공백(디자인 px)
SETTINGS_HINT_TO_SECTION_LINE = 3
SETTINGS_FOOTER_PAD = (4, 12)
SETTINGS_FOOTER_PAD_TOP_EXTRA = 12  # 본문과 닫기 버튼 사이 (4+12=16px, 이전 32px의 절반)
SETTINGS_FOOTER_PAD_OUTER = (
    SETTINGS_FOOTER_PAD[0] + SETTINGS_FOOTER_PAD_TOP_EXTRA,
    SETTINGS_FOOTER_PAD[1],
)
SETTINGS_BTN_PADX_FLAT = 10
SETTINGS_BTN_PADY_FLAT = 8
SETTINGS_MAIN_BTN_PAD = (15, 8)  # 메인 종료(F8) 버튼과 동일
SETTINGS_MAIN_ROW_BTN_PAD = (25, 10)  # 메인 Reload 등 넓은 행 버튼
SETTINGS_CARD_INNER_PAD = (16, 14)     # 설정창 카드 내부 패딩

# —— 다크 팔레트 (`pipela_qt/theme.py` 와 동일 톤; Qt·레이아웃 상수와 맞춤) ——
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


# 설정창 제목 계층 — 본문 옵션 구역은 작은 볼드 + 색으로 구분 (Qt 패널·`pipela_mod` 폰트 헬퍼)
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
    global left_click_feature_enabled, right_hold_feature_enabled, ride_feature_enabled, hp_refill_feature_enabled, flame_trigger_feature_enabled, kill_counter_enabled, kill_counter_graph_bar_scale_percent
    global left_click_interval_ms, left_click_hold_sec
    global left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    global RELOAD_NOBULLET_IMAGE_PATH, RELOAD_BULLET_IMAGE_PATH, RELOAD_VAULT_IMAGE_PATH, RELOAD_NOBULLET_IMAGE_DATA, RELOAD_BULLET_IMAGE_DATA, RELOAD_VAULT_IMAGE_DATA, HP_REFILL_ZKEY_IMAGE_DATA
    global RIDE_TARGET_IMAGE_PATH, HP_REFILL_ZKEY_IMAGE_PATH, AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH, AMMO_RESTOCK_INVEN_IMAGE_PATH, AMMO_RESTOCK_BANK_IMAGE_PATH
    global CALL_MERC_1_IMAGE_PATH, CALL_MERC_2_IMAGE_PATH, CALL_MERC_3_IMAGE_PATH, CALL_MERC_4_IMAGE_PATH
    global START_GAME_IMAGE_PATH, START_GAME_LAUNCHER_IMAGE_DATA
    global START_GAME_INTRO_SKIP_IMAGE_PATH, START_GAME_INTRO_SKIP_IMAGE_DATA
    global START_GAME_ACCEPT_IMAGE_PATH, START_GAME_ACCEPT_IMAGE_DATA
    global merc_fire_enabled, merc_fire_key_code
    global merc_fire_random_min_ms, merc_fire_random_max_ms
    global console_log_retention_minutes, console_log_time_display_mode
    global pipela_ui_font_pt
    global kill_counter_stats_row_order
    global kill_counter_lap_start_ts
    global kill_counter_lap_pause_segments
    global region_preview_overlay_saved_kind
    global game_window_center_on_detect_enabled
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

        # Merc Fire (merc_fire_*). 없으면 예전 flame_trigger_key_* 에서 1회만 읽음(이후 저장 시 구키 삭제)
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

        load_console_ui_region_preview(
            key,
            g,
            CONSOLE_LOG_RETENTION_MIN_MIN,
            CONSOLE_LOG_RETENTION_MAX_MIN,
            CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            CONSOLE_LOG_TIME_MODE_RELATIVE,
            _REGION_PREVIEW_PERSIST_VALID,
        )

        winreg.CloseKey(key)
    except FileNotFoundError:
        # 레지스트리 키가 없으면 기본값 사용 (처음 실행)
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
    global left_click_feature_enabled, right_hold_feature_enabled, ride_feature_enabled, hp_refill_feature_enabled, flame_trigger_feature_enabled, kill_counter_enabled, kill_counter_graph_bar_scale_percent
    global left_click_interval_ms, left_click_hold_sec
    global left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    global RELOAD_NOBULLET_IMAGE_PATH, RELOAD_BULLET_IMAGE_PATH, RELOAD_VAULT_IMAGE_PATH, RELOAD_NOBULLET_IMAGE_DATA, RELOAD_BULLET_IMAGE_DATA, RELOAD_VAULT_IMAGE_DATA, HP_REFILL_ZKEY_IMAGE_DATA
    global RIDE_TARGET_IMAGE_PATH, HP_REFILL_ZKEY_IMAGE_PATH, AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH, AMMO_RESTOCK_INVEN_IMAGE_PATH, AMMO_RESTOCK_BANK_IMAGE_PATH
    global CALL_MERC_1_IMAGE_PATH, CALL_MERC_2_IMAGE_PATH, CALL_MERC_3_IMAGE_PATH, CALL_MERC_4_IMAGE_PATH
    global START_GAME_IMAGE_PATH, START_GAME_INTRO_SKIP_IMAGE_PATH, START_GAME_ACCEPT_IMAGE_PATH
    global merc_fire_enabled, merc_fire_key_code
    global merc_fire_random_min_ms, merc_fire_random_max_ms
    global console_log_retention_minutes, console_log_time_display_mode
    global pipela_ui_font_pt
    global kill_counter_stats_row_order
    global kill_counter_lap_start_ts
    global kill_counter_lap_pause_segments
    global region_preview_overlay_saved_kind
    global game_window_center_on_detect_enabled
    try:
        # 레지스트리 키 생성 또는 열기
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.CloseKey(key)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_WRITE)
        gsave = globals()
        
        save_sz_same_key(key, gsave, _CONFIG_SAVE_BOOLS_PRE_KC)
        save_kill_counter_state(key, gsave)
        save_sz_same_key(key, gsave, _CONFIG_SAVE_BOOLS_FLAME)

        save_sz_same_key(key, gsave, _CONFIG_SAVE_LEFTCLICK_FIELDS)

        for _rn in _CONFIG_SAVE_JSON_REGION_NAMES:
            save_json_region_optional(key, _rn, gsave[_rn])

        save_reg_global_pairs(key, gsave, _CONFIG_SAVE_SZ_FIELDS)
        save_reg_global_pairs(key, gsave, _CONFIG_LOAD_TEMPLATE_IMAGE_PATHS)

        save_ammo_restock_thresholds(key, gsave)
        save_call_merc_thresholds(key, gsave)
        winreg.SetValueEx(key, "ammo_restock_toggle_key_code", 0, winreg.REG_SZ, str(ammo_restock_toggle_key_code))

        save_sz_same_key(key, gsave, _CONFIG_SAVE_MERC_FIRE_FIELDS)

        save_console_ui_region_preview(
            key,
            gsave,
            CONSOLE_LOG_RETENTION_MIN_MIN,
            CONSOLE_LOG_RETENTION_MAX_MIN,
            CONSOLE_LOG_TIME_MODE_ABSOLUTE,
            CONSOLE_LOG_TIME_MODE_RELATIVE,
            _REGION_PREVIEW_PERSIST_VALID,
        )

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
    _smart_updater_hwnd_cache = refresh_smart_updater_hwnd_cached(
        _smart_updater_hwnd_cache, START_GAME_SMART_UPDATER_TITLE_SUBSTR,
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
    global target_hwnd
    target_hwnd = refresh_eternalcity_hwnd_cached(target_hwnd)
    return target_hwnd


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
    # 게임 창이 활성화 상태인지 확인
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
    # IsIconic 윈도우(GetWindowRect → -32000) 등 비정상 음수 좌표 차단(가상 화면을 크게 벗어남)
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
    """저수준 오른쪽 마우스 누름"""
    global ignore_right
    ignore_right = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    ignore_right = False

def mouse_right_up():
    """저수준 오른쪽 마우스 떼기"""
    global ignore_right
    ignore_right = True
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
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


# region_type / capture kind 디스패치 — pipela_core.region_dispatch (위 import 에서 _REGION_* 별칭)


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


def _template_last_hit_store(kind: str, patch_bgr) -> None:
    """워커 스레드에서 호출 — 성공 매칭 패치(BGR) 보관 (`_template_last_hit_bgr`)."""
    if patch_bgr is None or getattr(patch_bgr, "size", 0) == 0:
        return
    _template_last_hit_bgr[kind] = patch_bgr


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


# OCR이 한 틱에 비현실적으로 튀는 경우 세션·통계·표시 갱신에서 제외
# 한 번의 폴링에서 이전 n1 대비 **증가분** 상한(비율 조건 없이 적용). 2686→50109 같은 오인식 차단.
_KILL_COUNTER_OCR_MAX_DELTA_PER_POLL = 3500
_KILL_COUNTER_OCR_MAX_UNANCHORED_N1 = 500_000  # 이전 검출 없을 때 단독 허용 상한(비현실적 첫 OCR 차단)
# 영구 통계 JSON: 단일 이벤트 증가분이 이 값을 넘으면 로드 시 제거(과거 오인식 이벤트 정리)
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
    """killcount.md 마지막 행 누적(초인 상한)을 초과하면 True — 비정상 OCR."""
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
    # 비율과 무관하게 1틱 증가 상한 — 기존은 ni>prev*45와 동시에만 Δ 제한이 걸려 중간 비율·대Δ(예: 2686→50109)가 통과함.
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
    global kill_counter_session_baseline_n1, kill_counter_session_last_n1, kill_counter_session_carried_kills
    global kill_counter_session_start_ts
    kill_counter_session_baseline_n1 = None
    kill_counter_session_last_n1 = None
    kill_counter_session_carried_kills = 0
    kill_counter_session_start_ts = None
    _kill_counter_reset_spike_confirm()


def _kill_counter_session_total_kills_display():
    """세션 누적 킬(첫 검출 숫자1 대비 현재 숫자1까지의 증가 + 완료된 구간)."""
    global kill_counter_session_baseline_n1, kill_counter_session_last_n1, kill_counter_session_carried_kills
    if kill_counter_session_baseline_n1 is None:
        return 0
    return int(
        kill_counter_session_carried_kills
        + max(0, (kill_counter_session_last_n1 or 0) - kill_counter_session_baseline_n1)
    )


def _kill_counter_update_session_from_n1(ni: int):
    """
    숫자1(현재 킬) 갱신. 첫 검출을 기준으로 증가분을 세고,
    큰 하락(단계 리셋 추정)이면 이전 구간의 (마지막−기준)을 누적에 더한다.
    """
    global kill_counter_session_baseline_n1, kill_counter_session_last_n1, kill_counter_session_carried_kills
    global kill_counter_session_start_ts
    if kill_counter_session_baseline_n1 is None:
        kill_counter_session_baseline_n1 = ni
        kill_counter_session_last_n1 = ni
        kill_counter_session_start_ts = time.time()
        return
    prev = kill_counter_session_last_n1
    if prev is None:
        kill_counter_session_last_n1 = ni
        return
    if ni < prev and (prev - ni) >= 2:
        kill_counter_session_carried_kills += max(0, prev - kill_counter_session_baseline_n1)
        kill_counter_session_baseline_n1 = ni
        kill_counter_session_last_n1 = ni
        return
    if ni < kill_counter_session_baseline_n1 and prev >= kill_counter_session_baseline_n1:
        kill_counter_session_carried_kills += max(0, prev - kill_counter_session_baseline_n1)
        kill_counter_session_baseline_n1 = ni
        kill_counter_session_last_n1 = ni
        return
    if ni < prev and (prev - ni) == 1:
        return
    kill_counter_session_last_n1 = ni


def _kill_counter_session_reanchor_after_ocr_gap(ni: int) -> None:
    """인식 실패(empty/error/no_pair) 뒤 첫 성공 시: 세션 표시 합을 유지한 채 n1에 맞춤.
    update_session만 쓰면 오인식·공백 구간 뒤 절대값이 누적 킬처럼 통계에 박힐 수 있음."""
    global kill_counter_session_baseline_n1, kill_counter_session_last_n1, kill_counter_session_carried_kills
    global kill_counter_session_start_ts
    try:
        ni = int(ni)
    except (TypeError, ValueError):
        return
    if ni < 0:
        return
    baseline_was_none = kill_counter_session_baseline_n1 is None
    t = _kill_counter_session_total_kills_display()
    kill_counter_session_carried_kills = int(t)
    kill_counter_session_baseline_n1 = ni
    kill_counter_session_last_n1 = ni
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


def _kill_counter_rank_table_path():
    return os.path.join(SCRIPT_DIR, "killcount.md")


# killcount.md와 동기화 — 파일이 없거나 비었을 때만 사용 (포인트 열 = 해당 호칭 달성 누적, 다음 행 포인트 = 몬스터킬 상한)
_KILL_COUNTER_RANK_POINTS_FALLBACK = (
    0,
    90000,
    218000,
    345000,
    473000,
    600000,
    822000,
    1053000,
    1293000,
    1548000,
    1800000,
    2133000,
    2479000,
    2839000,
    3222000,
    3600000,
    4044000,
    4506000,
    4986000,
    5497000,
    6000000,
    6556000,
    7132000,
    7732000,
    8371000,
    9000000,
    9667000,
    10359000,
    11079000,
    11845000,
    12600000,
    13378000,
    14185000,
    15025000,
    15919000,
    16800000,
    17689000,
    18612000,
    19572000,
    20593000,
    21600000,
    22600000,
    23638000,
    24718000,
    25867000,
    27000000,
    28111000,
    29265000,
    30465000,
    31742000,
    33000000,
)
_KILL_COUNTER_RANK_TITLES_FALLBACK = (
    "견습생1",
    "견습생1",
    "견습생2",
    "견습생3",
    "견습생4",
    "견습생5",
    "초보자1",
    "초보자2",
    "초보자3",
    "초보자4",
    "초보자5",
    "숙련자1",
    "숙련자2",
    "숙련자3",
    "숙련자4",
    "숙련자5",
    "전문가1",
    "전문가2",
    "전문가3",
    "전문가4",
    "전문가5",
    "장인1",
    "장인2",
    "장인3",
    "장인4",
    "장인5",
    "달인1",
    "달인2",
    "달인3",
    "달인4",
    "달인5",
    "대가1",
    "대가2",
    "대가3",
    "대가4",
    "대가5",
    "명인1",
    "명인2",
    "명인3",
    "명인4",
    "명인5",
    "명장1",
    "명장2",
    "명장3",
    "명장4",
    "명장5",
    "거장1",
    "거장2",
    "귀인1",
    "귀인2",
    "초인",
)


def _kill_counter_rank_builtin_rows():
    pts = _KILL_COUNTER_RANK_POINTS_FALLBACK
    titles = _KILL_COUNTER_RANK_TITLES_FALLBACK
    n = len(pts)
    out = []
    for i in range(n):
        out.append(
            {
                "num": i,
                "title": titles[i],
                "point": int(pts[i]),
                "next_cap": int(pts[i + 1]) if i + 1 < n else None,
            },
        )
    return out


def _kill_counter_parse_rank_md_text(body: str):
    """killcount.md 본문 → 행 dict 목록 (정렬)."""
    rows = []
    if not (body or "").strip():
        return rows
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] in ("번호", "---", "------") or set(cells[0]) <= {"-", ":"}:
            continue
        try:
            rnum = int(cells[0])
        except ValueError:
            continue
        title = (cells[1] or "").strip()
        try:
            point = int(re.sub(r"[\s,]", "", cells[2] or "0"))
        except ValueError:
            continue
        mk_raw = (cells[3] or "").strip().replace(" ", "")
        if mk_raw in ("-", "—", ""):
            next_cap = None
        else:
            try:
                next_cap = int(re.sub(r"[\s,]", "", mk_raw))
            except ValueError:
                next_cap = None
        rows.append({"num": rnum, "title": title, "point": point, "next_cap": next_cap})
    rows.sort(key=lambda r: int(r["point"]))
    return rows


def _kill_counter_load_rank_table():
    """killcount.md 파이프 표 → 포인트 오름차순. 파일 실패·빈 표 시 내장 폴백."""
    global _kill_counter_rank_table_rows
    if _kill_counter_rank_table_rows is not None:
        return _kill_counter_rank_table_rows
    rows = []
    path = _kill_counter_rank_table_path()
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, "r", encoding=enc) as f:
                rows = _kill_counter_parse_rank_md_text(f.read())
        except OSError:
            rows = []
        if rows:
            break
    if not rows:
        rows = _kill_counter_rank_builtin_rows()
    _kill_counter_rank_table_rows = rows
    return rows


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
        return "예상 불가 (킬 속도 없음)"
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
    """킬작 졸업까지 — 예상 시간만(우측 정렬용)."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "예상 시간 —"
    cap, _tit = _kill_counter_rank_final_goal()
    if cap is None:
        return "예상 시간 —"
    if int(n1) >= int(cap):
        return "달성"
    eta = _kill_counter_goal_choin_eta_suffix(kills_last_hour, kph_roll24)
    if eta == "—":
        return "예상 시간 —"
    return f"예상 시간 {eta}"


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
        return "예상 불가 (킬 속도 없음)"
    hours = float(rem) / rate
    return _kill_counter_fmt_eta_hours_mins(hours)


def _kill_counter_goal_tier_pct_float():
    """현재 등급 구간 달성도 0~100 (killcount.md). OCR·표 없으면 None."""
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
    """「다음 단계까지」게이지 위 — 현재호칭->다음호칭."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "목표·현재 킬 OCR 대기"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "killcount.md 없음 또는 표 파싱 실패"
    tit = (st.get("title") or "—").strip() or "—"
    if st.get("at_max"):
        return f"{tit}->—"
    nt = (st.get("next_title") or "—").strip() or "—"
    return f"{tit}->{nt}"


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
    """게이지 아래 — 예상 시간만."""
    n1 = _kill_counter_progress_n1_or_none()
    if n1 is None:
        return "예상 시간 —"
    st = _kill_counter_tier_state_for_n1(n1)
    if not st:
        return "예상 시간 —"
    if st.get("at_max"):
        return "예상 시간 —"
    eta = _kill_counter_goal_segment_eta_suffix(kills_last_hour, kph_roll24)
    if eta == "—":
        return "예상 시간 —"
    return f"예상 시간 {eta}"


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


def _kill_counter_stats_ensure_loaded():
    global _kill_counter_stats_loaded, _kill_counter_stats_events
    if _kill_counter_stats_loaded:
        return
    _kill_counter_stats_loaded = True
    path = _kill_counter_stats_file_path()
    _kill_counter_stats_events = []
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
    except Exception as e:
        print(f"[Kill Counter] 통계 JSON 불러오기 실패: {e}", flush=True)
    try:
        _kill_counter_stats_prune_events(time.time())
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
        payload = {"events": list(_kill_counter_stats_events)}
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
                # 재실행·자정 이후 첫 OCR: 이미 파일에 있는 「오늘」 증가분 합만큼 n1에서 빼서
                # 일일 기준을 맞춘다. 그렇지 않으면 baseline=n1 → allow=0 이 되어
                # 저장된 오늘 이벤트가 전부 잘려 나간다.
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
            _kill_counter_stats_rebuild_daily_from_events()
        _kill_counter_stats_schedule_save()
    except Exception:
        pass


def _kill_counter_stats_reset_all():
    """영구 킬 통계(이벤트·일별 합·JSON 파일) 전부 비움."""
    global _kill_counter_stats_save_timer, _kill_counter_stats_events, _kill_counter_stats_daily
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
        _kill_counter_stats_daily = {}
        kill_counter_reconcile_local_date = None
        kill_counter_n1_at_local_day_start = None
        if _kill_counter_stats_save_timer is not None:
            try:
                _kill_counter_stats_save_timer.cancel()
            except Exception:
                pass
            _kill_counter_stats_save_timer = None
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


# 킬 그래프 막대 버킷(분). 1440 = 로컬 캘린더 1일(최근 _KILL_COUNTER_GRAPH_DAY_BUCKET_WINDOW_DAYS일).
_KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED = (1, 5, 15, 30, 60, 1440)
_KILL_COUNTER_GRAPH_DAY_BUCKET_WINDOW_DAYS = 30
# 그래프 우측 시간 버킷 버튼 — 동일 문자 폭(6)으로 크기 통일
_KILL_COUNTER_GRAPH_BUCKET_BTN_CHAR_WIDTH = 6


def _kill_counter_local_bucket_key(ts: float, bucket_minutes: int):
    """로컬 시계 기준 버킷 시작 (연,월,일,시,분). bucket_minutes는 1·5·15·30·60·1440(일)."""
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
    버킷마다 킬 합(구간에 이벤트 없으면 0). 항목: {"kills", "hhmm"(축 라벨), "ymdhm"}.
    1·5·15·30·60분: 오늘 로컬 0시~현재. 1일: 로컬 날짜 기준 최근 N일(오늘 포함).
    """
    bm = int(bucket_minutes)
    if bm not in _KILL_COUNTER_GRAPH_BUCKET_MINUTES_ALLOWED:
        bm = 1
    now = time.time()
    sums = collections.defaultdict(int)
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        evs = list(_kill_counter_stats_events)

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
            return []
        if now + 0.5 < t0:
            return []
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
                },
            )
            d += datetime.timedelta(days=1)
        return out

    t0 = float(_kill_counter_local_midnight_ts())
    if now + 0.5 < t0:
        return []
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
            }
        )
        if k == k_end:
            break
        cur_ts += float(bm) * 60.0
    return out


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
    """랩 블록 제목 왼쪽 — 누적 킬(머리글)."""
    ts = kill_counter_lap_start_ts
    if ts is None:
        return "랩 : —"
    return f"랩 : {_kill_counter_stats_sum_lap_total():,}"


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


def _kill_counter_stats_daily_lines_text(max_days=30):
    """날짜별 표시용 텍스트 (날짜 내림차순, 한 줄: MM-DD + 우측정렬 킬 수 + 킬)."""
    with _kill_counter_stats_lock:
        _kill_counter_stats_ensure_loaded()
        keys = sorted(_kill_counter_stats_daily.keys(), reverse=True)[: max(1, int(max_days))]
    if not keys:
        return "(기록 없음)"
    lines = []
    for k in keys:
        try:
            n = int(_kill_counter_stats_daily.get(k, 0))
        except (TypeError, ValueError):
            n = 0
        try:
            _d = datetime.datetime.strptime(k, "%Y-%m-%d")
            k_disp = _d.strftime("%m-%d")
        except (ValueError, TypeError):
            k_disp = k
        num_str = _kill_counter_fmt_int_display(n)
        # 숫자만 고정폭 필드로 우측 정렬(한글 본문은 맑은 고딕·폴백)
        lines.append(f"{k_disp}  {num_str:>12}  킬")
    return "\n".join(lines)


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
        # 숫자 일부만 바뀌어도 국소 픽셀 차는 크게 나오는 경우가 많음 — 평균만으로는 누락 방지
        if float(np.max(d)) >= 6.0:
            return max(mean_d, _KILL_COUNTER_CHANGE_MEAN_ABS_THRESH + 0.01)
        return mean_d
    except Exception:
        return float("inf")


def _kill_counter_should_skip_ocr_same_screen(cur_bgr) -> bool:
    """직전 루프 캡처와 거의 같으면 True(OCR 생략). 급증 확인·오류 재시도 중에는 False."""
    global kill_counter_last_poll_phase
    global kill_counter_spike_confirm_streak, _kill_counter_last_change_probe_bgr
    if cur_bgr is None or getattr(cur_bgr, "size", 0) == 0:
        return False
    if kill_counter_last_poll_phase is None:
        return False
    if kill_counter_last_poll_phase in ("unstable", "no_pair", "empty", "error"):
        return False
    if kill_counter_spike_confirm_streak > 0:
        return False
    prev = _kill_counter_last_change_probe_bgr
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
    # psm 11 은 sparse text 로 느리고 킬 숫자 한 줄에는 보통 7·6 이 충분
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


def _kill_counter_tesseract_available():
    """pytesseract + Tesseract 실행 파일이 실제로 동작하는지(get_tesseract_version 성공)."""
    try:
        import pytesseract
    except ImportError:
        return False
    _kill_counter_ensure_tesseract_cmd()
    import pytesseract
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _kill_counter_tesseract_available_cached():
    """상태 UI 등에서 반복 호출용 — 수 초 단위로만 실제 검사."""
    global _kill_counter_tesseract_av_cache
    now = time.monotonic()
    if _kill_counter_tesseract_av_cache is not None:
        v, ts = _kill_counter_tesseract_av_cache
        if now - ts < 12.0:
            return v
    v = _kill_counter_tesseract_available()
    _kill_counter_tesseract_av_cache = (v, now)
    return v


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
    global kill_counter_enabled, target_hwnd, select_mode, kill_counter_detect_region
    global kill_counter_last_poll_phase, kill_counter_last_poll_detail, kill_counter_last_progress
    if not kill_counter_enabled:
        return "off", None
    if not target_hwnd:
        return "idle", "게임 창 미연결"
    if select_mode:
        return "idle", "영역 선택 모드"
    if not kill_counter_detect_region:
        return "idle", "감지 영역 미지정"
    if not _kill_counter_tesseract_available_cached():
        return "idle", "Tesseract 미설치"
    ph = kill_counter_last_poll_phase
    if ph is None:
        return "kc_waiting", "첫 OCR 결과 대기"
    d = kill_counter_last_poll_detail
    if ph == "ok":
        lp = (kill_counter_last_progress or "").strip()
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
    global running, target_hwnd, kill_counter_enabled, select_mode
    global kill_counter_detect_region, kill_counter_last_progress, kill_counter_last_poll_ts
    global kill_counter_last_poll_phase, kill_counter_last_poll_detail
    global kill_counter_session_baseline_n1, kill_counter_session_last_n1, kill_counter_session_carried_kills
    global _kill_counter_last_change_probe_bgr
    sct = mss.mss()
    while running:
        snap = get_registry_config_snapshot()
        kc_en = snapshot_bool(snap, "kill_counter_enabled", kill_counter_enabled)
        kc_roi = snap.get("kill_counter_detect_region", kill_counter_detect_region)
        _kc_active = kc_en and target_hwnd and (not select_mode) and kc_roi
        if not _kc_active:
            _kill_counter_last_change_probe_bgr = None
        if _kc_active:
            img = capture_region(target_hwnd, sct, kc_roi)
            _skip_ocr = _kill_counter_should_skip_ocr_same_screen(img)
            _kc_has = img is not None and getattr(img, "size", 0) > 0
            if _kc_has:
                telemetry_kc_frame(
                    skipped=bool(_skip_ocr),
                    ran_ocr=(not _skip_ocr),
                )
            if not _skip_ocr:
                kill_counter_last_poll_ts = time.time()
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
                            kill_counter_last_progress = raw_prog
                            _prev_ph = kill_counter_last_poll_phase
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
                            kill_counter_last_poll_phase = "ok"
                            kill_counter_last_poll_detail = None
                        else:
                            _prev = kill_counter_session_last_n1
                            if _prev is None:
                                _prev = kill_counter_session_baseline_n1
                            _kill_counter_ocr_maybe_log_reject(n1, _prev)
                            if kill_counter_last_progress:
                                n1g, n2g = _kill_counter_slash_pair_parts(kill_counter_last_progress)
                                if n1g and n2g:
                                    val = f"현재 킬 {_kill_counter_fmt_int_str(n1g)}"
                                    err = None
                            else:
                                val = None
                                err = err or "OCR 급증 무시"
                            kill_counter_last_poll_phase = "unstable"
                            kill_counter_last_poll_detail = "급증 의심 — 직전 표시 유지"
                    else:
                        kill_counter_last_progress = raw_prog
                        kill_counter_last_poll_phase = "no_pair"
                        kill_counter_last_poll_detail = "a/b 숫자 쌍 아님"
                else:
                    kill_counter_last_progress = ""
                    if err:
                        kill_counter_last_poll_phase = "error"
                        kill_counter_last_poll_detail = err
                    else:
                        kill_counter_last_poll_phase = "empty"
                        kill_counter_last_poll_detail = None
                if label_rect_cap is not None or num_rect_cap is not None:
                    try:
                        if kc_roi is not None:
                            rp = get_region_pixels(target_hwnd, kc_roi)
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
                _kill_counter_last_change_probe_bgr = np.ascontiguousarray(img)
        if running:
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
                _template_last_hit_store(kind, patch_bgr)
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

    threading.Thread(target=_work, daemon=True).start()


def ride_loop():
    """Ride 루프 (target.png 이미지 감지) - 상시 작동"""
    global image_detected, image_score, running, target_hwnd, ride_detect_region, ride_feature_enabled
    
    sct = mss.mss()
    last_ratio = None
    template_original = None
    last_ride_path = None
    scaled_template = None
    
    while running:
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
            image_score = score  # 점수 저장 (GUI 표시용)
            if detected and patch_r is not None:
                _template_last_hit_store("ride_target", patch_r)
            
            if detected != image_detected:
                image_detected = detected
                set_capslock(detected)  # 감지되면 ON, 미감지면 OFF

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
    hp_refill_last_key_time = -1.0  # Z키 입력 후 쿨다운 (0.5초)
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
                print("[HP Refill] FAIL zkey.png (retrying)", flush=True)
                _hp_shown_fail = True
            time.sleep(1.0)
            continue
        _hp_shown_fail = False
        if not _hp_ok_logged:
            _loop_print("[HP Refill] Template OK (zkey)")
            roi0 = snap.get("hp_refill_detect_region", hp_refill_detect_region)
            _loop_print("[HP Refill] mode region" if roi0 else "[HP Refill] mode fullscreen")
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
            hp_refill_detection_score = score  # GUI 실시간 표시용
            if detected and patch_h is not None:
                _template_last_hit_store("hp_zkey", patch_h)
            
            if detected:
                now = time.time()
                if hp_refill_last_key_time < 0 or (now - hp_refill_last_key_time) >= HP_REFILL_KEY_COOLDOWN:
                    send_key(hp_kc, target_hwnd)
                    hp_refill_last_key_time = now
                    hp_refill_trigger_total += 1
                    _loop_print(f"[HP Refill] hit → {vk_to_display_name(hp_kc)} (#{hp_refill_trigger_total})")

        time.sleep(
            GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.05
        )
    
    sct.close()

def reload_loop():
    """Reload 루프"""
    global reload_active, running, target_hwnd, nobullet_detected, last_nobullet_time, nobullet_detection_score, bullet_detection_score, vault_detection_score, reload_success_count, reload_ammo_count, RELOAD_NOBULLET_IMAGE_PATH, RELOAD_BULLET_IMAGE_PATH, RELOAD_VAULT_IMAGE_PATH
    global reload_nobullet_threshold, reload_bullet_threshold, reload_vault_threshold
    global reload_nobullet_match_region, reload_bullet_match_region, reload_vault_match_region
    
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
            _loop_print("[Reload] Template OK (nobullet, bullet)")
        return nobullet_template is not None and bullet_template is not None
    
    # 초기 로드
    load_templates()
    
    while running:
        _snap_cached = None

        def snap_once():
            nonlocal _snap_cached
            if _snap_cached is None:
                _snap_cached = get_registry_config_snapshot()
            return _snap_cached

        # 주기적으로 경로 확인 및 템플릿 재로드 (5초마다)
        path_check_count += 1
        if path_check_count >= 5:
            path_check_count = 0
            if not load_templates(snap_once()):
                time.sleep(1.0)
                continue
        
        if target_hwnd and reload_active and not select_mode:
            snap = snap_once()
            thr_nb = snapshot_float(snap, "reload_nobullet_threshold", reload_nobullet_threshold)
            thr_bu = snapshot_float(snap, "reload_bullet_threshold", reload_bullet_threshold)
            thr_v = snapshot_float(snap, "reload_vault_threshold", reload_vault_threshold)
            ammo_count_local = snapshot_int(snap, "reload_ammo_count", int(reload_ammo_count))
            roi_nb = snap.get("reload_nobullet_match_region", reload_nobullet_match_region)
            roi_bu = snap.get("reload_bullet_match_region", reload_bullet_match_region)
            roi_v = snap.get("reload_vault_match_region", reload_vault_match_region)
            # 템플릿이 없으면 로드 시도
            if nobullet_template is None or bullet_template is None:
                if not load_templates(snap_once()):
                    time.sleep(1.0)
                    continue
            
            current_ratio = get_scale_ratio(target_hwnd)
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
            
            # 작업이 진행 중이면 nobullet 감지 안 함 (작업 빠르게 진행)
            if nobullet_detected:
                time.sleep(0.1)
                continue
            
            # 10초 쿨다운 체크 (last_nobullet_time이 설정된 경우에만)
            if last_nobullet_time >= 0:
                elapsed = time.time() - last_nobullet_time
                if elapsed < 10.0:
                    remaining = 10.0 - elapsed
                    check_count += 1
                    if check_count >= 10:  # 10초마다 체크
                        check_count = 0
                    time.sleep(1.0)  # 1초마다 체크
                    continue
            
            if scaled_nobullet is None or scaled_bullet is None:
                time.sleep(0.5)
                continue
            
            # 1초마다 nobullet 감지
            screen = capture_region(target_hwnd, sct, roi_nb)
            if screen is None:
                time.sleep(1.0)
                continue
            
            if scaled_nobullet is None or nobullet_template is None:
                time.sleep(0.5)
                continue
            
            _template_probe_mark("reload", "nobullet")
            patch_nb, score = _template_match_patch_if_ok(screen, scaled_nobullet, thr_nb)
            detected = patch_nb is not None
            nobullet_detection_score = score  # GUI 표시용 점수 업데이트
            if detected and patch_nb is not None:
                _template_last_hit_store("reload_nobullet", patch_nb)
            # ① NoBullet 미감지(대기) 구간에서는 ②·③(bullet, vault)을 캡처·매칭하지 않는다.
            # (기존: `reload_idle_update_bullet_vault_scores` 로 약 5초마다 GUI 점수만 갱신 → 주기적 «감지»로 보임)
            bullet_detection_score = 0.0
            vault_detection_score = 0.0

            # 감지 상태 체크
            check_count += 1
            if check_count >= 5:  # 5초마다 체크
                check_count = 0
            
            if detected:
                _loop_print("[Reload] nobullet OK")
                nobullet_detected = True
                last_nobullet_time = time.time()  # 감지 시간 기록
                
                # Flame Trigger 해제 (우클릭 유지 해제 + Merc Fire 루프 해제)
                global flame_trigger_active, flame_trigger_start_time, flame_trigger_feature_enabled
                _reload_had_ft = bool(flame_trigger_active)

                def _reload_ft_disable():
                    global flame_trigger_active
                    flame_trigger_active = False
                    mouse_right_up()

                automation_disable_flame_trigger_if_active(
                    flame_trigger_active=_reload_had_ft,
                    disable=_reload_ft_disable,
                )
                _loop_print("[Reload] FT OFF" if _reload_had_ft else "[Reload] FT idle")
                
                time.sleep(1.0)
                
                # bullet.png 감지
                _loop_print("[Reload] bullet ...")
                screen = capture_region(target_hwnd, sct, roi_bu)
                if screen is None:
                    print("[Reload] bullet FAIL capture")
                    nobullet_detected = False
                    time.sleep(0.5)
                    continue
                
                if scaled_bullet is None:
                    print("[Reload] bullet FAIL Template")
                    nobullet_detected = False
                    time.sleep(0.5)
                    continue
                
                b_score, b_tl, bullet_pos = reload_match_bullet_on_screen(
                    screen,
                    scaled_bullet,
                    thr_bu,
                    on_patch=lambda p: _template_last_hit_store("reload_bullet", p),
                    probe=lambda: _template_probe_mark("reload", "bullet"),
                )
                bullet_detection_score = b_score

                if bullet_pos is None and roi_v is not None:
                    mp = snap.get("RELOAD_VAULT_IMAGE_PATH", RELOAD_VAULT_IMAGE_PATH)
                    vault_template, last_vault_path = load_image_data_if_path_changed(
                        mp,
                        "reload_vault_image_data",
                        last_vault_path,
                        vault_template,
                    )
                    if vault_template is not None:
                        sm = scale_template(vault_template, current_ratio)
                        scr_m = capture_region(target_hwnd, sct, roi_v)
                        if scr_m is not None and sm is not None:
                            vault_detection_score, m_tl = reload_match_vault_on_screen(
                                scr_m,
                                sm,
                                thr_v,
                                on_patch=lambda p: _template_last_hit_store(
                                    "reload_vault", p
                                ),
                                probe=lambda: _template_probe_mark("reload", "vault"),
                            )
                            mh, mw = int(sm.shape[0]), int(sm.shape[1])
                            abs_v = _match_center_to_screen_xy(
                                target_hwnd,
                                roi_v,
                                m_tl,
                                mw,
                                mh,
                            )
                            if (
                                m_tl is not None
                                and vault_detection_score >= thr_v
                                and abs_v is not None
                            ):
                                abs_x, abs_y = abs_v
                                _loop_print(f"[Reload] vault dbc ({abs_x},{abs_y})")
                                reload_move_sleep_double_click(
                                    abs_x,
                                    abs_y,
                                    mouse_move_fn=mouse_move,
                                    mouse_double_click_fn=mouse_double_click,
                                )
                                _loop_print("[Reload] vault dbc OK")
                                time.sleep(0.35)
                                screen = capture_region(target_hwnd, sct, roi_bu)
                                if screen is not None and scaled_bullet is not None:
                                    b_score, b_tl, bullet_pos = (
                                        reload_match_bullet_on_screen(
                                            screen,
                                            scaled_bullet,
                                            thr_bu,
                                            on_patch=lambda p: _template_last_hit_store(
                                                "reload_bullet", p
                                            ),
                                            probe=lambda: _template_probe_mark(
                                                "reload", "bullet"
                                            ),
                                        )
                                    )
                                    bullet_detection_score = b_score
                                else:
                                    bullet_pos = None
                
                if bullet_pos:
                    _loop_print("[Reload] bullet OK")
                    bh, bw = scaled_bullet.shape[:2]
                    abs_pt = _match_center_to_screen_xy(
                        target_hwnd, roi_bu, b_tl, bw, bh,
                    )
                    if abs_pt is not None:
                        abs_x, abs_y = abs_pt
                        _loop_print(f"[Reload] dbc ({abs_x},{abs_y})")
                        reload_move_sleep_double_click(
                            abs_x,
                            abs_y,
                            mouse_move_fn=mouse_move,
                            mouse_double_click_fn=mouse_double_click,
                        )
                        _loop_print("[Reload] dbc OK")
                        
                        # 키보드 입력: 장전 총알 수(숫자 키) + 엔터
                        ammo_n, digits = reload_clamp_ammo_count(ammo_count_local)
                        _loop_print(f"[Reload] ammo {ammo_n}")
                        reload_send_digit_keys_and_return(digits, target_hwnd, send_key)
                        _loop_print(f"[Reload] keys OK ({digits}+↵)")

                        def _reload_ft_enable():
                            global flame_trigger_active, flame_trigger_start_time
                            flame_trigger_active = True
                            flame_trigger_start_time = time.time()

                        if automation_reenable_flame_trigger_after_success(
                            feature_enabled=snapshot_bool(
                                snap,
                                "flame_trigger_feature_enabled",
                                flame_trigger_feature_enabled,
                            ),
                            restore_flag=True,
                            enable=_reload_ft_enable,
                        ):
                            _loop_print("[Reload] FT ON")
                        else:
                            _loop_print("[Reload] FT skip")
                        
                        _loop_print(f"[Reload] OK #{reload_success_count + 1}")
                        reload_success_count += 1  # 성공 횟수 증가
                        nobullet_detected = False  # 작업 완료 후 리셋
                    else:
                        print("[Reload] dbc FAIL rect")
                        nobullet_detected = False
                else:
                    print("[Reload] bullet FAIL")
                    nobullet_detected = False
        
        # 평소에는 1초마다 체크 (작업 중이면 이미 continue로 빠져나감)
        time.sleep(GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 1.0)
    
    sct.close()

# 탄약 Restock 맵 — pipela_core.ammo_restock_catalog (UI 섹션 튜플·폰트 훅은 `main` 전용)
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

# Call Merc 맵 — pipela_core.call_merc_catalog (UI 섹션 튜플·폰트 훅은 `main` 전용)
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
    _loop_print(f"[Ammo Restock] {log_tag} ({abs_x},{abs_y})")
    mouse_move(abs_x, abs_y)
    time.sleep(0.05)
    mouse_click()
    _loop_print(f"[Ammo Restock] {log_tag} OK")


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
    # 더블클릭 — [Reload] dbc 와 동일 토큰
    if double:
        _loop_print(f"{_CALL_MERC_LOG_PREFIX} dbc ({abs_x},{abs_y})")
    else:
        _loop_print(f"{_CALL_MERC_LOG_PREFIX} {log_tag} ({abs_x},{abs_y})")
    mouse_move(abs_x, abs_y)
    time.sleep(0.08)
    if double:
        mouse_double_click()
        _loop_print(f"{_CALL_MERC_LOG_PREFIX} dbc OK")
    else:
        mouse_click()
        _loop_print(f"{_CALL_MERC_LOG_PREFIX} {log_tag} OK")


def ammo_restock_loop():
    """Ammo Restock 루프"""
    global ammo_restock_active, running, target_hwnd, ammo_restock_loop_count
    global ammo_restock_buybutton_threshold, ammo_restock_inven_threshold, ammo_restock_bank_threshold
    global ammo_restock_buybutton_score, ammo_restock_inven_score, ammo_restock_bank_score
    global ammo_buybutton_match_region, ammo_inven_match_region, ammo_bank_match_region
    
    g = globals()
    templates: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    last_ammo_paths: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    sct = mss.mss()
    last_ratio = None
    scaled: dict = {k: None for k in _AMMO_RESTOCK_KINDS}
    _ammo_ok_logged = False
    _ammo_fail_shown = False
    
    while running:
        if target_hwnd and ammo_restock_active and not select_mode:
            snap = get_registry_config_snapshot()
            ok, path_changed = ammo_restock_sync_templates(
                g, templates, last_ammo_paths, path_snap=snap,
            )
            if path_changed:
                last_ratio = None
            if not ok:
                _ammo_ok_logged = False
                if not _ammo_fail_shown:
                    print("[Ammo Restock] templates missing — retrying", flush=True)
                    _ammo_fail_shown = True
                time.sleep(1.0)
                continue
            _ammo_fail_shown = False
            if not _ammo_ok_logged:
                _loop_print("[Ammo Restock] Template OK (buy, inven, bank)")
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
            current_ratio = get_scale_ratio(target_hwnd)
            last_ratio, ratio_changed = refresh_scaled_map_if_ratio_changed(
                templates, scaled, _AMMO_RESTOCK_KINDS, current_ratio, last_ratio,
            )
            if ratio_changed:
                size = get_window_size(target_hwnd)
                if size:
                    _loop_print(f"[Ammo Restock] scale {size[0]}×{size[1]} ({current_ratio:.2f})")
            
            screen = capture_region(target_hwnd, sct, roi_bb)
            if screen is None:
                time.sleep(0.5)
                continue
            
            st_buy = scaled["buybutton"]
            _template_probe_mark("ammo_restock", "buybutton")
            g["ammo_restock_buybutton_score"], buy_tl = _match_template_ccoeff_normed_max(screen, st_buy)
            for _slot in ("inven", "bank"):
                roi_s = _ammo_roi_val(_slot)
                scr_s = capture_region(target_hwnd, sct, roi_s)
                if scr_s is not None:
                    _template_probe_mark("ammo_restock", _slot)
                    sc_s, _ = _match_template_ccoeff_normed_max(scr_s, scaled[_slot])
                    g[_AMMO_SCORE_GLOBAL_BY_KIND[_slot]] = sc_s
                else:
                    g[_AMMO_SCORE_GLOBAL_BY_KIND[_slot]] = 0.0
            
            if buy_tl is not None and g["ammo_restock_buybutton_score"] >= thr_bb:
                buybutton_pos = True
                pb = _template_extract_match_patch(screen, st_buy, buy_tl)
                if pb is not None:
                    _template_last_hit_store("ammo_buybutton", pb)
            else:
                buybutton_pos = None
            
            if buybutton_pos:
                if get_window_rect(target_hwnd):
                    _ammo_restock_click_at_match(
                        target_hwnd, roi_bb, buy_tl, st_buy, _AMMO_LOOP_LOG_TAG["buybutton"],
                    )
                    time.sleep(0.1)
                    send_key(VK_4)
                    time.sleep(0.05)
                    send_key(VK_5)
                    time.sleep(0.05)
                    send_key(VK_RETURN)
                    _loop_print("[Ammo Restock] keys 4,5,↵")
                    
                    time.sleep(0.15)
                    screen = capture_region(target_hwnd, sct, roi_in)
                    if screen is None:
                        g["ammo_restock_inven_score"] = 0.0
                        print("[Ammo Restock] capture FAIL")
                        time.sleep(0.2)
                        continue
                    
                    st_inv = scaled["inven"]
                    _template_probe_mark("ammo_restock", "inven")
                    g["ammo_restock_inven_score"], inv_tl = _match_template_ccoeff_normed_max(screen, st_inv)
                    if inv_tl is not None and g["ammo_restock_inven_score"] >= thr_in:
                        inven_pos = True
                        pi = _template_extract_match_patch(screen, st_inv, inv_tl)
                        if pi is not None:
                            _template_last_hit_store("ammo_inven", pi)
                    else:
                        inven_pos = None
                    
                    if inven_pos:
                        _ammo_restock_click_at_match(
                            target_hwnd, roi_in, inv_tl, st_inv, _AMMO_LOOP_LOG_TAG["inven"],
                        )
                        time.sleep(0.15)
                        screen = capture_region(target_hwnd, sct, roi_bk)
                        if screen is None:
                            g["ammo_restock_bank_score"] = 0.0
                            print("[Ammo Restock] capture FAIL")
                            time.sleep(0.2)
                            continue
                        
                        st_bnk = scaled["bank"]
                        _template_probe_mark("ammo_restock", "bank")
                        g["ammo_restock_bank_score"], bank_tl = _match_template_ccoeff_normed_max(screen, st_bnk)
                        if bank_tl is not None and g["ammo_restock_bank_score"] >= thr_bk:
                            bank_pos = True
                            pbnk = _template_extract_match_patch(screen, st_bnk, bank_tl)
                            if pbnk is not None:
                                _template_last_hit_store("ammo_bank", pbnk)
                        else:
                            bank_pos = None
                        
                        if bank_pos:
                            _ammo_restock_click_at_match(
                                target_hwnd, roi_bk, bank_tl, st_bnk, _AMMO_LOOP_LOG_TAG["bank"],
                            )
                            ammo_restock_loop_count += 1
                            _loop_print(f"[Ammo Restock] cycle OK #{ammo_restock_loop_count}")
                            time.sleep(0.1)
                        else:
                            print("[Ammo Restock] bank FAIL")
                            time.sleep(0.2)
                            continue
                    else:
                        print("[Ammo Restock] inven FAIL")
                        time.sleep(0.2)
                        continue
                else:
                    print("[Ammo Restock] window FAIL")
                    time.sleep(0.2)
                    continue
            else:
                time.sleep(0.2)
                continue
        else:
            time.sleep(
                GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.1
            )
    
    sct.close()
    _loop_print("[Ammo Restock] loop end")


def call_merc_loop():
    """용병 호출 — ①은 트리거만; ②③④는 단계마다 ROI만 확인 후 클릭. ① 직전 FT가 켜져 있었을 때만 끝에 FT 재켜기."""
    global call_merc_active, call_merc_sequence_busy, running, target_hwnd, call_merc_loop_count
    global call_merc_restore_ft_after_cycle
    global call_merc_1_threshold, call_merc_2_threshold, call_merc_3_threshold, call_merc_4_threshold
    global call_merc_1_score, call_merc_2_score, call_merc_3_score, call_merc_4_score
    global flame_trigger_active, flame_trigger_start_time, flame_trigger_feature_enabled

    g = globals()
    templates = {k: None for k in _CALL_MERC_KINDS}
    last_paths = {k: None for k in _CALL_MERC_KINDS}
    sct = mss.mss()
    last_ratio = None
    scaled = {}
    phase = 0  # 0=①만 감시(Reload nobullet 폴링과 동일), 1~3=②~④ 진행
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
            _loop_print(f"{_CALL_MERC_LOG_PREFIX} Template OK (trigger, contract, call, close)")
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
            call_merc_sequence_busy = False
            call_merc_restore_ft_after_cycle = False

        if not load_templates(snap):
            time.sleep(1.0)
            continue

        # phase와 항상 동기화 — load_templates 실패·target/select 분기에서 이전 값이 남아 노란색(작업중)이 고착되는 것 방지
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
                    _loop_print(f"{_CALL_MERC_LOG_PREFIX} scale {size[0]}×{size[1]} ({current_ratio:.2f})")

            if phase == 0:
                if time.monotonic() < _arm_until:
                    time.sleep(0.06)
                    continue
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
                    _loop_print(f"{_CALL_MERC_LOG_PREFIX} trigger OK")
                    # FT 끄기 전에 발동 여부 저장 — 끝날 때 원래 켜져 있었을 때만 다시 켬
                    had_flame_trigger = bool(flame_trigger_active)
                    call_merc_restore_ft_after_cycle = had_flame_trigger

                    def _merc_ft_disable():
                        global flame_trigger_active
                        flame_trigger_active = False
                        mouse_right_up()

                    automation_disable_flame_trigger_if_active(
                        flame_trigger_active=had_flame_trigger,
                        disable=_merc_ft_disable,
                    )
                    _loop_print(
                        f"{_CALL_MERC_LOG_PREFIX} FT OFF"
                        if had_flame_trigger
                        else f"{_CALL_MERC_LOG_PREFIX} FT idle"
                    )
                time.sleep(0.12)
                continue

            if not get_window_rect(target_hwnd):
                time.sleep(0.2)
                continue

            if phase == 1:
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
                    _loop_print(f"{_CALL_MERC_LOG_PREFIX} cycle OK #{call_merc_loop_count}")

                    def _merc_ft_enable():
                        global flame_trigger_active, flame_trigger_start_time
                        flame_trigger_active = True
                        flame_trigger_start_time = time.time()

                    if automation_reenable_flame_trigger_after_success(
                        feature_enabled=ft_en,
                        restore_flag=call_merc_restore_ft_after_cycle,
                        enable=_merc_ft_enable,
                    ):
                        _loop_print(f"{_CALL_MERC_LOG_PREFIX} FT ON")
                    else:
                        _loop_print(f"{_CALL_MERC_LOG_PREFIX} FT skip")
                    call_merc_restore_ft_after_cycle = False
                    _arm_until = time.monotonic() + CALL_MERC_ARM_COOLDOWN_SEC
                    _prev = phase
                    phase = 0
                    _call_merc_ui_sync_phase(_prev, phase)
                    call_merc_sequence_busy = False  # 이번 틱 시작 시 phase==3으로 True였을 수 있음 — 즉시 해제
                    time.sleep(0.15)
                else:
                    time.sleep(0.08)
                continue

        else:
            time.sleep(
                GAME_CLIENT_POWER_SAVE_LOOP_SLEEP_SEC if _game_client_power_save_active else 0.1
            )

    sct.close()
    _loop_print(f"{_CALL_MERC_LOG_PREFIX} loop end")


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

    _pipela_mod = sys.modules[__name__]

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
                if mono_now > _start_game_accept_arm_until_mono:
                    _start_game_accept_armed = False
                    _start_game_accept_arm_until_mono = 0.0
                    start_game_accept_score = 0.0
                    _loop_print("[START GAME] Accept 무장 시간 초과 — 대기")
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
                mx, my = int(loc_ac[0]), int(loc_ac[1])
                th, tw = scaled_ac.shape[0], scaled_ac.shape[1]
                rect_ac = get_window_rect(gh_ac)
                if not rect_ac:
                    time.sleep(0.2)
                    continue
                wx, wy = int(rect_ac[0]), int(rect_ac[1])
                rp_ac = get_region_pixels(gh_ac, cap_ac) if cap_ac else None
                ox, oy = (rp_ac[0], rp_ac[1]) if rp_ac else (0, 0)
                cx = int(wx + ox + mx + tw // 2)
                cy = int(wy + oy + my + th // 2)
                pb_ac = _template_extract_match_patch(screen_ac, scaled_ac, loc_ac)
                if pb_ac is not None:
                    _template_last_hit_store("start_game_accept", pb_ac)
                _loop_print(f"[START GAME] Accept match {max_ac:.2f} → click ({cx},{cy})")
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
                    _loop_print("[START GAME] Intro Skip 무장 시간 초과 — 대기")
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
                mx, my = int(loc_is[0]), int(loc_is[1])
                th, tw = scaled_is.shape[0], scaled_is.shape[1]
                rect_g = get_window_rect(gh)
                if not rect_g:
                    time.sleep(0.2)
                    continue
                wx, wy = int(rect_g[0]), int(rect_g[1])
                rp_g = get_region_pixels(gh, cap_is) if cap_is else None
                ox, oy = (rp_g[0], rp_g[1]) if rp_g else (0, 0)
                cx = int(wx + ox + mx + tw // 2)
                cy = int(wy + oy + my + th // 2)
                pb_is = _template_extract_match_patch(screen_g, scaled_is, loc_is)
                if pb_is is not None:
                    _template_last_hit_store("start_game_intro_skip", pb_is)
                _loop_print(f"[START GAME] Intro Skip match {max_is:.2f} → click ({cx},{cy})")
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
                _loop_print("[START GAME] Intro Skip OK → Accept 무장")
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
            ratio = START_GAME_LAUNCHER_TEMPLATE_SCALE_RATIO
            scaled = scale_template(tpl, ratio)
            if scaled is None:
                start_game_launcher_score = 0.0
                time.sleep(0.4)
                continue
            cap_reg = snap.get("start_game_launcher_match_region", start_game_launcher_match_region)
            screen = capture_region(uh, sct, cap_reg)
            _template_probe_mark("start_game", "launcher")
            if screen is None:
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            if screen.shape[0] < scaled.shape[0] or screen.shape[1] < scaled.shape[1]:
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            max_val, max_loc = _match_template_ccoeff_normed_max(screen, scaled)
            if max_loc is None:
                start_game_launcher_score = 0.0
                time.sleep(0.12)
                continue
            start_game_launcher_score = float(max_val)
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

            rect = get_window_rect(uh)
            if not rect:
                time.sleep(0.2)
                continue
            wx, wy = int(rect[0]), int(rect[1])
            rp = get_region_pixels(uh, cap_reg) if cap_reg else None
            ox, oy = (rp[0], rp[1]) if rp else (0, 0)
            mx, my = int(max_loc[0]), int(max_loc[1])
            th, tw = scaled.shape[0], scaled.shape[1]
            cx = int(wx + ox + mx + tw // 2)
            cy = int(wy + oy + my + th // 2)
            pb = _template_extract_match_patch(screen, scaled, max_loc)
            if pb is not None:
                _template_last_hit_store("start_game_launcher", pb)
            _loop_print(
                f"[START GAME] 런처 1회 클릭 match {max_val:.2f} → ({cx},{cy})",
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
                _loop_print("[START GAME] 런처 창 소멸(1클릭) — Intro Skip 무장")
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t0 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            if w0 == "aborted":
                time.sleep(0.12)
                continue

            # 5초 안에 런처가 남아 있으면 1회만 추가 클릭
            uh3 = refresh_smart_updater_hwnd_if_needed()
            if not uh3:
                _arm_t0 = time.monotonic()
                _loop_print(
                    "[START GAME] 런처 창 소멸(1차 5s 대기 직전/직후) — Intro Skip 무장",
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
            ratio_b = START_GAME_LAUNCHER_TEMPLATE_SCALE_RATIO
            scaled_b = scale_template(tpl, ratio_b)
            if scaled_b is None:
                time.sleep(0.4)
                continue
            screen_b = capture_region(uh3, sct, cap2)
            _template_probe_mark("start_game", "launcher")
            if screen_b is None:
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            if (
                screen_b.shape[0] < scaled_b.shape[0]
                or screen_b.shape[1] < scaled_b.shape[1]
            ):
                start_game_launcher_score = 0.0
                time.sleep(0.2)
                continue
            max_b, loc_b = _match_template_ccoeff_normed_max(screen_b, scaled_b)
            if loc_b is None:
                start_game_launcher_score = 0.0
                time.sleep(0.12)
                continue
            start_game_launcher_score = float(max_b)
            if max_b < thr2:
                _arm_t0 = time.monotonic()
                _loop_print("[START GAME] 런처 템플릿 미매칭(2차) — Intro Skip 무장")
                _start_game_intro_skip_armed = True
                _start_game_intro_skip_arm_until_mono = (
                    _arm_t0 + float(START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)
                )
                time.sleep(0.35)
                continue
            rect3 = get_window_rect(uh3)
            if not rect3:
                time.sleep(0.2)
                continue
            wx3, wy3 = int(rect3[0]), int(rect3[1])
            rp3 = get_region_pixels(uh3, cap2) if cap2 else None
            ox3, oy3 = (rp3[0], rp3[1]) if rp3 else (0, 0)
            mx2, my2 = int(loc_b[0]), int(loc_b[1])
            th2, tw2 = scaled_b.shape[0], scaled_b.shape[1]
            cx2 = int(wx3 + ox3 + mx2 + tw2 // 2)
            cy2 = int(wy3 + oy3 + my2 + th2 // 2)
            pb2 = _template_extract_match_patch(screen_b, scaled_b, loc_b)
            if pb2 is not None:
                _template_last_hit_store("start_game_launcher", pb2)
            _loop_print(
                f"[START GAME] 런처 2회차(재시도 1회) match {max_b:.2f} → ({cx2},{cy2})",
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
                _loop_print("[START GAME] 런처 창 소멸(2클릭) — Intro Skip 무장")
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
                f"[START GAME] 2클릭 후에도 런처 유지 — {launcher_click_cooldown_sec:.1f}s 쿨다운",
            )
            time.sleep(0.35)
    finally:
        try:
            sct.close()
        except Exception:
            pass


def left_click_loop():
    """왼쪽 클릭 반복 루프"""
    global left_click_active, running, left_click_interval_ms
    global left_click_random_enabled, left_click_random_min_ms, left_click_random_max_ms
    while running:
        snap = get_registry_config_snapshot()
        lc_rand = snapshot_bool(snap, "left_click_random_enabled", left_click_random_enabled)
        lc_iv = snapshot_float(snap, "left_click_interval_ms", float(left_click_interval_ms))
        lc_rmin = snapshot_float(snap, "left_click_random_min_ms", float(left_click_random_min_ms))
        lc_rmax = snapshot_float(snap, "left_click_random_max_ms", float(left_click_random_max_ms))
        if left_click_active and is_mouse_in_window() and not select_mode:
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

def right_hold_loop():
    """오른쪽 마우스 유지 루프"""
    global right_hold_active, right_hold_feature_enabled, running
    while running:
        snap = get_registry_config_snapshot()
        rh_en = snapshot_bool(snap, "right_hold_feature_enabled", right_hold_feature_enabled)
        if right_hold_active and rh_en and is_mouse_in_window() and not select_mode:
            mouse_right_down()
            time.sleep(0.05)
        else:
            time.sleep(GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC if _game_client_power_save_active else 0.01)

def flame_trigger_loop():
    """화면 중앙 우클릭 홀드 + 마우스 고정 + Merc Fire(설정 키를 간격으로 연속 입력)"""
    global flame_trigger_active, flame_trigger_feature_enabled, running, target_hwnd, flame_trigger_start_time
    global merc_fire_enabled, merc_fire_key_code, flame_trigger_press_text_until, flame_trigger_press_key_name
    global merc_fire_random_min_ms, merc_fire_random_max_ms, flame_trigger_press_count
    global flame_trigger_last_press_interval_sec, flame_trigger_prev_press_timestamp
    flame_trigger_executed = False  # 실행 여부 플래그
    last_key_time = 0  # 마지막 키 입력 시간
    next_key_interval = 0  # 다음 키 입력까지의 간격 (랜덤 사용 시)
    key_loop_active = True  # Merc Fire(키 연속 입력) 루프 활성화
    
    while running:
        snap = get_registry_config_snapshot()
        ft_feat = snapshot_bool(snap, "flame_trigger_feature_enabled", flame_trigger_feature_enabled)
        mf_en = snapshot_bool(snap, "merc_fire_enabled", merc_fire_enabled)
        mf_kc = snapshot_int(snap, "merc_fire_key_code", int(merc_fire_key_code))
        mf_lo = snapshot_float(snap, "merc_fire_random_min_ms", float(merc_fire_random_min_ms))
        mf_hi = snapshot_float(snap, "merc_fire_random_max_ms", float(merc_fire_random_max_ms))
        if not ft_feat and flame_trigger_active:
            flame_trigger_active = False
        # flame_trigger_active가 False가 되면 즉시 해제 처리
        if not flame_trigger_active:
            if flame_trigger_executed:
                # 즉시 우클릭 해제 및 키 루프 해제
                mouse_right_up()
                flame_trigger_executed = False
                key_loop_active = False
                next_key_interval = 0
                flame_trigger_prev_press_timestamp = None
                flame_trigger_last_press_interval_sec = 0.0
            time.sleep(
                GAME_CLIENT_POWER_SAVE_INPUT_POLL_SEC if _game_client_power_save_active else 0.01
            )
            continue
        
        if target_hwnd and not select_mode:
            if not flame_trigger_executed:
                # 한 번만 실행: 중앙으로 이동 후 우클릭 홀드
                rect = get_window_rect(target_hwnd)
                # 최소화 등으로 클라이언트가 비정상이면 1회 실행 자체를 건너뜀(스냅 방지)
                if (
                    rect
                    and rect[2] > rect[0]
                    and rect[3] > rect[1]
                    and not is_window_minimized(target_hwnd)
                ):
                    wx, wy, wx2, wy2 = rect
                    center_x = wx + (wx2 - wx) // 2
                    center_y = wy + (wy2 - wy) // 2
                    mouse_move(center_x, center_y)
                    time.sleep(0.1)
                    mouse_right_down()
                    flame_trigger_executed = True
                    flame_trigger_start_time = time.time()  # 전역 변수에 저장
                    flame_trigger_press_count = 0  # 세션 시작 시 발동 횟수 초기화
                    flame_trigger_prev_press_timestamp = None
                    flame_trigger_last_press_interval_sec = 0.0
                    # 설정에 따라 키 루프 활성화 여부 결정
                    key_loop_active = mf_en
                    _ft_merc_t0 = time.time()
                    last_key_time = _ft_merc_t0
                    # 랜덤 간격(ms→초) — 첫 키는 아래에서 즉시 1회 보낸 뒤 이 간격으로 이어짐
                    next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0
                    if key_loop_active and mf_en:
                        send_key(mf_kc, target_hwnd)
                        flame_trigger_press_count = 1
                        flame_trigger_last_press_interval_sec = (
                            _ft_merc_t0 - flame_trigger_start_time
                        )
                        flame_trigger_prev_press_timestamp = _ft_merc_t0
                        last_key_time = _ft_merc_t0
                        flame_trigger_press_text_until = _ft_merc_t0 + 0.5
                        flame_trigger_press_key_name = vk_to_display_name(mf_kc)
                        next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0
                    try:
                        _flame_start_banner_queue.put_nowait(1)
                    except queue.Full:
                        pass
            
            # 실행 후 처리: 가동 내내 창 중앙에 마우스 스냅 (휠 클릭으로 OFF 할 때까지)
            if flame_trigger_executed:
                current_time = time.time()

                rect = get_window_rect(target_hwnd)
                # 최소화 등으로 클라이언트 사각형이 비정상이면 스냅·키 루프 모두 우회 — 비정상 좌표(-32000) 로의
                # SetCursorPos 가 0,0 부근으로 클램프되어 커서 점멸로 보일 수 있음
                rect_ok = bool(
                    rect
                    and rect[2] > rect[0]
                    and rect[3] > rect[1]
                    and not is_window_minimized(target_hwnd)
                )
                if rect_ok:
                    wx, wy, wx2, wy2 = rect
                    center_x = wx + (wx2 - wx) // 2
                    center_y = wy + (wy2 - wy) // 2
                    
                    cur = try_screen_cursor_pos_for_macros()
                    if cur is None:
                        # 실패·(0,0) 유령 — 중앙으로 간주해 dist>5 스냅만 억제 (키 루프는 계속)
                        current_x, current_y = center_x, center_y
                    else:
                        current_x, current_y = cur
                    
                    # 설정된 간격마다 설정된 키 누르기 (루프가 활성화되고 설정이 켜져있는 경우만)
                    if key_loop_active and mf_en:
                        time_since_last_key = current_time - last_key_time
                        if time_since_last_key >= next_key_interval:
                            send_key(mf_kc, target_hwnd)
                            flame_trigger_press_count += 1
                            if flame_trigger_prev_press_timestamp is not None:
                                flame_trigger_last_press_interval_sec = (
                                    current_time - flame_trigger_prev_press_timestamp
                                )
                            else:
                                flame_trigger_last_press_interval_sec = (
                                    current_time - flame_trigger_start_time
                                )
                            flame_trigger_prev_press_timestamp = current_time
                            last_key_time = current_time
                            # 마우스 아래 "Flame Trigger Press N" 표시 (0.5초)
                            flame_trigger_press_text_until = current_time + 0.5
                            flame_trigger_press_key_name = vk_to_display_name(mf_kc)
                            next_key_interval = random.uniform(mf_lo, mf_hi) / 1000.0
                    
                    dist = ((current_x - center_x) ** 2 + (current_y - center_y) ** 2) ** 0.5
                    if dist > 5:
                        mouse_move(center_x, center_y)
                        mouse_right_down()
                    
                    time.sleep(0.05)
                else:
                    # 창이 없으면 OFF
                    flame_trigger_active = False
                    flame_trigger_executed = False
                    mouse_right_up()
                    key_loop_active = False
                    flame_trigger_prev_press_timestamp = None
                    flame_trigger_last_press_interval_sec = 0.0
                    _loop_print("[Flame Trigger] OFF (no window)")
        else:
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
    if not running or not left_click_active or not left_click_feature_enabled:
        return
    if select_mode or not is_mouse_in_window():
        return
    if _physical_left_button_down():
        user_left_pending = True


def on_click(x, y, button, pressed):
    """마우스 클릭 감지"""
    global left_click_active, right_hold_active, right_hold_feature_enabled, flame_trigger_active, flame_trigger_feature_enabled, ignore_left, ignore_right, left_pressed, left_click_id, user_left_pending
    global _left_off_arm_gen
    
    if select_mode or not is_mouse_in_window():
        return
    
    # 왼쪽 클릭
    if button == mouse.Button.left:
        if pressed:
            if left_click_active and left_click_feature_enabled:
                # ON 상태에서 OFF: 보통 press에서 user_left_pending. 자동 클릭과 겹치면 ignore_left로 press가 버려짐 → 지연 보정.
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
                return  # 자동 클릭(발동 ON 경로)은 무시
            if left_click_feature_enabled:
                # 기능 ON이고 OFF 상태면 홀드 체크
                left_pressed = True
                left_click_id += 1
                current_id = left_click_id
                threading.Thread(target=check_left_hold, args=(current_id,), daemon=True).start()
        else:
            left_pressed = False
            if user_left_pending:
                user_left_pending = False
                left_click_active = False
                _loop_print("[LeftClick] OFF")
    
    # 오른쪽 클릭: 누르면 바로 토글 (기능 ON일 때만)
    elif button == mouse.Button.right and not ignore_right and pressed:
        if right_hold_feature_enabled:
            right_hold_active = not right_hold_active
            _loop_print(f"[RightHold] {'ON' if right_hold_active else 'OFF'}")
    
    # 마우스 휠 클릭: Flame Trigger 발동 ON/OFF (기능이 켜져 있을 때만)
    elif button == mouse.Button.middle and pressed:
        if flame_trigger_feature_enabled:
            flame_trigger_active = not flame_trigger_active
            _loop_print(f"[Flame Trigger] {'ON' if flame_trigger_active else 'OFF'}")

def check_left_hold(click_id):
    """왼쪽 버튼 홀드 체크 (ON용) - left_click_feature_enabled일 때만 발동"""
    global left_click_active, left_pressed, left_click_id, left_click_feature_enabled
    time.sleep(left_click_hold_sec)
    # 같은 클릭이고 아직 누르고 있는지, 기능이 켜져 있는지 확인
    if left_click_feature_enabled and left_pressed and click_id == left_click_id and not left_click_active:
        left_click_active = True
        left_pressed = False
        _loop_print("[LeftClick] ON")

def on_key(key):
    """키보드 감지"""
    global running, select_mode, ammo_restock_active, reload_active
    if key == keyboard.Key.f8:
        _loop_print(f"[{PIPELA_APP_DISPLAY_NAME}] 종료")
        set_capslock(False)
        running = False
        return False
    elif key == keyboard.Key.f5:
        reload_active = not reload_active
        _loop_print(f"[Reload] {'ON' if reload_active else 'OFF'}")
    else:
        vk = _pynput_key_to_vk(key)
        if vk is not None and vk == (ammo_restock_toggle_key_code & 0xFF):
            ammo_restock_active = not ammo_restock_active
            _loop_print(f"[Ammo Restock] {'ON' if ammo_restock_active else 'OFF'}")

# 감지 영역 미리보기 — Qt `pipela_qt.region_preview_overlay` 전용
# _REGION_PREVIEW_PERSIST_VALID — pipela_core.region_dispatch
# 마지막으로 켜 둔 미리보기 종류(None=끔) — 재실행 시 복원
region_preview_overlay_saved_kind = None
# 영역 선택·템플릿 캡처 — `pipela_qt.*_drag_overlay` + `pipela_mod`
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
    select_mode = False


def _force_close_region_select_overlay_only():
    """감지 영역 선택 오버레이만 닫음 (select_mode·active_type 정리)."""
    global _region_select_active_type, select_mode
    try:
        from pipela_qt.region_drag_overlay import close_qt_region_select_overlay

        close_qt_region_select_overlay()
    except Exception:
        pass
    _region_select_active_type = None
    select_mode = False


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

        qt_region_preview_toggle(sys.modules[__name__], region_type, label)
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

        qt_region_select_start(sys.modules[__name__], region_type, label)
    except Exception as e:
        print(f"[{label}] 영역 선택 실패: {e}", flush=True)


# --- 화면 템플릿 매칭(cv2.matchTemplate / find_image*) 전수 ---
#  번들 기본 PNG 디렉터리: SCRIPT_DIR/templates/ (UI 아이콘은 icon/ 유지)
#  루프              글로벌 경로 / 레지스트리 *_image_data        설정 UI · 「캡처」
#  ride_loop         RIDE_TARGET / ride_target_image_data        RideSettingsWindow
#  reload_loop       RELOAD_NOBULLET / reload_nobullet_image_data  ThresholdSettingsWindow (NoBullet)
#  reload_loop       RELOAD_BULLET / reload_bullet_image_data       ThresholdSettingsWindow (Bullet)
#  reload_loop       RELOAD_VAULT / reload_vault_image_data  ThresholdSettingsWindow (Vault)
#  hp_refill_loop    HP_REFILL_ZKEY / hp_refill_zkey_image_data    ThresholdSettingsWindow (HP Bar)
#  ammo_restock_loop 3종 buybutton·inven·bank                    AmmoRestockSettingsWindow
#  call_merc_loop   ①=nobullet과 동일 트리거, ②③④=후속 클릭              CallMercSettingsWindow
#  kill_counter_loop OCR(pytesseract) — 사용자 PNG 템플릿 없음.
#  위 슬롯은 pipela_core.template_capture_catalog · start_template_image_capture 와 1:1 대응.
#  매칭 ROI: ride/hp는 타겟 행 「영역 선택」과 동일 전역, reload/ammo→*_match_region(미지정=전체 창).


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

        qt_template_capture_start(sys.modules[__name__], kind, label, on_applied)
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


def _pipela_resolve_reinstall_exe_url():
    """버전 비교 없이 EXE만 다시 받을 URL. PIPELA_REINSTALL_EXE_URL 우선, 없으면 manifest download_url."""
    forced = (PIPELA_REINSTALL_EXE_URL or "").strip()
    if forced:
        return forced, None
    data, err = _pipela_fetch_update_manifest()
    if err:
        return None, f"manifest: {err}"
    dl = _pipela_update_manifest_download_url(data)
    if not dl:
        return (
            None,
            "download_url 없음. 환경변수 PIPELA_REINSTALL_EXE_URL 에 EXE 주소를 넣거나 manifest JSON을 채우세요.",
        )
    return dl, None


def _pipela_is_frozen_exe():
    return bool(getattr(sys, "frozen", False))


def _pipela_current_exe_path():
    if not _pipela_is_frozen_exe():
        return None
    return os.path.normpath(os.path.abspath(sys.executable))


def _pipela_download_update_file(url: str, dest_path: str):
    """새 EXE 다운로드. 성공 시 None, 실패 시 오류 문자열."""
    part = dest_path + ".part"
    try:
        if os.path.isfile(part):
            os.unlink(part)
    except OSError:
        pass
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"{PIPELA_APP_DISPLAY_NAME}/{PIPELA_APP_VERSION} (update-download)",
            },
            method="GET",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=600, context=ctx) as resp:
            chunk = 256 * 1024
            with open(part, "wb") as out:
                while True:
                    b = resp.read(chunk)
                    if not b:
                        break
                    out.write(b)
        os.replace(part, dest_path)
        return None
    except Exception as e:
        try:
            if os.path.isfile(part):
                os.unlink(part)
        except OSError:
            pass
        try:
            if os.path.isfile(dest_path):
                os.unlink(dest_path)
        except OSError:
            pass
        return str(e)


def _pipela_launch_exe_replace_and_restart(staging_exe: str, target_exe: str, wait_pid: int):
    """Windows: 배치로 wait_pid 종료 대기 → staging 을 target_exe 로 교체 → 재실행. 호출 직후 앱을 종료할 것."""
    staging_exe = os.path.normpath(os.path.abspath(staging_exe))
    target_exe = os.path.normpath(os.path.abspath(target_exe))
    bat_fd, bat_path = tempfile.mkstemp(prefix="pipela_update_", suffix=".bat")
    try:
        os.close(bat_fd)
    except OSError:
        pass
    # cmd.exe / 배치는 경로에 따옴표 유지
    lines = "\r\n".join(
        [
            "@echo off",
            "setlocal",
            f'set "NEW={staging_exe}"',
            f'set "EXE={target_exe}"',
            f'set "WPID={wait_pid}"',
            ":waitproc",
            f'tasklist /FI "PID eq %WPID%" 2^>nul ^| find "%WPID%" ^>nul',
            "if %errorlevel%==0 (",
            "timeout /t 1 /nobreak >nul",
            "goto waitproc",
            ")",
            "timeout /t 1 /nobreak >nul",
            ":trymove",
            'move /Y "%NEW%" "%EXE%"',
            "if errorlevel 1 (",
            "timeout /t 1 /nobreak >nul",
            "goto trymove",
            ")",
            'start "" "%EXE%"',
            'del "%~f0" & exit /b 0',
            "",
        ]
    )
    try:
        with open(bat_path, "w", newline="\r\n", encoding="cp949", errors="replace") as bf:
            bf.write(lines)
    except Exception:
        try:
            with open(bat_path, "w", newline="\r\n", encoding="utf-8", errors="replace") as bf:
                bf.write(lines)
        except Exception as ex:
            try:
                os.unlink(bat_path)
            except OSError:
                pass
            raise ex
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags == 0 and sys.platform == "win32":
        creationflags = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        close_fds=True,
        creationflags=creationflags,
        cwd=os.path.dirname(bat_path) or None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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
        # 레지에서 Intro Skip(런처)이 꺼져 있어도, 런처만 있는 기동이면 START 템플릿① 감지·클릭은 즉시 켜둔다.
        try:
            if not is_window_minimized(int(launcher_hwnd)):
                start_game_launcher_active = True
                refresh_registry_config_snapshot(globals())
        except Exception:
            pass
    start_tray_only = (game_hwnd is None and launcher_hwnd is None) and PIPELA_TRAY_AVAILABLE
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
    running = False
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
        if m is not None and getattr(m, "pipela_overlay_tick_ms", None) is not None:
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
    running = True
    _ensure_start_game_launcher_loop_thread()
    try:
        _pipela_qt_shell.run_qt_application(pipela_mod=pipela_mod, start_tray_only=start_tray_only)
    finally:
        shutdown_after_ui_mainloop()


if __name__ == "__main__":
    while "--qt" in sys.argv:
        sys.argv.remove("--qt")
    while "--tk" in sys.argv:
        sys.argv.remove("--tk")
    main_qt()
