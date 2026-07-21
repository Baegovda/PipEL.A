#pragma once

#include <cstdint>

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::dock {

// AGENT: qt_dock_anchor.py — game-first, then launcher; KC game-only.
std::intptr_t resolveDockAnchorFromSession(std::intptr_t target_hwnd,
                                           std::intptr_t launcher_hwnd);

std::intptr_t resolveDockAnchorHwnd(std::intptr_t& cached_target,
                                    std::intptr_t& cached_launcher);

std::intptr_t resolveGameOnlyAnchorHwnd(std::intptr_t& cached_target);

}  // namespace pipela::ui::dock
