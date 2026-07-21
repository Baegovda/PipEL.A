#include "dock/dock_anchor.hpp"

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::dock {

std::intptr_t resolveDockAnchorFromSession(std::intptr_t target_hwnd,
                                           std::intptr_t launcher_hwnd) {
    if (target_hwnd && pipela::core::win32::isWindow(target_hwnd) &&
        !pipela::core::win32::isWindowMinimized(target_hwnd)) {
        return target_hwnd;
    }
    if (launcher_hwnd && pipela::core::win32::isWindow(launcher_hwnd) &&
        !pipela::core::win32::isWindowMinimized(launcher_hwnd)) {
        return launcher_hwnd;
    }
    return 0;
}

std::intptr_t resolveDockAnchorHwnd(std::intptr_t& cached_target,
                                    std::intptr_t& cached_launcher) {
    cached_target = pipela::core::win32::refreshEternalcityHwndCached(cached_target);
    if (cached_target && pipela::core::win32::isWindow(cached_target) &&
        !pipela::core::win32::isWindowMinimized(cached_target)) {
        return cached_target;
    }
    cached_launcher = pipela::core::win32::refreshSmartUpdaterHwndCached(cached_launcher);
    if (cached_launcher && pipela::core::win32::isWindow(cached_launcher) &&
        !pipela::core::win32::isWindowMinimized(cached_launcher)) {
        return cached_launcher;
    }
    return 0;
}

std::intptr_t resolveGameOnlyAnchorHwnd(std::intptr_t& cached_target) {
    cached_target = pipela::core::win32::refreshEternalcityHwndCached(cached_target);
    if (cached_target && pipela::core::win32::isWindow(cached_target) &&
        !pipela::core::win32::isWindowMinimized(cached_target)) {
        return cached_target;
    }
    return 0;
}

}  // namespace pipela::ui::dock
