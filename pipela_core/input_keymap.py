"""AGENT: pynput key conversion helpers shared by listeners."""

from __future__ import annotations

from typing import Any


def pynput_key_to_vk(key: Any, keyboard_mod: Any) -> int | None:
    """pynput key -> Windows VK 0-255; None if unmapped."""
    try:
        if key is not None and hasattr(key, "vk") and key.vk is not None:
            return int(key.vk) & 0xFF
    except Exception:
        pass
    try:
        _named = {
            keyboard_mod.Key.f1: 0x70,
            keyboard_mod.Key.f2: 0x71,
            keyboard_mod.Key.f3: 0x72,
            keyboard_mod.Key.f4: 0x73,
            keyboard_mod.Key.f5: 0x74,
            keyboard_mod.Key.f6: 0x75,
            keyboard_mod.Key.f7: 0x76,
            keyboard_mod.Key.f8: 0x77,
            keyboard_mod.Key.f9: 0x78,
            keyboard_mod.Key.f10: 0x79,
            keyboard_mod.Key.f11: 0x7A,
            keyboard_mod.Key.f12: 0x7B,
            keyboard_mod.Key.space: 0x20,
            keyboard_mod.Key.enter: 0x0D,
            keyboard_mod.Key.tab: 0x09,
            keyboard_mod.Key.esc: 0x1B,
            keyboard_mod.Key.backspace: 0x08,
            keyboard_mod.Key.insert: 0x2D,
            keyboard_mod.Key.delete: 0x2E,
            keyboard_mod.Key.page_up: 0x21,
            keyboard_mod.Key.page_down: 0x22,
            keyboard_mod.Key.end: 0x23,
            keyboard_mod.Key.home: 0x24,
            keyboard_mod.Key.left: 0x25,
            keyboard_mod.Key.up: 0x26,
            keyboard_mod.Key.right: 0x27,
            keyboard_mod.Key.down: 0x28,
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
