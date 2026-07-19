#pragma once

#include <tuple>

namespace pipela::core::win32 {

struct SideDockLayout {
    int x_phys{0};
    int y_phys{0};
    int fw_phys{0};
    int fh_phys{0};
    double scale{1.0};
    int w_log{0};
    int h_log{0};
    int x_log{0};
    int y_log{0};
};

std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h);

bool chromeOuterRectPlausibleForLeftDock(int chrome_left,
                                         int chrome_top,
                                         int chrome_right,
                                         int chrome_bottom,
                                         int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int tol_phys = 36);

// AGENT: pure subset of pipela_qt.qt_side_dock.compute_side_dock_layout (right side).
SideDockLayout computeSideDockLayoutRight(int client_left,
                                          int client_top,
                                          int client_right,
                                          int client_bottom,
                                          int dock_w_log,
                                          double scale);

}  // namespace pipela::core::win32
