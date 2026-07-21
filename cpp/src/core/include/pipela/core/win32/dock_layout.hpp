#pragma once

// AGENT: Compatibility shim — dock layout moved to app layer (Phase 2). Remove with pybind (Phase 6).
#include "../../../../../app/dock/side_dock_layout.hpp"

namespace pipela::core::win32 {

using SideDockLayout = pipela::app::dock::SideDockLayout;

inline std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h) {
    return pipela::app::dock::clampDockLogicalGeometry(x, y, w, h);
}

inline bool chromeOuterRectPlausibleForLeftDock(int chrome_left,
                                                int chrome_top,
                                                int chrome_right,
                                                int chrome_bottom,
                                                int client_left,
                                                int client_top,
                                                int client_right,
                                                int client_bottom,
                                                int tol_phys = 36) {
    return pipela::app::dock::chromeOuterRectPlausibleForLeftDock(
        chrome_left, chrome_top, chrome_right, chrome_bottom, client_left, client_top, client_right,
        client_bottom, tol_phys);
}

inline SideDockLayout computeSideDockLayoutRight(int client_left,
                                                 int client_top,
                                                 int client_right,
                                                 int client_bottom,
                                                 int dock_w_log,
                                                 double scale) {
    return pipela::app::dock::computeSideDockLayoutRight(client_left, client_top, client_right,
                                                         client_bottom, dock_w_log, scale);
}

}  // namespace pipela::core::win32
