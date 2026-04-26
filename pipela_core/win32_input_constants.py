"""Win32 mouse_event / keybd_event 상수 및 VK 표시 이름."""

from __future__ import annotations

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

VK_CAPITAL = 0x14
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_0 = 0x30
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_4 = 0x34
VK_5 = 0x35
VK_6 = 0x36
VK_7 = 0x37
VK_8 = 0x38
VK_9 = 0x39
VK_RETURN = 0x0D
VK_Z = 0x5A

VK_TO_KEY_NAME = {
    VK_0: "0",
    VK_1: "1",
    VK_2: "2",
    VK_3: "3",
    VK_4: "4",
    VK_5: "5",
    VK_6: "6",
    VK_7: "7",
    VK_8: "8",
    VK_9: "9",
}


def vk_to_display_name(vk) -> str:
    """가상 키 코드를 표시용 문자열로 변환."""
    vk = vk & 0xFF
    if vk in VK_TO_KEY_NAME:
        return VK_TO_KEY_NAME[vk]
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x70 <= vk <= 0x7B:
        return f"F{vk - 0x70 + 1}"
    extra = {
        0x20: "Space",
        0x0D: "Enter",
        0x09: "Tab",
        0x1B: "Esc",
        0x08: "Backspace",
        0x2D: "Insert",
        0x2E: "Delete",
        0x21: "PgUp",
        0x22: "PgDn",
        0x23: "End",
        0x24: "Home",
        0x25: "Left",
        0x26: "Up",
        0x27: "Right",
        0x28: "Down",
    }
    return extra.get(vk, f"0x{vk:02X}")
