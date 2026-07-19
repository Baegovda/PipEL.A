"""Win32: 이터널시티·스마트업데이터 런처 HWND 탐색, 클라이언트/외곽 화면 rect."""

from __future__ import annotations

import os
import sys
import time

import win32gui

# GetWindowText는 일부 D3D/전체화면 클라이언트에서 상대적으로 비쌀 수 있어,
# `IsWindow`로 살아 있는 동안에는 재검증 간격을 둔다(오버레이 틱의 ov_hwnd).
_ET_GWT_REVALIDATE_MIN = float(
    os.environ.get("PIPELA_HWND_GWT_REVALIDATE_MIN_SEC", "0.55")
)
_SU_GWT_REVALIDATE_MIN = float(
    os.environ.get("PIPELA_HWND_SMART_GWT_REVALIDATE_MIN_SEC", "1.35")
)
# 게임/런처 미탐지 상태에서 EnumWindows 연타 방지(수백만 회 GetWindowText 방지)
_ET_ENUM_MIN_INTERVAL = float(os.environ.get("PIPELA_HWND_ENUM_MIN_SEC", "0.72"))
_SU_ENUM_MIN_INTERVAL = float(os.environ.get("PIPELA_HWND_SMART_ENUM_MIN_SEC", "0.72"))
_last_et_gwt_mono: float = 0.0
_last_et_gwt_hwnd = None
_last_et_enum_mono: float = 0.0
_last_su_gwt_mono: float = 0.0
_last_su_gwt_hwnd = None
_last_su_enum_mono: float = 0.0

ETERNALCITY_TITLE_KO = "이터널시티"
ETERNALCITY_TITLE_EN = "EternalCity"

# START GAME 런처 — main 의 START_GAME_SMART_UPDATER_TITLE_SUBSTR 과 동일 값
SMART_UPDATER_TITLE_KO_SUBSTR = "스마트업데이터"


def eternalcity_title_matches(title: str) -> bool:
    if not title:
        return False
    return ETERNALCITY_TITLE_KO in title or ETERNALCITY_TITLE_EN in title


def find_eternalcity_window():
    """이터널시티 창 찾기. 보이는 창 우선; 없으면 타이틀만 맞는 창 포함(로딩 직후 등)."""

    def callback_visible(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            try:
                t = win32gui.GetWindowText(hwnd)
            except Exception:
                t = ""
            if eternalcity_title_matches(t):
                windows.append(hwnd)
        return True

    def callback_any_title(hwnd, windows):
        try:
            t = win32gui.GetWindowText(hwnd)
        except Exception:
            t = ""
        if eternalcity_title_matches(t):
            windows.append(hwnd)
        return True

    windows: list = []
    win32gui.EnumWindows(callback_visible, windows)
    if windows:
        return windows[0]
    windows.clear()
    win32gui.EnumWindows(callback_any_title, windows)
    return windows[0] if windows else None


def smart_updater_title_matches(title: str, korean_substr: str = SMART_UPDATER_TITLE_KO_SUBSTR) -> bool:
    """스마트업데이터 런처 HWND 식별 — 한글 부분 문자열 + 영문/공백 변형."""
    if not title:
        return False
    if korean_substr and korean_substr in title:
        return True
    t = title.lower()
    if "smart updater" in t:
        return True
    # Enum 콜백 핫패스 — 공백 없는 일반 표기는 조인 없이 먼저 처리
    if "smartupdater" in t or "smartupdate" in t:
        return True
    if "smart" not in t:
        return False
    compact = "".join(ch for ch in t if ch.isalnum())
    return "smartupdater" in compact or "smartupdate" in compact


def find_smart_updater_window(korean_substr: str = SMART_UPDATER_TITLE_KO_SUBSTR):
    """스마트업데이터 / Smart Updater 등 — START GAME 런처 전용 HWND."""

    def _title_ok(t):
        return smart_updater_title_matches(t, korean_substr)

    def callback_visible(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            try:
                t = win32gui.GetWindowText(hwnd)
            except Exception:
                t = ""
            if _title_ok(t):
                windows.append(hwnd)
        return True

    def callback_any_title(hwnd, windows):
        try:
            t = win32gui.GetWindowText(hwnd)
        except Exception:
            t = ""
        if _title_ok(t):
            windows.append(hwnd)
        return True

    windows: list = []
    win32gui.EnumWindows(callback_visible, windows)
    if windows:
        return windows[0]
    windows.clear()
    win32gui.EnumWindows(callback_any_title, windows)
    return windows[0] if windows else None


def force_eternalcity_hwnd_enum_next_tick() -> None:
    """`target_hwnd` 가 비어 있을 때 ``EnumWindows`` 스로틀(기본 ~0.72s) 때문에 재탐색이 밀리는 구간 완화.

    런처→클라 전환 직후 첫 ``refresh_target_hwnd_if_needed`` 에서 곧바로 이터널시티 HWND 를 다시 찾게 한다.
    """
    global _last_et_enum_mono
    _last_et_enum_mono = 0.0


def refresh_eternalcity_hwnd_cached(prev_hwnd):
    """캐시된 HWND가 여전히 이터널시티 창이면 재사용, 아니면 Enum.

    오버레이/위치 추적 등에서 매 프레임 호출될 수 있어 Enum 생략으로 부하를 줄인다.
    타이틀은 `GetWindowText`로만 검증; 같은 HWND·살아 있으면 재검증을 간격(기본 0.2s)로 생략한다.
    """
    global _last_et_gwt_mono, _last_et_gwt_hwnd, _last_et_enum_mono
    now = time.monotonic()
    try:
        if prev_hwnd and win32gui.IsWindow(prev_hwnd):
            if (
                _ET_GWT_REVALIDATE_MIN > 0.0
                and _last_et_gwt_hwnd == prev_hwnd
                and (now - _last_et_gwt_mono) < _ET_GWT_REVALIDATE_MIN
            ):
                return prev_hwnd
            try:
                title = win32gui.GetWindowText(prev_hwnd)
            except Exception:
                title = ""
            _last_et_gwt_mono = now
            _last_et_gwt_hwnd = prev_hwnd
            if eternalcity_title_matches(title):
                return prev_hwnd
    except Exception:
        pass
    if prev_hwnd is None and (now - _last_et_enum_mono) < _ET_ENUM_MIN_INTERVAL:
        return None
    _last_et_gwt_hwnd = None
    _last_et_gwt_mono = 0.0
    found = find_eternalcity_window()
    _last_et_enum_mono = time.monotonic()
    if found:
        _last_et_gwt_hwnd = found
        _last_et_gwt_mono = time.monotonic()
    return found


def refresh_smart_updater_hwnd_cached(prev_hwnd, korean_substr: str = SMART_UPDATER_TITLE_KO_SUBSTR):
    """캐시된 스마트업데이터 HWND가 유효하면 재사용, 아니면 Enum."""
    global _last_su_gwt_mono, _last_su_gwt_hwnd, _last_su_enum_mono
    now = time.monotonic()
    try:
        if prev_hwnd and win32gui.IsWindow(prev_hwnd):
            if (
                _SU_GWT_REVALIDATE_MIN > 0.0
                and _last_su_gwt_hwnd == prev_hwnd
                and (now - _last_su_gwt_mono) < _SU_GWT_REVALIDATE_MIN
            ):
                return prev_hwnd
            try:
                title = win32gui.GetWindowText(prev_hwnd)
            except Exception:
                title = ""
            _last_su_gwt_mono = now
            _last_su_gwt_hwnd = prev_hwnd
            if smart_updater_title_matches(title, korean_substr):
                return prev_hwnd
    except Exception:
        pass
    if prev_hwnd is None and (now - _last_su_enum_mono) < _SU_ENUM_MIN_INTERVAL:
        return None
    _last_su_gwt_hwnd = None
    _last_su_gwt_mono = 0.0
    found = find_smart_updater_window(korean_substr)
    _last_su_enum_mono = time.monotonic()
    if found:
        _last_su_gwt_hwnd = found
        _last_su_gwt_mono = time.monotonic()
    return found


def splash_placement_anchor_hwnd(pipela_mod: object | None) -> int | None:
    """스플래시를 표시할 모니터 선택용 HWND — 타깃(클라) → 이터널시티 탐색 → 스마트업 런처."""

    if sys.platform != "win32" or pipela_mod is None:
        return None
    try:
        th = getattr(pipela_mod, "target_hwnd", None)
        if th is not None:
            h = int(th)
            if win32gui.IsWindow(h):
                return h
    except Exception:
        pass
    try:
        ec = find_eternalcity_window()
        if ec is not None:
            hi = int(ec)
            if win32gui.IsWindow(hi):
                return hi
    except Exception:
        pass
    try:
        su = find_smart_updater_window()
        if su is not None:
            hi = int(su)
            if win32gui.IsWindow(hi):
                return hi
    except Exception:
        pass
    return None


def get_window_rect(hwnd):
    """클라이언트 영역 화면 좌표 (타이틀바 제외). 실패 시 None."""
    try:
        rect = win32gui.GetClientRect(hwnd)
        point = win32gui.ClientToScreen(hwnd, (0, 0))
        return (point[0], point[1], point[0] + rect[2], point[1] + rect[3])
    except Exception:
        return None


def get_window_outer_rect_screen(hwnd):
    """창 바깥 사각형(타이틀·테두리 포함) 화면 좌표. 실패 시 None."""
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return None
        r = win32gui.GetWindowRect(h)
        if not r:
            return None
        return (int(r[0]), int(r[1]), int(r[2]), int(r[3]))
    except Exception:
        return None


def get_window_size(hwnd):
    """클라이언트 가로·세로. 실패 시 None."""
    rect = get_window_rect(hwnd)
    if not rect:
        return None
    return (rect[2] - rect[0], rect[3] - rect[1])
