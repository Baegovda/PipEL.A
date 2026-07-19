from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path


class DCompHud:
    def __init__(self) -> None:
        self._dll = None
        self._ok = False
        self._anchor_hwnd = 0

    @property
    def ok(self) -> bool:
        return bool(self._ok)

    def try_load_and_init(self, anchor_hwnd: int = 0) -> bool:
        if sys.platform != "win32":
            return False
        if self._ok:
            return True
        dll_path = self._resolve_dll_path()
        if not dll_path:
            return False
        try:
            dll = ctypes.WinDLL(str(dll_path))
        except Exception:
            return False

        try:
            dll.hud_init.argtypes = [ctypes.c_ulonglong]
            dll.hud_init.restype = ctypes.c_int
            dll.hud_set_visible.argtypes = [ctypes.c_int]
            dll.hud_set_visible.restype = None
            dll.hud_set_icons.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
            dll.hud_set_icons.restype = None
            dll.hud_set_position.argtypes = [ctypes.c_int, ctypes.c_int]
            dll.hud_set_position.restype = None
            dll.hud_shutdown.argtypes = []
            dll.hud_shutdown.restype = None
        except Exception:
            return False

        try:
            ok = int(dll.hud_init(int(anchor_hwnd) & 0xFFFFFFFFFFFFFFFF))
        except Exception:
            return False
        if ok != 1:
            return False
        self._dll = dll
        self._ok = True
        self._anchor_hwnd = int(anchor_hwnd) if anchor_hwnd else 0
        return True

    def ensure_init(self, anchor_hwnd: int) -> bool:
        """Ensure the native HUD is initialized with the given anchor HWND.

        If already initialized with a different anchor, re-init.
        """
        if sys.platform != "win32":
            return False
        ah = int(anchor_hwnd) if anchor_hwnd else 0
        if ah <= 0:
            return bool(self._ok)
        if self._ok and int(self._anchor_hwnd) == ah:
            return True
        if self._ok and int(self._anchor_hwnd) != ah:
            self.shutdown()
        return self.try_load_and_init(ah)

    def shutdown(self) -> None:
        if not self._ok or self._dll is None:
            return
        try:
            self._dll.hud_shutdown()
        except Exception:
            pass
        self._ok = False
        self._dll = None
        self._anchor_hwnd = 0

    def set_visible(self, visible: bool) -> None:
        if not self._ok or self._dll is None:
            return
        try:
            self._dll.hud_set_visible(1 if visible else 0)
        except Exception:
            pass

    def set_icons(self, move_on: bool, fire_on: bool, ride_on: bool) -> None:
        if not self._ok or self._dll is None:
            return
        try:
            self._dll.hud_set_icons(1 if move_on else 0, 1 if fire_on else 0, 1 if ride_on else 0)
        except Exception:
            pass

    def set_position(self, x_phys: int, y_phys: int) -> None:
        if not self._ok or self._dll is None:
            return
        try:
            self._dll.hud_set_position(int(x_phys), int(y_phys))
        except Exception:
            pass

    def _resolve_dll_path(self) -> Path | None:
        # User override
        p = (os.environ.get("PIPELA_CURSOR_HUD_DCOMP_DLL") or "").strip()
        if p:
            pp = Path(p)
            if pp.is_file():
                return pp

        # Frozen builds: prefer packaged DLL next to app.
        try:
            meipass = Path(getattr(sys, "_MEIPASS", "") or "")
        except Exception:
            meipass = Path()
        if str(meipass):
            for rel in (
                Path("native") / "cursor_hud_dcomp" / "cursor_hud_dcomp.dll",
                Path("cursor_hud_dcomp.dll"),
            ):
                cand = meipass / rel
                if cand.is_file():
                    return cand
        try:
            exe_dir = Path(sys.executable).resolve().parent
        except Exception:
            exe_dir = Path()
        if str(exe_dir):
            for rel in (
                Path("native") / "cursor_hud_dcomp" / "cursor_hud_dcomp.dll",
                Path("cursor_hud_dcomp.dll"),
            ):
                cand = exe_dir / rel
                if cand.is_file():
                    return cand

        repo_root = Path(__file__).resolve().parents[1]
        candidates = [
            # Local dev default (our build script outputs here)
            repo_root / "native" / "cursor_hud_dcomp" / "build" / "cursor_hud_dcomp.dll",
            repo_root / "native" / "cursor_hud_dcomp" / "build" / "Release" / "cursor_hud_dcomp.dll",
            repo_root / "native" / "cursor_hud_dcomp" / "build" / "Debug" / "cursor_hud_dcomp.dll",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None


def dcomp_hud_enabled() -> bool:
    """Whether DComp HUD is enabled.

    Default is ON. Set `PIPELA_CURSOR_HUD_DCOMP=0/false/off` to disable explicitly.
    """
    v = str(os.environ.get("PIPELA_CURSOR_HUD_DCOMP", "1") or "1").strip().lower()
    if v in ("0", "false", "no", "off", "n"):
        return False
    return True

