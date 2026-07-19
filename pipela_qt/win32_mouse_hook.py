"""Win32 low-level mouse hook helper (WH_MOUSE_LL).

Runs the hook on a dedicated thread with its own message loop.
Never call Qt APIs from the hook thread; use a callback that bridges to UI thread safely.
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable


WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13
WM_MOUSEMOVE = 0x0200
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

LRESULT = ctypes.c_ssize_t  # LONG_PTR
WPARAM = ctypes.c_size_t  # UINT_PTR
LPARAM = ctypes.c_ssize_t  # LONG_PTR


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        # `ctypes.wintypes` may not expose ULONG_PTR on some Python builds.
        ("dwExtraInfo", ctypes.c_size_t),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    WPARAM,
    LPARAM,
)


class Win32LowLevelMouseHook:
    """Start/stop a WH_MOUSE_LL hook.

    The callback is invoked as `on_move(x_phys, y_phys)` on WM_MOUSEMOVE.
    """

    def __init__(self, on_move: Callable[[int, int], None]) -> None:
        self._on_move = on_move
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._thread_id: int = 0
        self._hook: int = 0
        self._proc = LowLevelMouseProc(self._hook_proc)
        self._running = False

        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        self._user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        self._user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self._user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            WPARAM,
            LPARAM,
        ]
        self._user32.CallNextHookEx.restype = LRESULT
        self._user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            WPARAM,
            LPARAM,
        ]
        self._user32.PostThreadMessageW.restype = wintypes.BOOL

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            self._running = True
            self._thread = threading.Thread(target=self._run, name="pipela-mouse-hook", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            tid = int(self._thread_id) if self._thread_id else 0
        if tid:
            try:
                self._user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            except Exception:
                pass
        th = self._thread
        if th is not None:
            try:
                th.join(timeout=0.8)
            except Exception:
                pass
        with self._lock:
            self._thread = None
            self._thread_id = 0
            self._hook = 0

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._running)

    def is_hook_installed(self) -> bool:
        with self._lock:
            return bool(self._hook)

    def _hook_proc(self, nCode: int, wParam: int, lParam: int):
        try:
            if nCode >= 0 and int(wParam) == WM_MOUSEMOVE:
                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                try:
                    self._on_move(int(ms.pt.x), int(ms.pt.y))
                except Exception:
                    pass
        except Exception:
            pass
        return self._user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _run(self) -> None:
        try:
            tid = int(self._kernel32.GetCurrentThreadId())
        except Exception:
            tid = 0
        with self._lock:
            self._thread_id = tid

        try:
            hmod = wintypes.HINSTANCE(0)
            hk = self._user32.SetWindowsHookExW(
                WH_MOUSE_LL,
                self._proc,
                hmod,
                0,
            )
        except Exception:
            hk = 0
        with self._lock:
            self._hook = int(hk) if hk else 0

        msg = wintypes.MSG()
        try:
            while True:
                rv = self._user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if rv == 0:  # WM_QUIT
                    break
                if rv == -1:
                    break
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            pass

        hk2 = 0
        with self._lock:
            hk2 = int(self._hook)
            self._hook = 0
        if hk2:
            try:
                self._user32.UnhookWindowsHookEx(hk2)
            except Exception:
                pass


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    WPARAM,
    LPARAM,
)


class Win32LowLevelKeyboardHook:
    """Start/stop a WH_KEYBOARD_LL hook.

    The callback is invoked as `on_key(vk, is_down)` for key transitions.
    """

    def __init__(self, on_key: Callable[[int, bool], None]) -> None:
        self._on_key = on_key
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._thread_id: int = 0
        self._hook: int = 0
        self._proc = LowLevelKeyboardProc(self._hook_proc)
        self._running = False

        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        self._user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        self._user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self._user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            WPARAM,
            LPARAM,
        ]
        self._user32.CallNextHookEx.restype = LRESULT
        self._user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            WPARAM,
            LPARAM,
        ]
        self._user32.PostThreadMessageW.restype = wintypes.BOOL

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            self._running = True
            self._thread = threading.Thread(target=self._run, name="pipela-key-hook", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            tid = int(self._thread_id) if self._thread_id else 0
        if tid:
            try:
                self._user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            except Exception:
                pass
        th = self._thread
        if th is not None:
            try:
                th.join(timeout=0.8)
            except Exception:
                pass
        with self._lock:
            self._thread = None
            self._thread_id = 0
            self._hook = 0

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._running)

    def is_hook_installed(self) -> bool:
        with self._lock:
            return bool(self._hook)

    def _hook_proc(self, nCode: int, wParam: int, lParam: int):
        try:
            if nCode >= 0:
                msg = int(wParam)
                if msg in (WM_KEYDOWN, WM_SYSKEYDOWN, WM_KEYUP, WM_SYSKEYUP):
                    ks = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    is_down = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    try:
                        self._on_key(int(ks.vkCode), bool(is_down))
                    except Exception:
                        pass
        except Exception:
            pass
        return self._user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _run(self) -> None:
        try:
            tid = int(self._kernel32.GetCurrentThreadId())
        except Exception:
            tid = 0
        with self._lock:
            self._thread_id = tid

        try:
            hmod = wintypes.HINSTANCE(0)
            hk = self._user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._proc,
                hmod,
                0,
            )
        except Exception:
            hk = 0
        with self._lock:
            self._hook = int(hk) if hk else 0

        msg = wintypes.MSG()
        try:
            while True:
                rv = self._user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if rv == 0:  # WM_QUIT
                    break
                if rv == -1:
                    break
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            pass

        hk2 = 0
        with self._lock:
            hk2 = int(self._hook)
            self._hook = 0
        if hk2:
            try:
                self._user32.UnhookWindowsHookEx(hk2)
            except Exception:
                pass

