#include "overlays/title_strip_geometry.hpp"

#include <algorithm>

#include "dock/side_dock_layout.hpp"
#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::overlays {

namespace {

constexpr int kMinTitleFramePx = 4;
constexpr int kFallbackBarH = 30;

int launcherStripTopBleedPhys(double scale) {
    // AGENT: Smart-updater title chrome can extend slightly above outer-top; pull strip up to mask bleed-through.
    if (scale <= 0.01) {
        scale = 1.0;
    }
    return std::max(12, static_cast<int>(std::lround(10.0 * scale)));
}

void applyLauncherStripVerticalMask(int& y_phys, int& h_phys, double scale) {
    const int bleed = launcherStripTopBleedPhys(scale);
    y_phys -= bleed;
    h_phys += bleed;
}

}  // namespace

TitleStripGeometry computeTitleStripGeometry(std::intptr_t anchor_hwnd,
                                             pipela::ui::dock::UiDockPhase phase,
                                             int kill_panel_right_phys,
                                             int control_outer_left_phys,
                                             int dock_w_log,
                                             double scale,
                                             bool launcher_debug_chrome) {
    TitleStripGeometry out;
    if (!anchor_hwnd || !pipela::core::win32::isWindow(anchor_hwnd)) {
        return out;
    }
    const auto gr = pipela::core::win32::getWindowOuterRectScreen(anchor_hwnd);
    const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd);
    const int ol = std::get<0>(gr);
    const int ot = std::get<1>(gr);
    (void)std::get<2>(gr);
    const int cl = std::get<0>(cr);
    const int ct = std::get<1>(cr);
    const int cr_r = std::get<2>(cr);
    if (cr_r <= cl || std::get<3>(cr) <= ct) {
        return out;
    }

    int bar_h = ct - ot;
    if (bar_h < kMinTitleFramePx) {
        bar_h = kFallbackBarH;
    }
    bar_h = std::max(8, bar_h);

    if (phase == pipela::ui::dock::UiDockPhase::Launcher && !launcher_debug_chrome) {
        const int w0 = std::max(8, cr_r - cl);
        out.x_phys = cl;
        out.y_phys = ot;
        out.w_phys = w0;
        out.h_phys = bar_h;
        applyLauncherStripVerticalMask(out.y_phys, out.h_phys, scale);
        out.valid = true;
        return out;
    }

    int left_x = ol;
    if (control_outer_left_phys > 0 && control_outer_left_phys < cr_r) {
        left_x = control_outer_left_phys;
    } else if (dock_w_log > 0 && scale > 0.0) {
        pipela::app::dock::AnchorClientRects rects;
        rects.client_left = cl;
        rects.client_top = ct;
        rects.client_right = cr_r;
        rects.client_bottom = std::get<3>(cr);
        rects.outer_left = ol;
        rects.outer_top = ot;
        rects.outer_right = std::get<2>(gr);
        rects.outer_bottom = std::get<3>(gr);
        if (auto lay = pipela::app::dock::computeSideDockLayoutLeft(
                anchor_hwnd, rects, dock_w_log, scale,
                pipela::app::dock::DockHeightPolicy::ClientOrOuterFallback)) {
            if (lay->x_phys > 0 && lay->x_phys < cr_r) {
                left_x = lay->x_phys;
            }
        }
    }

    int right_x = cr_r;
    if (kill_panel_right_phys > right_x) {
        right_x = kill_panel_right_phys;
    }
    const int w = std::max(8, right_x - left_x);
    if (w < 8 || bar_h < 8) {
        return out;
    }
    out.x_phys = left_x;
    out.y_phys = ot;
    out.w_phys = w;
    out.h_phys = bar_h;
    if (phase == pipela::ui::dock::UiDockPhase::Launcher) {
        applyLauncherStripVerticalMask(out.y_phys, out.h_phys, scale);
    }
    out.valid = true;
    return out;
}

}  // namespace pipela::ui::overlays
