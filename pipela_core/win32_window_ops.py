"""Win32 창 조작·DPI·모니터 작업 영역 — `main`·Qt 공통 (HWND는 호출 측에서 전달)."""

from __future__ import annotations

import ctypes
import os
import sys
import time

import win32con
import win32gui
from ctypes import wintypes

# 동일 (위, 아래) HWND 쌍에 대한 연속 SetWindowPos 스로틀 — 스트립·오버레이 틱이 매번 ~2회씩 호출할 때 CPU·DWM 부하↓
_SWP_ZORDER_PAIR_MIN_SEC = 1.12
_swpos_z_last_mono: dict[tuple[int, int], float] = {}

# MonitorFromWindow + GetDpiForMonitor — 해상도 스트립·DPI 표시에서 초당 수천 회 호출될 수 있음
_DPI_MON_CACHE_TTL = max(
    0.0,
    float(os.environ.get("PIPELA_DPI_MON_CACHE_SEC", "0.85") or 0.85),
)
_dpi_mon_cache: dict[int, tuple[float, int]] = {}


def win32_native_root_hwnd_from_child(child_hwnd: int) -> int | None:
    """자식 HWND → 최상위 root HWND (GetAncestor GA_ROOT). 실패 시 None."""
    if not child_hwnd:
        return None
    try:
        ch = int(child_hwnd)
        GA_ROOT = 2
        root_hw = ctypes.windll.user32.GetAncestor(ch, GA_ROOT)
        return int(root_hw) if root_hw else ch
    except Exception:
        return None


def win32_force_toolwindow_exstyle(hwnd) -> None:
    """작업 표시줄·작업 전환에 안 잡히게 WS_EX_TOOLWINDOW 켜고 WS_EX_APPWINDOW 끔."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        hwnd = int(hwnd)
        if not win32gui.IsWindow(hwnd):
            return
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        user32 = ctypes.windll.user32
        style = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
        new_style = (style | WS_EX_TOOLWINDOW) & (~WS_EX_APPWINDOW & 0xFFFFFFFF)
        if new_style == style:
            return
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        win32gui.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


def win32_set_window_outer_rect(hwnd, x, y, w, h) -> None:
    """geometry 직후 같은 좌표를 SetWindowPos로 한 번 더 반영 (딸림 완화)."""
    try:
        if not hwnd:
            return
        hwnd = int(hwnd)
        if not win32gui.IsWindow(hwnd):
            return
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w < 1 or h < 1:
            return
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        win32gui.SetWindowPos(
            hwnd, 0, x, y, w, h,
            SWP_NOZORDER | SWP_NOACTIVATE,
        )
    except Exception:
        pass


def win32_set_window_owner(hwnd_owned, hwnd_owner) -> None:
    """
    최상위 팝업형 창의 **소유자** HWND 설정(GWLP_HWNDPARENT).
    소유 창은 소유자보다 **항상 위**(Z)로 쌓이며, 전역 TOPMOST가 아님 → 다른 앱이 앞에 오면 그 위에 표시.
    hwnd_owner=0 또는 None 이면 소유 관계 해제.
    """
    if sys.platform != "win32" or not hwnd_owned:
        return
    try:
        ho = int(hwnd_owned)
        if not win32gui.IsWindow(ho):
            return
        ow = 0 if hwnd_owner is None else int(hwnd_owner)
        if ow != 0 and not win32gui.IsWindow(ow):
            return
        GWLP_HWNDPARENT = -8
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW(ho, GWLP_HWNDPARENT, ctypes.c_void_p(ow))
        else:
            user32.SetWindowLongW(ho, GWLP_HWNDPARENT, ow)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        win32gui.SetWindowPos(
            ho,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


def win32_set_window_topmost(hwnd, topmost: bool = True) -> None:
    """
    HWND를 **최상위(Z) 밴드**로 올리거나 해제. 일반 창(대부분의 게임)보다 위에 확실히 표시.
    위치·크기·활성 포커스는 그대로(SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE).
    """
    if sys.platform != "win32" or not hwnd:
        return
    try:
        hwnd = int(hwnd)
        if not win32gui.IsWindow(hwnd):
            return
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        insert_after = HWND_TOPMOST if topmost else HWND_NOTOPMOST
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            insert_after,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except Exception:
        pass


def get_native_window_dpi(hwnd=None) -> int:
    """창이 놓인 모니터 DPI(96=100%) 또는 시스템 DPI. 비Windows·실패 시 96."""
    if sys.platform != "win32":
        return 96
    user32 = ctypes.windll.user32
    if hwnd:
        try:
            if hasattr(user32, "GetDpiForWindow"):
                dpi = int(user32.GetDpiForWindow(int(hwnd)))
                if dpi > 0:
                    return dpi
        except Exception:
            pass
    try:
        dpi = int(user32.GetDpiForSystem())
        if dpi > 0:
            return dpi
    except Exception:
        pass
    return 96


def get_dpi_for_monitor_containing_window(hwnd) -> int:
    """
    창이(대부분) 올라간 모니터의 **효과** DPI(Windows «배율 100%/125%…»와 대응).
    Win32: MonitorFromWindow → shcore.GetDpiForMonitor(MDT_EFFECTIVE_DPI).
    실패·비 Windows 시 get_native_window_dpi로 대체. hwnd None/0은 시스템/포그라운드 쪽과 동일하게 처리.
    """
    global _dpi_mon_cache
    if sys.platform != "win32" or not hwnd:
        return get_native_window_dpi(hwnd)
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            _dpi_mon_cache.pop(h, None)
            return get_native_window_dpi(None)
        now = time.monotonic()
        if _DPI_MON_CACHE_TTL > 0.0:
            hit = _dpi_mon_cache.get(h)
            if hit is not None and (now - hit[0]) < _DPI_MON_CACHE_TTL:
                return int(hit[1])
        user32 = ctypes.windll.user32
        MONITOR_DEFAULTTONEAREST = 2
        hmon = user32.MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST)
        if not hmon:
            out = get_native_window_dpi(h)
            if _DPI_MON_CACHE_TTL > 0.0:
                _dpi_mon_cache[h] = (time.monotonic(), int(out))
            return out
        shcore = ctypes.windll.shcore
        MDT_EFFECTIVE_DPI = 0
        dpix = ctypes.c_uint(0)
        dpiy = ctypes.c_uint(0)
        res = int(
            shcore.GetDpiForMonitor(
                int(hmon), MDT_EFFECTIVE_DPI, ctypes.byref(dpix), ctypes.byref(dpiy),
            )
        )
        if res == 0 and int(dpix.value) > 0:
            out = int(dpix.value)
            if _DPI_MON_CACHE_TTL > 0.0:
                _dpi_mon_cache[h] = (time.monotonic(), out)
                if len(_dpi_mon_cache) > 256:
                    _dpi_mon_cache.clear()
            return out
    except Exception:
        pass
    out = get_native_window_dpi(int(hwnd))
    try:
        hi = int(hwnd)
        if _DPI_MON_CACHE_TTL > 0.0 and win32gui.IsWindow(hi):
            _dpi_mon_cache[hi] = (time.monotonic(), int(out))
    except Exception:
        pass
    return out


def set_window_z_order_directly_above(hwnd_above, hwnd_below) -> None:
    """hwnd_above를 hwnd_below 바로 위 Z-order로. 포커스는 옮기지 않음."""
    global _swpos_z_last_mono
    try:
        if not hwnd_above or not hwnd_below:
            return
        ha, hb = int(hwnd_above), int(hwnd_below)
        if not win32gui.IsWindow(ha) or not win32gui.IsWindow(hb):
            return
        if ha == hb:
            return
        pair = (ha, hb)
        now = time.monotonic()
        prev = _swpos_z_last_mono.get(pair, 0.0)
        if now - prev < _SWP_ZORDER_PAIR_MIN_SEC:
            return
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        win32gui.SetWindowPos(
            ha, hb, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
        _swpos_z_last_mono[pair] = now
        if len(_swpos_z_last_mono) > 64:
            _swpos_z_last_mono.clear()
    except Exception:
        pass


def is_window_minimized(hwnd) -> bool:
    """최소화면 캡처·매칭 스킵용."""
    if not hwnd:
        return True
    try:
        return bool(win32gui.IsIconic(hwnd))
    except Exception:
        return True


def is_window_maximized(hwnd) -> bool:
    """Win32 ``IsZoomed`` — 최대화(작업 표시줄까지 채우는 모드) 여부."""
    if not hwnd:
        return False
    try:
        return bool(win32gui.IsZoomed(int(hwnd)))
    except Exception:
        return False


def _set_foreground_window_attach_input(hwnd: int) -> None:
    """다른 프로세스 창을 앞으로 — ``SetForegroundWindow`` 제한 완화(AttachThreadInput)."""
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        fg = user32.GetForegroundWindow()
        if not fg:
            win32gui.SetForegroundWindow(h)
            return
        tid_fg = int(user32.GetWindowThreadProcessId(fg, None))
        tid_cur = int(kernel32.GetCurrentThreadId())
        if tid_fg and tid_fg != tid_cur:
            user32.AttachThreadInput(tid_fg, tid_cur, True)
        try:
            win32gui.BringWindowToTop(h)
            win32gui.SetForegroundWindow(h)
        finally:
            if tid_fg and tid_fg != tid_cur:
                user32.AttachThreadInput(tid_fg, tid_cur, False)
    except Exception:
        try:
            win32gui.SetForegroundWindow(int(hwnd))
        except Exception:
            pass


def win32_window_minimize(hwnd) -> bool:
    """앵커 창 최소화(타이틀 최소화 버튼과 동일한 ``ShowWindow``)."""
    if not hwnd:
        return False
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return False
        win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
        return True
    except Exception:
        return False


def win32_window_restore_normal(hwnd) -> bool:
    """최소화(아이콘) 상태면 ``SW_RESTORE`` — 이미 일반 표시면 그대로 둠."""
    if not hwnd:
        return False
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return False
        if win32gui.IsIconic(h):
            win32gui.ShowWindow(h, win32con.SW_RESTORE)
        return True
    except Exception:
        return False


def _try_window_fill_monitor_work_area(hwnd: int) -> bool:
    """WS_POPUP·일부 D3D 창이 ``SC_MAXIMIZE``/``SW_MAXIMIZE`` 를 무시할 때 — 모니터 작업 영역에 외곽 맞춤."""
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return False
        work = get_monitor_work_rect_phys(h)
        if not work:
            return False
        wl, wt, wr, wb = work
        w = max(8, int(wr) - int(wl))
        hgt = max(8, int(wb) - int(wt))
        user32 = ctypes.windll.user32
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040
        SWP_FRAMECHANGED = 0x0020
        return bool(
            user32.SetWindowPos(
                h,
                0,
                int(wl),
                int(wt),
                w,
                hgt,
                SWP_NOZORDER | SWP_SHOWWINDOW | SWP_FRAMECHANGED,
            )
        )
    except Exception:
        return False


def win32_window_maximize_or_restore(hwnd) -> bool:
    """최대화 ↔ 복원 토글. 타이틀 바와 동일하게 ``WM_SYSCOMMAND`` 우선, 실패 시 ``ShowWindow``,
    그래도 안 되면 ``PostMessage`` + 작업 영역 ``SetWindowPos`` (일부 보더리스·D3D).
    """
    if not hwnd:
        return False
    try:
        h0 = int(hwnd)
        if not win32gui.IsWindow(h0):
            return False
        h = win32_native_root_hwnd_from_child(h0) or h0
        if not win32gui.IsWindow(h):
            h = h0

        _set_foreground_window_attach_input(h)

        if win32gui.IsIconic(h):
            win32gui.ShowWindow(h, win32con.SW_RESTORE)

        was_zoomed = bool(win32gui.IsZoomed(h))
        cmd = win32con.SC_RESTORE if was_zoomed else win32con.SC_MAXIMIZE
        try:
            win32gui.SendMessage(h, win32con.WM_SYSCOMMAND, cmd, 0)
        except Exception:
            pass
        # D3D/보더리스 — DefWindowProc 반영·IsZoomed 갱신이 한 틱 늦는 경우가 있어 즉시 읽지 않음
        time.sleep(0.05)
        now_zoomed = bool(win32gui.IsZoomed(h))
        if was_zoomed == now_zoomed:
            if was_zoomed:
                win32gui.ShowWindow(h, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(h, win32con.SW_MAXIMIZE)

        now_zoomed = bool(win32gui.IsZoomed(h))
        if not was_zoomed and not now_zoomed:
            try:
                win32gui.PostMessage(h, win32con.WM_SYSCOMMAND, win32con.SC_MAXIMIZE, 0)
            except Exception:
                pass
            time.sleep(0.05)
            now_zoomed = bool(win32gui.IsZoomed(h))
        if not was_zoomed and not now_zoomed:
            _try_window_fill_monitor_work_area(h)
        return True
    except Exception:
        return False


def win32_window_post_close(hwnd) -> bool:
    """``WM_CLOSE`` — 창이 일반적인 종료 절차를 타도록(강제 ``DestroyWindow`` 아님)."""
    if not hwnd:
        return False
    try:
        h = int(hwnd)
        if not win32gui.IsWindow(h):
            return False
        win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False


def clamp_rect_to_monitor_work_area(hwnd, x, y, w, h):
    """HWND 모니터 rcWork 안에 (x,y)+크기(w,h)가 들어가도록 보정."""
    if not hwnd:
        return (max(0, int(x)), max(0, int(y)), int(w), int(h))
    try:
        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        hmon = user32.MonitorFromWindow(int(hwnd), 2)
        if not hmon or not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return (max(0, int(x)), max(0, int(y)), int(w), int(h))
        wl, wt = mi.rcWork.left, mi.rcWork.top
        wr, wb = mi.rcWork.right, mi.rcWork.bottom
        w = int(w)
        h = int(h)
        if w > (wr - wl):
            w = max(1, wr - wl)
        if h > (wb - wt):
            h = max(1, wb - wt)
        x = max(wl, min(int(x), wr - w))
        y = max(wt, min(int(y), wb - h))
        return (x, y, w, h)
    except Exception:
        return (max(0, int(x)), max(0, int(y)), int(w), int(h))


def get_monitor_work_rect_phys(hwnd) -> tuple[int, int, int, int] | None:
    """앵커 HWND가 있는 모니터 **작업 영역** ``rcWork`` (Win32 물리 화면 좌표). 실패 시 None."""
    if not hwnd:
        return None
    try:
        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        hmon = user32.MonitorFromWindow(int(hwnd), 2)
        if not hmon or not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return None
        return (
            int(mi.rcWork.left),
            int(mi.rcWork.top),
            int(mi.rcWork.right),
            int(mi.rcWork.bottom),
        )
    except Exception:
        return None


def dock_outer_rect_touch_client_left(
    hwnd_anchor,
    client_left_phys: int,
    y: int,
    w_phys: int,
    h_phys: int,
) -> tuple[int, int, int, int]:
    """
    패널이 게임 **왼쪽**에 붙을 때: Win32 **외곽 오른쪽** = 게임 **클라이언트 왼** ``client_left_phys``.

    ``round(논리폭 * DPI/96)`` 만 쓰면 125% 등에서 1px 단위로 클라이언트를 살짝 덮을 수 있어,
    폭은 ``w = snap - x`` 로 **끝점을 맞춰** 역산한다.
    """
    work = get_monitor_work_rect_phys(hwnd_anchor)
    wl, wt, wr, wb = (0, 0, 10**9, 10**9) if work is None else work
    snap = int(client_left_phys)
    w_t = max(8, int(w_phys))
    h = max(1, int(h_phys))
    h = min(h, max(1, wb - wt))
    y = max(wt, min(int(y), wb - h))
    # 외곽 오른쪽 = snap (게임 클라 왼). min(snap,wr) 쓰면 모서리가 어긋남.
    x = max(wl, snap - w_t)
    w = snap - x
    if w < 8:
        w = 8
        x = snap - w
        if x < wl:
            x = wl
            w = snap - x
    if x + w > wr:
        w = max(8, wr - x)
    return (x, y, w, h)


def dock_outer_rect_touch_client_right(
    hwnd_anchor,
    client_right_phys: int,
    y: int,
    w_phys: int,
    h_phys: int,
) -> tuple[int, int, int, int]:
    """
    패널이 게임 **오른쪽**에 붙을 때: Win32 **외곽 왼쪽** = 게임 **클라이언트 오른** ``client_right_phys``.
    """
    work = get_monitor_work_rect_phys(hwnd_anchor)
    wl, wt, wr, wb = (0, 0, 10**9, 10**9) if work is None else work
    snap = int(client_right_phys)
    w_t = max(8, int(w_phys))
    h = max(1, int(h_phys))
    h = min(h, max(1, wb - wt))
    y = max(wt, min(int(y), wb - h))
    x = max(wl, snap)
    avail = wr - x
    if avail >= 8:
        w = max(8, min(w_t, avail))
    elif avail > 0:
        w = max(1, min(w_t, avail))
    else:
        w = min(w_t, 8)
    if x + w > wr:
        w = max(1, wr - x)
    return (x, y, w, h)


def center_outer_window_on_monitor_work_area(hwnd) -> bool:
    """
    최상위 창(테두리 포함)을 해당 창이 있는 모니터 작업 영역(rcWork) 정중앙으로 이동.
    최대화·최소화 창은 건드리지 않음(최대화는 True로 종료). 실패 시 False.
    """
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        hwnd = int(hwnd)
        if not win32gui.IsWindow(hwnd):
            return False
        if is_window_minimized(hwnd):
            return False
        try:
            if win32gui.IsZoomed(hwnd):
                return True
        except Exception:
            pass
        wr0 = win32gui.GetWindowRect(hwnd)
        if not wr0:
            return False
        wx, wy, wx2, wy2 = wr0
        ww, wh = int(wx2 - wx), int(wy2 - wy)
        if ww < 8 or wh < 8:
            return False
        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        hmon = user32.MonitorFromWindow(hwnd, 2)
        if not hmon or not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return False
        wl, wt = int(mi.rcWork.left), int(mi.rcWork.top)
        wrx, wry = int(mi.rcWork.right), int(mi.rcWork.bottom)
        avail_w = wrx - wl
        avail_h = wry - wt
        new_x = wl + max(0, (avail_w - ww) // 2)
        new_y = wt + max(0, (avail_h - wh) // 2)
        new_x = max(wl, min(int(new_x), wrx - ww))
        new_y = max(wt, min(int(new_y), wry - wh))
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        win32gui.SetWindowPos(
            hwnd, 0, new_x, new_y, 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
        )
        return True
    except Exception:
        return False


def ensure_process_dpi_awareness() -> bool:
    """프로세스 DPI 인식(가능한 최선). UI(제어창) 생성 전 1회."""
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                return True
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception:
        pass
    return False
