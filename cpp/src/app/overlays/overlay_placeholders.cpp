#include "overlay_placeholders.hpp"

#include <algorithm>
#include <cmath>

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::overlays {

namespace {

void applyPanelHeightOverride(pipela::app::dock::SideDockLayout& lay,
                              int h_log,
                              int snap,
                              int ol,
                              int ot,
                              int o_right,
                              int ob,
                              bool right_side) {
    if (h_log <= 0) {
        return;
    }
    lay.h_log = std::max(8, h_log);
    lay.fh_phys = std::max(8, static_cast<int>(std::lround(lay.h_log * lay.scale)));
    lay.dedupe_sig = pipela::app::dock::sideDockDedupeSig(
        snap, ol, ot, o_right, ob, lay.x_phys, lay.y_phys, lay.fw_phys, lay.fh_phys, right_side);
}

}  // namespace

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
                                  int panel_height_log_override) {
    pipela::app::dock::AnchorClientRects rects;
    if (auto read = pipela::app::dock::readAnchorClientRects(anchor_hwnd)) {
        rects = *read;
    } else {
        rects.client_left = client_left;
        rects.client_top = client_top;
        rects.client_right = client_right;
        rects.client_bottom = client_bottom;
        rects.outer_left = client_left;
        rects.outer_top = client_top;
        rects.outer_right = client_right;
        rects.outer_bottom = client_bottom;
        if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
            const auto gr = pipela::core::win32::getWindowOuterRectScreen(anchor_hwnd);
            rects.outer_left = std::get<0>(gr);
            rects.outer_top = std::get<1>(gr);
            rects.outer_right = std::get<2>(gr);
            rects.outer_bottom = std::get<3>(gr);
        }
    }

    const int ol = rects.outer_left;
    const int ot = rects.outer_top;
    const int o_right = rects.outer_right;
    const int ob = rects.outer_bottom;

    if (auto ctrl = pipela::app::dock::computeSideDockLayoutLeft(
            anchor_hwnd, rects, dock_w_log, scale,
            pipela::app::dock::DockHeightPolicy::ClientOrOuterFallback)) {
        dock.last_layout = *ctrl;
    } else {
        dock.last_layout = {};
    }

    if (auto klay = pipela::app::dock::computeSideDockLayoutRight(
            anchor_hwnd, rects, dock_w_log, scale,
            pipela::app::dock::DockHeightPolicy::ClientInnerOnly)) {
        kill.dock_layout = *klay;
    } else {
        kill.dock_layout = {};
    }

    if (panel_height_log_override > 0) {
        const int snap_l = rects.clientValid() ? rects.client_left : ol;
        const int snap_r = rects.clientValid() ? rects.client_right : o_right;
        applyPanelHeightOverride(dock.last_layout, panel_height_log_override, snap_l, ol, ot, o_right,
                                 ob, false);
        int kc_h = panel_height_log_override;
        if (auto client_h = pipela::app::dock::anchorClientInnerHeightLogical(anchor_hwnd, scale)) {
            kc_h = std::min(kc_h, *client_h);
        }
        applyPanelHeightOverride(kill.dock_layout, kc_h, snap_r, ol, ot, o_right, ob, true);
    }

    strip.strip_right_phys = rects.clientValid() ? rects.client_right : o_right;
    if (kill_panel_visible && kill.dock_layout.valid()) {
        strip.strip_right_phys =
            std::max(strip.strip_right_phys, kill.dock_layout.x_phys + kill.dock_layout.fw_phys);
    }
    dock.visible = dock.last_layout.valid();
    strip.visible = true;
    kill.visible = kill_panel_visible && kill.dock_layout.valid();
}

}  // namespace pipela::ui::overlays
