"""주 디스플레이 주사율 기반 틱(ms) — `main`·Qt·워커 공통."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

_refresh_hz_cache: int | None = None
# (hwnd, hmonitor, hz) — 창이 올라간 모니터가 바뀔 때만 재조회
_refresh_hz_for_window_cache: tuple[int, int, int] | None = None

_ENUM_CURRENT_SETTINGS = -1
_CCHDEVICENAME = 32


class _DEVMODEW(ctypes.Structure):
    _fields_ = (
        ("dmDeviceName", ctypes.c_wchar * _CCHDEVICENAME),
        ("dmSpecVersion", ctypes.c_uint16),
        ("dmDriverVersion", ctypes.c_uint16),
        ("dmSize", ctypes.c_uint16),
        ("dmDriverExtra", ctypes.c_uint16),
        ("dmFields", ctypes.c_uint32),
        ("dmOrientation", ctypes.c_int16),
        ("dmPaperSize", ctypes.c_int16),
        ("dmPaperLength", ctypes.c_int16),
        ("dmPaperWidth", ctypes.c_int16),
        ("dmScale", ctypes.c_int16),
        ("dmCopies", ctypes.c_int16),
        ("dmDefaultSource", ctypes.c_int16),
        ("dmPrintQuality", ctypes.c_int16),
        ("dmColor", ctypes.c_int16),
        ("dmDuplex", ctypes.c_int16),
        ("dmYResolution", ctypes.c_int16),
        ("dmTTOption", ctypes.c_int16),
        ("dmCollate", ctypes.c_int16),
        ("dmFormName", ctypes.c_wchar * _CCHDEVICENAME),
        ("dmLogPixels", ctypes.c_uint16),
        ("dmBitsPerPel", ctypes.c_uint32),
        ("dmPelsWidth", ctypes.c_uint32),
        ("dmPelsHeight", ctypes.c_uint32),
        ("dmDisplayFlags", ctypes.c_uint32),
        ("dmDisplayFrequency", ctypes.c_uint32),
        ("dmICMMethod", ctypes.c_uint32),
        ("dmICMIntent", ctypes.c_uint32),
        ("dmMediaType", ctypes.c_uint32),
        ("dmDitherType", ctypes.c_uint32),
        ("dmReserved1", ctypes.c_uint32),
        ("dmReserved2", ctypes.c_uint32),
        ("dmPanningWidth", ctypes.c_uint32),
        ("dmPanningHeight", ctypes.c_uint32),
    )


def _win32_refresh_hz_from_devmode(device: str | None) -> int:
    """`EnumDisplaySettingsW` 현재 모드 주사율. device가 None이면 주 디스플레이."""
    dm = _DEVMODEW()
    dm.dmSize = ctypes.sizeof(_DEVMODEW)
    dm.dmDriverExtra = 0
    if device is None:
        ok = ctypes.windll.user32.EnumDisplaySettingsW(
            None, _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)
        )
    else:
        ok = ctypes.windll.user32.EnumDisplaySettingsW(
            device, _ENUM_CURRENT_SETTINGS, ctypes.byref(dm)
        )
    if not ok:
        return 60
    hz = int(dm.dmDisplayFrequency)
    if hz <= 1 or hz < 30 or hz > 480:
        return 60
    return hz


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = (
        ("cbSize", ctypes.c_uint32),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", ctypes.c_uint32),
        ("szDevice", ctypes.c_wchar * _CCHDEVICENAME),
    )


def _win32_primary_display_refresh_hz() -> int:
    """주 디스플레이 현재 모드 주사율(Hz). 실패·비정상 값이면 60."""
    try:
        return _win32_refresh_hz_from_devmode(None)
    except Exception:
        return 60


def _win32_refresh_hz_for_monitor(hmonitor: int) -> int:
    """HMONITOR가 가리키는 디스플레이 어댑터의 현재 모드 주사율."""
    try:
        mi = _MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if not ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi)):
            return _win32_primary_display_refresh_hz()
        dev = mi.szDevice
        return _win32_refresh_hz_from_devmode(dev)
    except Exception:
        return _win32_primary_display_refresh_hz()


def display_refresh_hz() -> int:
    """캐시된 주 디스플레이 주사율. Non-Windows는 60."""
    global _refresh_hz_cache
    if _refresh_hz_cache is not None:
        return _refresh_hz_cache
    hz = 60
    if sys.platform == "win32":
        try:
            hz = _win32_primary_display_refresh_hz()
        except Exception:
            hz = 60
    _refresh_hz_cache = hz
    return hz


def display_refresh_hz_for_window(hwnd: int | None) -> int:
    """
    창(HWND)이 표시되는 모니터의 현재 모드 주사율.
    Non-Windows·실패 시 `display_refresh_hz()`와 동일하게 처리.
    """
    global _refresh_hz_for_window_cache
    if sys.platform != "win32":
        return display_refresh_hz()
    try:
        MONITOR_DEFAULTTONEAREST = 2
        h_w = int(hwnd or 0)
        hmon = int(ctypes.windll.user32.MonitorFromWindow(h_w, MONITOR_DEFAULTTONEAREST))
        if not hmon:
            return display_refresh_hz()
        c = _refresh_hz_for_window_cache
        if c is not None and c[0] == h_w and c[1] == hmon:
            return c[2]
        hz = _win32_refresh_hz_for_monitor(hmon)
        _refresh_hz_for_window_cache = (h_w, hmon, hz)
        return hz
    except Exception:
        return display_refresh_hz()


def display_tick_ms() -> int:
    """주사율에 맞춘 after/타이머 간격(ms). 최소 1."""
    return max(1, int(round(1000.0 / float(display_refresh_hz()))))


def ui_anim_tick_ms() -> int:
    """장식용 QTimer 기본 틱 — **주 디스플레이** 현재 모드 주사율."""
    return display_tick_ms()


def ui_anim_tick_ms_for_window(hwnd: int | None) -> int:
    """``hwnd``가 올라간 모니터 주사율에 맞춘 장식 애니 틱; 0/None이면 주 디스플레이."""
    if not hwnd:
        return display_tick_ms()
    return display_tick_ms_for_window(int(hwnd))


def ui_anim_tick_ms_for_qwidget(w: object | None) -> int:
    """Qt 위젯 최상위 창의 ``winId()``로 모니터 틱(표시 후 유효). 실패 시 주 디스플레이."""
    if w is None:
        return display_tick_ms()
    try:
        window = getattr(w, "window", lambda: None)()
        if window is None:
            return display_tick_ms()
        wid = int(window.winId())
        return display_tick_ms_for_window(wid) if wid else display_tick_ms()
    except Exception:
        return display_tick_ms()


def ui_anim_tick_ms_for_pipela(pipela_mod: object | None) -> int:
    """게임 타깃 HWND가 올라간 모니터 주사율 틱; 없으면 주 디스플레이."""
    if pipela_mod is None:
        return display_tick_ms()
    try:
        refresh = getattr(pipela_mod, "refresh_target_hwnd_if_needed", None)
        if callable(refresh):
            th = refresh()
            if th:
                return display_tick_ms_for_window(int(th))
    except Exception:
        pass
    return display_tick_ms()


def display_tick_ms_for_window(hwnd: int | None) -> int:
    """`hwnd`가 올라간 모니터 주사율에 맞춘 타이머 간격(ms). 최소 1."""
    return max(1, int(round(1000.0 / float(display_refresh_hz_for_window(hwnd)))))


def display_aligned_wall_ms(wall_ms: float) -> int:
    """wall_ms에 가장 가까운 display_tick_ms() 배수(최소 1틱)."""
    tick = display_tick_ms()
    n = max(1, int(round(float(wall_ms) / float(tick))))
    return n * tick
