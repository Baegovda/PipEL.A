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

}  // namespace pipela::core::win32
