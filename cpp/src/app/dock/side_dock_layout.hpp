#pragma once

#include <algorithm>
#include <cstdint>
#include <optional>
#include <tuple>

namespace pipela::app::dock {

enum class SideDockSide { Left, Right };

enum class DockHeightPolicy {
    // AGENT: Kill counter — never use outer-window height when client rect is bad.
    ClientInnerOnly,
    // Control panel — legacy fallback to outer height if client rect transiently invalid.
    ClientOrOuterFallback,
};

struct AnchorClientRects {
    int client_left{0};
    int client_top{0};
    int client_right{0};
    int client_bottom{0};
    int outer_left{0};
    int outer_top{0};
    int outer_right{0};
    int outer_bottom{0};

    bool clientValid() const {
        return client_right > client_left && client_bottom > client_top;
    }

    int clientInnerHeightPhys() const {
        return clientValid() ? std::max(8, client_bottom - client_top) : 0;
    }
};

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
    std::uint64_t dedupe_sig{0};

    bool valid() const { return fw_phys >= 8 && fh_phys >= 8 && w_log >= 8 && h_log >= 8; }
};

std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h);

// AGENT: Pin dock outer rect to anchor client inner — returns {y_phys, fh_phys}.
std::pair<int, int> clampToClientInnerPhys(int y_phys, int fh_phys, const AnchorClientRects& rects);

bool chromeOuterRectPlausibleForLeftDock(int chrome_left,
                                         int chrome_top,
                                         int chrome_right,
                                         int chrome_bottom,
                                         int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int tol_phys = 36);

std::optional<AnchorClientRects> readAnchorClientRects(std::intptr_t anchor_hwnd);

std::optional<int> anchorClientInnerHeightLogical(std::intptr_t anchor_hwnd, double scale);

std::optional<int> computeDockPairFillWLog(std::intptr_t anchor_hwnd, double scale);

std::uint64_t sideDockDedupeSig(int snap,
                                int ol,
                                int ot,
                                int o_right,
                                int ob,
                                int x_phys,
                                int y_phys,
                                int fw_phys,
                                int fh_phys,
                                bool right_side);

std::optional<SideDockLayout> computeSideDockLayoutLeft(std::intptr_t anchor_hwnd,
                                                        const AnchorClientRects& rects,
                                                        int dock_w_log,
                                                        double scale,
                                                        DockHeightPolicy height_policy);

std::optional<SideDockLayout> computeSideDockLayoutRight(std::intptr_t anchor_hwnd,
                                                         const AnchorClientRects& rects,
                                                         int dock_w_log,
                                                         double scale,
                                                         DockHeightPolicy height_policy);

// Legacy wrappers (no outer rect / anchor snap).
SideDockLayout computeSideDockLayoutLeft(int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int dock_w_log,
                                         double scale);

SideDockLayout computeSideDockLayoutRight(int client_left,
                                          int client_top,
                                          int client_right,
                                          int client_bottom,
                                          int dock_w_log,
                                          double scale);

}  // namespace pipela::app::dock
