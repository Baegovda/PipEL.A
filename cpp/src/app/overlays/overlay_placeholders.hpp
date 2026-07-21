#pragma once

#include "dock/side_dock_layout.hpp"

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::overlays {

// AGENT: Thin wrappers over pipela_core C++ dock math (pipela_qt/qt_side_dock.py port).
inline std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h) {
    return pipela::app::dock::clampDockLogicalGeometry(x, y, w, h);
}

inline pipela::app::dock::SideDockLayout computeLeftDockLayout(std::intptr_t anchor_hwnd,
                                                                 int client_left,
                                                                 int client_top,
                                                                 int client_right,
                                                                 int client_bottom,
                                                                 int dock_w_log,
                                                                 double scale) {
    pipela::app::dock::AnchorClientRects rects;
    rects.client_left = client_left;
    rects.client_top = client_top;
    rects.client_right = client_right;
    rects.client_bottom = client_bottom;
    rects.outer_left = client_left;
    rects.outer_top = client_top;
    rects.outer_right = client_right;
    rects.outer_bottom = client_bottom;
    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        if (auto read = pipela::app::dock::readAnchorClientRects(anchor_hwnd)) {
            rects = *read;
        }
    }
    if (auto lay = pipela::app::dock::computeSideDockLayoutLeft(
            anchor_hwnd, rects, dock_w_log, scale,
            pipela::app::dock::DockHeightPolicy::ClientOrOuterFallback)) {
        return *lay;
    }
    return {};
}

inline pipela::app::dock::SideDockLayout computeRightDockLayout(std::intptr_t anchor_hwnd,
                                                                  int client_left,
                                                                  int client_top,
                                                                  int client_right,
                                                                  int client_bottom,
                                                                  int dock_w_log,
                                                                  double scale) {
    pipela::app::dock::AnchorClientRects rects;
    rects.client_left = client_left;
    rects.client_top = client_top;
    rects.client_right = client_right;
    rects.client_bottom = client_bottom;
    rects.outer_left = client_left;
    rects.outer_top = client_top;
    rects.outer_right = client_right;
    rects.outer_bottom = client_bottom;
    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        if (auto read = pipela::app::dock::readAnchorClientRects(anchor_hwnd)) {
            rects = *read;
        }
    }
    if (auto lay = pipela::app::dock::computeSideDockLayoutRight(
            anchor_hwnd, rects, dock_w_log, scale,
            pipela::app::dock::DockHeightPolicy::ClientInnerOnly)) {
        return *lay;
    }
    return {};
}

struct DockOverlayPlaceholder {
    bool visible{false};
    pipela::app::dock::SideDockLayout last_layout{};
};

struct TitleStripPlaceholder {
    bool visible{false};
    int strip_right_phys{0};
};

struct KillCounterFloaterPlaceholder {
    bool visible{false};
    pipela::app::dock::SideDockLayout dock_layout{};
};

void syncDockChromeFromGameClient(DockOverlayPlaceholder& dock,
                                  TitleStripPlaceholder& strip,
                                  KillCounterFloaterPlaceholder& kill,
                                  std::intptr_t anchor_hwnd,
                                  int client_left,
                                  int client_top,
                                  int client_right,
                                  int client_bottom,
                                  int dock_w_log,
                                  double scale,
                                  bool kill_panel_visible,
                                  int panel_height_log_override = 0);

}  // namespace pipela::ui::overlays
