#include "pipela/core/win32/dock_layout.hpp"

#include <algorithm>
#include <cmath>

namespace pipela::core::win32 {

std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h) {
    w = std::clamp(w, 8, 8192);
    h = std::clamp(h, 8, 16384);
    x = std::clamp(x, -65535, 65535);
    y = std::clamp(y, -65535, 65535);
    return {x, y, w, h};
}

bool chromeOuterRectPlausibleForLeftDock(int chrome_left,
                                         int chrome_top,
                                         int chrome_right,
                                         int chrome_bottom,
                                         int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int tol_phys) {
    (void)chrome_left;
    (void)chrome_top;
    (void)chrome_bottom;
    (void)client_top;
    (void)client_right;
    (void)client_bottom;
    return std::abs(chrome_right - client_left) <= tol_phys;
}

SideDockLayout computeSideDockLayoutRight(int client_left,
                                          int client_top,
                                          int client_right,
                                          int client_bottom,
                                          int dock_w_log,
                                          double scale) {
    SideDockLayout out;
    if (scale <= 0.01) {
        scale = 1.0;
    }
    dock_w_log = std::max(8, dock_w_log);
    const int fh_phys = std::max(8, client_bottom - client_top);
    const int fw_phys = std::max(8, static_cast<int>(std::lround(dock_w_log * scale)));
    const int x_phys = client_right;
    const int y_phys = client_top;
    out.x_phys = x_phys;
    out.y_phys = y_phys;
    out.fw_phys = fw_phys;
    out.fh_phys = fh_phys;
    out.scale = scale;
    out.w_log = dock_w_log;
    out.h_log = std::max(8, static_cast<int>(std::lround(fh_phys / scale)));
    out.x_log = static_cast<int>(std::lround(x_phys / scale));
    out.y_log = static_cast<int>(std::lround(y_phys / scale));
    return out;
}

}  // namespace pipela::core::win32
