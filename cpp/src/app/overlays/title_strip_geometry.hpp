#pragma once

#include <cstdint>

#include "dock/dock_ui_phase.hpp"

namespace pipela::ui::overlays {

struct TitleStripGeometry {
    int x_phys{0};
    int y_phys{0};
    int w_phys{0};
    int h_phys{0};
    bool valid{false};
};

// AGENT: Python `game_title_bar_overlay._compute_strip_geometry` MVP subset.
TitleStripGeometry computeTitleStripGeometry(std::intptr_t anchor_hwnd,
                                             pipela::ui::dock::UiDockPhase phase,
                                             int kill_panel_right_phys,
                                             int control_outer_left_phys,
                                             int dock_w_log,
                                             double scale,
                                             bool launcher_debug_chrome = false);

}  // namespace pipela::ui::overlays
