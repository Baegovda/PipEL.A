#include "pipela/core/win32/foreground_monitor.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <functional>
#endif

namespace pipela::core::win32 {

#ifdef _WIN32
namespace {

std::function<void(std::intptr_t)>& foregroundCallbackSlot() {
    static std::function<void(std::intptr_t)> cb;
    return cb;
}

void CALLBACK foregroundHookProc(HWINEVENTHOOK /*hook*/,
                               DWORD event,
                               HWND hwnd,
                               LONG id_object,
                               LONG /*id_child*/,
                               DWORD /*id_thread*/,
                               DWORD /*time*/) {
    if (event != EVENT_SYSTEM_FOREGROUND || id_object != OBJID_WINDOW || hwnd == nullptr) {
        return;
    }
    const auto& cb = foregroundCallbackSlot();
    if (cb) {
        cb(reinterpret_cast<std::intptr_t>(hwnd));
    }
}

}  // namespace
#endif

ForegroundWinEventMonitor::~ForegroundWinEventMonitor() { stop(); }

bool ForegroundWinEventMonitor::start(Callback cb) {
#ifdef _WIN32
    stop();
    if (!cb) {
        return false;
    }
    foregroundCallbackSlot() = std::move(cb);
    hook_ = SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, nullptr,
                            foregroundHookProc, 0, 0, WINEVENT_OUTOFCONTEXT);
    return hook_ != nullptr;
#else
    (void)cb;
    return false;
#endif
}

void ForegroundWinEventMonitor::stop() {
#ifdef _WIN32
    if (hook_ != nullptr) {
        UnhookWinEvent(static_cast<HWINEVENTHOOK>(hook_));
        hook_ = nullptr;
    }
    foregroundCallbackSlot() = nullptr;
#endif
}

}  // namespace pipela::core::win32
