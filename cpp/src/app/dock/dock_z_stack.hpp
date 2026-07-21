#pragma once

#include <cstdint>

namespace pipela::ui::dock {

// AGENT: Per-chrome Z-order — game < overlay < chrome (qt_dock_z_stack.py).
void clearDockedChromeZStackState(std::intptr_t chrome_hwnd);

void syncDockedChromeZOrder(std::intptr_t chrome_hwnd,
                            std::intptr_t anchor_hwnd,
                            std::intptr_t overlay_hwnd,
                            bool set_owner,
                            bool force_z_restack = false);

// Convenience: stack control + optional overlay in one call (client phase tick).
void syncDockedChromeZOrder(std::intptr_t game_hwnd, std::intptr_t overlay_hwnd,
                            std::intptr_t chrome_hwnd);

void syncTitleStripAboveAnchor(std::intptr_t strip_hwnd, std::intptr_t anchor_hwnd,
                               bool set_owner);

}  // namespace pipela::ui::dock
