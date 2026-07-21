#include "dock/dock_z_stack.hpp"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <cstdint>
#include <map>
#include <tuple>
#include <utility>

#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"

namespace pipela::ui::dock {

namespace {

using ZStackKey = std::tuple<std::intptr_t, std::intptr_t, std::intptr_t>;

std::map<std::intptr_t, ZStackKey>& zStackLastKey() {
    static std::map<std::intptr_t, ZStackKey> cache;
    return cache;
}

}  // namespace

void clearDockedChromeZStackState(std::intptr_t chrome_hwnd) {
    if (chrome_hwnd == 0) {
        return;
    }
    zStackLastKey().erase(chrome_hwnd);
}

void syncDockedChromeZOrder(std::intptr_t chrome_hwnd,
                            std::intptr_t anchor_hwnd,
                            std::intptr_t overlay_hwnd,
                            bool set_owner,
                            bool force_z_restack) {
    if (!chrome_hwnd || !anchor_hwnd) {
        return;
    }
    if (!pipela::core::win32::isWindow(chrome_hwnd) ||
        !pipela::core::win32::isWindow(anchor_hwnd)) {
        return;
    }
    if (set_owner) {
        pipela::core::win32::setWindowOwner(chrome_hwnd, anchor_hwnd);
    }
    pipela::core::win32::setWindowTopmost(chrome_hwnd, false);

    const std::intptr_t ov = (overlay_hwnd && pipela::core::win32::isWindow(overlay_hwnd))
                                 ? overlay_hwnd
                                 : 0;
    const ZStackKey key{anchor_hwnd, chrome_hwnd, ov};
    if (!force_z_restack) {
        const auto it = zStackLastKey().find(chrome_hwnd);
        if (it != zStackLastKey().end() && it->second == key) {
            return;
        }
    }

    if (ov != 0) {
        pipela::core::win32::setWindowZOrderDirectlyAbove(ov, anchor_hwnd, force_z_restack);
        pipela::core::win32::setWindowZOrderDirectlyAbove(chrome_hwnd, ov, force_z_restack);
    } else {
        pipela::core::win32::setWindowZOrderDirectlyAbove(chrome_hwnd, anchor_hwnd,
                                                            force_z_restack);
    }
    zStackLastKey()[chrome_hwnd] = key;
}

void syncDockedChromeZOrder(std::intptr_t game_hwnd, std::intptr_t overlay_hwnd,
                            std::intptr_t chrome_hwnd) {
    if (!game_hwnd || !chrome_hwnd) {
        return;
    }
    syncDockedChromeZOrder(chrome_hwnd, game_hwnd, overlay_hwnd, false, false);
}

void syncTitleStripAboveAnchor(std::intptr_t strip_hwnd, std::intptr_t anchor_hwnd,
                               bool set_owner) {
    syncDockedChromeZOrder(strip_hwnd, anchor_hwnd, 0, set_owner, false);
}

}  // namespace pipela::ui::dock
