#pragma once

#include <cstdint>

#include "dock/side_dock_layout.hpp"

class QWidget;

namespace pipela::app::dock {

// AGENT: Qt uses layout logical coords (Python parity); Win32 uses clamped physical rect.
bool applySideDockLayoutToWidget(QWidget* widget,
                                   const SideDockLayout& layout,
                                   std::intptr_t anchor_hwnd);

// Optional logical height cap (launcher debug panel) — still clamped to anchor client inner height.
bool applySideDockLayoutWithHeightCap(QWidget* widget,
                                      const SideDockLayout& layout,
                                      std::intptr_t anchor_hwnd,
                                      int max_inner_height_log);

}  // namespace pipela::app::dock
