#include "pipela/core/win32/input_synth.hpp"

#include "pipela/core/feature_trace_log.hpp"

#include <atomic>
#include <chrono>
#include <sstream>
#include <thread>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::win32 {

namespace {

// AGENT: Parity main.py MOUSE_CLICK_IGNORE_SEC (0.004s).
constexpr int kSynthIgnoreMs = 4;

// AGENT: Tag Pipela-owned SendInput events (also sets LLMHF_INJECTED on Win32).
constexpr ULONG_PTR kPipelaSynthExtraInfo = 0x5049504C504CULL;  // "PIPL"

std::atomic<bool> g_ignore_left{false};
std::atomic<bool> g_ignore_right{false};

void traceSynth(const char* op, FeatureTraceDepth depth = FeatureTraceDepth::Verbose) {
    featureTraceLogAt(depth, "synth", std::string("PROG ") + op);
}

void traceSynthKv(const char* op, const std::string& kv,
                  FeatureTraceDepth depth = FeatureTraceDepth::Verbose) {
    featureTraceLogAt(depth, "synth", std::string("PROG ") + op + " " + kv);
}

void sendInput(INPUT& in) {
#ifdef _WIN32
    if (in.type == INPUT_MOUSE) {
        in.mi.dwExtraInfo = kPipelaSynthExtraInfo;
    }
    SendInput(1, &in, sizeof(INPUT));
#else
    (void)in;
#endif
}

}  // namespace

bool synthIgnoreLeft() { return g_ignore_left.load(std::memory_order_acquire); }

bool synthIgnoreRight() { return g_ignore_right.load(std::memory_order_acquire); }

void mouseLeftClick() {
#ifdef _WIN32
    g_ignore_left.store(true, std::memory_order_release);
    traceSynth("mouseLeftClick begin ignore_left=1");
    INPUT down{};
    down.type = INPUT_MOUSE;
    down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
    INPUT up{};
    up.type = INPUT_MOUSE;
    up.mi.dwFlags = MOUSEEVENTF_LEFTUP;
    sendInput(down);
    sendInput(up);
    std::this_thread::sleep_for(std::chrono::milliseconds(kSynthIgnoreMs));
    g_ignore_left.store(false, std::memory_order_release);
    traceSynth("mouseLeftClick end ignore_left=0");
#endif
}

void mouseRightDown() {
#ifdef _WIN32
    g_ignore_right.store(true, std::memory_order_release);
    traceSynth("mouseRightDown begin ignore_right=1");
    INPUT in{};
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN;
    sendInput(in);
    std::this_thread::sleep_for(std::chrono::milliseconds(kSynthIgnoreMs));
    g_ignore_right.store(false, std::memory_order_release);
    traceSynth("mouseRightDown end ignore_right=0");
#endif
}

void mouseRightUp() {
#ifdef _WIN32
    g_ignore_right.store(true, std::memory_order_release);
    traceSynth("mouseRightUp begin ignore_right=1");
    INPUT in{};
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_RIGHTUP;
    sendInput(in);
    std::this_thread::sleep_for(std::chrono::milliseconds(kSynthIgnoreMs));
    g_ignore_right.store(false, std::memory_order_release);
    traceSynth("mouseRightUp end ignore_right=0");
#endif
}

void sendVirtualKey(unsigned short vk, bool key_up) {
#ifdef _WIN32
    traceSynthKv(key_up ? "sendVirtualKey up" : "sendVirtualKey down",
                 "vk=0x" + std::to_string(vk), FeatureTraceDepth::Verbose);
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
    traceSynthKv("setCapsLock", on ? "target=ON" : "target=OFF");
    sendVirtualKey(VK_CAPITAL, false);
    sendVirtualKey(VK_CAPITAL, true);
#endif
    (void)on;
}

void mouseMove(int x, int y) {
#ifdef _WIN32
    // AGENT: Parity main.py mouse_move — SetCursorPos in screen pixels (not SendInput absolute).
    if (x == 0 && y == 0) {
        return;
    }
    if (x <= -32000 || y <= -32000) {
        return;
    }
    featureTraceThrottle("synth/mouseMove", 300, FeatureTraceDepth::Deep, "synth",
                         "PROG mouseMove x=" + std::to_string(x) + " y=" + std::to_string(y));
    SetCursorPos(x, y);
#endif
}

void mouseLeftDoubleClick() {
#ifdef _WIN32
    g_ignore_left.store(true, std::memory_order_release);
    traceSynth("mouseLeftDoubleClick begin ignore_left=1");
    INPUT down{};
    down.type = INPUT_MOUSE;
    down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
    INPUT up{};
    up.type = INPUT_MOUSE;
    up.mi.dwFlags = MOUSEEVENTF_LEFTUP;
    sendInput(down);
    sendInput(up);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    sendInput(down);
    sendInput(up);
    std::this_thread::sleep_for(std::chrono::milliseconds(kSynthIgnoreMs));
    g_ignore_left.store(false, std::memory_order_release);
    traceSynth("mouseLeftDoubleClick end ignore_left=0");
#endif
}

}  // namespace pipela::core::win32
