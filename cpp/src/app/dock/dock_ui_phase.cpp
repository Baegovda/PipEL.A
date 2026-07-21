#include "dock/dock_ui_phase.hpp"

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::dock {

const char* uiDockPhaseString(UiDockPhase phase) {
    switch (phase) {
        case UiDockPhase::Client:
            return "client";
        case UiDockPhase::Launcher:
            return "launcher";
        case UiDockPhase::Standby:
        default:
            return "standby";
    }
}

UiDockPhase resolveUiDockPhase(std::intptr_t target_hwnd, std::intptr_t launcher_hwnd,
                                bool (*is_minimized)(std::intptr_t)) {
    auto minimized = [&](std::intptr_t hwnd) {
        if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
            return true;
        }
        if (is_minimized != nullptr) {
            return is_minimized(hwnd);
        }
        return false;
    };
    if (target_hwnd && !minimized(target_hwnd)) {
        return UiDockPhase::Client;
    }
    if (launcher_hwnd && !minimized(launcher_hwnd)) {
        return UiDockPhase::Launcher;
    }
    return UiDockPhase::Standby;
}

}  // namespace pipela::ui::dock
