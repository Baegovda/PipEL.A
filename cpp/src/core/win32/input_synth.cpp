#include "pipela/core/win32/input_synth.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::win32 {

namespace {

void sendInput(INPUT& in) {
#ifdef _WIN32
    SendInput(1, &in, sizeof(INPUT));
#else
    (void)in;
#endif
}

}  // namespace

void mouseLeftClick() {
#ifdef _WIN32
    INPUT down{};
    down.type = INPUT_MOUSE;
    down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
    INPUT up{};
    up.type = INPUT_MOUSE;
    up.mi.dwFlags = MOUSEEVENTF_LEFTUP;
    sendInput(down);
    sendInput(up);
#endif
}

void mouseRightDown() {
#ifdef _WIN32
    INPUT in{};
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN;
    sendInput(in);
#endif
}

void mouseRightUp() {
#ifdef _WIN32
    INPUT in{};
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_RIGHTUP;
    sendInput(in);
#endif
}

void sendVirtualKey(unsigned short vk, bool key_up) {
#ifdef _WIN32
    INPUT in{};
    in.type = INPUT_KEYBOARD;
    in.ki.wVk = vk;
    in.ki.dwFlags = key_up ? KEYEVENTF_KEYUP : 0;
    sendInput(in);
#endif
}

void setCapsLock(bool on) {
#ifdef _WIN32
    const SHORT state = GetKeyState(VK_CAPITAL);
    const bool cur = (state & 0x0001) != 0;
    if (cur == on) {
        return;
    }
    sendVirtualKey(VK_CAPITAL, false);
    sendVirtualKey(VK_CAPITAL, true);
#endif
    (void)on;
}

void mouseMove(int x, int y) {
#ifdef _WIN32
    INPUT in{};
    in.type = INPUT_MOUSE;
    in.mi.dx = x * (65535 / GetSystemMetrics(SM_CXSCREEN));
    in.mi.dy = y * (65535 / GetSystemMetrics(SM_CYSCREEN));
    in.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE;
    sendInput(in);
#endif
}

void mouseLeftDoubleClick() {
#ifdef _WIN32
    mouseLeftClick();
    mouseLeftClick();
#endif
}

}  // namespace pipela::core::win32
